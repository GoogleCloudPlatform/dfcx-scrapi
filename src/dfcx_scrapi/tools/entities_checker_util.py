"""A set of Utility methods to check entities on DFCX Agents."""

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

import logging
from typing import Dict, List
from collections import Counter
from operator import attrgetter
import pandas as pd
import re
from google.cloud.dialogflowcx_v3beta1 import types
from dfcx_scrapi.core import scrapi_base
from dfcx_scrapi.core.flows import Flows
from dfcx_scrapi.core.pages import Pages
from dfcx_scrapi.core.intents import Intents
from dfcx_scrapi.core.entity_types import EntityTypes
from dfcx_scrapi.core.conversation import DialogflowConversation
from dfcx_scrapi.core.transition_route_groups import TransitionRouteGroups

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

class EntitiesCheckerUtil(scrapi_base.ScrapiBase):
    """Utility class for checking DFCX Agent's entities."""
    def __init__(
        self,
        agent_id: str,
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

        self.agent_id = agent_id
        self.creds_path = creds_path

    def _count_training_phrases(
        self,
        df: pd.DataFrame) -> Dict:
        """Counts the number of duplicate training phrases
        Args:
            df (pd.DataFrame): A DataFrame containing training phrases.
        Returns:
            Dict: A Dict with training phrase as key and count as a value.
        """
        grouped_tps_df = (
          df.groupby(["display_name"]).agg({"training_phrase":list})
        )
        training_phrases_mapper = grouped_tps_df.T.to_dict()
        tps_counter_dict = {
            intent:dict(Counter(tps["training_phrase"]))
            for intent, tps in training_phrases_mapper.items()
        }
        return tps_counter_dict

    def _add_is_duplicate_tp_column(
        self,
        df: pd.DataFrame) -> pd.DataFrame:
        """Add a column is_duplicate_tp that identify whether
        the training phrase is a duplicate or not
        Args:
            df (pd.DataFrame): A DataFrame containing training phrases.
        Returns:
            pd.DataFrame: A DataFrame with is_duplicate_tp column.
        """
        def _evaluate_duplicate(row: pd.Series, counter: Dict) -> bool:
            intent = row["display_name"]
            training_phrase = row["training_phrase"]
            count = counter[intent].get(training_phrase, None)
            return count > 1

        training_phrases_counter = self._count_training_phrases(df)
        df["is_duplicate_tp"] = [None] * len(df)
        df["is_duplicate_tp"] = (
            df
            .apply(
                _evaluate_duplicate,
                counter=training_phrases_counter,
                axis=1
            )
        )
        return df

    @staticmethod
    def _change_column_names(
        df: pd.DataFrame,
        columns: dict) -> pd.DataFrame:

        df = df.rename(
            columns=columns
        )

        return df

    def _create_entities_intents_df(
        self,
        bulk_intents_df: pd.DataFrame) -> pd.DataFrame:
        """Transforms bulk intent data into a DataFrame focused on entities.
        Converts a DataFrame of bulk intents into a format suitable for entity
        analysis.
        Args:
            bulk_intents_df (pd.DataFrame): A DataFrame containing bulk intent
            data.
        Returns:
            pd.DataFrame: A DataFrame with transformed entity information.
        """
        bulk_intents_df["training_phrase"] = bulk_intents_df.text
        df = (
            bulk_intents_df
            .groupby(
              ["name", "display_name", "training_phrase_idx"], as_index=False
              )
            .agg(
                {
                    "training_phrase":list,
                    "text":list,
                    "parameter_id":list,
                    "entity_type": list,
                    "is_list": list,
                }
            )
            .reset_index()
        )
        df["training_phrase"] = [
          "".join(map(str, text)) for text in df["training_phrase"]
          ]

        df = self._add_is_duplicate_tp_column(df)
        df = (
          df.explode(["text", "parameter_id", "entity_type", "is_list"])
          .reset_index(drop=True)
        )

        df = self._change_column_names(
            df=df,
            columns={
                "name":"intent_name",
                "display_name":"intent_display_name",
                "entity_type":"entity_type_name",
            })

        df = df[[
            "intent_name",
            "intent_display_name",
            "training_phrase",
            "is_duplicate_tp",
            "text",
            "parameter_id",
            "is_list",
            "entity_type_name",
        ]]

        return df

    def _create_entities_mapper(
        self,
        entities_df: pd.DataFrame,
        kind: str="KIND_MAP") -> Dict:
        """
        Creates a dictionary mapping entity display names to their entities
        for efficient lookup.
        Args:
            entities_df: A DataFrame containing entity information with columne
            like 'kind' and 'entities'.
            kind: A string value that describe the "kind" of the entity type.
        Returns:
            Dict: A dictionary mapping entity display names to their
            corresponding entity information.
        """
        if kind not in ["KIND_MAP", "KIND_REGEX", "KIND_LIST"]:
            raise UserWarning(
              "kind can only be 'KIND_MAP', 'KIND_REGEX','KIND_LIST'")
        kind_map_df = entities_df[entities_df["kind"].eq(kind)]

        return kind_map_df.set_index("entity_type_display_name").T.to_dict()

    def _unpack_nested_entities(
        self,
        entities_df: pd.DataFrame) -> pd.DataFrame:
        """Unpacks nested entities within a DataFrame. Processes a DataFrame
        containing entity types, potentially with nested entities, and flattens
        the structure. Replaces nested entity references with their
        corresponding entity values.
        Args:
            entities_df: A DataFrame containing entity type
            information, possibly with nested entities.
        Returns:
            pd.DataFrame: A DataFrame with nested entities replaced by their
            corresponding values.
        """

        def _update_nested_entities(parent_entities: dict, mapper: dict):
            new_entities = {}
            for child in parent_entities.keys():
                if child.startswith("@"):
                    child_entity_type = child[1:]
                    child_entities = mapper.get(child_entity_type, None)
                    if child_entities:
                        new_entities.update(child_entities["entities"])
            return new_entities

        entities_mapper = self._create_entities_mapper(entities_df.copy())
        kind_list_df = entities_df[entities_df["kind"].eq("KIND_LIST")]
        other_entities_df = (
          entities_df[entities_df["kind"].isin(["KIND_MAP", "KIND_REGEXP"])]
        )
        updated_entities = kind_list_df.entities.apply(
                _update_nested_entities, mapper=entities_mapper
            )
        kind_list_df = kind_list_df.assign(entities=updated_entities)
        df = pd.concat([kind_list_df, other_entities_df]).reset_index(drop=True)

        return df

    def _create_entities_df(
        self,
        entity_types_df: pd.DataFrame) -> pd.DataFrame:
        """Creates a DataFrame of entities and their synonyms. Aggregates
        entity type information, groups by entity type, and constructs a
        DataFrame with entity values and their corresponding synonyms.
        Args:
            entity_types_df: A DataFrame containing entity type information.
        Returns:
            pd.DataFrame: A DataFrame with columns for entity type name,
            display name, kind, and a dictionary of entity values and synonyms.
        """
        df = (
            entity_types_df
            .groupby(
                [
                    "entity_type_id",
                    "display_name",
                    "kind",
                    "entity_value"
                ]
            )
            .agg({"synonyms": list})
            .reset_index()
        )
        df = (
            df
            .groupby(["entity_type_id", "display_name", "kind"])
            .apply(lambda x: dict(zip(x["entity_value"], x["synonyms"])))
            .reset_index()
        )
        df = self._change_column_names(
            df=df.copy(),
            columns={
                "entity_type_id":"entity_type_name",
                "display_name":"entity_type_display_name",
                0:"entities"
            }
        )

        return df

    def _validate_tagged_entity_labels(self, df: pd.DataFrame) -> pd.DataFrame:
        """Validates entity labels in a DataFrame and assigns flags and expected
        parameters. This function iterates through a DataFrame containing text
        and entity information. It assigns a boolean flag ('is_valid_entity')
        indicating if the entity label is valid and a dictionary
        ('expected_parameter') containing expected parameters for the entity.
        Args:
            df: A DataFrame containing text, entity type names, and optional
            additional columns.
        Returns:
            pd.DataFrame: The original DataFrame with added columns
            'is_valid_entity' and 'expected_parameter'.
        """
        def _has_valid_entity(row: pd.Series):
            text = row["text"].lower().strip()
            entities = row["entities"]
            parameter_id = row["parameter_id"]
            is_list = row["is_list"]

            for entity_value, synonyms in entities.items():
                for synonym in synonyms:
                    if text == synonym.lower().strip():
                        row["is_valid_entity"] = True
                        row["expected_parameter"] = (
                            {parameter_id: [entity_value]}
                            if is_list else {parameter_id: entity_value}
                        )
                        break
            return row

        df["is_valid_entity"] = [False] * len(df)
        df["expected_parameter"] = [{}] * len(df)
        df = df.apply(_has_valid_entity, axis=1)

        return df

    def extract_entities_in_intents_df(
        self,
        agent_id: str) -> pd.DataFrame:
        """Extracts a dataframe containing information about entities in Intents
        Args:
            agent_id: The ID of the Dialogflow CX agent.
        Returns:
            pd.DataFrame: A DataFrame containing data about entities in Intents
        """
        dfcx_intents = Intents(creds_path=self.creds_path, agent_id=agent_id)
        bulk_intents_df = dfcx_intents.bulk_intent_to_df(mode="advanced")
        df = self._create_entities_intents_df(bulk_intents_df=bulk_intents_df)

        return df

    def extract_entities_df(
        self,
        agent_id: str,
        unpack_synonyms: bool=False) -> pd.DataFrame:
        """Extracts a dataframe containing data about entities in Entity types
        Args:
            agent_id: The ID of the Dialogflow CX agent.
        Returns:
            pd.DataFrame: A DataFrame containing data about entities in
            Entity types
        """

        dfcx_entitytypes = EntityTypes(
          creds_path=self.creds_path, agent_id=agent_id
        )
        entity_types_df = (
            dfcx_entitytypes.entity_types_to_df(mode="advanced")["entity_types"]
        )
        df = self._create_entities_df(entity_types_df=entity_types_df)
        if unpack_synonyms:
            df = self._unpack_nested_entities(df)

        return df

    def _get_flows_df(self, agent_id: str) -> pd.DataFrame:
        """Retrieves a DataFrame containing information about DFCX flows
        Args:
          agent_id: The ID of the Dialogflow CX agent.
        Returns:
          pd.DataFrame: A DataFrame containing data about the agent's flows.
        """
        dfcx_flows = Flows(creds_path=self.creds_path, agent_id=agent_id)
        flows_list = dfcx_flows.list_flows(agent_id=agent_id)
        flows_df = pd.DataFrame(
            [
                {
                    "flow_display_name": flow.display_name,
                    "flow_name": flow.name,
                    "page_name": f"{flow.name}/START_PAGE",
                    "route_groups": flow.transition_route_groups,
                    "routes": flow.transition_routes,
                }
                for flow in flows_list
            ]
        )

        return flows_df

    def _get_pages_df(self, flows_df: pd.DataFrame) -> pd.DataFrame:
        """
        Retrieves a DataFrame containing information about DFCX pages associated
        with flows.
        Args:
          flows_df (pd.DataFrame): A DataFrame containing data aboutDFCX flows.
          This DataFrame should have columns of'flow_display_name' and
          'flow_name'.
        Returns:
          pd.DataFrame: A DataFrame containing detailed data about pages
          associated with the flows.
        """
        dfcx_pages = Pages(creds_path=self.creds_path)
        pages_df = (
            flows_df[["flow_display_name", "flow_name"]]
            .assign(page_obj=flows_df.flow_name.apply(dfcx_pages.list_pages))
            .explode("page_obj", ignore_index=True)
        )
        pages_df = pages_df[~pages_df.page_obj.isna()]
        pages_df = pages_df.assign(
            page_display_name=lambda df: df.page_obj.apply(
                attrgetter("display_name")
            ),
            page_name=lambda df: df.page_obj.apply(
                attrgetter("name")
            ),
            parameters=lambda df: df.page_obj.apply(
                attrgetter("form.parameters")
            ),
            route_groups=lambda df: df.page_obj.apply(
                attrgetter("transition_route_groups")
            ),
            routes=lambda df: df.page_obj.apply(
                attrgetter("transition_routes")
            ),
        )
        pages_df = pages_df.drop(columns="page_obj")
        pages_df = (
            pd.concat(
                [
                    flows_df.assign(page_display_name="START_PAGE"),
                    pages_df
                ],ignore_index=True)
            .drop(columns="flow_name")
        )

        return pages_df

    def _get_trgs_df(self, flows_df: pd.DataFrame):
        """Extracts Transition Route Groups (TRGs) from a DataFrame of flows.
        Retrieves TRGs for each flow in the input DataFrame and creates a new
        DataFrame with extracted TRG objects.
        Args:
            flows_df (pd.DataFrame): A DataFrame containing flow names.
        Returns:
            pd.DataFrame: A DataFrame with 'flow_name' and 'trgs_obj' columns,
            where 'trgs_obj' contains TRG objects.
        """
        dfcx_trgs = TransitionRouteGroups(creds_path=self.creds_path)
        df = (
            flows_df[["flow_name"]]
            .assign(
              trgs_obj=flows_df.flow_name.apply(
                dfcx_trgs.list_transition_route_groups
                )
              )
            .explode("trgs_obj", ignore_index=True)
        )

        return df

    def _get_intent_routes_from_trg(
        self,
        trg_obj: types.TransitionRouteGroup,
        intents_map: dict) -> List:
        """
        Extracts intent routes from a TransitionRouteGroup object.
        Args:
          trg_obj: A TransitionRouteGroup object containing route information.
          intents_map: A dictionary mapping intent keys to display names.
        Returns:
          A list of dictionaries representing intent routes with conditions.
        """
        intent_routes = []
        for route in trg_obj.transition_routes:
            if not route.intent:
                continue
            intent_display_name = intents_map.get(route.intent)
            if route.condition:
                intent_routes.append({
                    intent_display_name: self._convert_param_str_to_dict(
                        route.condition
                    )
                })
            else:
                intent_routes.append({intent_display_name: {}})

        return intent_routes

    def _get_conditional_routes_from_trg(
        self,
        trg_obj: types.TransitionRouteGroup) -> List:
        """Extracts conditional routes from a TransitionRouteGroup object.
        Iterates through the transition routes within the TRG object, extracting
        and converting conditions to dictionaries.
        Args:
            trg_obj: The TransitionRouteGroup object to process.
        Returns:
            List[Dict[str, str]]: A list of dictionaries representing the
            extracted conditions.
        """
        conditions = []
        for route in trg_obj.transition_routes:
            if route.condition:
                conditions.append(
                    self._convert_param_str_to_dict(route.condition)
                )

        return conditions

    def _get_trgs_intents_mapper(
        self,
        flows_df: pd.DataFrame,
        intents_map: dict) -> Dict:
        """Extracts intent information from Transition Route Groups (TRGs)
        associated with flows. Processes a DataFrame containing flows,
        identifies TRGs, and retrieves associated intent routes. Filters for
        TRGs with valid intent routes, and constructs a mapping of TRG names to
        their intent information.
        Args:
            flows_df: A DataFrame containing a 'flow_name' column.
            intents_map: A dictionary mapping intent keys to display names.
        Returns:
            Dict[str, Dict]: A dictionary mapping TRG names to dictionaries
            containing extracted intent information.
        """
        df = self._get_trgs_df(flows_df)
        trgs_df = df[~df.trgs_obj.isna()]
        trgs_df = trgs_df.assign(
            trg_name=lambda df: df.trgs_obj.apply(
                attrgetter("name")
            ),
            trg_display_name=lambda df: df.trgs_obj.apply(
                attrgetter("display_name")
            ),
            intent_routes=lambda df: df.trgs_obj.apply(
                self._get_intent_routes_from_trg, intents_map=intents_map
            ),
            conditional_routes=lambda df:df.trgs_obj.apply(
                self._get_conditional_routes_from_trg
            )
        )
        trgs_df = (
            trgs_df
            .copy()
            .loc[trgs_df.intent_routes.map(len) > 0]
            .drop(columns=["flow_name", "trgs_obj"])
            .reset_index(drop=True)
        )

        trgs_map = trgs_df.set_index("trg_name").T.to_dict()

        return trgs_map

    @staticmethod
    def _convert_param_str_to_dict(condition) -> Dict[str, str]:
        """Converts a condition string to a dictionary of key-value pairs.
        Parses a condition string containing key-value pairs separated by
        'AND' or 'OR' operators. Extracts key-value pairs, handling potential
        errors and invalid characters.
        Args:
            condition: The condition string to be converted.
        Returns:
            Dict[str, str]: A dictionary mapping keys to their corresponding
            values, or an empty dictionary if parsing fails.
        """
        data_dict = {}
        conditions = re.split(r"AND|OR", condition)
        disallowed_chars = {"!", "<", ">"}
        for cond in conditions:
            if any(char in cond for char in disallowed_chars):
                continue
            try:
                key, value = cond.strip().split("=")
                key = key.split(".")[-1].replace(" ", "")
                value = value.replace(" ", "").strip('"').strip("'")
                if value not in ("", "null"):
                    data_dict[key] = value
            except ValueError:
                pass

        return data_dict

    def _unpack_route_objs(
        self,
        row: pd.Series,
        intents_map: dict):
        """
        Unpacks route objects into lists of intent display names and conditions.
        Args:
          row: A pandas Series containing route data.
          intents_map: A dictionary mapping intent keys to display names.
        Returns:
          An updated "intent_display_name" and "condition" columns.
        """
        routes = row["routes"]
        intents, conditions = [], []
        for route in routes:
            if route.intent:
                intent_display_name = intents_map.get(route.intent)
                if intent_display_name:
                    intents.append(intent_display_name)
                    conditions.append({})
                if route.condition:
                    condition_dict = (
                        self._convert_param_str_to_dict(
                          condition=route.condition
                          )
                    )
                    if condition_dict:
                        conditions[-1] = condition_dict
        row["intent_display_name"] = intents
        row["condition"] = conditions

        return row

    def _extract_intents_by_trg_name(
        self,
        row: pd.Series,
        trgs_map: dict) -> pd.Series:
        """
        Extract a route group id into lists of intent display names and
        conditions.
        Args:
          row: A pandas Series containing route group data.
          trgs_map: A dictionary mapping route group keys to a list of intent
          routes
        Returns:
          pd.Series: An updated "intent_display_name" and "condition" row.
        """
        trg_name = row["route_groups"]
        intent_routes, intents, conditions = [], [], []

        intent_routes = trgs_map.get(trg_name)
        if not intent_routes:
            return row

        for intent_route in intent_routes.get("intent_routes"):
            intent, condition = next(iter(intent_route.items()))
            intents.append(intent)
            conditions.append(condition)
            if isinstance(condition, str):
                conditions[-1] = self._convert_param_str_to_dict(
                    condition=condition
                    )
        row["intent_display_name"] = intents
        row["condition"] = conditions
        row["route_group"] = trgs_map.get(trg_name)["trg_display_name"]

        return row

    def _get_intents_from_route_groups(
        self,
        pages_df: pd.DataFrame,
        trgs_map: dict) -> pd.DataFrame:
        """
        Extracts intents and conditions from route groups in a DataFrame.
        Args:
          pages_df: A DataFrame containing route group data.
          trgs_map: A dictionary mapping route group keys to information.
        Returns:
          A DataFrame with extracted intents, conditions, and route type data.
        """
        df = (
            pages_df
            .drop(columns="routes")
            .loc[pages_df.route_groups.map(len) > 0]
            .explode("route_groups")
        )
        df = df.assign(
            intent_display_name=[[]] * len(df),
            condition=[[]] * len(df),
            route_type=["transition_route_group"] * len(df),
            route_group=[""] * len(df),
        )
        intents_from_route_groups_df = (
            df
            .copy()
            .apply(
                self._extract_intents_by_trg_name,
                trgs_map=trgs_map,
                axis=1
            )
        )

        return (
            intents_from_route_groups_df
            .explode(["intent_display_name", "condition"])
            .loc[lambda d: ~d["intent_display_name"].isna()]
            .drop(columns="route_groups")
            .reset_index(drop=True)
        )

    def _get_intents_from_routes(
        self,
        pages_df: pd.DataFrame,
        intents_map: dict) -> pd.DataFrame:
        """
        Extracts intents and conditions from transition routes in a DataFrame.
        Args:
          pages_df: A DataFrame containing transition route data.
          trgs_map: A dictionary mapping transition route keys to information.
        Returns:
          A DataFrame with extracted intents, conditions, and route type data.
        """
        df = (
            pages_df
            .drop(columns="route_groups")
            .loc[pages_df.routes.map(len) > 0]
        )
        df = df.assign(
            intent_display_name=[[]] * len(df),
            condition=[[]] * len(df),
            route_type=["transition_route"] * len(df),
            route_group=[""] * len(df),
        )
        intents_from_routes_df = (
            df
            .copy()
            .apply(
                self._unpack_route_objs,
                intents_map=intents_map,
                axis=1
            )
        )

        return (
            intents_from_routes_df
            .explode(["intent_display_name", "condition"])
            .loc[lambda d: ~d["intent_display_name"].isna()]
            .drop(columns="routes")
            .reset_index(drop=True)
        )

    def get_entities_in_pages(self, agent_id: str=None):
        """Extracts entities from page parameters. Retrieves page and flow data
        for the specified agent. Identifies and extracts entities from non-empty
        page parameters.
        Args:
            agent_id: The ID of the agent otherwise, Defaults to self.agent_id.
        Returns:
            pd.DataFrame: A DataFrame containing extracted entities from page
            parameters, including data like parameter ID, entity type name,
            required flag, and entity type display name.
        """
        if not agent_id:
            agent_id = self.agent_id

        flows_df = self._get_flows_df(agent_id=agent_id)
        pages_df = self._get_pages_df(flows_df=flows_df)
        pages_df = pages_df.loc[(~pages_df.parameters.isna())]
        pages_df = (
            pages_df
            .loc[pages_df.parameters.map(len) > 0]
            .explode(["parameters"])
            .reset_index(drop=True)
        )
        df = pages_df.assign(
            parameter_id=lambda df:df.parameters.apply(
                attrgetter("display_name")
            ),
            entity_type_name=lambda df:df.parameters.apply(
                attrgetter("entity_type")
            ),
            isrequired=lambda df:df.parameters.apply(
                attrgetter("required")
            )
        )
        df = df.drop(columns="parameters")
        et = EntityTypes(creds_path=self.creds_path, agent_id=agent_id)
        entity_types_map = et.get_entities_map()
        df["entity_type_display_name"] = (
            df["entity_type_name"]
            .apply(entity_types_map.get)
        )

        return df

    def get_intent_routes_from_pages(
        self,
        agent_id: str=None) -> pd.DataFrame:
        """Extracts intent information from page routes and route groups.
        Retrieves pages, flows, and intents data, then processes routes and
        route groups to extract intent information.
        Args:
            agent_id: The ID of the agent otherwise,Defaults to self.agent_id.
        Returns:
            pd.DataFrame: A DataFrame containing extracted intent data from
            pages.
        """
        if not agent_id:
            agent_id = self.agent_id
        flows_df = self._get_flows_df(agent_id=agent_id)
        pages_df = self._get_pages_df(flows_df)
        dfcx_intents = Intents(creds_path=self.creds_path, agent_id=agent_id)
        intents_map = dfcx_intents.get_intents_map()
        trgs_map = self._get_trgs_intents_mapper(flows_df, intents_map)
        df = pages_df.drop(columns="parameters")
        intents_from_routes_df = self._get_intents_from_routes(
            pages_df=df, intents_map=intents_map
        )
        intents_from_route_groups_df = self._get_intents_from_route_groups(
            pages_df=df, trgs_map=trgs_map
        )
        all_intents_df = (
            pd.concat([intents_from_routes_df, intents_from_route_groups_df])
            .reset_index(drop=True)
        )

        return all_intents_df

    def _get_conditional_routes_from_pages(
        self,
        df: pd.DataFrame) -> pd.DataFrame:
        """Extracts and expands conditional routes from a DataFrame. Processes
        the 'routes' column, extracting conditions and creating a new row for
        each condition.
        Args:
            df: A DataFrame containing 'routes' and potentially 'route_groups'
            columns.
        Returns:
            pd.DataFrame: The input DataFrame with expanded 'routes' column,
            containing one condition per row.
        """
        def _get_conditions_from_routes(routes: list):
            list_routes = []
            for route in routes:
                if route.condition:
                    list_routes.append(route.condition)
            return list_routes

        if "routes" not in df.columns and "route_groups" not in df.columns:
            raise UserWarning(
                "The given df requires to have routes and route_groups columns"
            )
        routes = df.routes.apply(_get_conditions_from_routes)
        df["routes"] = routes
        df = df.explode("routes").reset_index(drop=True)

        return df

    def validate_entities_in_intents(
        self,
        agent_id: str=None) -> pd.DataFrame:
        """Validates entities within intents. Compares extracted entities from
        intents with a broader entity dataset to identify potential
        inconsistencies or errors.
        Args:
            agent_id: The ID of the agent otherwise, Defaults to self.agent_id.
        Returns:
            pd.DataFrame: A DataFrame containing validation results for entities
            within intents, including information about intent, training phrase,
            entity type, and validation status.
        """
        if not agent_id:
            agent_id = self.agent_id

        entities_intents_df = self.extract_entities_in_intents_df(
          agent_id=agent_id
        )
        entities_df = self.extract_entities_df(
          agent_id=agent_id, unpack_synonyms=True)
        data_df = entities_intents_df.merge(
            entities_df, on="entity_type_name", how="left")
        data_df = data_df.dropna(subset=["entities"])
        data_df = (
          data_df
          .loc[~data_df.entity_type_display_name.isna()]
          .reset_index(drop=True)
        )
        df = self._validate_tagged_entity_labels(data_df)
        df = df[
                [
                    "intent_display_name",
                    "training_phrase",
                    "is_duplicate_tp",
                    "text",
                    "parameter_id",
                    "is_list",
                    "entity_type_display_name",
                    "kind",
                    "is_valid_entity",
                    "expected_parameter",
                ]
            ]

        return df

    def _get_conditons_from_routes(
        self,
        routes: List) -> List:
        """Extracts conditions from a list of routes.Iterates through the
        provided routes, extracting and converting conditions into dictionaries.
        Args:
            routes: A list of route objects containing condition data.
        Returns:
            List: A list of condition dictionaries.
        """
        all_routes = []

        if routes:
            for route in routes:
                if route.condition:
                    condition_dict = self._convert_param_str_to_dict(
                      route.condition)
                    all_routes.append(condition_dict)

        return all_routes

    def _get_conditions_from_route_groups(
        self,
        route_groups: List,
        trgs_map: Dict) -> List:
        """Extracts conditional routes from a list of target IDs.
        Retrieves conditional routes for each target ID from the provided
        `trgs_map` and combines them into a single list.
        Args:
            route_groups (List): A list of target IDs.
            trgs_map (Dict): A mapping of target IDs to their corresponding
            data, including conditional routes.
        Returns:
            List: A combined list of conditional routes from all specified IDs.
        """
        all_routes = []
        for trg_id in route_groups:
            trg = trgs_map.get(trg_id)
            if trg:
                all_routes = all_routes + trg["conditional_routes"]
        return all_routes

    def _extract_to_synonyms(
        self,
        entities_df: pd.DataFrame,
        in_synonyms: bool=True) -> pd.DataFrame:
        """Extracts entity synonyms from dictionaries within the DataFrame.
        Filters entities based on type (KIND_LIST or KIND_MAP) and extracts both
        keys and values as separate columns (entity and synonyms).
        Args:
            entities_df: A DataFrame containing an 'entities' column with
            dictionary values.
            in_synonyms: If True, A DataFrame has 'synonyms' column with a list
            of synonyms. If False, A DataFrame has 'synonym' column with a
            synonym in a string value.
        Returns:
            pd.DataFrame: A DataFrame with extracted entity and synonym columns,
            potentially exploded based on the 'in_synonyms' parameter.
        """
        entities_df=entities_df.loc[entities_df.entities.map(len) > 0]
        entities_df = (
          entities_df.loc[entities_df.kind.isin(["KIND_LIST", "KIND_MAP"])]
        )
        entities_df = entities_df.assign(
            entity=entities_df.entities.apply(
              lambda e: [k for k, v in e.items()]),
            synonyms=entities_df.entities.apply(
              lambda e: [v for k, v in e.items()]),
        ).drop(columns="entities")
        entities_df = (
          entities_df.explode(["entity", "synonyms"]).reset_index(drop=True)
        )
        if not in_synonyms:
            entities_df = (
              self._change_column_names(
                df=entities_df, columns={"synonyms": "synonym"})
            )
            entities_df = entities_df.explode("synonym").reset_index(drop=True)

        return entities_df

    def _evaluate_routes(
      self,
      df: pd.DataFrame,
      agent_id: str=None) -> pd.DataFrame:
        """Extracts and transforms route information for subsequent analysis.
        Calculates conditional routes and conditional routes in target intents
        based on the provided DataFrame.
        Args:
            df: A DataFrame containing route and route_group data.
            agent_id: The ID of the agent otherwise, Defaults to self.agent_id.
        Returns:
            pd.DataFrame: The input DataFrame with added 'conditional_routes'
            and 'conditional_routes_in_trg' columns.
        """
        if not agent_id:
            agent_id = self.agent_id
        flows_df = self._get_flows_df(agent_id=agent_id)
        dfcx_intents = Intents(creds_path=self.creds_path, agent_id=agent_id)
        intents_map = dfcx_intents.get_intents_map()
        trgs_map = self._get_trgs_intents_mapper(flows_df, intents_map)

        df = df.assign(
            conditional_routes=df.routes.apply(
                self._get_conditons_from_routes
            ),
            conditional_routes_in_trg=df.route_groups.apply(
                self._get_conditions_from_route_groups, trgs_map=trgs_map
            )
        ).drop(columns=["routes", "route_groups"])

        return df

    def _evaluate_results(self, df: pd.DataFrame):
        """Evaluates entity detection results. Compares expected and actual
        parameters for each row, determining if entity was correctly captured.
        Args:
            df (pd.DataFrame): A DataFrame containing entity, parameter_id, and
            parameters_set data.
        Returns:
            pd.DataFrame: The input DataFrame with an additional 'result' column
            indicating 'PASS' or 'FAIL'.
        """
        def _evaluate_parameter_output(row: pd.Series):
            parameter_id = row["parameter_id"].lower()
            entity = row["entity"].lower()
            captured_parameters = row["parameters_set"]
            if captured_parameters:
                for param, value in captured_parameters.items():
                    if (param.lower() == parameter_id and
                    value.lower() == entity):
                        return "PASS"
            return "FAIL"

        df = df.assign(
            result=df.apply(
                _evaluate_parameter_output, axis=1
            )
        )

        return df

    def test_entities_detection(self, agent_id: str=None) -> pd.DataFrame:
        """Validates entity detection in agent pages. Compares expected and
        actual match types and captured parameters for each entity.
        Args:
            agent_id: The ID of the agent otherwise, Defaults to self.agent_id.
        Returns:
            pd.DataFrame: A DataFrame containing the results of the entity
            detection test, indicating pass or fail for each entity.
        """
        if not agent_id:
            agent_id=self.agent_id

        entities_df = self.extract_entities_df(
          agent_id=agent_id, unpack_synonyms=True)
        entities_df = (
            self._extract_to_synonyms(
              entities_df=entities_df, in_synonyms=False)
            .drop(columns="entity_type_display_name")
        )
        pages_mapper_df = self.get_entities_in_pages(agent_id=agent_id)
        df = (
            pages_mapper_df
            .merge(entities_df, on="entity_type_name", how="left")
            .drop(columns=["route_groups", "routes"])
        )
        df = df.loc[~df.synonym.isna()].reset_index(drop=True)
        df = self._change_column_names(df=df, columns={"synonym": "utterance"})
        dfcx_dc = DialogflowConversation(
          creds_path=self.creds_path, agent_id=agent_id)
        results = dfcx_dc.run_intent_detection(test_set=df)
        results = self._evaluate_results(results)

        return results

    def _has_expected_route(self, row: pd.Series) -> bool:
        """Determines if a given row has an expected route based on its entity
        and parameter. Checks if the entity value matches the expected value
        for the parameter in either conditional_routes or
        conditional_routes_in_trg.
        Args:
            row: A row from the DataFrame containing entity, parameter_id,
            conditional_routes, and conditional_routes_in_trg data.
        Returns:
            bool: True if an expected route exists, False otherwise.
        """
        def check_routes(routes):
            if isinstance(row["entity"], float):
                return False
            if routes:
                for route in routes:
                    if isinstance(route, dict) and bool(route):
                        param, value = route.copy().popitem()
                        param = param.lower()
                        value = value.lower()
                        if (row["parameter_id"].lower() == param and
                            row["entity"].replace(" ", "").lower() == value
                           ):
                            return True
            return False
        return (check_routes(row["conditional_routes"]) or
                check_routes(row["conditional_routes_in_trg"]))

    def validate_page_transitions_with_entities(
      self,
      agent_id: str=None) -> pd.DataFrame:
        """Validates page transition routes based on predefined entities.
        Ensures that the bot performs an action after capturing the expected
        entity.
        Args:
            agent_id: The ID of the agent otherwise, Defaults to self.agent_id.
        Returns:
            pd.DataFrame: A DataFrame containing validation results,
            'has_route', indicating whether expected routes exist for required
            entities.
        """
        if not agent_id:
            agent_id=self.agent_id
        entities_df = self.extract_entities_df(
          agent_id=agent_id, unpack_synonyms=True)
        entities_df = (
            self._extract_to_synonyms(entities_df)
            .drop(columns="entity_type_display_name")
        )
        pages_mapper_df = self.get_entities_in_pages(agent_id=agent_id)
        df = (
          pages_mapper_df.merge(entities_df, on="entity_type_name", how="left")
        )
        df = self._evaluate_routes(df)
        df = df.loc[df.isrequired]
        df = df.assign(
            has_route=df.apply(
                self._has_expected_route, axis=1
            )
        )

        return df
