"""A set of builder methods to create CX proto resource objects"""

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
from typing import List, Dict, Union, Any

import pandas as pd
from google.cloud.dialogflowcx_v3beta1.types import TransitionRoute
from google.cloud.dialogflowcx_v3beta1.types import EventHandler

# logging config
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


class BuildersCommon:
    """Base class for other Builder classes"""

    _proto_type = None
    _proto_type_str = "None"


    def __init__(self, obj=None):
        self.proto_obj = None
        if obj is not None:
            self.load_proto_obj(obj)

        self._dataframe_instance = self._Dataframe(self)


    def _check_proto_obj_attr_exist(self):
        """Check if the proto_obj exists otherwise raise an error."""
        if self.proto_obj is None:
            raise ValueError(
                "There is no proto_obj!"
                "\nUse `create_new_proto_obj` or `load_proto_obj` to continue."
            )
        elif not isinstance(self.proto_obj, self._proto_type):  # pylint: disable=W1116
            raise ValueError(
                f"proto_obj is not {self._proto_type_str} type."
                "\nPlease create or load the correct type to continue."
            )


    def load_proto_obj(self, obj, overwrite: bool = False):
        """Load an existing object to proto_obj for further uses.

        Args:
          obj (proto object):
            An existing proto object.
          overwrite (bool)
            Overwrite the new proto_obj if proto_obj already
            contains some object.

        Returns:
          An object stored in proto_obj
        """
        if not isinstance(obj, self._proto_type):  # pylint: disable=W1116
            raise ValueError(
                "The object you're trying to load"
                f" is not {self._proto_type_str}!"
            )
        if self.proto_obj and not overwrite:
            raise UserWarning(
                f"proto_obj already contains {self._proto_type_str}."
                " If you wish to overwrite it, pass overwrite as True."
            )

        if overwrite or not self.proto_obj:
            self.proto_obj = obj

        return self.proto_obj


    def _is_type_or_list_of_types(self, obj, type_, var_name: str = None):
        """Check whether the `obj` type is `type_` or
        is a list with elements of `type_` otherwise raise an error.

        Args:
            obj:
              The object to check
            type_:
              Type of `obj`
            var_name (str):
              The variable name to show in the error message.

        Raises:
            ValueError: If the `obj` type is not `type_` or a list of `type_`s.
        """
        default_error_msg = "Incorrect type!!"
        error_msg_map = {
            str: (
                f"`{var_name}` should be either a string or a list of strings."
            ),
            EventHandler: (
                f"`{var_name}` should be either a EventHandler"
                " or a list of EventHandlers."
            ),
            TransitionRoute: (
                f"`{var_name}` should be either a TransitionRoute"
                " or a list of TransitionRoutes."
            ),
        }

        if not(
            isinstance(obj, type_) or
            (isinstance(obj, list) and
             all(isinstance(item, type_) for item in obj))
        ):
            msg = error_msg_map.get(obj, default_error_msg)
            raise ValueError(msg)


    def _match_transition_route(
        self,
        transition_route: TransitionRoute,
        target_route: TransitionRoute = None,
        intent: str = None,
        condition: str = None
    ) -> bool:
        """Check if transition_route's intent and condition
        matches with the input.

        At least one of the `target_route`, `intent`, or `condition` should
        be specfied.

        Args:
            transition_route (TransitionRoute):
              The TransitionRoute that input should match with.
            taget_route (TransitionRoute):
              The target TransitionRoute that we want to match.
            intent (str):
              TransitionRoute's intent that we want to match.
            condition (str):
              TransitionRoute's condition that we want to match.

        Returns:
            True if the `transition_route` matched with the input.
        """
        # Type/Error checking
        if not isinstance(transition_route, TransitionRoute):
            raise ValueError(
                "`transition_route` should have the type TransitionRoute."
            )
        if not(target_route or intent or condition):
            raise ValueError(
                "At least one of `target_route`, `intent`, or `condition`"
                " must be specified."
            )

        # Check if the transition route matches
        is_match = False
        if target_route:
            is_match = self._check_transition_route_with_target_route(
                transition_route, target_route
            )
        if intent and condition:
            is_match = self._check_transition_route_with_intent_and_condition(
                transition_route, intent, condition
            )
        elif intent and not condition:
            is_match = self._check_transition_route_with_intent(
                transition_route, intent
            )
        elif not intent and condition:
            is_match = self._check_transition_route_with_condition(
                transition_route, condition
            )

        return is_match


    def _check_transition_route_with_target_route(
        self,
        transition_route: TransitionRoute,
        target_route: TransitionRoute
    ) -> bool:
        """Check if transition_route's intent and condition
        matches with the target_route's intent and condition.

        Args:
            transition_route (TransitionRoute):
              The TransitionRoute that input should match with.
            taget_route (TransitionRoute):
              The target TransitionRoute that we want to match.

        Returns:
            True if the `transition_route` matched with the input.
        """
        # Type/Error checking
        if not isinstance(target_route, TransitionRoute):
            raise ValueError("`target_route` should be a TransitionRoute.")

        if (
            transition_route.condition == target_route.condition and
            transition_route.intent == target_route.intent
        ):
            return True
        return False


    def _check_transition_route_with_intent_and_condition(
        self,
        transition_route: TransitionRoute,
        intent: str,
        condition: str
    ) -> bool:
        """Check if transition_route's intent and condition
        matches with the input.

        Args:
            transition_route (TransitionRoute):
              The TransitionRoute that input should match with.
            intent (str):
              TransitionRoute's intent that we want to match.
            condition (str):
              TransitionRoute's condition that we want to match.

        Returns:
            True if the `transition_route` matched with the input.
        """
        # Type/Error checking
        if not(isinstance(intent, str) and isinstance(condition, str)):
            raise ValueError("`intent` and `condition` should be a string.")

        if (
            transition_route.condition == condition and
            transition_route.intent == intent
        ):
            return True
        return False


    def _check_transition_route_with_intent(
        self,
        transition_route: TransitionRoute,
        intent: str
    ) -> bool:
        """Check if transition_route's intent matches with the input.

        Args:
            transition_route (TransitionRoute):
              The TransitionRoute that input should match with.
            intent (str):
              TransitionRoute's intent that we want to match.

        Returns:
            True if the `transition_route` matched with the input.
        """
        # Type/Error checking
        if not isinstance(intent, str):
            raise ValueError("`intent` should be a string.")

        if transition_route.intent == intent:
            return True
        return False


    def _check_transition_route_with_condition(
        self,
        transition_route: TransitionRoute,
        condition: str
    ) -> bool:
        """Check if transition_route's condition matches with the input.

        Args:
            transition_route (TransitionRoute):
              The TransitionRoute that input should match with.
            condition (str):
              TransitionRoute's condition that we want to match.

        Returns:
            True if the `transition_route` matched with the input.
        """
        # Type/Error checking
        if not isinstance(condition, str):
            raise ValueError("`condition` should be a string.")

        if transition_route.condition == condition:
            return True
        return False


    def _find_unmatched_event_handlers(
        self, event_handlers: Union[EventHandler, List[EventHandler]]
    ) -> List[EventHandler]:
        """Find the EventHandlers of proto_obj which is not present
        in the `event_handlers`

        Args:
          event_handlers (EventHandler | List[EventHandler]):
            A single or list of EventHandler to remove
              from the existing EventHandlers in proto_obj.

        Returns:
          A list of EventHandlers
        """
        # Type error checking
        self._is_type_or_list_of_types(
            event_handlers, EventHandler, "event_handlers"
        )

        if not isinstance(event_handlers, list):
            event_handlers = [event_handlers]

        return [
            eh
            for eh in self.proto_obj.event_handlers
            if eh not in event_handlers
        ]


    def _find_unmatched_event_handlers_by_name(
        self, event_names: Union[str, List[str]]
    ) -> List[EventHandler]:
        """Find the EventHandlers of proto_obj which their event names
        is not present in the `event_names`

        Args:
          event_names (str | List[str]):
            A single or list of EventHandler's event names corresponding
              to the EventHandler to remove from the existing
              EventHandlers in proto_obj.

        Returns:
          A list of EventHandlers
        """
        # Type error checking
        self._is_type_or_list_of_types(event_names, str, "event_names")

        if not isinstance(event_names, list):
            event_names = [event_names]

        return [
            eh
            for eh in self.proto_obj.event_handlers
            if eh.event not in event_names
        ]


    def to_dataframe(self, mode: str = "basic") -> pd.DataFrame:
        """Creates a DataFrame for proto_obj.

        Args:
          mode (str):
            Whether to return 'basic' DataFrame or 'advanced' one.
            Refer to `data.dataframe_schemas.json` for schemas.

        Returns:
          A pandas DataFrame.
        """
        self._check_proto_obj_attr_exist()

        return self._dataframe_instance.proto_to_dataframe(
            obj=self.proto_obj, mode=mode)


    def from_dataframe(self, df: pd.DataFrame, action: str):
        """Perform an `action` from the DataFrame `df` on proto_obj.

        Args:
            df (pd.DataFrame):
                The input DataFrame.
            action (str):
                'create', 'delete', 'append'

        Returns:
          A protobuf object stored in proto_obj
        """
        if action != "create":
            self._check_proto_obj_attr_exist()

        return self._dataframe_instance.dataframe_to_proto(
            df=df, action=action)



    class _DataframeCommon():
        """An internal base class to store DataFrame related methods."""

        _dataframes_map = {
            "Intent": {
                "basic": ["display_name", "training_phrase"],
                "advanced": [
                    "name", "display_name", "description", "priority",
                    "is_fallback", "labels", "id", "repeat_count",
                    "training_phrase", "training_phrase_idx",
                    "text", "text_idx",
                    "parameter_id", "entity_type", "is_list", "redact",
                ],
            },
            "EntityType": {
                "basic": ["display_name", "entity_value", "synonyms"],
                "advanced": [
                    "entity_type_id", "display_name", "kind",
                    "auto_expansion_mode", "fuzzy_extraction", "redact",
                    "entity_value", "synonyms", "excluded_phrases",
                ],
            },
            "TransitionRouteGroup": {
                "basic": [
                    "name", "display_name", "flow_id",
                    "intent", "condition", "target_type", "target_id",
                    "has_fulfillment", "has_fulfillment_webhook",
                    "target_name", "flow_name", # "intent_name",
                ],
                "advanced": [
                    "name", "display_name", "flow_id",
                    "intent", "condition", "target_type", "target_id",
                    "messages", "preset_parameters", "conditional_cases",
                    "webhook", "webhook_tag", "return_partial_responses",
                    "target_name", "flow_name", # "intent_name",
                ],
            },
            "Webhook": {
                "basic": ["display_name", "uri"],
                "advanced": [
                    "name", "display_name", "timeout", "disabled",
                    "service_type", "uri",
                    "username", "password", "request_headers",
                ]
            },
            "Fulfillment": {
                "basic": ["has_fulfillment", "has_fulfillment_webhook"],
                "advanced": [
                    "messages", "preset_parameters", "conditional_cases",
                    "webhook", "webhook_tag", "return_partial_responses",
                ]
            },
            "TransitionRoute": {
                "basic": [
                    "intent", "condition", "target_type", "target_id",
                    "has_fulfillment", "has_fulfillment_webhook",
                ],
                "advanced": [
                    "intent", "condition", "target_type", "target_id",
                    "messages", "preset_parameters", "conditional_cases",
                    "webhook", "webhook_tag", "return_partial_responses",
                ],
            }
        }


        def __init__(self, outer_self):
            self._outer_self = outer_self


        def _find_mode(self, df: pd.DataFrame) -> str:
            """Find the mode that the `df` represents.

            Args:
                df (pd.DataFrame):
                    The input DataFrame

            Returns:
                The mode as a string.
            """
            proto_name = self._outer_self._proto_type_str # pylint: disable=W0212
            output_schemas = self._dataframes_map.get(proto_name)

            if output_schemas is not None:
                for mode, schema in output_schemas.items():
                    if set(df.columns) == set(schema):
                        return str(mode)

            raise ValueError(
                "`df` does not match with any of the schemas."
            )

        @staticmethod
        def _is_column_has_single_value(df: pd.DataFrame, column: str) -> bool:
            """Check whether the `column` in the `df` has only one value.

            Args:
                df (pd.DataFrame):
                    The input DataFrame.
                column (str):
                    column name as string.

            Returns:
                True if the `column` has single value else False
            """
            if column not in df.columns:
                raise ValueError(
                    f"column `{column}` is not present in the df."
                )

            vals = list(df[column].unique())
            if len(vals) != 1:
                return False
            return True

        @staticmethod
        def _get_unique_value_of_a_column(
            df: pd.DataFrame, column: str
        ) -> Any:
            """Check whether the `column` in the `df` has only one value
            and returns that value.

            Args:
                df (pd.DataFrame):
                    The input DataFrame.
                column (str):
                    column name as string.

            Returns:
                Unique value of the column.
            """
            if not __class__._is_column_has_single_value(df, column): # pylint: disable=W0212
                raise UserWarning(
                    f"The column `{column}` has none or"
                    " more than one unique value."
                )

            return list(df[column].unique())[0]

        @staticmethod
        def _is_df_has_single_display_name(df: pd.DataFrame) -> str:
            """Check whether the 'display_name' column in df has only one value
            and returns that value.

            Args:
                df (pd.DataFrame):
                    The input DataFrame.

            Returns:
                display_name as a string.
            """
            return __class__._get_unique_value_of_a_column(df, "display_name") # pylint: disable=W0212

        def _is_df_display_name_match_with_proto(self, df: pd.DataFrame):
            """Check whether the 'display_name' column in df matches with
            the proto_obj 'display_name'.

            Args:
              df (pd.DataFrame):
                The input DataFrame.

            Raises:
              ValueError: If the 'display_name' of df does not match
              with the proto_obj.
            """
            proto_disp_name = self._outer_self.proto_obj.display_name
            disp_name = self._is_df_has_single_display_name(df)

            if disp_name != proto_disp_name:
                raise ValueError(
                    "The input DataFrame `df` refers to a proto with a"
                    " different display_name from the one stored in proto_obj."
                )


        def _process_from_df_create(self, df: pd.DataFrame, mode: str):
            """Prototype method to perform `create` action on proto_obj."""
            raise NotImplementedError("Subclass should implement this method!")

        def _process_from_df_append(self, df: pd.DataFrame, mode: str):
            """Prototype method to perform `append` action on proto_obj."""
            raise NotImplementedError("Subclass should implement this method!")

        def _process_from_df_delete(self, df: pd.DataFrame, mode: str):
            """Prototype method to perform `delete` action on proto_obj."""
            raise NotImplementedError("Subclass should implement this method!")

        def dataframe_to_proto(
            self, df: pd.DataFrame, action: str
        ):
            """Perform an `action` from the DataFrame `df` on proto_obj.

            Args:
                df (pd.DataFrame):
                    The input DataFrame to read the data from.
                action (str):
                    'create', 'delete', 'append'

            Returns:
                A protobuf object stored in the proto_obj.
            """
            # Find the `mode` value based on passed df
            mode = self._find_mode(df)

            # TODO: Input df check: schema, values
            if action == "create":
                return self._process_from_df_create(df=df, mode=mode)
            elif action == "append":
                return self._process_from_df_append(df=df, mode=mode)
            elif action == "delete":
                return self._process_from_df_delete(df=df, mode=mode)
            else:
                raise ValueError(
                    "`action` types: ['create', 'delete', 'append']."
                )


        @staticmethod
        def _concat_dict_to_df(
            df: pd.DataFrame, dict_: Dict[str, Any]
        ) -> pd.DataFrame:
            """Transform a dictionary to a DataFrame then
            concatenate with the existing DataFrame.

            Args:
                df (pd.DataFrame):
                    The DataFrame to append the row to.
                dict_ (Dict[str, Any]):
                    The dictionary representing a row.

            Returns:
                A DataFrame with a new row.
            """
            # Error checking: `dict_` keys against `df` columns
            extra_keys = [k for k in dict_ if k not in df.columns]
            if extra_keys:
                raise ValueError(
                    "`dict_` has a key that is not included in"
                    f" the `df` columns: {extra_keys}."
                )

            # Alternative row creation:
            # row = pd.DataFrame.from_dict(dict_, orient="index").transpose()
            row = pd.DataFrame(dict_, index=[0])
            df = pd.concat([df, row], ignore_index=True)

            return df

        def _process_proto_to_df_basic(self, obj) -> pd.DataFrame:
            """Prototype method to create a DataFrame
            from a proto_obj in basic mode."""
            raise NotImplementedError("Subclass should implement this method!")

        def _process_proto_to_df_advanced(self, obj) -> pd.DataFrame:
            """Prototype method to create a DataFrame
            from a proto_obj in advanced mode."""
            raise NotImplementedError("Subclass should implement this method!")

        def proto_to_dataframe(
            self, obj, mode: str = "basic"
        ) -> pd.DataFrame:
            """Converts a protobuf object to pandas DataFrame.

            Args:
              obj:
                A protobuf object.
              mode (str):
                Whether to return 'basic' DataFrame or 'advanced' one.
                Refer to `data.dataframe_schemas.json` for schemas.

            Returns:
              A pandas DataFrame
            """
            if mode == "basic":
                return self._process_proto_to_df_basic(obj)
            elif mode == "advanced":
                return self._process_proto_to_df_advanced(obj)
            else:
                raise ValueError("`mode` types: ['basic', 'advanced'].")


    class _Dataframe(_DataframeCommon):
        """Prototype class to create a DataFrame from a proto_obj."""
        pass # pylint: disable=W0107
