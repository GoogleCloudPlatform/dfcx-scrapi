"""Working with built in CX validation functions"""

# Copyright 2021 Google LLC
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

import logging
import re
from typing import Dict
import pandas as pd

from dfcx_scrapi.core.scrapi_base import ScrapiBase
from dfcx_scrapi.core.agents import Agents
from dfcx_scrapi.core.flows import Flows

SCOPES = [
    "https://www.googleapis.com/auth/cloud-platform",
    "https://www.googleapis.com/auth/dialogflow",
]


class ValidationKit(ScrapiBase):
    """Helper for working with built in CX validation functions"""

    def __init__(
        self,
        creds_path: str = None,
        creds_dict: Dict = None,
        creds=None,
        scope=False,
    ):
        super().__init__(
            creds_path=creds_path,
            creds_dict=creds_dict,
            creds=creds,
            scope=scope,
        )

        self.agents = Agents(creds_path=creds_path, creds_dict=creds_dict)
        self.flows = Flows(creds_path=creds_path, creds_dict=creds_dict)

    def validation_results_to_dataframe(self, validation_results: Dict):
        """ "Transform the Validation results into a dataframe.
        Note will not work if you call get_validation_result with a
        flow_id specified. For calling validate ensure lro is complete
        Args:
            validation_results: dictionary of validation results
                passed back from get_validation_result or validate functions

        Return:
            df: dataframe containing the validation results
        """

        agent_id = "/".join(validation_results["name"].split("/")[0:6])

        flows_map = self.flows.get_flows_map(agent_id)
        max_cols_old = 0
        dataframe = pd.DataFrame()

        for flow in validation_results["flowValidationResults"]:

            temp = "/".join(flow["name"].split("/")[:-1])
            val_msg = flow.get("validationMessages", {})
            if bool(val_msg):
                temp_df = pd.DataFrame(val_msg)
                temp_df.insert(0, "flow", flows_map[temp])

                max_cols_new = max([len(x) for x in temp_df.resourceNames])

                if max_cols_new > max_cols_old:
                    for i in range(1, max_cols_new + 1):
                        temp_df["resource{}".format(i)] = None
                    max_cols_old = max_cols_new

                for index in temp_df.index:
                    i = 1
                    for frame in temp_df["resourceNames"][index]:
                        temp_df["resource{}".format(i)][index] = frame[
                            "displayName"
                        ]
                        i += 1

                dataframe = dataframe.append(temp_df)
                max_cols_old = 0

        return dataframe

    def intent_disambiguation(self, agent_id, refresh=False, flow=None):
        """Obtains the intent disambiguation tasks from the validation tool
            Args:
                refresh: (optional) False means validation results are pulled
                    as is. True means the validation tool is refreshed then
                    results are pulled
                flow: (optional) If specified results are returned
                    for the indicated flow display name


        Returns:
          Dictionary of intent disambiguation Validation results
          in two dataframes.
              extended: All intent disambiguation validtion results as
                seperate instances. If 5 training phrases conflict
                in 5 intents they will be shown as 5 rows.
              compact: Only showing the first instance of a conflict
                for each grouping. If 5 trainig phrases conflic in 5 intents
                only the first training phrase will show.
        """

        if refresh:
            validation = self.agents.validate_agent(agent_id)
        else:
            validation = self.agents.get_validation_result(agent_id=agent_id)

        validation_df = self.validation_results_to_dataframe(validation)
        if flow:
            validation_df = validation_df[validation_df["flow"] == flow]

        # Parse df
        resources = validation_df.columns
        resources = [r for r in resources if "resource" in r]
        validation_df = validation_df[["flow", "detail"] + resources]

        disambig_id, intents_list, tp_list, id_ = [], [], [], 0
        flows = []
        phrase = "Multiple intents share training phrases which are too similar"
        for _, row in validation_df.iterrows():
            deets, flow = row["detail"], row["flow"]
            if bool(re.search(phrase, deets)):
                intents = re.findall("Intent '(.*)': training phrase ", deets)
                training_phrases = re.findall("training phrase '(.*)'", deets)
                intents_list = intents_list + intents
                tp_list = tp_list + training_phrases
                disambig_id = disambig_id + ([id_] * len(training_phrases))
                flows = flows + ([flow] * len(training_phrases))
                id_ += 1



        extraction = pd.DataFrame()
        extraction["disambig_id"] = disambig_id
        extraction.insert(0, "flow", flows)
        extraction["intent"] = intents_list
        extraction["training_phrase"] = tp_list

        if extraction.empty:
            logging.info(
                "Validation results do not contain clashing intent phrases.")
            return None

        intent_options = (
            extraction.groupby(["disambig_id"])["intent"]
            .apply(list)
            .reset_index()
            .rename(columns={"intent": "intents"})
        )
        intent_options["intents"] = intent_options.apply(
            lambda x: list(set(x["intents"])), axis=1
        )

        extraction = pd.merge(
            extraction, intent_options, on=["disambig_id"], how="left"
        )

        internal = extraction.copy()

        internal["intent_count"] = internal.apply(
            lambda x: len(x["intents"]), axis=1
        )
        external = (
            extraction.groupby(["flow", "disambig_id"])
            .agg(
                {
                    "training_phrase": "first",
                    "intents": "first",
                    "intent": "count",
                }
            )
            .reset_index()
            .rename(columns={"intent": "conflicting_tp_count"})
        )
        external["intent_count"] = external.apply(
            lambda x: len(x["intents"]), axis=1
        )

        return {"extended": internal, "compact": external}
