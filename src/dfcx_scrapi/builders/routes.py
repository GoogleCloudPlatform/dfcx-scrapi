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

from google.cloud.dialogflowcx_v3beta1.types import Fulfillment
from google.cloud.dialogflowcx_v3beta1.types import TransitionRoute
from google.cloud.dialogflowcx_v3beta1.types import EventHandler
from dfcx_scrapi.builders.builders_common import BuildersCommon
from dfcx_scrapi.builders.fulfillments import FulfillmentBuilder

# logging config
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


class TransitionRouteBuilder(BuildersCommon):
    """Base Class for CX TransitionRoute builder."""

    _proto_type = TransitionRoute
    _proto_type_str = "TransitionRoute"


    def __str__(self) -> str:
        """String representation of the proto_obj."""
        self._check_proto_obj_attr_exist()

        target_str = self._show_target()
        transition_criteria = self._show_transition_criteria()
        fulfillment_str = self._show_fulfillment()

        return (
            f"{target_str}"
            f"\n{transition_criteria}"
            f"\nFulfillment:\n\n{fulfillment_str}"
        )


    def _show_transition_criteria(self) -> str:
        """String representation for the transition criteria of proto_obj."""
        self._check_proto_obj_attr_exist()

        intent_str, cond_str = "Not Specified", "Not Specified"
        if self.proto_obj.intent:
            intent_str = self.proto_obj.intent
        if self.proto_obj.condition:
            cond_str = self.proto_obj.condition
        return (
            "Transition criteria:"
            f"\n\tIntent: {intent_str}"
            f"\n\tCondition: {cond_str}"
        )


    def _show_target(self) -> str:
        """String representation for the target of proto_obj."""
        self._check_proto_obj_attr_exist()

        if self.proto_obj.target_page:
            target_type = "Page"
            target_id = self.proto_obj.target_page
        elif self.proto_obj.target_flow:
            target_type = "Flow"
            target_id = self.proto_obj.target_flow
        else:
            target_type = "Not Specified"
            target_id = "None"
        return f"Target: {target_type}\nTarget ID: {target_id}"


    def _show_fulfillment(self) -> str:
        """String representation for the fulfillment of proto_obj."""
        self._check_proto_obj_attr_exist()

        fulfillment_str = ""
        if self.proto_obj.trigger_fulfillment:
            fulfillment_str = str(
                FulfillmentBuilder(self.proto_obj.trigger_fulfillment)
            )

        return fulfillment_str


    def show_transition_route(self, mode: str = "whole"):
        """Show the proto_obj information.
        Args:
          mode (str):
            Specifies what part of the TransitionRoute to show.
            Options:
              ['target', 'fulfillment',
               'transition criteria' or 'conditions', 'whole']
        """
        self._check_proto_obj_attr_exist()

        if mode == "target":
            print(self._show_target())
        elif mode in ["transition criteria", "conditions"]:
            print(self._show_transition_criteria())
        elif mode == "fulfillment":
            print(self._show_fulfillment())
        elif mode == "whole":
            print(self)
        else:
            raise ValueError(
                "mode should be in"
                " ['target', 'fulfillment',"
                " 'transition criteria' or 'conditions', 'whole']"
            )


    def create_new_proto_obj(
        self,
        intent: str = None,
        condition: str = None,
        trigger_fulfillment: Fulfillment = None,
        target_page: str = None,
        target_flow: str = None,
        overwrite: bool = False
    ) -> TransitionRoute:
        """Create a new TransitionRoute.

        Args:
          intent (str):
            Indicates that the transition can only happen when the given
            intent is matched.
            Format:
            ``projects/<Project ID>/locations/<Location ID>/
              agents/<Agent ID>/intents/<Intent ID>``.
            At least one of ``intent`` or ``condition`` must be specified.
            When both ``intent`` and ``condition`` are specified,
            the transition can only happen when both are fulfilled.
          condition (str):
            The condition to evaluate.
            See the conditions reference:
            https://cloud.google.com/dialogflow/cx/docs/reference/condition
            At least one of ``intent`` or ``condition`` must be specified.
            When both ``intent`` and ``condition`` are specified,
            the transition can only happen when both are fulfilled.
          trigger_fulfillment (Fulfillment):
            The fulfillment to call when the condition is satisfied.
            When ``trigger_fulfillment`` and ``target`` are defined,
            ``trigger_fulfillment`` is executed first.
          target_page (str):
            The target page to transition to. Format:
            ``projects/<Project ID>/locations/<Location ID>/
              agents/<Agent ID>/flows/<Flow ID>/pages/<Page ID>``.
            At most one of ``target_page`` and ``target_flow``
            can be specified at the same time.
          target_flow (str):
            The target flow to transition to. Format:
            ``projects/<Project ID>/locations/<Location ID>/
              agents/<Agent ID>/flows/<Flow ID>``.
            At most one of ``target_page`` and ``target_flow``
            can be specified at the same time.
          overwrite (bool)
            Overwrite the new proto_obj if proto_obj already
            contains a TransitionRoute.

        Returns:
          A TransitionRoute object stored in proto_obj.
        """
        # Types error checking
        if ((intent and not isinstance(intent, str)) or
            (condition and not isinstance(condition, str)) or
            (target_page and not isinstance(target_page, str)) or
            (target_flow and not isinstance(target_flow, str))):
            raise ValueError(
                "intent, condition, target_page, and target_flow"
                " if existed should be a string."
            )
        if (trigger_fulfillment and
            not isinstance(trigger_fulfillment, Fulfillment)):
            raise ValueError(
                "The type of trigger_fulfillment should be a Fulfillment."
            )
        # Minimum requirement error checking
        if not(intent or condition):
            raise RuntimeError(
                "At least one of `intent` or `condition` must be specified."
            )
        # Oneof error checking
        if target_page and target_flow:
            raise RuntimeError(
                "At most one of `target_page` and `target_flow`"
                " can be specified at the same time."
            )
        # `overwrite` parameter error checking
        if self.proto_obj and not overwrite:
            raise UserWarning(
                "proto_obj already contains a TransitionRoute."
                " If you wish to overwrite it, pass overwrite as True."
            )

        # Create the TransitionRoute
        if overwrite or not self.proto_obj:
            # Create empty Fulfillment in case user didn't pass any
            if not trigger_fulfillment:
                trigger_fulfillment = Fulfillment()

            self.proto_obj = TransitionRoute(
                intent=intent,
                condition=condition,
                trigger_fulfillment=trigger_fulfillment,
                target_page=target_page,
                target_flow=target_flow
            )

        return self.proto_obj




