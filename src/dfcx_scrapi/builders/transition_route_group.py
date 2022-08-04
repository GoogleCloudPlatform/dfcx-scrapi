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

from typing import List, Union

from google.cloud.dialogflowcx_v3beta1 import types
from google.cloud.dialogflowcx_v3beta1.types import TransitionRoute


class TransitionRouteGroupBuilder:
    """Base Class for CX TransitionRouteGroup builder."""


    def __init__(self, obj: types.TransitionRouteGroup = None):
        self.proto_obj = None
        if obj:
            self.load_transition_route_group(obj)


    def _check_transition_route_group_exist(self):
        """Check if the proto_obj exists otherwise raise an error."""

        if not self.proto_obj:
            raise ValueError(
                "There is no proto_obj!"
                "\nUse create_empty_transition_route_group or"
                " load_transition_route_group to continue."
            )
        elif not isinstance(self.proto_obj, types.TransitionRouteGroup):
            raise ValueError(
                "proto_obj is not a TransitionRouteGroup type."
                "\nPlease create or load the correct type to continue."
            )


    def load_transition_route_group(
        self, obj: types.TransitionRouteGroup, overwrite: bool = False
    ) -> types.TransitionRouteGroup:
        """Load an existing TransitionRouteGroup to proto_obj for further uses.

        Args:
          obj (TransitionRouteGroup):
            An existing TransitionRouteGroup obj.
          overwrite (bool)
            Overwrite the new proto_obj if proto_obj already
            contains a TransitionRouteGroup.

        Returns:
          A TransitionRouteGroup object stored in proto_obj
        """
        if not isinstance(obj, types.TransitionRouteGroup):
            raise ValueError(
                "The object you're trying to load is not a TransitionRouteGroup"
            )
        if self.proto_obj and not overwrite:
            raise Exception(
                "proto_obj already contains an TransitionRouteGroup."
                " If you wish to overwrite it, pass overwrite as True."
            )
        if overwrite or not self.proto_obj:
            self.proto_obj = obj

        return self.proto_obj


    def create_empty_transition_route_group(
        self,
        display_name: str,
        transition_routes: Union[TransitionRoute, List[TransitionRoute]] = None,
        overwrite: bool = False
    ) -> types.TransitionRouteGroup:
        """Create an empty TransitionRouteGroup.

        Args:
            display_name (str):
                Required. The human-readable name of the
                transition route group, unique within the flow.
                The display name can be no longer than 30 characters.
            transition_routes (TransitionRoute | List[TransitionRoute]):
                Transition routes associated with this TransitionRouteGroup.
            overwrite (bool)
                Overwrite the new proto_obj if proto_obj already
                contains a TransitionRouteGroup.

        Returns:
            A TransitionRouteGroup object stored in proto_obj.
        """
        if not (display_name and isinstance(display_name, str)):
            raise ValueError("display_name should be a nonempty string.")
        if ((not isinstance(transition_routes, TransitionRoute)) or
            (not isinstance(transition_routes, list) and all(
                (isinstance(tr, TransitionRoute) for tr in transition_routes)
            ))):
            raise ValueError(
                "transition_routes should be either a TransitionRoute or"
                " a list of TransitionRoutes."
            )
        if self.proto_obj and not overwrite:
            raise Exception(
                "proto_obj already contains a TransitionRouteGroup."
                " If you wish to overwrite it, pass overwrite as True."
            )
        if overwrite or not self.proto_obj:
            if not isinstance(transition_routes, list):
                transition_routes = [transition_routes]
            self.proto_obj = types.TransitionRouteGroup(
                display_name=display_name,
                transition_routes=transition_routes
            )

        return self.proto_obj


    def add_transition_route(
        self,
        transition_routes: Union[TransitionRoute, List[TransitionRoute]]
    ) -> types.TransitionRouteGroup:
        """Add single or multiple TransitionRoutes to the TransitionRouteGroup.

        Args:
            transition_routes (TransitionRoute | List[TransitionRoute]):
                A single or list of TransitionRoutes to add
                to this TransitionRouteGroup.
        Returns:
            A TransitionRouteGroup object stored in proto_obj.
        """
        if ((not isinstance(transition_routes, TransitionRoute)) or
            (not isinstance(transition_routes, list) and all(
                (isinstance(tr, TransitionRoute) for tr in transition_routes)
            ))):
            raise ValueError(
                "transition_routes should be either a TransitionRoute or"
                " a list of TransitionRoutes."
            )

        if not isinstance(transition_routes, list):
            transition_routes = [transition_routes]
        self.proto_obj.transition_routes.extend(transition_routes)

        return self.proto_obj
