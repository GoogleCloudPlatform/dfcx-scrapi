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
from typing import List, Union

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
        if obj:
            self.load_proto_obj(obj)


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
