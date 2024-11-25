"""Evaluation tooling for Vertex Conversation DataStores native service."""

# Copyright 2024 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import dataclasses
import io
import itertools
import json
import math
import os
import re
from datetime import datetime, timezone
from typing import Union

import matplotlib.pyplot as plt
import pandas as pd
import plotly.graph_objects as go
from google.cloud import bigquery
from googleapiclient.discovery import build
from googleapiclient.http import MediaInMemoryUpload, MediaIoBaseDownload
from tqdm import tqdm

from dfcx_scrapi.core.scrapi_base import ScrapiBase
from dfcx_scrapi.tools.agent_response import AgentResponse
from dfcx_scrapi.tools.metrics import build_metrics

_FOLDER_ID = re.compile(r"folders\/(.*?)(?=\/|\?|$)")
EVAL_RESULTS_COLS = [
            "answer_generator_llm_rendered_prompt",
            "search_results"
            ]

class DataStoreEvaluator(ScrapiBase):
    def __init__(self, metrics: list[str], model: str = "text-bison@002"):
       self.model = self.model_setup(model)
       self.metrics = build_metrics(metrics, generation_model=self.model)

    def run(self, scraper_output: pd.DataFrame) -> "EvaluationResult":
        timestamp = datetime.now(tz=timezone.utc)
        scraper_output = scraper_output.copy(deep=True)
        result = pd.DataFrame(index=scraper_output.index)

        for metric in self.metrics:
           result = pd.concat([result, metric.run(scraper_output)], axis=1)

        # adding timestamp and agent display name so they can be used as a multi
        # index
        result["evaluation_timestamp"] = timestamp.isoformat()

        return EvaluationResult(scraper_output, result)