class EventHandlerBuilder(BuildersCommon):
    """Base Class for CX EventHandler builder."""

    _proto_type = EventHandler
    _proto_type_str = "EventHandler"


    def __str__(self) -> str:
        """String representation of the proto_obj."""
        self._check_proto_obj_attr_exist()

        event_and_target_str = self._show_event_and_target()
        fulfillment_str = self._show_fulfillment()

        return (
            f"{event_and_target_str}"
            f"\nFulfillment:\n\n{fulfillment_str}"
        )


    def _show_event_and_target(self) -> str:
        """String representation for the target of proto_obj."""
        self._check_proto_obj_attr_exist()

        # Event str
        event_str = f"Event: {self.proto_obj.event}"
        # Target str
        if self.proto_obj.target_page:
            target_type = "Page"
            target_id = self.proto_obj.target_page
        elif self.proto_obj.target_flow:
            target_type = "Flow"
            target_id = self.proto_obj.target_flow
        else:
            target_type = "Not Specified"
            target_id = "None"
        return (
            f"{event_str}"
            f"\nTarget: {target_type}"
            f"\nTarget ID: {target_id}"
        )


    def _show_fulfillment(self) -> str:
        """String representation for the fulfillment of proto_obj."""
        self._check_proto_obj_attr_exist()

        fulfillment_str = ""
        if self.proto_obj.trigger_fulfillment:
            fulfillment_str = str(
                FulfillmentBuilder(self.proto_obj.trigger_fulfillment)
            )

        return fulfillment_str


    def show_event_handler(self, mode: str = "whole"):
        """Show the proto_obj information.
        Args:
          mode (str):
            Specifies what part of the EventHandler to show.
            Options:
              ['basic' or 'target' or 'event', 'fulfillment', 'whole']
        """
        self._check_proto_obj_attr_exist()

        if mode in ["basic", "target", "event"]:
            print(self._show_event_and_target())
        elif mode == "fulfillment":
            print(self._show_fulfillment())
        elif mode == "whole":
            print(self)
        else:
            raise ValueError(
                "mode should be in"
                " ['basic' or 'target' or 'event', 'fulfillment', 'whole']"
            )


    def create_new_proto_obj(
        self,
        event: str,
        trigger_fulfillment: Fulfillment = None,
        target_page: str = None,
        target_flow: str = None,
        overwrite: bool = False
    ) -> EventHandler:
        """Create a new EventHandler.

        Args:
          event (str):
            Required. The name of the event to handle.
          trigger_fulfillment (Fulfillment):
            The fulfillment to call when the event occurs.
            Handling webhook errors with a fulfillment enabled with webhook
            could cause infinite loop. It is invalid to specify
            such fulfillment for a handler handling webhooks.
          target_page (str):
            The target page to transition to. Format:
            ``projects/<Project ID>/locations/<Location ID>/
              agents/<Agent ID>/flows/<Flow ID>/pages/<Page ID>``.
            At most one of ``target_page`` and ``target_flow``
            can be specified at the same time.
          target_flow (str):
            The target flow to transition to. Format:
            ``projects/<Project ID>/locations/<Location ID>/
              agents/<Agent ID>/flows/<Flow ID>``.
            At most one of ``target_page`` and ``target_flow``
            can be specified at the same time.
          overwrite (bool)
            Overwrite the new proto_obj if proto_obj already
            contains a EventHandler.

        Returns:
          An EventHandler object stored in proto_obj.
        """
        # Types error checking
        if event and not isinstance(event, str):
            raise ValueError("event should be a string.")
        if (trigger_fulfillment and
            not isinstance(trigger_fulfillment, Fulfillment)):
            raise ValueError(
                "The type of trigger_fulfillment should be a Fulfillment."
            )
        # Oneof error checking
        if target_page and target_flow:
            raise RuntimeError(
                "At most one of `target_page` and `target_flow`"
                " can be specified at the same time."
            )
        # `overwrite` parameter error checking
        if self.proto_obj and not overwrite:
            raise UserWarning(
                "proto_obj already contains an EventHandler."
                " If you wish to overwrite it, pass overwrite as True."
            )
        # Create the EventHandler
        if overwrite or not self.proto_obj:
            # Create empty Fulfillment in case user didn't pass any
            if not trigger_fulfillment:
                trigger_fulfillment = Fulfillment()

            self.proto_obj = EventHandler(
                event=event,
                trigger_fulfillment=trigger_fulfillment,
                target_page=target_page,
                target_flow=target_flow
            )

        return self.proto_obj
