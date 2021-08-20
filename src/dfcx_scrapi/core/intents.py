"""Intent Resource functions."""

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

from collections import defaultdict
import json
import logging
from typing import Dict
import numpy as np
import pandas as pd

import google.cloud.dialogflowcx_v3beta1.services as services
import google.cloud.dialogflowcx_v3beta1.types as types

from dfcx_scrapi.core.scrapi_base import ScrapiBase

# logging config
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


class Intents(ScrapiBase):
    """Core Class for CX Intent Resource functions."""

    def __init__(
        self,
        creds_path: str = None,
        creds_dict: Dict = None,
        creds=None,
        scope=False,
        intent_id: str = None,
        agent_id: str = None,
    ):
        super().__init__(
            creds_path=creds_path,
            creds_dict=creds_dict,
            creds=creds,
            scope=scope,
        )

        if intent_id:
            self.intent_id = intent_id
            self.client_options = self._set_region(self.intent_id)

        if agent_id:
            self.agent_id = agent_id

    @staticmethod
    def intent_proto_to_dataframe(obj: types.Intent, mode="basic"):
        """intents to dataframe

        Args:
          obj, intent protobuf object
          mode: (Optional) basic returns display name and training phrase as
            plain text.
          Advanced returns training phrase and parameters df broken out by
            parts.
        """
        if mode == "basic":
            intent_dict = defaultdict(list)
            if "training_phrases" in obj:
                for train_phrase in obj.training_phrases:
                    item_list = []
                    if len(train_phrase.parts) > 1:
                        for item in train_phrase.parts:
                            item_list.append(item.text)
                        intent_dict[obj.display_name].append("".join(item_list))
                    else:
                        intent_dict[obj.display_name].append(
                            train_phrase.parts[0].text
                        )
            else:
                intent_dict[obj.display_name].append("")

            data_frame = pd.DataFrame.from_dict(
                intent_dict, orient="index"
            ).transpose()
            data_frame = data_frame.stack().to_frame().reset_index(level=1)
            data_frame = data_frame.rename(
                columns={"level_1": "intent", 0: "tp"}
            ).reset_index(drop=True)
            data_frame = data_frame.sort_values(["intent", "tp"])

            return data_frame

        elif mode == "advanced":

            train_phrases = obj.training_phrases
            params = obj.parameters
            if len(train_phrases) > 0:
                tp_df = pd.DataFrame()
                tp_id = 0
                for train_phrase in train_phrases:
                    part_id = 0
                    for part in train_phrase.parts:
                        tp_df = tp_df.append(
                            pd.DataFrame(
                                columns=[
                                    "display_name",
                                    "name",
                                    "training_phrase",
                                    "part",
                                    "text",
                                    "parameter_id",
                                    "repeat_count",
                                    "id",
                                ],
                                data=[
                                    [
                                        obj.display_name,
                                        obj.name,
                                        tp_id,
                                        part_id,
                                        part.text,
                                        part.parameter_id,
                                        train_phrase.repeat_count,
                                        train_phrase.id,
                                    ]
                                ],
                            )
                        )
                        part_id += 1
                    tp_id += 1

                phrases = tp_df.copy()
                phrase_lst = (
                    phrases.groupby(["training_phrase"])["text"]
                    .apply(lambda x: "".join(x))  # pylint: disable=W0108
                    .reset_index()
                    .rename(columns={"text": "phrase"})
                )

                phrases = pd.merge(
                    phrases, phrase_lst, on=["training_phrase"], how="outer"
                )

                if len(params) > 0:
                    param_df = pd.DataFrame()
                    for param in params:
                        param_df = param_df.append(
                            pd.DataFrame(
                                columns=["display_name", "id", "entity_type"],
                                data=[
                                    [
                                        obj.display_name,
                                        param.id,
                                        param.entity_type,
                                    ]
                                ],
                            )
                        )
                    return {"phrases": phrases, "parameters": param_df}

                else:
                    return {
                        "phrases": phrases,
                        "parameters": pd.DataFrame(
                            columns=["display_name", "id", "entity_type"]
                        ),
                    }

            else:
                return {
                    "phrases": pd.DataFrame(
                        columns=[
                            "display_name",
                            "name",
                            "training_phrase",
                            "part",
                            "text",
                            "parameter_id",
                            "repeat_count",
                            "id",
                            "phrase",
                        ],
                        data=[
                            [
                                obj.display_name,
                                obj.name,
                                np.nan,
                                np.nan,
                                np.nan,
                                np.nan,
                                np.nan,
                                np.nan,
                                np.nan,
                            ]
                        ],
                    ),
                    "parameters": pd.DataFrame(
                        columns=["display_name", "id", "entity_type"]
                    ),
                }

        else:
            raise ValueError("Mode types: [basic, advanced]")

    def get_intents_map(self, agent_id: str = None, reverse=False):
        """Exports Agent Intent Names and UUIDs into a user friendly dict.

        Args:
          - agent_id, the formatted CX Agent ID to use
          - reverse, (Optional) Boolean flag to swap key:value -> value:key

        Returns:
          - intents_map, Dictionary containing Intent UUIDs as keys and
              intent.display_name as values
        """
        if not agent_id:
            agent_id = self.agent_id

        if reverse:
            intents_dict = {
                intent.display_name: intent.name
                for intent in self.list_intents(agent_id)
            }

        else:
            intents_dict = {
                intent.name: intent.display_name
                for intent in self.list_intents(agent_id)
            }

        return intents_dict

    def list_intents(self, agent_id: str = None):
        """Exports List of all intents in specific CX Agent.

        Args:
          agent_id, the CX agent id to pull the intents from

        Returns:
          intents, List of Intent objects
        """
        if not agent_id:
            agent_id = self.agent_id

        request = types.intent.ListIntentsRequest()
        request.parent = agent_id

        client_options = self._set_region(agent_id)
        client = services.intents.IntentsClient(
            credentials=self.creds, client_options=client_options
        )
        response = client.list_intents(request)

        intents = []
        for page in response.pages:
            for intent in page.intents:
                intents.append(intent)

        return intents

    def get_intent(self, intent_id: str = None):
        """Get a single Intent object based on specific CX Intent ID.

        Args:
          intent_id, the properly formatted CX Intent ID

        Returns:
          response, a single Intent object
        """
        if not intent_id:
            intent_id = self.intent_id

        client_options = self._set_region(intent_id)
        client = services.intents.IntentsClient(
            credentials=self.creds, client_options=client_options
        )
        response = client.get_intent(name=intent_id)

        return response

    def create_intent(
        self,
        agent_id,
        obj=None,
        intent_dictionary: dict = None):
        """Creates an intent in the agent from a protobuff or dictionary.

        Args:
          - agent_id, the formatted CX Agent ID to use
          - obj, (Optional) intent protobuf
          -intent_dictionary, (optional) dictionary of the intent to pass in
            with structure

        example intent dictionary:
           test_intent = {
            "description": "",
            "display_name": "my_intent",
            "is_fallback": False,
            "labels": {},
            "priority": 500000,
            "training_phrases": [
                {
                    "id": "",
                    "parts": [
                        {
                            "text": "hello"
                        },
                        {
                            "text": "all"
                        }
                    ],
                    "repeat_count": 1
                },
                {
                    "id": "",
                    "parts": [
                        {
                            "text": "hi"
                        }
                    ],
                    "repeat_count": 1
                }
            ]
        }


        Returns:
          - intents protobuff object
        """

        if obj and intent_dictionary:
            raise ValueError("cannot provide both obj and intent_dictionary")
        elif obj:
            intent = obj
            intent.name = ""
        elif intent_dictionary:
            intent = types.intent.Intent.from_json(json.dumps(
                intent_dictionary))
        else:
            raise ValueError("must provide either obj or intent_dictionary")

        client_options = self._set_region(agent_id)
        client = services.intents.IntentsClient(
            client_options=client_options, credentials=self.creds
        )
        response = client.create_intent(parent=agent_id, intent=intent)

        return response

    def update_intent(
        self,
        intent_id: str = None,
        obj=None,
        language_code=None):
        """Updates a single Intent object based on provided args.
        Args:
          intent_id, the destination Intent ID. Must be formatted properly
              for Intent IDs in CX.
          obj, The CX Intent object in proper format. This can also
              be extracted by using the get_intent() method.
        """
        if obj:
            intent = obj
            intent.name = intent_id

        else:
            if not intent_id:
                intent_id = self.intent_id
            intent = self.get_intent(intent_id)

        client_options = self._set_region(intent_id)
        client = services.intents.IntentsClient(
            client_options=client_options, credentials=self.creds
        )

        if language_code:
            req = types.intent.UpdateIntentRequest(
                intent=intent,
                language_code=language_code
            )
            response = client.update_intent(req)
        else:
            response = client.update_intent(intent=intent)

        return response

    def delete_intent(self, intent_id, obj=None):
        """deletes an intent

        Args:
          intent_id, intent to delete
        """
        if obj:
            intent_id = obj.name
        else:
            client_options = self._set_region(intent_id)
            client = services.intents.IntentsClient(
                client_options=client_options, credentials=self.creds
            )
            client.delete_intent(name=intent_id)

    def bulk_intent_to_df(self, agent_id=None, mode="basic"):
        """intents to dataframe

        Args:
          agent_id, agent to pull list of intents
          mode: (Optional) basic returns display name and training phrase as
            plain text.
          Advanced returns training phrase and parameters df broken out by
            parts.
        """

        if not agent_id:
            agent_id = self.agent_id

        intents = self.list_intents(agent_id)
        if mode == "basic":
            main_frame = pd.DataFrame()
            for obj in intents:
                data_frame = self.intent_proto_to_dataframe(obj, mode=mode)
                main_frame = main_frame.append(data_frame)
            main_frame = main_frame.sort_values(["intent", "tp"])
            return main_frame

        elif mode == "advanced":
            master_phrases = pd.DataFrame()
            master_parameters = pd.DataFrame()
            for obj in intents:
                output = self.intent_proto_to_dataframe(obj, mode="advanced")
                master_phrases = master_phrases.append(output["phrases"])
                master_parameters = master_parameters.append(
                    output["parameters"]
                )
            return {"phrases": master_phrases, "parameters": master_parameters}

        else:
            raise ValueError("Mode types: [basic, advanced]")

    def intents_to_df_cosine_prep(self, agent_id: str = None):
        """Exports a dataframe and defaultdict of Intents for use with Cosine
        Similarity tools.

        Args:
          agent_id, agent to pull list of intents from

        Returns:
          df, a Pandas Dataframe of Intents and TPs
          intent_dict, a Defaultdict(List) that is prepped to feed to the
            Cosine similarity tool (offline)
        """
        if not agent_id:
            agent_id = self.agent_id

        intent_dict = defaultdict(list)
        intents = self.list_intents(agent_id)

        for intent in intents: # pylint: disable=R1702
            if intent.display_name == "Default Negative Intent":
                pass
            else:
                if "training_phrases" in intent:
                    for tp in intent.training_phrases:
                        s = []
                        if len(tp.parts) > 1:
                            for item in tp.parts:
                                s.append(item.text)
                            intent_dict[intent.display_name].append("".join(s))
                        else:
                            intent_dict[intent.display_name].append(
                                tp.parts[0].text)
                else:
                    intent_dict[intent.display_name].append("")

        df = pd.DataFrame.from_dict(intent_dict, orient="index").transpose()
        df = df.stack().to_frame().reset_index(level=1)
        df = df.rename(
            columns={"level_1":"intent",0:"tp"}).reset_index(drop=True)
        df = df.sort_values(["intent","tp"])

        return df, intent_dict