@dataclasses.dataclass
class EvaluationResult:
    scrape_outputs: pd.DataFrame = None
    metric_outputs: pd.DataFrame = None

    @property
    def timestamp(self) -> str:
        return self.metric_outputs["evaluation_timestamp"].iloc[0]

    @staticmethod
    def truncate(df, column):
        truncated_fix = "<TRUNCATED: Google Sheet 50k character limit>"
        def _truncate(value):
            if len(value) < 50_000:
                return value
            else:
                return value[:50_000 - len(truncated_fix)] + truncated_fix
        df[column] = df[column].apply(_truncate)

    @staticmethod
    def find_folder(folder_name, drive_service) -> Union[tuple[str, str], None]:
        """Finds a folder by name in Google Drive."""
        query = (
            f"name = '{folder_name}' and "
            f"mimeType = 'application/vnd.google-apps.folder' and "
            f"trashed = false"
        )
        fields = "nextPageToken, files(id, name, webViewLink)"
        list_request = drive_service.files().list(q=query, fields=fields)
        result = list_request.execute()
        folders = result.get("files", [])
        if not folders:
            return None

        return folders[0].get("id"), folders[0].get("webViewLink")

    @staticmethod
    def create_folder(
        folder_name, drive_service
        ) -> tuple[Union[str, None], Union[str, None]]:
        """Creates a folder in Google Drive."""
        create_request = drive_service.files().create(
            body={
                "name": folder_name,
                "mimeType": "application/vnd.google-apps.folder"
            },
            fields="id, webViewLink"
        )
        result = create_request.execute()

        return result.get("id"), result.get("webViewLink")

    @staticmethod
    def create_json(
            content, file_name, parent, drive_service
            ) -> tuple[Union[str, None], Union[str, None]]:
        """Creates a .json file in the specified Google Drive folder."""
        request = drive_service.files().create(
            body={"name": file_name, "parents": [parent]},
            media_body=MediaInMemoryUpload(
                json.dumps(content, indent=4).encode("utf-8"),
                mimetype="text/plain",
            ),
            fields="id, webViewLink",
        )
        result = request.execute()

        return result.get("id"), result.get("webViewLink")

    @staticmethod
    def create_chunks(iterable, chunk_size):
        for chunk in itertools.zip_longest(*([iter(iterable)] * chunk_size)):
            yield [element for element in chunk if element is not None]

    @staticmethod
    def delete_worksheet(sheet_id, worksheet_id, sheets_service):
        """Deletes a worksheet."""
        sheets_service.spreadsheets().batchUpdate(
            spreadsheetId=sheet_id,
            body={"requests": [{"deleteSheet": {"sheetId": worksheet_id}}]},
        ).execute()

    @staticmethod
    def get_bigquery_types(df):
        "Maps DataFrame data types to BigQuery data types."
        types = []
        data_type_mapping = {
            'object': 'STRING',
            'int64': 'INTEGER',
            'float64': 'FLOAT',
            'bool': 'BOOLEAN',
            'datetime64[ns]': 'TIMESTAMP'  # Assuming nanosecond timestamps
            }
        for dtype in df.dtypes:
            if dtype in data_type_mapping:
                types.append(data_type_mapping[dtype])
            else:
                # Handle other data types (error handling or placeholder)
                types.append('STRING')  # Placeholder, adjust as needed
                print(f"Warning: Unhandled data type: {dtype}")

        return types

    @staticmethod
    def sanitize_column_names(df):
        "Sanitizes column names replacing special characters with underscores."
        sanitized_names = []
        for col in df.columns:
            # Replace special characters with underscores
            sanitized_name = re.sub(r"[^\w\s]", "_", col)
            sanitized_names.append(sanitized_name)

        return df.rename(columns=dict(zip(df.columns, sanitized_names)))

    @staticmethod
    def list_folder(folder_id, drive_service) -> list[tuple[str, str]]:
        query = f"'{folder_id}' in parents and trashed = false"
        list_request = drive_service.files().list(
            q=query, fields="nextPageToken, files(id, name)"
        )
        result = list_request.execute()
        items = result.get("files", [])
        return [(item["id"], item["name"]) for item in items]

    @staticmethod
    def download_json(file_id, drive_service):
        request = drive_service.files().get_media(fileId=file_id)
        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while not done:
            _, done = downloader.next_chunk()

        fh.seek(0)

        return json.loads(fh.read().decode('utf-8'))

    def load(self, folder_url, credentials):
        folder_id_match = _FOLDER_ID.search(folder_url)
        if not folder_id_match:
            raise ValueError()

        folder_id = folder_id_match.group(1)
        drive_service = build("drive", "v3", credentials=credentials)

        file_id = self.find_file_in_folder(
            folder_id, "results.json", drive_service)
        json_content = self.download_json(file_id, drive_service)

        queryset = pd.DataFrame.from_dict(
            json_content["queryset"], orient="index")
        responses = pd.DataFrame.from_dict(
            json_content["responses"], orient="index"
        )

        ar = AgentResponse()
        queryset["query_result"] = responses.apply(
            ar.from_row, axis=1
        )
        self.scrape_outputs = queryset

        self.metric_outputs = pd.DataFrame.from_dict(
            json_content["metrics"], orient="index"
        )

    def aggregate(self, columns: list[str] = None):
        if not columns:
            columns = self.metric_outputs.columns
        shared_columns = self.metric_outputs.columns.intersection(set(columns))
        result = pd.DataFrame(self.metric_outputs[shared_columns])
        result["name"] = self.scrape_outputs["agent_display_name"]
        result["evaluation_timestamp"] = (
            self.metric_outputs["evaluation_timestamp"]
        )
        result = result.set_index(["name", "evaluation_timestamp"])

        return result.groupby(level=[0, 1]).mean(numeric_only=True)

    def export(self, folder_name: str, chunk_size: int, credentials):
        drive_service = build("drive", "v3", credentials=credentials)
        folder = self.find_folder(folder_name, drive_service)
        if folder:
            folder_id, folder_url = folder
        else:
            folder_id, folder_url = self.create_folder(
                folder_name, drive_service
                )

        queryset = self.scrape_outputs.drop("query_result", axis=1)
        responses = self.scrape_outputs["query_result"].apply(
            lambda x: x.to_row()
            )
        responses = pd.DataFrame(responses.to_list(), index=queryset.index)

        json_content = {
            "queryset": queryset.to_dict(orient="index"),
            "responses": responses.to_dict(orient="index"),
            "metrics": self.metric_outputs.to_dict(orient="index"),
        }
        json_id, json_url = self.create_json(
            json_content, "results.json", folder_id, drive_service
        )

        for column in EVAL_RESULTS_COLS:
            self.truncate(responses, column)

        results = pd.concat([queryset, responses, self.metric_outputs], axis=1)
        worksheets = {
            "summary": self.aggregate().fillna("#N/A"),
            "results": results.fillna("#N/A")
        }
        sheets_service = build("sheets", "v4", credentials=credentials)
        self.create_sheet(
            worksheets=worksheets,
            title="results",
            parent=folder_id,
            chunk_size=chunk_size,
            sheets_service=sheets_service,
            drive_service=drive_service,
        )
        return folder_url

    def export_to_csv(self, file_name: str):
        queryset = self.scrape_outputs.drop("query_result", axis=1)
        responses = self.scrape_outputs["query_result"].apply(
            lambda x: x.to_row())
        responses = pd.DataFrame(responses.to_list(), index=queryset.index)

        for column in EVAL_RESULTS_COLS:
            self.truncate(responses, column)

        results = pd.concat([queryset, responses, self.metric_outputs], axis=1)
        temp_dir = "/tmp/evaluation_results"
        os.makedirs(temp_dir, exist_ok=True)
        filepath = os.path.join(temp_dir, file_name)
        results.to_csv(filepath, index=False)

        return filepath

    def display_on_screen(self):
        queryset = self.scrape_outputs.drop("query_result", axis=1)
        responses = self.scrape_outputs["query_result"].apply(
            lambda x: x.to_row())
        responses = pd.DataFrame(responses.to_list(), index=queryset.index)

        for column in EVAL_RESULTS_COLS:
            self.truncate(responses, column)

        results = pd.concat([queryset, responses, self.metric_outputs], axis=1)

        return results

    def export_to_bigquery(
            self,
            eval_results,
            project_id: str,
            dataset_id: str,
            table_name: str,
            credentials
            ):
        data=eval_results.scrape_outputs["query_result"].apply(
            lambda x: x.to_row())
        data = pd.DataFrame(data.to_list(),eval_results.scrape_outputs.index)
        eval_results.scrape_outputs["query_result"] = None
        df = pd.concat(
            [
                data,
                eval_results.scrape_outputs,
                eval_results.metric_outputs
                ],
                axis=1)

        df = EvaluationResult.sanitize_column_names(df)
        client = bigquery.Client(project=project_id, credentials=credentials)

        try:
            df['conversation_id'] = df['conversation_id'].astype(str)
            df['latency'] = df['latency'].astype(str)
            df['expected_uri'] = df['expected_uri'].astype(str)
            df['answerable'] = df['answerable'].astype(str)
            df['golden_snippet'] = df['golden_snippet'].astype(str)

            df = df.drop('query_result', axis=1)
            df = df.drop('golden_snippet', axis=1)
            df = df.drop('answerable', axis=1)

            load_job = client.load_table_from_dataframe(df, '.'.join(
                [project_id, dataset_id, table_name]))

            return load_job.result()
        except Exception as e:
            print(f"Error exporting data: {e}")
            return None  # Indicate failure

    def find_file_in_folder(
            self,
            folder_id,
            name,
            drive_service
            ) -> Union[str, None]:
        for file_id, file_name in self.list_folder(folder_id, drive_service):
            if file_name == name:
                return file_id
        return None

    def add_worksheet(
            self, sheet_id, content, title, sheets_service, chunk_size) -> None:
        """Adds a worksheet to an existing spreadsheet."""
        sheets_service.spreadsheets().batchUpdate(
            spreadsheetId=sheet_id,
            body={"requests": [{"addSheet": {"properties": {"title": title}}}]},
        ).execute()

        for chunk in tqdm(
            self.create_chunks(content, chunk_size),
            total=math.ceil(len(content) / chunk_size),
            desc=f"Creating worksheet: {title}",
            ):
            sheets_service.spreadsheets().values().append(
                spreadsheetId=sheet_id,
                range=f"'{title}'!A1",
                valueInputOption="RAW",
                body={"values": chunk},
            ).execute()

    def create_sheet(
            self, worksheets, title, parent, chunk_size, sheets_service,
            drive_service) -> Union[str, None]:
        """Creates a new spreadsheet with worksheets."""
        body = {"properties": {"title": title}}
        create_request = sheets_service.spreadsheets().create(
            body=body, fields="spreadsheetId"
        )
        create_result = create_request.execute()
        sheet_id = create_result.get("spreadsheetId")

        parents_request = drive_service.files().get(
            fileId=sheet_id, fields="parents")
        parents_result = parents_request.execute()
        parents = parents_result.get("parents")
        previous_parents = ",".join(parents) if parents else None

        if not sheet_id:
            return

        for worksheet_title, content in worksheets.items():
            content_dict = content.to_dict(orient="split")
            self.add_worksheet(
                sheet_id=sheet_id,
                content=[content_dict["columns"]] + content_dict["data"],
                title=worksheet_title,
                sheets_service=sheets_service,
                chunk_size=chunk_size,
            )

        all_request = sheets_service.spreadsheets().get(spreadsheetId=sheet_id)
        all_result = all_request.execute()
        default_sheet_id = all_result["sheets"][0]["properties"]["sheetId"]

        self.delete_worksheet(sheet_id, default_sheet_id, sheets_service)
        _ = drive_service.files().update(
            fileId=sheet_id,
            addParents=parent,
            removeParents=previous_parents,
            fields="id, parents"
            ).execute()

        return f"https://docs.google.com/spreadsheets/d/{sheet_id}/edit"


