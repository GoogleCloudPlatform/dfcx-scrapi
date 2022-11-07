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

from typing import List, Dict, Union, Any

from google.cloud.dialogflowcx_v3beta1.types import Fulfillment
from google.cloud.dialogflowcx_v3beta1.types import ResponseMessage
from google.cloud.dialogflowcx_v3beta1.types import TransitionRoute
from google.cloud.dialogflowcx_v3beta1.types import EventHandler

from google.protobuf import struct_pb2


class FulfillmentBuilder:
    """Base Class for CX Fulfillment builder."""

    def __init__(self, obj: Fulfillment = None):
        self.proto_obj = None
        if obj:
            self.load_fulfillment(obj)


    def __str__(self) -> str:
        """String representation of the proto_obj."""
        self._check_fulfillment_exist()

        return


    def _check_fulfillment_exist(self):
        """Check if the proto_obj exists otherwise raise an error."""
        if not self.proto_obj:
            raise ValueError(
                "There is no proto_obj!"
                "\nUse create_new_fulfillment or load_fulfillment to continue"
            )
        elif not isinstance(self.proto_obj, Fulfillment):
            raise ValueError(
                "proto_obj is not a Fulfillment type."
                "\nPlease create or load the correct type to continue."
            )


    def load_fulfillment(
        self, obj: Fulfillment, overwrite: bool = False
    ) -> Fulfillment:
        """Load an existing Fulfillment to proto_obj for further uses.

        Args:
          obj (Fulfillment):
            An existing Fulfillment obj.
          overwrite (bool)
            Overwrite the new proto_obj if proto_obj already
            contains a Fulfillment.

        Returns:
          A Fulfillment object stored in proto_obj
        """
        if not isinstance(obj, Fulfillment):
            raise ValueError(
                "The object you're trying to load is not a Fulfillment!"
            )
        if self.proto_obj and not overwrite:
            raise Exception(
                "proto_obj already contains a Fulfillment."
                " If you wish to overwrite it, pass overwrite as True."
            )

        if overwrite or not self.proto_obj:
            self.proto_obj = obj

        return self.proto_obj


    def _response_message_creator(
        self,
        response_type: str,
        message: Union[str, List[str], Dict[str, Any]],
        mode: str = None
    ) -> ResponseMessage:
        """Represents a response message that can be returned by a
        conversational agent.
        Response messages are also used for output audio synthesis.

        Args:
          response_type (str):
            Type of the response message. It should be one of the following:
            'text', 'live_agent_handoff', 'conversation_success',
            'output_audio_text', 'play_audio', 'telephony_transfer_call'
          message (str | List[str] | Dict[str, str]):
            The output message. For each response_type
            it should be formatted like the following:
              text --> str | List[str]
              live_agent_handoff --> Dict[str, Any]
              conversation_success --> Dict[str, Any]
              output_audio_text --> str
              play_audio --> str
              telephony_transfer_call --> str
          mode (str):
            This argument is only applicable for 'output_audio_text'.
            It should be one of the following: 'text', 'ssml'

        Returns:
          A ResponseMessage object
        """
        if response_type == "text":
            if isinstance(message, str):
                response_message = ResponseMessage(
                    text=ResponseMessage.Text(text=[message])
                )
            elif isinstance(message, list):
                if not all((isinstance(msg, str) for msg in message)):
                    raise ValueError(
                        "Only strings are allowed in message list."
                    )
                response_message = ResponseMessage(
                    text=ResponseMessage.Text(text=message)
                )
            else:
                raise ValueError(
                    "For 'text' message should be"
                    " either a string or a list of strings."
                )
        elif response_type == "live_agent_handoff":
            if isinstance(message, dict):
                if not all((isinstance(key, str) for key in message.keys())):
                    raise ValueError(
                        "Only strings are allowed as dictionary keys in message"
                    )
                proto_struct = struct_pb2.Struct()
                proto_struct.update(message)
                live_agent_handoff = ResponseMessage.LiveAgentHandoff(
                    metadata=proto_struct
                )
                response_message = ResponseMessage(
                    live_agent_handoff=live_agent_handoff
                )
            else:
                raise ValueError(
                    "For 'live_agent_handoff',"
                    " message should be a dictionary."
                )
        elif response_type == "conversation_success":
            if isinstance(message, dict):
                if not all((isinstance(key, str) for key in message.keys())):
                    raise ValueError(
                        "Only strings are allowed as dictionary keys in message"
                    )
                proto_struct = struct_pb2.Struct()
                proto_struct.update(message)
                convo_success = ResponseMessage.ConversationSuccess(
                    metadata=proto_struct
                )
                response_message = ResponseMessage(
                    conversation_success=convo_success
                )
            else:
                raise ValueError(
                    "For 'conversation_success',"
                    " message should be a dictionary."
                )
        elif response_type == "output_audio_text":
            if isinstance(message, str):
                if mode == "text":
                    output_audio_text = ResponseMessage.OutputAudioText(
                        text=message
                    )
                elif mode == "ssml":
                    output_audio_text = ResponseMessage.OutputAudioText(
                        ssml=message
                    )
                else:
                    raise ValueError(
                        "mode should be either 'text' or 'ssml'"
                        " for output_audio_text."
                    )
                response_message = ResponseMessage(
                    output_audio_text=output_audio_text
                )
            else:
                raise ValueError(
                    "For 'output_audio_text', message should be a string."
                )
        elif response_type == "play_audio":
            if isinstance(message, str):
                # Validate the URI here if needed
                response_message = ResponseMessage(
                    play_audio=ResponseMessage.PlayAudio(
                        audio_uri=message
                    )
                )
            else:
                raise ValueError(
                    "For 'play_audio', message should be a valid URI."
                )
        elif response_type == "telephony_transfer_call":
            if isinstance(message, str):
                # Validate the E.164 format here if needed
                transfer_call_obj = ResponseMessage.TelephonyTransferCall(
                    phone_number=message
                )
                response_message = ResponseMessage(
                    telephony_transfer_call=transfer_call_obj
                )
            else:
                raise ValueError(
                    "For 'telephony_transfer_call',"
                    " message should be a valid E.164 format phone number."
                )
        else:
            raise ValueError(
                "response_type should be one of the following:"
                " 'text', 'live_agent_handoff', 'conversation_success',"
                " 'output_audio_text', 'play_audio', 'telephony_transfer_call'"
            )

        return response_message


    def add_response_message(
        self,
        response_type: str,
        message: Union[str, List[str], Dict[str, Any]],
        mode: str = None
    ) -> Fulfillment:
        """Add a rich message response to present to the user.

        Args:
          response_type (str):
            Type of the response message. It should be one of the following:
            'text', 'live_agent_handoff', 'conversation_success',
            'output_audio_text', 'play_audio', 'telephony_transfer_call'
          message (str | List[str] | Dict[str, str]):
            The output message. For each response_type
            it should be formatted like the following:
              text --> str | List[str]
              live_agent_handoff --> Dict[str, Any]
              conversation_success --> Dict[str, Any]
              output_audio_text --> str
              play_audio --> str
              telephony_transfer_call --> str
          mode (str):
            This argument is only applicable for 'output_audio_text'.
            It should be one of the following: 'text', 'ssml'

        Returns:
          A Fulfillment object stored in proto_obj
        """
        self._check_fulfillment_exist()

        response_msg = self._response_message_creator(
            response_type=response_type, message=message, mode=mode
        )
        self.proto_obj.messages.append(response_msg)

        return self.proto_obj


    def add_parameter_presets(
        self,
        parameter_map: Dict[str, str]
    ) -> Fulfillment:
        """Set parameter values.

        Args:
          parameter_map (Dict[str, str]):
            A dictionary that represents parameters as keys
            and the parameter values as it's values.
        Returns:
          A Fulfillment object stored in proto_obj
        """
        self._check_fulfillment_exist()

        if isinstance(parameter_map, dict):
            if not all((
                isinstance(key, str) and isinstance(val, str)
                for key, val in parameter_map.items()
            )):
                raise ValueError(
                    "Only strings are allowed as"
                    " dictionary keys and values in parameter_map."
                )
            for parameter, value in parameter_map.items():
                self.proto_obj.set_parameter_actions.append(
                    Fulfillment.SetParameterAction(
                        parameter=parameter, value=value
                    )
                )

            return self.proto_obj
        else:
            raise ValueError(
                "parameter_map should be a dictionary."
            )


    def create_new_fulfillment(
        self,
        webhook: str = None,
        tag: str = None,
        return_partial_responses: bool = False,
        overwrite: bool = False
    ) -> Fulfillment:
        """Create a new Fulfillment.

        Args:
          webhook (str):
            The webhook to call. Format:
            ``projects/<Project ID>/locations/<Location ID>/agents
              /<Agent ID>/webhooks/<Webhook ID>``.
          tag (str):
            The tag is typically used by
            the webhook service to identify which fulfillment is being
            called, but it could be used for other purposes. This field
            is required if ``webhook`` is specified.
          return_partial_responses (bool):
            Whether Dialogflow should return currently
            queued fulfillment response messages in
            streaming APIs. If a webhook is specified, it
            happens before Dialogflow invokes webhook.
          overwrite (bool)
            Overwrite the new proto_obj if proto_obj already
            contains a Fulfillment.

        Returns:
            A Fulfillment object stored in proto_obj.
        """
        if (return_partial_responses and
            not isinstance(return_partial_responses, bool)):
            raise ValueError(
                "return_partial_responses should be bool."
            )
        if ((webhook and not isinstance(webhook, str)) or
            (tag and not isinstance(tag, str))):
            raise ValueError(
                "webhook and tag should be string."
            )
        if webhook and not tag:
            raise ValueError(
                "tag is required when webhook is specified."
            )
        if self.proto_obj and not overwrite:
            raise Exception(
                "proto_obj already contains a Fulfillment."
                " If you wish to overwrite it, pass overwrite as True."
            )
        if overwrite or not self.proto_obj:
            self.proto_obj = Fulfillment(
                webhook=webhook,
                return_partial_responses=return_partial_responses,
                tag=tag
            )

        return self.proto_obj


    def add_conditional_case(
        self,
    ) -> Fulfillment:
        """A list of cascading if-else conditions. Cases are mutually
        exclusive. The first one with a matching condition is selected,
        all the rest ignored.

        Args:

        Returns:
          A Fulfillment object stored in proto_obj
        """
        self._check_fulfillment_exist()


