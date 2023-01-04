"""A set of builder methods to create CX proto resource objects"""

# Copyright 2022 Google LLC
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

from google.cloud.dialogflowcx_v3beta1.types import TransitionRoute
from google.cloud.dialogflowcx_v3beta1.types import EventHandler

# logging config
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


class BuilderBase:
    """Base class for other Builder classes"""
    _proto_type = None
    _proto_type_str = "None"


    def __init__(self, obj=None):
        self.proto_obj = None
        if obj:
            self.load_proto_obj(obj)


    def _check_proto_obj_attr_exist(self):
        """Check if the proto_obj exists otherwise raise an error."""
        if not self.proto_obj:
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
            raise Exception(
                f"proto_obj already contains {self._proto_type_str}."
                " If you wish to overwrite it, pass overwrite as True."
            )

        if overwrite or not self.proto_obj:
            self.proto_obj = obj

        return self.proto_obj


    def create_new_proto_obj(self):
        """Prototype method for creating a new proto object."""
        ...


    def _match_transition_route(
        self,
        transition_route: TransitionRoute,
        target_route: TransitionRoute = None,
        intent: str = None,
        condition: str = None
    ) -> bool:
        """Check if transition_route's intent and condition
        matches with the input.

        At least one of the `transition_route`, `intent`, or `condition` should
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
                "At least one of `intent` or `condition` must be specified."
            )
        if (
            (intent and not isinstance(intent, str)) or
            (condition and not isinstance(condition, str))
        ):
            raise ValueError("`intent` and/or `condition` should be a string.")
        if target_route and not isinstance(target_route, TransitionRoute):
            raise ValueError("`target_route` should be a TransitionRoute.")

        # Check if the transition route matches
        if target_route:
            if (
                transition_route.condition == target_route.condition and
                transition_route.intent == target_route.intent
            ):
                return True
        if intent:
            if condition:
                if (
                    transition_route.condition == condition and
                    transition_route.intent == intent
                ):
                    return True
            else:
                if transition_route.intent == intent:
                    return True
        else:
            if transition_route.condition == condition:
                return True

        return False


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

