"""Utility file for NLU Utterance Similarity to work with CX resources."""

# Copyright 2023 Google LLC
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

import sys
import numpy as np
import pandas as pd
import scann
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from typing import Dict, Set

import tensorflow_hub

from dfcx_scrapi.core import flows
from dfcx_scrapi.core import intents
from dfcx_scrapi.core import pages
from dfcx_scrapi.core import scrapi_base
from dfcx_scrapi.core import transition_route_groups

if "google.colab" in sys.modules:
    from google.colab import data_table
    data_table.enable_dataframe_formatter()

SHEETS_SCOPE = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive",
]


class KonaEmbeddingModel:
    """Download USE4 model and prep for calculating embeddings."""
    def __init__(self):
        module_url = "https://tfhub.dev/google/universal-sentence-encoder/4"
        self.model = tensorflow_hub.load(module_url)

    def embed(self, utterances, batch_size=512):
        """Generates embeddings for a given set of utterances."""
        embeddings = []
        for next_idx in range(0, len(utterances), batch_size):
            batch_utterances = utterances[next_idx: next_idx + batch_size]
            batch_embeddings = self.model(batch_utterances).numpy()
            embeddings.append(batch_embeddings)
        embeddings = np.vstack(embeddings)

        return embeddings

class SheetsLoader:
    """Load data from Google Sheets."""
    def __init__(self, creds_path: str = None):
        sheets_creds = ServiceAccountCredentials.from_json_keyfile_name(
            filename=creds_path,
            scopes=SHEETS_SCOPE,
        )
        self.sheets_client = gspread.authorize(sheets_creds)

    def load_column_from_sheet(self, sheet_name, worksheet_name, column_name):
        """Load a column from a Google Sheets file"""
        try:
            sheet = self.sheets_client.open(sheet_name)
        except gspread.SpreadsheetNotFound as gse:
            raise KeyError(
                f"Couldn't find sheet '{sheet_name}'."
                "Did you share it with your service account?"
            ) from gse

        worksheet = sheet.worksheet(worksheet_name)
        worksheet_data = pd.DataFrame(worksheet.get_all_records())
        try:
            column_data = worksheet_data[column_name]
        except KeyError as err:
            raise KeyError(f"Couldn't find column '{column_name}'") from err

        return column_data.to_numpy()


