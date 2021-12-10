"""Utility file for dataframe functions in support of Dialogflow CX."""

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

import json
import logging
import time
from typing import Dict, List
import gspread
import pandas as pd
import numpy as np
from pyasn1.type.univ import Boolean
from tabulate import tabulate
from gspread_dataframe import set_with_dataframe
from oauth2client.service_account import ServiceAccountCredentials

import google.cloud.dialogflowcx_v3beta1.types as types

from dfcx_scrapi.core import (
    scrapi_base,
    intents,
    entity_types,
    flows,
    pages,
    transition_route_groups,
)

g_drive_scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive",
]

# logging config
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


class DataframeFunctions(scrapi_base.ScrapiBase):
    """Class that supports dataframe functions in DFCX."""

    def __init__(
        self,
        creds_path: str = None,
        creds_dict: dict = None,
        creds=None,
        scope=False,
    ):
        super().__init__(
            creds_path=creds_path,
            creds_dict=creds_dict,
            creds=creds,
            scope=scope,
        )

        logging.info("create dfcx creds %s", creds_path)
        self.entities = entity_types.EntityTypes(creds_path, creds_dict)
        self.intents = intents.Intents(creds_path, creds_dict)
        self.flows = flows.Flows(creds_path, creds_dict)
        self.pages = pages.Pages(creds_path, creds_dict)
        self.route_groups = transition_route_groups.TransitionRouteGroups(
            creds_path, creds_dict
        )
        self.creds_path = creds_path

    @staticmethod
    def progress_bar(current, total, bar_length=50, type_="Progress"):
        """Display progress bar for processing."""
        percent = float(current) * 100 / total
        arrow = "-" * int(percent / 100 * bar_length - 1) + ">"
        spaces = " " * (bar_length - len(arrow))
        print(
            "{2}({0}/{1})".format(current, total, type_)
            + "[%s%s] %d %%" % (arrow, spaces, percent),
            end="\r",
        )

    @staticmethod
    def _coerce_to_string(dataframe: pd.DataFrame, fields: List[str]):
        """Coerce incoming object type to string"""
        for field in fields:
            dataframe = dataframe.astype({field: "string"})

        return dataframe

    @staticmethod
    def _coerce_to_int(dataframe: pd.DataFrame, fields: List[str]):
        """Coerce incoming object type to int"""
        for field in fields:
            dataframe = dataframe.astype({field: "int32"})

        return dataframe

    @staticmethod
    def _make_schema(columns: List[str]) -> pd.DataFrame:

        dataframe = pd.DataFrame(columns=columns)

        type_map = {
            "display_name": "string",
            "text": "string",
            "parameter_id": "string",
            "training_phrase": "int32",
            "part": "int32",
            "id": "string",
            "entity_type": "string",
        }

        temp_data = {}
        for column in dataframe.columns:
            dataframe = dataframe.astype({column: type_map[column]})
            temp_data[column] = type_map[column]

        dataframe = dataframe.append(temp_data, ignore_index=True)

        return dataframe

    @staticmethod
    def _remap_intent_values(original_intent: types.Intent) -> types.Intent:

        new_intent = types.intent.Intent()
        new_intent.name = original_intent.name
        new_intent.display_name = original_intent.display_name
        new_intent.priority = original_intent.priority
        new_intent.is_fallback = original_intent.is_fallback
        new_intent.labels = dict(original_intent.labels)
        new_intent.description = original_intent.description

        return new_intent

    def _update_intent_from_dataframe(
        self,
        intent_id: str,
        train_phrases: pd.DataFrame,
        params=None,
        mode: str = "basic",
    ):
        """Make an Updated Intent Object based on already existing Intent.

        The intent must exist in the agent.
        This method will modify the existing Intent object based on the
        incoming dataframe parameters.
        *Note* this is an internal method and should not be used on its own to
        update the Intent object.

        Args:
          intent_id: name parameter of the intent to update
          train_phrases: dataframe of training phrases in advanced have
            training_phrase and parts column to track the build
          params(optional): dataframe of parameters
          mode: basic - build assuming one row is one training phrase no
            entities, advance - build keeping track of training phrases and
            parts with the training_phrase and parts column.

        Returns:
          intent_pb: the new intents protobuf object
        """

        if mode == "basic":
            if hasattr(train_phrases, "text"):
                train_phrases = train_phrases[["text"]]
                train_phrases = self._coerce_to_string(train_phrases, ["text"])
            else:
                tp_schema = self._make_schema(["text", "parameter_id"])

                logging.error(
                    "%s mode train_phrases schema must be: \n%s",
                    mode,
                    tabulate(tp_schema, headers="keys", tablefmt="psql"),
                )
                raise KeyError("Missing column 'text' in DataFrame columns")

        elif mode == "advanced":
            if all(
                k in train_phrases
                for k in ["training_phrase", "part", "text", "parameter_id"]
            ):

                train_phrases = train_phrases[
                    ["training_phrase", "part", "text", "parameter_id"]
                ]
                train_phrases = self._coerce_to_int(
                    train_phrases, ["training_phrase", "part"]
                )
                train_phrases = self._coerce_to_string(
                    train_phrases, ["text", "parameter_id"]
                )

                if not params.empty:
                    params = params[["id", "entity_type"]]
                    params = self._coerce_to_string(
                        params, ["id", "entity_type"]
                    )

            else:
                tp_schema = self._make_schema(
                    ["training_phrase", "part", "text", "parameter_id"]
                )
                p_schema = self._make_schema(["id", "entity_type"])

                logging.error(
                    "%s mode train_phrases schema must be: \n%s",
                    mode,
                    tabulate(
                        tp_schema.transpose(),
                        headers="keys",
                        tablefmt="psql",
                    ),
                )
                logging.error(
                    "%s mode parameter schema must be %s \n",
                    mode,
                    tabulate(
                        p_schema.transpose(),
                        headers="keys",
                        tablefmt="psql",
                    ),
                )
                raise KeyError("Missing column name in DataFrame. See schema.")

        else:
            raise ValueError("Mode must be 'basic' or 'advanced'")

        original = self.intents.get_intent(intent_id=intent_id)
        intent = self._remap_intent_values(original)

        # training phrases
        if mode == "advanced":
            training_phrases = []
            for phrase in list(set(train_phrases["training_phrase"])):
                tp_parts = train_phrases[
                    train_phrases["training_phrase"].astype(int) == int(phrase)
                ]
                parts = []
                for _, row in tp_parts.iterrows():
                    part = {
                        "text": row["text"],
                        "parameter_id": row["parameter_id"],
                    }
                    parts.append(part)

                training_phrase = {"parts": parts, "repeat_count": 1, "id": ""}
                training_phrases.append(training_phrase)

            intent.training_phrases = training_phrases
            parameters = []
            for _, row in params.iterrows():
                parameter = {
                    "id": row["id"],
                    "entity_type": row["entity_type"],
                    "is_list": False,
                    "redact": False,
                }
                parameters.append(parameter)

            if parameters:
                intent.parameters = parameters

        elif mode == "basic":
            training_phrases = []
            for _, row in train_phrases.iterrows():
                part = {"text": row["text"], "parameter_id": None}
                parts = [part]
                training_phrase = {"parts": parts, "repeat_count": 1, "id": ""}
                training_phrases.append(training_phrase)
            intent.training_phrases = training_phrases
        else:
            raise ValueError("mode must be basic or advanced")

        # json_intent = json.dumps(intent)
        # intent_pb = types.Intent.from_json(json_intent)
        return intent

    def bulk_update_intents_from_dataframe(
        self,
        agent_id: str,
        tp_df: pd.DataFrame,
        params_df: pd.DataFrame = None,
        mode: str = "basic",
        update_flag: Boolean = False,
        rate_limiter: int = 5,
        language_code: str = None
    ):
        """Update existing Intent, TPs and Parameters from a Dataframe.

        Args:
          agent_id: name parameter of the agent to update_flag - full path to
            agent
          tp_df: dataframe of bulk training phrases required columns:
            text, display_name in advanced mode have training_phrase and parts
            column to track the build
          params_df(optional): dataframe of bulk parameters
          mode: basic|advanced
            basic, build assuming one row is one training phrase no entities
            advanced, build keeping track of training phrases and parts with the
              training_phrase and parts column.
          update_flag: True to update_flag the intents in the agent
          rate_limiter: seconds to sleep between operations.
          language_code: Language code of the intents being uploaded. Reference:
            https://cloud.google.com/dialogflow/cx/docs/reference/language

        Returns:
          modified_intents: dictionary with intent display names as keys and
            the new intent protobufs as values
        """

        if mode == "basic":
            if all(k in tp_df for k in ["display_name", "text"]):
                tp_df = tp_df[["display_name", "text"]]
                tp_df = self._coerce_to_string(tp_df, ["display_name", "text"])

            else:
                tp_schema = pd.DataFrame(
                    index=["display_name", "text", "parameter_id"],
                    columns=[0],
                    data=["string", "string", "string"],
                ).astype({0: "string"})
                logging.error(
                    "%s mode train_phrases schema must be %s \n",
                    mode,
                    tabulate(
                        tp_schema.transpose(),
                        headers="keys",
                        tablefmt="psql",
                    ),
                )

        elif mode == "advanced":
            if all(
                k in tp_df
                for k in [
                    "display_name",
                    "training_phrase",
                    "part",
                    "text",
                    "parameter_id",
                ]
            ):

                tp_df = tp_df[
                    [
                        "display_name",
                        "training_phrase",
                        "part",
                        "text",
                        "parameter_id",
                    ]
                ]


                tp_df = self._coerce_to_string(
                    tp_df, ["display_name", "text", "parameter_id"]
                )

                tp_df = self._coerce_to_int(tp_df, ["training_phrase", "part"])

                if not params_df.empty:
                    params_df = params_df[["display_name", "id", "entity_type"]]
                    params_df = params_df.astype(
                        {
                            "display_name": "string",
                            "id": "string",
                            "entity_type": "string",
                        }
                    )

            else:
                tp_schema = pd.DataFrame(
                    index=[
                        "display_name",
                        "training_phrase",
                        "part",
                        "text",
                        "parameter_id",
                    ],
                    columns=[0],
                    data=["string", "int32", "int32", "string", "string"],
                ).astype({0: "string"})
                p_schema = pd.DataFrame(
                    index=["display_name", "id", "entity_type"],
                    columns=[0],
                    data=["string", "string", "string"],
                ).astype({0: "string"})
                logging.error(
                    "%s mode train_phrases schema must be %s \n",
                    mode,
                    tabulate(
                        tp_schema.transpose(),
                        headers="keys",
                        tablefmt="psql",
                    ),
                )
                logging.error(
                    "%s mode parameter schema must be %s \n",
                    mode,
                    tabulate(
                        p_schema.transpose(),
                        headers="keys",
                        tablefmt="psql",
                    ),
                )

        else:
            raise ValueError("mode must be basic or advanced")

        intents_map = self.intents.get_intents_map(
            agent_id=agent_id, reverse=True
        )

        intent_names = list(set(tp_df["display_name"]))

        new_intents = {}
        i = 0
        for intent_name in intent_names:
            if intent_name in (["", np.nan, None]):
                logging.warning("empty intent_name")
                continue

            tps = tp_df.copy()[tp_df["display_name"] == intent_name].drop(
                columns="display_name"
            )
            params = pd.DataFrame()
            if mode == "advanced":
                params = params_df.copy()[
                    params_df["display_name"] == intent_name
                ].drop(columns="display_name")

            if intent_name not in intents_map.keys():
                logging.error(
                    "FAIL to update - intent not found: [%s]", intent_name
                )
                continue

            new_intent = self._update_intent_from_dataframe(
                intent_id=intents_map[intent_name],
                train_phrases=tps,
                params=params,
                mode=mode,
            )
            new_intents[intent_name] = new_intent
            i += 1
            self.progress_bar(i, len(intent_names))
            if update_flag:
                self.intents.update_intent(
                    intent_id=new_intent.name,
                    obj=new_intent,
                    language_code=language_code
                )
                time.sleep(rate_limiter)

        return new_intents

    def _create_intent_from_dataframe(
        self,
        display_name: str,
        tp_df: pd.DataFrame,
        params_df: pd.DataFrame = None,
        meta: Dict[str, str] = None,
        mode: str = "basic",
    ):
        """Create an intent from a DataFrame.

        Args:
          display_name: display_name parameter of the intent to create
          train_phrases: dataframe of training phrases in advanced have
                  training_phrase and parts column to track the build
          params(optional): dataframe of parameters
          meta: dictionary
          mode: basic - build assuming one row is one training phrase no
                  entities, advance - build keeping track of training phrases
                  and parts with the training_phrase and parts column.

        Returns:
          intent_pb: the new intents protobuf object
        """
        if mode == "basic":
            if all(k in tp_df for k in ["text"]):
                tp_df = tp_df[["text"]]
                tp_df = self._coerce_to_string(tp_df, ["text"])

            else:
                tp_schema = self._make_schema(["text", "parameter_id"])

                logging.error(
                    "%s mode train_phrases schema must be %s \n",
                    mode,
                    tabulate(
                        tp_schema.transpose(),
                        headers="keys",
                        tablefmt="psql",
                    ),
                )

        elif mode == "advanced":
            if all(
                k in tp_df
                for k in ["training_phrase", "part", "text", "parameter_id"]
            ):
                tp_df = tp_df[
                    ["training_phrase", "part", "text", "parameter_id"]
                ]
                tp_df = self._coerce_to_string(tp_df, ["text", "parameter_id"])
                tp_df = self._coerce_to_int(tp_df, ["training_phrase", "part"])

                if not params_df.empty:
                    params_df = params_df[["id", "entity_type"]]
                    params_df = params_df.astype(
                        {"id": "string", "entity_type": "string"}
                    )
            else:
                tp_schema = self._make_schema(
                    ["training_phrase", "part", "text", "parameter_id"]
                )
                p_schema = self._make_schema(["id", "entity_type"])

                logging.error(
                    "%s mode train_phrases schema must be %s \n",
                    mode,
                    tabulate(
                        tp_schema.transpose(),
                        headers="keys",
                        tablefmt="psql",
                    ),
                )
                logging.error(
                    "%s mode parameter schema must be %s \n",
                    mode,
                    tabulate(
                        p_schema.transpose(),
                        headers="keys",
                        tablefmt="psql",
                    ),
                )

        else:
            raise ValueError("mode must be basic or advanced")

        intent = {}
        intent["display_name"] = display_name

        if meta:
            intent["priority"] = meta.get("priority", 500000)
            intent["is_fallback"] = meta.get("is_fallback", False)
            intent["labels"] = meta.get("labels", {})
            intent["description"] = meta.get("description", "")

        # training phrases
        if mode == "advanced":
            training_phrases = []
            for phrase in list(set(tp_df["training_phrase"])):
                tp_parts = tp_df[
                    tp_df["training_phrase"].astype(int) == int(phrase)
                ]
                parts = []
                for _, row in tp_parts.iterrows():
                    part = {
                        "text": row["text"],
                        "parameter_id": row["parameter_id"],
                    }
                    parts.append(part)

                training_phrase = {"parts": parts, "repeat_count": 1, "id": ""}
                training_phrases.append(training_phrase)

            intent["training_phrases"] = training_phrases
            parameters = []
            for _, row in params_df.iterrows():
                parameter = {
                    "id": row["id"],
                    "entity_type": row["entity_type"],
                    "is_list": False,
                    "redact": False,
                }
                parameters.append(parameter)

            if parameters:
                intent["parameters"] = parameters

        elif mode == "basic":
            training_phrases = []
            for _, row in tp_df.iterrows():
                part = {"text": row["text"], "parameter_id": None}
                parts = [part]
                training_phrase = {"parts": parts, "repeat_count": 1, "id": ""}
                training_phrases.append(training_phrase)
            intent["training_phrases"] = training_phrases
        else:
            raise ValueError("mode must be basic or advanced")

        json_intent = json.dumps(intent)
        intent_pb = types.Intent.from_json(json_intent)

        return intent_pb

    def bulk_create_intent_from_dataframe(
        self,
        agent_id: str,
        tp_df: pd.DataFrame,
        params_df: pd.DataFrame = None,
        mode: str = "basic",
        update_flag: Boolean = False,
        rate_limiter: int = 5,
        meta: Dict[str, str] = None,
    ):
        """Create Intents in DFCX from a DataFrame.

        Args:
          agent_id: name parameter of the agent to update_flag - full path to
           agent
          train_phrases_df: dataframe of bulk training phrases required
            columns of text, display_name in advanced mode have training_phrase
            and parts column to track the build
          params_df(optional): dataframe of bulk parameters
          mode: basic|advanced
            basic - build assuming one row is one training phrase no entities
            advanced - build keeping track of training phrases and parts with
              the training_phrase and parts column.
          update_flag: True to update_flag the intents in the agent
          rate_limiter: number of seconds to wait between calls
          meta: dictionary

        Returns:
          new_intents: dictionary with intent display names as keys and the new
            intent protobufs as values

        """
        if mode == "basic":
            if all(k in tp_df for k in ["display_name", "text"]):
                tp_df = tp_df[["display_name", "text"]]
                tp_df = self._coerce_to_string(tp_df, ["display_name", "text"])

            else:
                tp_schema = self._make_schema(
                    ["display_name", "text", "parameter_id"]
                )

                raise ValueError(
                    "%s mode train_phrases schema must be %s" % mode,
                    tabulate(
                        tp_schema.transpose(),
                        headers="keys",
                        tablefmt="psql",
                    ),
                )

        elif mode == "advanced":
            if all(
                k in tp_df
                for k in [
                    "display_name",
                    "training_phrase",
                    "part",
                    "text",
                    "parameter_id",
                ]
            ):
                if "meta" not in tp_df.columns:
                    tp_df["meta"] = [dict()] * len(tp_df)

                tp_df = tp_df[
                    [
                        "display_name",
                        "training_phrase",
                        "part",
                        "text",
                        "parameter_id",
                        "meta",
                    ]
                ]
                tp_df = self._coerce_to_string(
                    tp_df, ["display_name", "text", "parameter_id"]
                )
                tp_df = self._coerce_to_int(tp_df, ["training_phrase", "part"])

                if not params_df.empty:
                    params_df = params_df[["display_name", "id", "entity_type"]]
                    params_df = self._coerce_to_string(
                        params_df, ["display_name", "id", "entity_type"]
                    )

            else:
                tp_schema = self._make_schema(
                    [
                        "display_name",
                        "training_phrase",
                        "part",
                        "text",
                        "parameter_id",
                    ]
                )

                p_schema = self._make_schema(
                    ["display_name", "id", "entity_type"]
                )

                raise ValueError(
                    "%s mode train_phrases schema must be %s \n parameter\
                        schema must be %s"
                    % mode,
                    tabulate(
                        tp_schema.transpose(),
                        headers="keys",
                        tablefmt="psql",
                    ),
                    tabulate(
                        p_schema.transpose(),
                        headers="keys",
                        tablefmt="psql",
                    ),
                )

        else:
            raise ValueError("mode must be basic or advanced")

        temp_intents = list(set(tp_df["display_name"]))
        new_intents = {}
        i = 0
        for intent in temp_intents:
            tps = tp_df.copy()[tp_df["display_name"] == intent].drop(
                columns="display_name"
            )
            params = pd.DataFrame()
            if mode == "advanced":
                params = params_df.copy()[
                    params_df["display_name"] == intent
                ].drop(columns="display_name")

            new_intent = self._create_intent_from_dataframe(
                display_name=intent,
                tp_df=tps,
                params_df=params,
                meta=meta,
                mode=mode,
            )
            new_intents[intent] = new_intent
            i += 1
            self.progress_bar(i, len(temp_intents))
            if update_flag:
                time.sleep(rate_limiter)
                self.intents.create_intent(agent_id=agent_id, obj=new_intent)

        return new_intents

    def create_entity_from_dataframe(
        self,
        display_name: str,
        entity_df: pd.DataFrame,
        meta: Dict[str, str] = None,
    ):
        """Create an entity.

        Args:
          display_name: display_name parameter of the entity to update
          entity_df: dataframe values and synonyms
          meta: dictionary

        Returns:
          entity_pb: the new entity protobuf object
        """
        if not meta:
            meta = {}
        entity_obj = {}
        entity_obj["display_name"] = display_name
        entity_obj["kind"] = meta.get("kind", 1)
        entity_obj["auto_expansion_mode"] = meta.get("auto_expansion_mode", 0)
        entity_obj["excluded_phrases"] = meta.get("excluded_phrases", [])
        entity_obj["enable_fuzzy_extraction"] = meta.get(
            "enable_fuzzy_extraction", False
        )

        values = []
        for _, row in entity_df.iterrows():
            value = row["value"]
            synonyms = json.loads(row["synonyms"])

            part = {"value": value, "synonyms": synonyms}
            values.append(part)

        entity_obj["entities"] = values
        entity_pb = types.EntityType.from_json(json.dumps(entity_obj))

        return entity_pb

    def bulk_create_entity_from_dataframe(
        self, agent_id, entities_df, update_flag=False,
        language_code: str = None, rate_limiter=5,

    ):
        """Bulk create entities from a dataframe.

        Args:
          agent_id: name parameter of the agent to update_flag - full path to
            agent
          entities_df: dataframe of bulk entities;
            required columns: display_name, value, synonyms
          update_flag: True to update_flag the entities in the agent
          language_code: Language code of the intents being uploaded. Ref:
            https://cloud.google.com/dialogflow/cx/docs/reference/language
          rate_limiter: seconds to sleep between operations.

        Returns:
          custom_entities: dictionary with entity display names as keys and the
            new entity protobufs as values
        """

        if "meta" in entities_df.columns:
            meta = (
                entities_df.copy()[["display_name", "meta"]]
                .drop_duplicates()
                .reset_index()
            )

        i, custom_entities = 0, {}
        for entity in list(set(entities_df["display_name"])):
            one_entity = entities_df[entities_df["display_name"] == entity]
            if "meta" in locals():
                meta_ = meta[meta["display_name"] == entity]["meta"].iloc[0]
                meta_ = json.loads(meta_)
                new_entity = self.create_entity_from_dataframe(
                    display_name=entity, entity_df=one_entity, meta=meta
                )

            else:
                new_entity = self.create_entity_from_dataframe(
                    display_name=entity, entity_df=one_entity
                )

            custom_entities[entity] = new_entity
            i += 1

            if update_flag:
                self.entities.create_entity_type(
                    agent_id=agent_id,
                    obj=new_entity,
                    language_code=language_code,
                )
                time.sleep(rate_limiter)

            self.progress_bar(
                i, len(list(set(
                    entities_df["display_name"]))), type_="entities"
            )
        return custom_entities

    def bulk_update_entity_from_dataframe(
        self, entities_df, update_flag=False, language_code=None,
        rate_limiter=5
    ):
        """Bulk updates entities from a dataframe.

        Args:
          agent_id: name parameter of the agent to update_flag - full path to
            agent
          entities_df: dataframe of bulk entities;
            required columns: display_name, value, synonyms
          update_flag: True to update_flag the entities in the agent
          language_code: Language code of the intents being uploaded. Ref:
          https://cloud.google.com/dialogflow/cx/docs/reference/language
          rate_limiter: seconds to sleep between operations.

        Returns:
          custom_entities: dictionary with entity display names as keys and the
            new entity protobufs as values
        """
        if "meta" in entities_df.columns:
            meta = (
                entities_df.copy()[["display_name", "meta"]]
                .drop_duplicates()
                .reset_index()
            )

        i, custom_entities = 0, {}
        for entity in list(set(entities_df["display_name"])):
            one_entity = entities_df[entities_df["display_name"] == entity]
            if "meta" in locals():
                meta_ = meta[meta["display_name"] == entity]["meta"].iloc[0]
                meta_ = json.loads(meta_)
                new_entity = self.create_entity_from_dataframe(
                    display_name=entity, entity_df=one_entity, meta=meta
                )

            else:
                new_entity = self.create_entity_from_dataframe(
                    display_name=entity, entity_df=one_entity
                )

            custom_entities[entity] = new_entity
            i += 1
            entity_type_id = one_entity["name"].max()

            if update_flag:
                self.entities.update_entity_type(
                    entity_type_id, new_entity, language_code
                )
                time.sleep(rate_limiter)

            self.progress_bar(
                i, len(list(set(
                    entities_df["display_name"]))), type_="entities"
            )

        return custom_entities

    def create_transition_route_from_dataframe(self, route_df):
        """Create transition route.

        Args:
          route_df: dataframe with a singular routes data. Should only be one
            row
            intent: intent id
            condition: string condition. ex.
              $session.params.dtmf_diy_opt_in = 1 AND
              $session.params.dtmf_2_techinternet = 2
            target_page: page id
            target_flow: flow id
            webhook: webhook id
            webhook_tag: string webhook tag
            custom_payload: a singular payload or list of payloads ex. [{}, {}]
            fulfillment_text: = list of text ["yo", "hi"]
            parameter_presets: = dictionary of parameter presets ex.
              {"param1":"value","param2":"othervalues"}
            rate_limiter: seconds to sleep between operations.

        Returns:
          transitionRoute: transition route protobuf
        """

        transition_route = types.TransitionRoute()

        route_dict = route_df.to_dict()
        transition_route.intent = route_dict.get("intent", None)
        transition_route.condition = route_dict.get("condition", None)
        transition_route.target_page = route_dict.get("target_page", None)
        transition_route.target_flow = route_dict.get("target_flow", None)

        # fulfillment
        fulfillment = types.Fulfillment()
        fulfillment.webhook = route_dict.get("webhook", None)
        fulfillment.tag = route_dict.get("webhook_tag", None)

        custom_payload = route_dict.get("custom_payload", None)
        custom_payload_list = []
        if custom_payload:
            custom_payload = json.loads(custom_payload)
            if ~isinstance(custom_payload, list):
                custom_payload = [custom_payload]
            for single_payload in custom_payload:
                custom_payload_list.append({"payload": single_payload})

        fulfillment_text = route_dict.get("fulfillment_text", None)

        # custom payloads and text
        payload = {
            "messages": custom_payload_list
            + [{"text": {"text": fulfillment_text}}]
        }

        payload_json = json.dumps(payload)
        payload_json = json.dumps(payload)
        fulfillment = types.Fulfillment.from_json(payload_json)

        # parameter - presets
        set_param_actions = []
        parameter_presets = route_dict.get("parameter_presets", None)
        if parameter_presets:
            parameter_presets = json.loads(parameter_presets)
            for param in parameter_presets.keys():
                set_param_action = types.Fulfillment.SetParameterAction()
                set_param_action.parameter = param
                set_param_action.value = parameter_presets[param]
                set_param_actions.append(set_param_action)
        fulfillment.set_parameter_actions = set_param_actions
        transition_route.trigger_fulfillment = fulfillment

        return transition_route

    def bulk_create_route_group_from_dataframe(
        self, display_name, agent_id, flow_id, route_group_df, update_flag=False
    ):
        """create transition route - no support for end_session / just end flow.

        Args:
          display_name: name for the route group
          agent_id: agent id of target agent
          flow_id: flow id where to create route group
          route_group_df: dataframe with a routes data
            intent: intent id
            condition: string condition. ex.
              $session.params.dtmf_diy_opt_in = 1 AND
              $session.params.dtmf_2_techinternet = 2
            target_page: page id
            target_flow: flow id
            webhook: webhook id
            webhook_tag: string webhook tag
            custom_payload: a singular payload or list of payloads ex. [{}, {}]
            fulfillment_text: = list of text ["yo", "hi"]
            parameter_presets: = dictionary of parameter presets ex.
              {"param1":"value","param2":"othervalues"}
              update_flag: True to create the route group in the provided
                flow id

        Returns:
          rg: route group protobuf
        """
        if "intent" in route_group_df.columns:
            intents_map = self.intents.get_intents_map(
                agent_id=agent_id, reverse=True
            )
            route_group_df["intent"] = route_group_df.apply(
                lambda x: intents_map[x["intent"]], axis=1
            )

        if "target_flow" in route_group_df.columns:
            flows_map = self.flows.get_flows_map(
                agent_id=agent_id, reverse=True
            )
            route_group_df["target_flow"] = route_group_df.apply(
                lambda x: flows_map[x["target_flow"]], axis=1
            )

        if "target_page" in route_group_df.columns:
            pages_map = self.pages.get_pages_map(flow_id=flow_id, reverse=True)
            pages_map["End Flow"] = flow_id + "/pages/END_FLOW"
            route_group_df["target_page"] = route_group_df.apply(
                lambda x: pages_map[x["target_page"]], axis=1
            )

        transition_routes = []
        for _, row in route_group_df.iterrows():
            transition_route = self.create_transition_route_from_dataframe(row)
            transition_routes.append(transition_route)

        route_group = types.TransitionRouteGroup()
        route_group.display_name = display_name
        route_group.transition_routes = transition_routes

        if update_flag:
            self.route_groups.create_transition_route_group(
                flow_id=flow_id, obj=route_group
            )

        return route_group

    def sheets_to_dataframe(self, sheet_name, worksheet_name):
        """Move Intent/TP data from Google Sheets to a DataFrame."""
        scope = [
            "https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/drive",
        ]
        creds_gdrive = ServiceAccountCredentials.from_json_keyfile_name(
            self.creds_path, scope
        )
        client = gspread.authorize(creds_gdrive)
        g_sheets = client.open(sheet_name)
        sheet = g_sheets.worksheet(worksheet_name)
        data_pull = sheet.get_all_values()
        return pd.DataFrame(columns=data_pull[0], data=data_pull[1:])

    def dataframe_to_sheets(self, sheet_name, worksheet_name, dataframe):
        """Move Intent/TP data from a DataFrame to Google Sheets."""
        scope = [
            "https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/drive",
        ]
        creds_gdrive = ServiceAccountCredentials.from_json_keyfile_name(
            self.creds_path, scope
        )
        client = gspread.authorize(creds_gdrive)
        g_sheets = client.open(sheet_name)
        worksheet = g_sheets.worksheet(worksheet_name)
        set_with_dataframe(worksheet, dataframe)