class TransitionRouteBuilder:
    """Base Class for CX TransitionRoute builder."""

    def __init__(self, obj: TransitionRoute = None):
        self.proto_obj = None
        if obj:
            self.load_transition_route(obj)


    def __str__(self) -> str:
        """String representation of the proto_obj."""
        self._check_transition_route_exist()

        # Transition criteria str
        intent_str, cond_str = "Not Specified", "Not Specified"
        if self.proto_obj.intent:
            intent_str = self.proto_obj.intent
        if self.proto_obj.condition:
            cond_str = self.proto_obj.condition
        transition_criteria = (
            "Transition criteria:"
            f"\n\tIntent: {intent_str}\n\tCondition: {cond_str}"
        )
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
        target_str = f"Target: {target_type}\nTarget ID: {target_id}"
        # Fulfillment str
        if self.proto_obj.trigger_fulfillment:
            fulfillment_str = str(
                FulfillmentBuilder(self.proto_obj.trigger_fulfillment)
            )

        return f"{transition_criteria}\n{target_str}\n{fulfillment_str}"


    def _check_transition_route_exist(self):
        """Check if the proto_obj exists otherwise raise an error."""
        if not self.proto_obj:
            raise ValueError(
                "There is no proto_obj!\nUse create_new_transition_route"
                " or load_transition_route to continue."
            )
        elif not isinstance(self.proto_obj, TransitionRoute):
            raise ValueError(
                "proto_obj is not a TransitionRoute type."
                "\nPlease create or load the correct type to continue."
            )


    def load_transition_route(
        self, obj: TransitionRoute, overwrite: bool = False
    ) -> TransitionRoute:
        """Load an existing TransitionRoute to proto_obj for further uses.

        Args:
          obj (TransitionRoute):
            An existing TransitionRoute obj.
          overwrite (bool)
            Overwrite the new proto_obj if proto_obj already
            contains a TransitionRoute.

        Returns:
          A TransitionRoute object stored in proto_obj
        """
        if not isinstance(obj, TransitionRoute):
            raise ValueError(
                "The object you're trying to load is not a TransitionRoute!"
            )
        if self.proto_obj and not overwrite:
            raise Exception(
                "proto_obj already contains a TransitionRoute."
                " If you wish to overwrite it, pass overwrite as True."
            )
        if overwrite or not self.proto_obj:
            self.proto_obj = obj

        return self.proto_obj


    def create_new_transition_route(
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
            raise Exception(
                "At least one of `intent` or `condition` must be specified."
            )
        # Oneof error checking
        if target_page and target_flow:
            raise Exception(
                "At most one of `target_page` and `target_flow`"
                " can be specified at the same time."
            )
        # `overwrite` parameter error checking
        if self.proto_obj and not overwrite:
            raise Exception(
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


    def show_transition_route(self):
        """Show the proto_obj information."""
        self._check_transition_route_exist()

        print(self.__str__())


class EventHandlerBuilder:
    """Base Class for CX EventHandler builder."""

    def __init__(self, obj: EventHandler = None):
        self.proto_obj = None
        if obj:
            self.load_event_handler(obj)


    def __str__(self) -> str:
        """String representation of the proto_obj."""
        self._check_event_handler_exist()

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
        target_str = f"Target: {target_type}\nTarget ID: {target_id}"
        # Fulfillment str
        if self.proto_obj.trigger_fulfillment:
            fulfillment_str = str(
                FulfillmentBuilder(self.proto_obj.trigger_fulfillment)
            )

        return f"{event_str}\n{target_str}\n{fulfillment_str}"


    def _check_event_handler_exist(self):
        """Check if the proto_obj exists otherwise raise an error."""
        if not self.proto_obj:
            raise ValueError(
                "There is no proto_obj!\nUse create_new_event_handler"
                " or load_event_handler to continue."
            )
        elif not isinstance(self.proto_obj, EventHandler):
            raise ValueError(
                "proto_obj is not an EventHandler type."
                "\nPlease create or load the correct type to continue."
            )


    def load_event_handler(
        self, obj: EventHandler, overwrite: bool = False
    ) -> EventHandler:
        """Load an existing EventHandler to proto_obj for further uses.

        Args:
          obj (EventHandler):
            An existing EventHandler obj.
          overwrite (bool)
            Overwrite the new proto_obj if proto_obj already
            contains an EventHandler.

        Returns:
          An EventHandler object stored in proto_obj
        """
        if not isinstance(obj, EventHandler):
            raise ValueError(
                "The object you're trying to load is not an EventHandler!"
            )
        if self.proto_obj and not overwrite:
            raise Exception(
                "proto_obj already contains an EventHandler."
                " If you wish to overwrite it, pass overwrite as True."
            )
        if overwrite or not self.proto_obj:
            self.proto_obj = obj

        return self.proto_obj


    def create_new_event_handler(
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
            raise Exception(
                "At most one of target_page and target_flow"
                " can be specified at the same time."
            )
        # `overwrite` parameter error checking
        if self.proto_obj and not overwrite:
            raise Exception(
                "proto_obj already contains an EventHandler."
                " If you wish to overwrite it, pass overwrite as True."
            )
        # Create the EventHandler
        if overwrite or not self.proto_obj:
            self.proto_obj = EventHandler(
                event=event,
                trigger_fulfillment=trigger_fulfillment,
                target_page=target_page,
                target_flow=target_flow
            )

        return self.proto_obj


    def show_event_handler(self):
        """Show the proto_obj information."""
        self._check_event_handler_exist()

        print(self.__str__())
