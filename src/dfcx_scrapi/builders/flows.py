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
from dataclasses import dataclass
from typing import List, Union

from google.cloud.dialogflowcx_v3beta1.types import Flow
from google.cloud.dialogflowcx_v3beta1.types import NluSettings
from google.cloud.dialogflowcx_v3beta1.types import TransitionRoute
from google.cloud.dialogflowcx_v3beta1.types import EventHandler
from dfcx_scrapi.builders.builders_common import BuildersCommon
from dfcx_scrapi.builders.routes import TransitionRouteBuilder
from dfcx_scrapi.builders.routes import EventHandlerBuilder
from dfcx_scrapi.builders.fulfillments import FulfillmentBuilder

# logging config
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


class FlowBuilder(BuildersCommon):
    """Base Class for CX Flow builder."""

    _proto_type = Flow
    _proto_type_str = "Flow"


    def __str__(self) -> str:
        """String representation of the proto_obj."""
        self._check_proto_obj_attr_exist()

        return (
            f"Basic Information:\n{'='*25}\n{self._show_basic_info()}"
            f"\n\n\nTransitionRoutes:\n{'='*25}"
            f"\n{self._show_transition_routes()}"
            f"\n\n\nEventHandlers:\n{'='*25}\n{self._show_event_handlers()}"
            f"\n\n\nTransitoinRouteGroups:\n{'='*25}"
            f"\n{self._show_transition_route_groups()}")


    def _show_basic_info(self) -> str:
        """String representation for the basic information of proto_obj."""
        self._check_proto_obj_attr_exist()

        nlu_settings_str = (
            f"\tModel type: {self.proto_obj.nlu_settings.model_type.name}"
            "\n\tClassification threshold:"
            f" {self.proto_obj.nlu_settings.classification_threshold}"
            "\n\tTraining mode:"
            f" {self.proto_obj.nlu_settings.model_training_mode.name}"
        )

        return (
            f"display_name: {self.proto_obj.display_name}"
            f"\ndescription:\n\t{self.proto_obj.description}"
            f"\nNLU settings:\n{nlu_settings_str}"
        )


    def _show_transition_routes(self) -> str:
        """String representation for the transition routes of proto_obj."""
        self._check_proto_obj_attr_exist()

        return "\n".join([
            f"TransitionRoute {i+1}:\n{str(TransitionRouteBuilder(tr))}"
            f"\n{'*'*20}\n"
            for i, tr in enumerate(self.proto_obj.transition_routes)
        ])


    def _show_event_handlers(self) -> str:
        """String representation for the event handlers of proto_obj."""
        self._check_proto_obj_attr_exist()

        return "\n".join([
            f"EventHandler {i+1}:\n{str(EventHandlerBuilder(eh))}\n{'*'*20}\n"
            for i, eh in enumerate(self.proto_obj.event_handlers)
        ])


    def _show_transition_route_groups(self) -> str:
        """String representation for the transition route groups of proto_obj"""
        self._check_proto_obj_attr_exist()

        return "\n".join([
            f"TransitionRouteGroup {i+1}: {trg_id}"
            for i, trg_id in enumerate(self.proto_obj.transition_route_groups)
        ])


    def show_flow_info(
        self, mode: str = "whole"
    ) -> None:
        """Show the proto_obj information.

        Args:
          mode (str):
            Specifies what part of the page to show.
              Options:
              ['basic', 'whole',
              'routes' or 'transition routes',
              'route groups' or 'transition route groups',
              'events' or 'event handlers'
              ]
        """
        self._check_proto_obj_attr_exist()

        if mode == "basic":
            print(self._show_basic_info())
        elif mode in ["routes", "transition routes"]:
            print(self._show_transition_routes())
        elif mode in ["route groups", "transition route groups"]:
            print(self._show_transition_route_groups())
        elif mode in ["events", "event handlers"]:
            print(self._show_event_handlers())
        elif mode == "whole":
            print(self)
        else:
            raise ValueError(
                "mode should be in"
                "['basic', 'whole',"
                " 'routes', 'transition routes',"
                " 'route groups', 'transition route groups',"
                " 'events', 'event handlers']"
            )


    def show_stats(self) -> None:
        """Provide some stats about the Page."""
        self._check_proto_obj_attr_exist()

        stats_instance = FlowStats(self.proto_obj)
        stats_instance.generate_stats()


    def create_new_proto_obj(
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
        # Types error checking
        if not(display_name and isinstance(display_name, str)):
            raise ValueError("`display_name` should be a nonempty string.")
        if (
            description
            and not isinstance(description, str)
            and len(description) > 500
        ):
            raise ValueError(
                "`description` should be a string and"
                " it's length should be less than 500 characters."
            )
        # `overwrite` parameter error checking
        if self.proto_obj and not overwrite:
            raise UserWarning(
                "proto_obj already contains a Flow."
                " If you wish to overwrite it, pass `overwrite` as True."
            )
        # Create the Flow
        if overwrite or not self.proto_obj:
            self.proto_obj = Flow(
                display_name=display_name,
                description=description
            )
        # Set the NLU settings to default
        self.nlu_settings()

        return self.proto_obj


    def nlu_settings(
        self,
        model_type: int = 1,
        classification_threshold: float = 0.3,
        model_training_mode: int = 1
    ) -> Flow:
        """NLU related settings of the flow.

        Args:
          model_type (int):
            Indicates the type of NLU model:
              1 = MODEL_TYPE_STANDARD, 3 = MODEL_TYPE_ADVANCED
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
              1 = MODEL_TRAINING_MODE_AUTOMATIC
              2 = MODEL_TRAINING_MODE_MANUAL

        Returns:
          A Flow object stored in proto_obj.
        """
        self._check_proto_obj_attr_exist()

        # Type error checking
        if model_type not in [1, 3]:
            raise ValueError(
                "`model_type` should be in [1, 3]."
                "\n1: MODEL_TYPE_STANDARD"
                "\n3: MODEL_TYPE_ADVANCED"
            )
        if model_training_mode not in [1, 2]:
            raise ValueError(
                "`model_training_mode` should be in [1, 2]."
                "\n1: MODEL_TRAINING_MODE_AUTOMATIC"
                "\n2: MODEL_TRAINING_MODE_MANUAL"
            )
        if not(
            isinstance(classification_threshold, float)
            and (0 < classification_threshold < 1)
        ):
            raise ValueError(
                "`classification_threshold` should be a float"
                " range from 0.0 to 1.0."
            )

        the_nlu_settings = NluSettings(
            model_type=model_type,
            model_training_mode=model_training_mode,
            classification_threshold=classification_threshold
        )
        self.proto_obj.nlu_settings = the_nlu_settings

        return self.proto_obj


    def add_transition_route(
        self,
        transition_routes: Union[TransitionRoute, List[TransitionRoute]]
    ) -> Flow:
        """Add single or multiple TransitionRoutes to the Flow.

        Args:
          transition_routes (TransitionRoute | List[TransitionRoute]):
            A single or list of TransitionRoutes to add
            to the Flow existing in proto_obj.

        Returns:
          A Flow object stored in proto_obj.
        """
        self._check_proto_obj_attr_exist()

        # Type error checking
        self._is_type_or_list_of_types(
            transition_routes, TransitionRoute, "transition_routes"
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
            to the Flow existing in proto_obj.

        Returns:
          A Flow object stored in proto_obj.
        """
        self._check_proto_obj_attr_exist()

        # Type error checking
        self._is_type_or_list_of_types(
            event_handlers, EventHandler, "event_handlers"
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
        self._check_proto_obj_attr_exist()

        # Type error checking
        self._is_type_or_list_of_types(
            transition_route_groups, str, "transition_route_groups"
        )

        if not isinstance(transition_route_groups, list):
            transition_route_groups = [transition_route_groups]
        self.proto_obj.transition_route_groups.extend(transition_route_groups)

        return self.proto_obj


    def remove_transition_route(
        self,
        transition_route: TransitionRoute = None,
        intent: str = None,
        condition: str = None
    ) -> Flow:
        """Remove a transition route from the Flow.

        At least one of the `transition_route`, `intent`, or `condition` should
        be specfied.

        Args:
            transition_route (TransitionRoute):
              The TransitionRoute to remove from the Flow.
            intent (str):
              TransitionRoute's intent that should be removed from the Flow.
            condition (str):
              TransitionRoute's condition that should be removed from the Flow.

        Returns:
          A Flow object stored in proto_obj.
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


    def remove_event_handler(
        self,
        event_handlers: Union[EventHandler, List[EventHandler]] = None,
        event_names: Union[str, List[str]] = None
    ) -> Flow:
        """Remove single or multiple EventHandlers from the Flow.

        Args:
          event_handlers (EventHandler | List[EventHandler]):
            A single or list of EventHandler to remove
              from the Flow existing in proto_obj.
            Only one of the `event_handlers` and
              `event_names` should be specified.
          event_names (str | List[str]):
            A single or list of EventHandler's event names corresponding to the
              EventHandler to remove from the Flow existing in proto_obj.
            Only one of the `event_handlers` and
              `event_names` should be specified.

        Returns:
          A Flow object stored in proto_obj.
        """
        self._check_proto_obj_attr_exist()

        if event_handlers and event_names:
            raise UserWarning(
                "Only one of the `event_handlers` and "
                "`event_names` should be specified."
            )
        if event_handlers:
            new_ehs = self._find_unmatched_event_handlers(event_handlers)
        elif event_names:
            new_ehs = self._find_unmatched_event_handlers_by_name(event_names)
        else:
            raise UserWarning(
                "At least one of the `event_handlers` and "
                "`event_names` should be specified."
            )

        self.proto_obj.event_handlers = new_ehs

        return self.proto_obj


    def remove_transition_route_group(
        self,
        transition_route_groups: Union[str, List[str]]
    ) -> Flow:
        """Remove single or multiple TransitionRouteGroups from the Flow.

        Args:
          transition_route_groups (str | List[str]):
            A single or list of TransitionRouteGroup's id to remove
            from the Flow existing in proto_obj. Format:
            ``projects/<Project ID>/locations/<Location ID>/agents/<Agent ID>/
              flows/<Flow ID>/transitionRouteGroups/<TransitionRouteGroup ID>``.

        Returns:
          A Flow object stored in proto_obj.
        """
        self._check_proto_obj_attr_exist()

        # Type error checking
        self._is_type_or_list_of_types(
            transition_route_groups, str, "transition_route_groups"
        )

        if not isinstance(transition_route_groups, list):
            transition_route_groups = [transition_route_groups]

        new_trgs = [
            trg
            for trg in self.proto_obj.transition_route_groups
            if trg not in transition_route_groups
        ]
        self.proto_obj.transition_route_groups = new_trgs

        return self.proto_obj



@dataclass
class FlowStats():
    """A class for tracking the stats of CX Flow object."""
    flow_proto_obj: Flow

    # Transition Routes
    transition_routes_count: int = 0
    routes_with_fulfill_count: int = 0
    routes_with_webhook_fulfill_count: int = 0
    intent_routes_count: int = 0
    cond_routes_count: int = 0
    intent_and_cond_routes_count: int = 0

    # Event Handlers
    event_handlers_count: int = 0
    events_with_fulfill_count: int = 0
    events_with_webhook_fulfill_count: int = 0

    # Transition Route Groups
    transition_route_groups_count: int = 0


    def calc_transition_route_stats(self):
        """Calculating TransitionRoute related stats"""
        self.transition_routes_count = len(
            self.flow_proto_obj.transition_routes
        )
        for tr in self.flow_proto_obj.transition_routes:
            if tr.trigger_fulfillment:
                self.routes_with_fulfill_count += 1
                fb = FulfillmentBuilder(tr.trigger_fulfillment)
                if fb.has_webhook():
                    self.routes_with_webhook_fulfill_count += 1
            if tr.intent and tr.condition:
                self.intent_and_cond_routes_count += 1
            elif tr.intent and not tr.condition:
                self.intent_routes_count += 1
            elif not tr.intent and tr.condition:
                self.cond_routes_count += 1

    def create_transition_route_str(self) -> str:
        """String representation of TransitionRoutes stats."""
        transition_routes_str = (
            f"# of Transition Routes: {self.transition_routes_count}"
        )
        routes_with_fulfill_str = (
            f"# of routes with fulfillment: {self.routes_with_fulfill_count}"
        )
        routes_with_webhook_fulfill_str = (
            "# of routes uses webhook for fulfillment:"
            f" {self.routes_with_webhook_fulfill_count}"
        )
        intent_routes_str = f"# of intent routes: {self.intent_routes_count}"
        cond_routes_str = f"# of condition routes: {self.cond_routes_count}"
        intent_and_cond_routes_str = (
            "# of intent and condition routes:"
            f" {self.intent_and_cond_routes_count}"
        )

        return (
            f"{transition_routes_str}\n\t{intent_routes_str}"
            f"\n\t{cond_routes_str}\n\t{intent_and_cond_routes_str}"
            f"\n\t{routes_with_fulfill_str}"
            f"\n\t{routes_with_webhook_fulfill_str}"
        )


    def calc_event_handler_stats(self):
        """Calculating EventHandler related stats."""
        self.event_handlers_count = len(self.flow_proto_obj.event_handlers)
        for eh in self.flow_proto_obj.event_handlers:
            fb = FulfillmentBuilder(eh.trigger_fulfillment)
            if fb.has_webhook():
                self.events_with_webhook_fulfill_count += 1
            if eh.trigger_fulfillment:
                self.events_with_fulfill_count += 1

    def create_event_handler_str(self) -> str:
        """String representation of EventHandlers stats."""
        event_handlers_str = f"# of Event Handlers: {self.event_handlers_count}"
        events_with_fulfill_str = (
            "# of Event Handlers with fulfillment:"
            f" {self.events_with_fulfill_count}"
        )
        events_with_webhook_fulfill_str = (
            "# of Event Handlers uses webhook for fulfillment:"
            f" {self.events_with_webhook_fulfill_count}"
        )

        return (
            f"{event_handlers_str}\n\t{events_with_fulfill_str}"
            f"\n\t{events_with_webhook_fulfill_str}"
        )


    def create_transition_route_group_str(self) -> str:
        """String representation of TransitionRouteGroup stats."""
        self.transition_route_groups_count = len(
            self.flow_proto_obj.transition_route_groups
        )
        return (
            "# of Transition Route Groups:"
            f" {self.transition_route_groups_count}"
        )


    def generate_stats(self):
        """Generate stats for the Flow."""
        self.calc_transition_route_stats()
        self.calc_event_handler_stats()

        routes_stats_str = self.create_transition_route_str()
        events_stats_str = self.create_event_handler_str()
        route_groups_stats_str = self.create_transition_route_group_str()

        out = (
            f"{routes_stats_str}\n{events_stats_str}\n{route_groups_stats_str}"
        )
        print(out)
