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

from google.cloud.dialogflowcx_v3beta1 import types
from google.protobuf import struct_pb2


class FulfillmentBuilder:
    """Base Class for CX Fulfillment builder."""


    def __init__(self, obj: types.Fulfillment = None):
        self.proto_obj = None
        if obj:
            self.load_fulfillment(obj)


    def _check_fulfillment_exist(self):
        """Check if the proto_obj exists otherwise raise an error."""

        if not self.proto_obj:
            raise ValueError(
                "There is no proto_obj!"
                "\nUse create_empty_fulfillment or load_fulfillment to continue."
            )
        elif not isinstance(self.proto_obj, types.Fulfillment):
            raise ValueError(
                "proto_obj is not a Fulfillment type."
                "\nPlease create or load the correct type to continue."
            )


    def load_fulfillment(
        self, obj: types.Fulfillment, overwrite: bool = False
    ) -> types.Fulfillment:
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
        if not isinstance(obj, types.Fulfillment):
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
        response_type: str,
        message: Union[str, List[str], Dict[str, Any]],
        mode: str = None
    ) -> types.ResponseMessage:
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
                response_message = types.ResponseMessage(
                    text=types.ResponseMessage.Text(text=[message])
                )
            elif isinstance(message, list):
                if not all((isinstance(msg, str) for msg in message)):
                    raise ValueError(
                        "Only strings are allowed in message list."
                    )
                response_message = types.ResponseMessage(
                    text=types.ResponseMessage.Text(text=message)
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
                        "Only strings are allowed as dictionary keys in message."
                    )
                proto_struct = struct_pb2.Struct()
                proto_struct.update(message)
                live_agent_handoff = types.ResponseMessage.LiveAgentHandoff(
                    metadata=proto_struct
                )
                response_message = types.ResponseMessage(
                    live_agent_handoff=live_agent_handoff
                )
            else:
                raise ValueError(
                    "For 'live_agent_handoff',"
                    " message should be a dictionary."
                )
            pass
        elif response_type == "conversation_success":
            if isinstance(message, dict):
                if not all((isinstance(key, str) for key in message.keys())):
                    raise ValueError(
                        "Only strings are allowed as dictionary keys in message"
                    )
                proto_struct = struct_pb2.Struct()
                proto_struct.update(message)
                convo_success = types.ResponseMessage.ConversationSuccess(
                    metadata=proto_struct
                )
                response_message = types.ResponseMessage(
                    conversation_success=convo_success
                )
            else:
                raise ValueError(
                    "For 'conversation_success',"
                    " message should be a dictionary."
                )
            pass
        elif response_type == "output_audio_text":
            if isinstance(message, str):
                if mode == "text":
                    output_audio_text = types.ResponseMessage.OutputAudioText(
                        text=message
                    )
                elif mode == "ssml":
                    output_audio_text = types.ResponseMessage.OutputAudioText(
                        ssml=message
                    )
                else:
                    raise ValueError(
                        "mode should be either 'text' or 'ssml'"
                        " for output_audio_text."
                    )
                response_message = types.ResponseMessage(
                    output_audio_text=output_audio_text
                )
            else:
                raise ValueError(
                    "For 'output_audio_text', message should be a string."
                )
        elif response_type == "play_audio":
            if isinstance(message, str):
                # Validate the URI here if needed
                response_message = types.ResponseMessage(
                    play_audio=types.ResponseMessage.PlayAudio(
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
                transfer_call_obj = types.ResponseMessage.TelephonyTransferCall(
                    phone_number=message
                )
                response_message = types.ResponseMessage(
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
    

    def add_response_message(
        self,
        response_type: str,
        message: Union[str, List[str], Dict[str, Any]],
        mode: str = None
    ) -> types.Fulfillment:
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
    ) -> types.Fulfillment:
        """Set parameter values. For single 

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
                    types.Fulfillment.SetParameterAction(
                        parameter=parameter, value=value
                    )
                )

            return self.proto_obj
        else:
            raise ValueError(
                "parameter_map should be a dictionary."
            )


    def create_empty_fulfillment(
        self,
        webhook: str = None,
        tag: str = None,
        return_partial_responses: bool = False,
        overwrite: bool = False
    ) -> types.Fulfillment:
        """Create an empty Fulfillment.

        Args:
            webhook (str):
                The webhook to call. Format:
                ``projects/<Project ID>/locations/<Location ID>/agents
                  /<Agent ID>/webhooks/<Webhook ID>``.
            tag (str):
                The value of this field will be populated in the
                [WebhookRequest][google.cloud.dialogflow.cx.v3beta1.WebhookRequest]
                ``fulfillmentInfo.tag`` field by Dialogflow when the
                associated webhook is called. The tag is typically used by
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
            self.proto_obj = types.Fulfillment(
                webhook=webhook,
                return_partial_responses=return_partial_responses,
                tag=tag
            )

        return self.proto_obj


    def add_conditional_case(
        self,
    ) -> types.Fulfillment:
        """A list of cascading if-else conditions. Cases are mutually
        exclusive. The first one with a matching condition is selected,
        all the rest ignored.

        Args:

        Returns:
          A Fulfillment object stored in proto_obj
        """
        self._check_fulfillment_exist()
