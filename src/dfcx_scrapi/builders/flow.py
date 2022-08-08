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

from google.cloud.dialogflowcx_v3beta1.types import (
    Flow, NluSettings, TransitionRoute, EventHandler
)


class FlowBuilder:
    """Base Class for CX Flow builder."""


    def __init__(self, obj: Flow = None):
        self.proto_obj = None
        if obj:
            self.load_flow(obj)


    def _check_flow_exist(self):
        """Check if the proto_obj exists otherwise raise an error."""

        if not self.proto_obj:
            raise ValueError(
                "There is no proto_obj!"
                "\nUse create_new_flow or load_flow to continue."
            )
        elif not isinstance(self.proto_obj, Flow):
            raise ValueError(
                "proto_obj is not a Flow type."
                "\nPlease create or load the correct type to continue."
            )


    def load_flow(self, obj: Flow, overwrite: bool = False) -> Flow:
        """Load an existing Flow to proto_obj for further uses.

        Args:
          obj (Flow):
            An existing Flow obj.
          overwrite (bool)
            Overwrite the new proto_obj if proto_obj already
            contains a Flow.

        Returns:
          A Flow object stored in proto_obj
        """
        if not isinstance(obj, Flow):
            raise ValueError(
                "The object you're trying to load is not a Flow."
            )
        if self.proto_obj and not overwrite:
            raise Exception(
                "proto_obj already contains a Flow."
                " If you wish to overwrite it, pass overwrite as True."
            )
        if overwrite or not self.proto_obj:
            self.proto_obj = obj

        return self.proto_obj


    def create_new_flow(
        self,
        display_name: str,
        description: str = None,
        overwrite: bool = False
    ) -> Flow:
        """Create a new Flow.

        Args:
          display_name (str):
            Required. The human-readable name of the flow.
          description (str):
            The description of the flow. The maximum length is 500 characters.
            If exceeded, the request is rejected.
          overwrite (bool)
            Overwrite the new proto_obj if proto_obj already contains a Flow.

        Returns:
          A Flow object stored in proto_obj.
        """
        if not (display_name and isinstance(display_name, str)):
            raise ValueError("display_name should be a nonempty string.")
        if description and not isinstance(description, str):
            raise ValueError("description should be a string.")
        if self.proto_obj and not overwrite:
            raise Exception(
                "proto_obj already contains a Flow."
                " If you wish to overwrite it, pass overwrite as True."
            )
        if overwrite or not self.proto_obj:
            self.proto_obj = Flow(
                display_name=display_name,
                description=description
            )

        return self.proto_obj


    def add_transition_route(
        self,
        transition_routes: Union[TransitionRoute, List[TransitionRoute]]
    ) -> Flow:
        """Add single or multiple TransitionRoutes to the Flow.

        Args:
          transition_routes (TransitionRoute | List[TransitionRoute]):
            A single or list of TransitionRoutes to add
            to the Flow existed in proto_obj.
        Returns:
          A Flow object stored in proto_obj.
        """
        self._check_flow_exist()

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


    def add_event_handler(
        self,
        event_handlers: Union[EventHandler, List[EventHandler]]
    ) -> Flow:
        """Add single or multiple EventHandlers to the Flow.

        Args:
          event_handlers (EventHandler | List[EventHandler]):
            A single or list of EventHandler to add
            to the Flow existed in proto_obj.
        Returns:
          A Flow object stored in proto_obj.
        """
        self._check_flow_exist()

        if ((not isinstance(event_handlers, EventHandler)) or
            (not isinstance(event_handlers, list) and all(
                (isinstance(eh, EventHandler) for eh in event_handlers)
            ))):
            raise ValueError(
                "event_handlers should be either a EventHandler or"
                " a list of EventHandlers."
            )

        if not isinstance(event_handlers, list):
            event_handlers = [event_handlers]
        self.proto_obj.event_handlers.extend(event_handlers)

        return self.proto_obj


    def add_transition_route_group(
        self,
        transition_route_groups: Union[str, List[str]]
    ) -> Flow:
        """Add single or multiple TransitionRouteGroups to the Flow.

        Args:
          transition_route_groups (str | List[str]):
            A single or list of TransitionRouteGroup's id to add
            to the Flow existed in proto_obj. Format:
            ``projects/<Project ID>/locations/<Location ID>/agents/<Agent ID>/
              flows/<Flow ID>/transitionRouteGroups/<TransitionRouteGroup ID>``.
        Returns:
          A Flow object stored in proto_obj.
        """
        self._check_flow_exist()

        if ((not isinstance(transition_route_groups, str)) or
            (not isinstance(transition_route_groups, list) and all(
                (isinstance(trg, str) for trg in transition_route_groups)
            ))):
            raise ValueError(
                "transition_route_groups should be either a string or"
                " a list of strings."
            )

        if not isinstance(transition_route_groups, list):
            transition_route_groups = [transition_route_groups]
        self.proto_obj.transition_route_groups.extend(transition_route_groups)

        return self.proto_obj


    def nlu_settings(
        self,
        model_type: int = 1,
        classification_threshold: float = 0.3,
        model_training_mode: int = 0
    ) -> Flow:
        """NLU related settings of the flow.

        Args:
          model_type (int):
            Indicates the type of NLU model:
              0 = MODEL_TYPE_UNSPECIFIED
              1 = MODEL_TYPE_STANDARD
              3 = MODEL_TYPE_ADVANCED
          classification_threshold (float):
            To filter out false positive results and
            still get variety in matched natural language
            inputs for your agent, you can tune the machine
            learning classification threshold. If the
            returned score value is less than the threshold
            value, then a no-match event will be triggered.
            The score values range from 0.0 (completely
            uncertain) to 1.0 (completely certain). If set
            to 0.0, the default of 0.3 is used.
          model_training_mode (int):
            Indicates NLU model training mode:
              0 = MODEL_TRAINING_MODE_UNSPECIFIED
              1 = MODEL_TRAINING_MODE_AUTOMATIC
              2 = MODEL_TRAINING_MODE_MANUAL

        Returns:
          A Flow object stored in proto_obj.
        """
        self._check_flow_exist()

        if model_type not in [0, 1, 3]:
            raise ValueError(
                "model_type should be in [0, 1, 3]."
                "\n0: MODEL_TYPE_UNSPECIFIED"
                "\n1: MODEL_TYPE_STANDARD"
                "\n3: MODEL_TYPE_ADVANCED"
            )
        if model_training_mode not in [0, 1, 2]:
            raise ValueError(
                "model_training_mode should be in [0, 1, 2]."
                "\n0: MODEL_TRAINING_MODE_UNSPECIFIED"
                "\n1: MODEL_TRAINING_MODE_AUTOMATIC"
                "\n2: MODEL_TRAINING_MODE_MANUAL"
            )
        if not (isinstance(classification_threshold, float) and
            (0 < classification_threshold < 1)):
            raise ValueError(
                "classification_threshold should be a float"
                " range from 0.0 to 1.0."
            )

        the_nlu_settings = NluSettings(
            model_type=model_type,
            model_training_mode=model_training_mode,
            classification_threshold=classification_threshold
        )
        self.proto_obj.nlu_settings = the_nlu_settings

        return self.proto_obj