class NaturalLanguageUnderstandingUtil(scrapi_base.ScrapiBase):
    """Class to generate and analyze embeddings for a page."""

    def __init__(
        self,
        agent_id: str,
        flow_display_name: str,
        page_display_name: str,
        creds_path: str = None,
        creds_dict: Dict[str, str] = None,
        creds=None,
    ):
        super().__init__(
            creds_path=creds_path,
            creds_dict=creds_dict,
            creds=creds,
        )

        print("Loading training data...")
        self._load_data(agent_id, flow_display_name, page_display_name)

        print("Loading embedder...")
        self.embedder = KonaEmbeddingModel()

        print("Generating embeddings for training data...")
        (
            self.training_intents,
            self.training_phrases,
        ) = self._get_training_phrases()
        self.training_embeddings = self.generate_embeddings(
            self.training_phrases
        )

        print("Loading ScaNN searcher...")
        self.searcher = self._build_searcher(self.training_embeddings)

    def _load_data(
        self, agent_id: str, flow_display_name: str, page_display_name: str
    ):
        flow_loader = flows.Flows(creds=self.creds)
        self.flow = flow_loader.get_flow_by_display_name(
            flow_display_name, agent_id
        )

        trg_loader = transition_route_groups.TransitionRouteGroups(
            creds=self.creds
        )
        agent_trgs = trg_loader.list_transition_route_groups(agent_id)
        self.trgs = (
            agent_trgs + trg_loader.list_transition_route_groups(self.flow.name)
        )
        self.name_to_trg = {i.name: i for i in self.trgs}

        if page_display_name != "Start Page":
            page_loader = pages.Pages(creds=self.creds)
            page_map = page_loader.get_pages_map(self.flow.name, reverse=True)
            page_id = page_map.get(page_display_name, None)
            if page_id is None:
                raise ValueError(
                    f'Page "{page_display_name}" does not exist in the '
                    "specified agent."
                )
            self.page = page_loader.get_page(page_id)

        intent_names = self._list_page_intents()
        all_intents = intents.Intents(creds=self.creds).list_intents(agent_id)
        self.intents = list(
            filter(lambda x: x.name in intent_names, all_intents)
        )

    def _list_page_intents(self) -> Set[str]:
        """Lists all intents in-scope at the given page."""
        # See the public doc:
        # https://cloud.google.com/dialogflow/cx/docs/concept/handler#eval
        relevant_intents = set()
        relevant_trgs = set(self.flow.transition_route_groups)
        for tr in self.flow.transition_routes:
            if tr.intent:
                relevant_intents.add(tr.intent)
        if hasattr(self, "page"):
            relevant_trgs |= set(self.page.transition_route_groups)
            for tr in self.page.transition_routes:
                if tr.intent:
                    relevant_intents.add(tr.intent)
        for trg_name in relevant_trgs:
            trg = self.name_to_trg[trg_name]
            for tr in trg.transition_routes:
                if tr.intent:
                    relevant_intents.add(tr.intent)

        return relevant_intents

    def _get_training_phrases(self):
        intent_list = []
        training_phrases = []
        for intent in self.intents:
            for training_phrase in intent.training_phrases:
                phrase_str = "".join([i.text for i in training_phrase.parts])
                training_phrases.append(phrase_str)
                intent_list.append(intent.display_name)

        return np.array(intent_list), np.array(training_phrases)

    def generate_embeddings(self, utterances):
        return self.embedder.embed(utterances)

    def _build_searcher(self, embeddings, num_neighbors=10):
        normalized_dataset = (
            embeddings / np.linalg.norm(embeddings, axis=1)[:, np.newaxis]
        )

        # Use ScaNN brute force. This is fine for up to ~20k points
        searcher = (
            scann.scann_ops_pybind.builder(
                normalized_dataset, num_neighbors, "dot_product"
            )
            .score_brute_force()
            .build()
        )

        return searcher

    def find_similar_phrases(self, utterances):
        embeddings = self.generate_embeddings(utterances)
        nearest_idx, similarities = self.searcher.search_batched(embeddings)

        df = pd.DataFrame(
            {
                "Utterance": utterances,
                "Nearest Training Phrase": self.training_phrases[
                    nearest_idx[:, 0]
                ],
                "Nearest Intent": self.training_intents[nearest_idx[:, 0]],
                "Similarity": similarities[:, 0],
            }
        )

        return df

    def find_new_groups(self, utterances):
        utterances = np.unique(utterances)

        embeddings = self.generate_embeddings(utterances)

        train_nearest_idx, train_similarities = self.searcher.search_batched(
            embeddings
        )

        new_searcher = self._build_searcher(embeddings)
        new_nearest_idx, new_similarities = new_searcher.search_batched(
            embeddings
        )

        # Count how many new utterances are more similar
        # than any training phrase.
        closer_count = np.sum(
            new_similarities > train_similarities[:, :1], axis=1
        )

        # Pull out the largest groups.
        grouped_utterance_ids = set()
        groups = []
        similar_training_phrases = []
        similar_intents = []
        training_phrase_distances = []
        for utterance_idx in np.argsort(closer_count)[::-1]:
            if utterance_idx in grouped_utterance_ids:
                continue

            if closer_count[utterance_idx] < 2:
                break

            group_utterances = []
            for other_idx in new_nearest_idx[
                utterance_idx, : closer_count[utterance_idx]
            ]:
                if other_idx in grouped_utterance_ids:
                    # Some of the utterances in this group were
                    #  assigned to another group already, ignore this group.
                    break
                grouped_utterance_ids.add(other_idx)
                group_utterances.append(utterances[other_idx])
            else:
                # Found a new group, add it.
                match_idx = train_nearest_idx[utterance_idx, 0]
                similar_training_phrases.append(
                    self.training_phrases[match_idx]
                )
                similar_intents.append(self.training_intents[match_idx])
                training_phrase_distances.append(
                    train_similarities[utterance_idx, 0]
                )
                groups.append('"' + ('", "'.join(group_utterances)) + '"')

        df = pd.DataFrame(
            {
                "Utterances": groups,
                "Nearest Training Phrase": similar_training_phrases,
                "Nearest Intent": similar_intents,
                "Similarity": training_phrase_distances,
            }
        )

        return df

    def find_similar_training_phrases_in_different_intents(self):
        num_utterances = len(self.training_phrases)
        all_idx_1 = np.tile(np.arange(num_utterances)[:, None], 10)
        all_idx_2, similarities = self.searcher.search_batched(
            self.training_embeddings
        )

        # Only keep pairs in different intents
        def intents_differ(idx_1, idx_2):
            return self.training_intents[idx_1] != self.training_intents[idx_2]

        different_intent_mask = np.vectorize(intents_differ)(
            all_idx_1, all_idx_2
        )

        mismatch_mask = different_intent_mask & (similarities > 0.8)
        mismatch_idx_1 = all_idx_1[mismatch_mask]
        mismatch_idx_2 = all_idx_2[mismatch_mask]
        mismatch_similarities = similarities[mismatch_mask]

        # Remove any duplicates
        sort_mask = mismatch_idx_1 > mismatch_idx_2
        sort_vals_1 = mismatch_idx_1[sort_mask]
        mismatch_idx_1[sort_mask] = mismatch_idx_2[sort_mask]
        mismatch_idx_2[sort_mask] = sort_vals_1
        (unique_idx_1, unique_idx_2), unique_index = np.unique(
            [mismatch_idx_1, mismatch_idx_2], axis=1, return_index=True
        )
        unique_similarities = mismatch_similarities[unique_index]

        df = (
            pd.DataFrame(
                {
                    "Training phrase 1": self.training_phrases[unique_idx_1],
                    "Training phrase 2": self.training_phrases[unique_idx_2],
                    "Intent 1": self.training_intents[unique_idx_1],
                    "Intent 2": self.training_intents[unique_idx_2],
                    "Similarity": unique_similarities,
                }
            )
            .sort_values("Similarity", ascending=False)
            .reset_index(drop=True)
        )

        return df
