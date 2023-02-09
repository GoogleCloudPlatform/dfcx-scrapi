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
from google.cloud.dialogflowcx_v3beta1.types import TransitionRouteGroup
from dfcx_scrapi.builders.builders_common import BuildersCommon
from dfcx_scrapi.builders.routes import TransitionRouteBuilder

# logging config
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


class TransitionRouteGroupBuilder(BuildersCommon):
    """Base Class for CX TransitionRouteGroup builder."""

    _proto_type = TransitionRouteGroup
    _proto_type_str = "TransitionRouteGroup"


    def __str__(self) -> str:
        """String representation of the proto_obj."""
        self._check_proto_obj_attr_exist()

        transition_routes_str = "\n".join([
            f"\n\n - Transition Route{i+1}:\n{str(TransitionRouteBuilder(tr))}"
            for i, tr in enumerate(self.proto_obj.transition_routes)
        ])

        return (
            f"display_name: {self.proto_obj.display_name}"
            f"\nTransitionRoutes:\n{'-'*20}\n{transition_routes_str}"
        )


    def show_transition_route_group(self):
        """Show the proto_obj information."""
        self._check_proto_obj_attr_exist()

        print(self)


    def create_new_proto_obj(
        self,
        display_name: str,
        transition_routes: Union[TransitionRoute, List[TransitionRoute]] = None,
        overwrite: bool = False
    ) -> TransitionRouteGroup:
        """Create a new TransitionRouteGroup.

        Args:
          display_name (str):
            Required. The human-readable name of the
            transition route group, unique within the flow.
            The display name can be no longer than 30 characters.
          transition_routes (TransitionRoute | List[TransitionRoute]):
            Transition routes associated with this TransitionRouteGroup.
            Refer to `builders.routes.TransitionRouteBuilder` to build one.
          overwrite (bool)
            Overwrite the new proto_obj if proto_obj already
            contains a TransitionRouteGroup.

        Returns:
          A TransitionRouteGroup object stored in proto_obj.
        """
        # Types error checking
        if not (display_name and isinstance(display_name, str)):
            raise ValueError("display_name should be a nonempty string.")
        if transition_routes and not (
            isinstance(transition_routes, TransitionRoute) or
            (isinstance(transition_routes, list) and all(
                isinstance(tr, TransitionRoute) for tr in transition_routes))
        ):
            raise ValueError(
                "transition_routes should be either a TransitionRoute or"
                " a list of TransitionRoutes."
            )
        # `overwrite` parameter error checking
        if self.proto_obj and not overwrite:
            raise UserWarning(
                "proto_obj already contains a TransitionRouteGroup."
                " If you wish to overwrite it, pass overwrite as True."
            )
        # Create the TransitionRouteGroup
        if overwrite or not self.proto_obj:
            if not transition_routes:
                transition_routes = []
            if not isinstance(transition_routes, list):
                transition_routes = [transition_routes]
            self.proto_obj = TransitionRouteGroup(
                display_name=display_name,
                transition_routes=transition_routes
            )

        return self.proto_obj


    def add_transition_route(
        self,
        transition_routes: Union[TransitionRoute, List[TransitionRoute]]
    ) -> TransitionRouteGroup:
        """Add single or multiple TransitionRoutes to the TransitionRouteGroup.

        Args:
          transition_routes (TransitionRoute | List[TransitionRoute]):
            A single or list of TransitionRoutes to add
            to the TransitionRouteGroup existed in proto_obj.
        Returns:
          A TransitionRouteGroup object stored in proto_obj.
        """
        self._check_proto_obj_attr_exist()

        self._is_type_or_list_of_types(
            transition_routes, TransitionRoute, "transition_routes"
        )

        if not isinstance(transition_routes, list):
            transition_routes = [transition_routes]
        self.proto_obj.transition_routes.extend(transition_routes)

        return self.proto_obj


    def remove_transition_route(
        self,
        transition_route: TransitionRoute = None,
        intent: str = None,
        condition: str = None
    ) -> TransitionRouteGroup:
        """Remove a transition route from the TransitionRouteGroup.

        At least one of the `transition_route`, `intent`, or `condition` should
        be specfied.

        Args:
            transition_route (TransitionRoute):
              The TransitionRoute to remove from the TransitionRouteGroup.
            intent (str):
              TransitionRoute's intent that should be removed from
              the TransitionRouteGroup.
            condition (str):
              TransitionRoute's condition that should be removed from
              the TransitionRouteGroup.

        Returns:
          A TransitionRouteGroup object stored in proto_obj.
        """
        self._check_proto_obj_attr_exist()

        new_routes = []
        for tr in self.proto_obj.transition_routes:
            if self._match_transition_route(
                transition_route=tr, target_route=transition_route,
                intent=intent, condition=condition
            ):
                continue
            new_routes.append(tr)
        self.proto_obj.transition_routes = new_routes

        return self.proto_obj