@dataclasses.dataclass
class EvaluationVisualizer:
  evaluation_results: list[EvaluationResult]

  def radar_plot(self, columns: Union[list[str], None] = None):
    fig = go.Figure()
    summaries = pd.concat(
        [result.aggregate(columns) for result in self.evaluation_results]
    )
    summaries = summaries.to_dict(orient="split")

    for idx, values in enumerate(summaries["data"]):
      fig.add_trace(
          go.Scatterpolar(
              r=values,
              theta=summaries["columns"],
              fill='toself',
              name="_".join(summaries["index"][idx]),
          )
      )
    fig.update_layout(
        polar={"radialaxis": {"visible": True, "range": [0, 1]}},
        showlegend=True
    )
    fig.show()

  def count_barplot(self, column_name: str):
    results = []
    for result in self.evaluation_results:
      responses = result.scrape_outputs["query_result"].apply(
          lambda x: x.to_row())
      responses = pd.DataFrame(
          responses.to_list(), index=result.scrape_outputs.index
      )
      results.append(
          pd.concat(
              [result.scrape_outputs, responses, result.metric_outputs],
              axis=1
          )
      )
    results = pd.concat(results)
    results = results.set_index(["agent_display_name", "evaluation_timestamp"])
    grouped_counts = (
        results[column_name]
        .groupby(level=["agent_display_name", "evaluation_timestamp"])
        .value_counts()
        .unstack(fill_value=0)
    )
    grouped_counts.plot(kind="bar")
    plt.xlabel("Name")
    plt.ylabel("Count")
    plt.xticks(rotation=15)
    plt.title(f"{column_name} counts by name")
    plt.legend(title=column_name)
    plt.show()

  def mean_barplot(self, column_names: list[str]):
    results = []
    for result in self.evaluation_results:
      results.append(
          pd.concat([result.scrape_outputs, result.metric_outputs], axis=1)
      )
    results = pd.concat(results)
    results = results.set_index(["agent_display_name", "evaluation_timestamp"])
    grouped_means = (
        results[column_names]
        .groupby(level=["agent_display_name", "evaluation_timestamp"])
        .mean()
    )
    grouped_means.plot(kind="bar")
    plt.ylim(top=1.0)
    plt.xlabel("Name")
    plt.ylabel("Mean")
    plt.xticks(rotation=15)
    plt.title("mean by name")
    plt.show()
