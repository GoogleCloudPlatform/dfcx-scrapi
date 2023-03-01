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

import re
import logging
from typing import List, Dict, Union, Any

from google.cloud.dialogflowcx_v3beta1.types import ResponseMessage
from google.protobuf import struct_pb2
from dfcx_scrapi.builders.builders_common import BuildersCommon

# logging config
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


class ResponseMessageBuilder(BuildersCommon):
    """Base Class for CX ResponseMessage builder."""

    _proto_type = ResponseMessage
    _proto_type_str = "ResponseMessage"


    def __str__(self) -> str:
        """String representation of the proto_obj."""
        self._check_proto_obj_attr_exist()

        if self.proto_obj.text:
            resp_type = "text"
            resp_msg = self.proto_obj.text.text
        elif self.proto_obj.payload:
            resp_type = "payload"
            proto_struct = self.proto_obj.payload
            resp_msg = "\n\t".join([
                f"{k}: {v}" for k, v in proto_struct.items()
            ])
        elif self.proto_obj.conversation_success:
            resp_type = "conversation_success"
            proto_struct = self.proto_obj.conversation_success.metadata
            resp_msg = "\n\t".join([
                f"{k}: {v}" for k, v in proto_struct.items()
            ])
        elif self.proto_obj.output_audio_text:
            if self.proto_obj.output_audio_text.text:
                resp_type = "output_audio_text - text"
                resp_msg = self.proto_obj.output_audio_text.text
            elif self.proto_obj.output_audio_text.ssml:
                resp_type = "output_audio_text - ssml"
                resp_msg = self.proto_obj.output_audio_text.ssml
        elif self.proto_obj.live_agent_handoff:
            resp_type = "live_agent_handoff"
            proto_struct = self.proto_obj.live_agent_handoff.metadata
            resp_msg = "\n\t".join([
                f"{k}: {v}" for k, v in proto_struct.items()
            ])
        elif self.proto_obj.play_audio:
            resp_type = "play_audio"
            resp_msg = self.proto_obj.play_audio.audio_uri
        elif self.proto_obj.telephony_transfer_call:
            resp_type = "telephony_transfer_call"
            resp_msg = self.proto_obj.telephony_transfer_call.phone_number

        return (
            f"Response Type: {resp_type}\nMessage:\n\t{resp_msg}"
        )


    def show_response_message(self):
        """Show the proto_obj information."""
        self._check_proto_obj_attr_exist()
        print(self)


    def _create_text_response(
        self, message: Union[str, List[str]]
    ) -> ResponseMessage:
        """Create a text ResponseMessage.

        Args:
          message (str | List[str]):
            The output message. A single message as a string or
            multiple messages as a list of strings

        Returns:
          A ResponseMessage object
        """
        if isinstance(message, str):
            message = [message]
        elif isinstance(message, list):
            if not all((isinstance(msg, str) for msg in message)):
                raise ValueError(
                    "Only strings are allowed in message list for `text`."
                )
        else:
            raise ValueError(
                "For 'text' message should be"
                " either a string or a list of strings."
            )

        return ResponseMessage(text=ResponseMessage.Text(text=message))

    def _create_payload_response(
        self, message: Dict[str, Any]
    ) -> ResponseMessage:
        """Create a payload ResponseMessage.

        Args:
          message (Dict[str, Any]):
            The output message. Any dictionary which its keys are string.
            Dialogflow doesn't impose any structure on the values.

        Returns:
          A ResponseMessage object
        """
        if not(
            isinstance(message, dict)
            and all((isinstance(key, str) for key in message.keys()))
        ):
            raise ValueError(
                "For `payload`, message should be"
                " a dictionary and its keys should be strings."
            )

        proto_struct = struct_pb2.Struct()
        proto_struct.update(message)

        return ResponseMessage(payload=proto_struct)

    def _create_conversation_success_response(
        self, message: Dict[str, Any]
    ) -> ResponseMessage:
        """Create a conversation_success ResponseMessage.

        Args:
          message (Dict[str, Any]):
            The output message. Any dictionary which its keys are string.
            Dialogflow doesn't impose any structure on the values.

        Returns:
          A ResponseMessage object
        """
        proto_struct = struct_pb2.Struct()
        proto_struct.update(message)
        convo_success = ResponseMessage.ConversationSuccess(
            metadata=proto_struct
        )

        return ResponseMessage(conversation_success=convo_success)

    def _create_output_audio_text_response(
        self, message: str, mode: str
    ) -> ResponseMessage:
        """Create a output_audio_text ResponseMessage.

        Args:
          message (str):
            The output message. A text or ssml response as a string.
          mode (str):
            It should be one of the following: 'text', 'ssml'

        Returns:
          A ResponseMessage object
        """
        if not isinstance(message, str):
            raise ValueError(
                "For 'output_audio_text', message should be a string."
            )

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
                " for `output_audio_text`."
            )

        return ResponseMessage(output_audio_text=output_audio_text)

    def _create_live_agent_handoff_response(
        self, message: Dict[str, Any]
    ) -> ResponseMessage:
        """Create a live_agent_handoff ResponseMessage.

        Args:
          message (Dict[str, Any]):
            The output message. Any dictionary which its keys are string.
            Dialogflow doesn't impose any structure on the values.

        Returns:
          A ResponseMessage object
        """
        if not(
            isinstance(message, dict)
            and all((isinstance(key, str) for key in message.keys()))
        ):
            raise ValueError(
                "For `live_agent_handoff`, message should be"
                " a dictionary and its keys should be strings."
            )

        proto_struct = struct_pb2.Struct()
        proto_struct.update(message)
        live_agent_handoff = ResponseMessage.LiveAgentHandoff(
            metadata=proto_struct
        )

        return ResponseMessage(live_agent_handoff=live_agent_handoff)

    def _create_play_audio_response(self, message: str) -> ResponseMessage:
        """Create a play_audio ResponseMessage.

        Args:
          message (str):
            The output message. URI of the audio clip.
            Dialogflow does not impose any validation on this value.

        Returns:
          A ResponseMessage object
        """
        if not isinstance(message, str):
            raise ValueError(
                "For 'play_audio', message should be a valid URI string."
            )

        # TODO: Validate the URI here

        return ResponseMessage(
            play_audio=ResponseMessage.PlayAudio(audio_uri=message)
        )

    def _create_telephony_transfer_call_response(
        self, message: str
    ) -> ResponseMessage:
        """Create a telephony_transfer_call ResponseMessage.

        Args:
          message (str):
            The output message. A phone number in E.164 format as a string.
            `<https://en.wikipedia.org/wiki/E.164>`

        Returns:
          A ResponseMessage object
        """
        e_164_re_pattern = r"^\+[1-9]\d{1,14}$"
        if not (
            isinstance(message, str)
            and re.search(e_164_re_pattern, message)
        ):
            raise ValueError(
                "For 'telephony_transfer_call',"
                " message should be a valid E.164 format phone number."
            )
        transfer_call_obj = ResponseMessage.TelephonyTransferCall(
            phone_number=message
        )

        return ResponseMessage(telephony_transfer_call=transfer_call_obj)


    def create_new_proto_obj(
        self,
        message: Union[str, List[str], Dict[str, Any]],
        response_type: str = "text",
        mode: str = None
    ) -> ResponseMessage:
        """Create a ResponseMessage that can be returned by a
        conversational agent.
        ResponseMessages are also used for output audio synthesis.

        Args:
          message (str | List[str] | Dict[str, Any]):
            The output message. For each response_type
            it should be formatted like the following:
              text --> str | List[str]
                A single message as a string or
                multiple messages as a list of strings
              payload --> Dict[str, Any]
                Any dictionary which its keys are string.
                Dialogflow doesn't impose any structure on the values.
              conversation_success --> Dict[str, Any]
                Any dictionary which its keys are string.
                Dialogflow doesn't impose any structure on the values.
              output_audio_text --> str
                A text or ssml response as a string.
              live_agent_handoff --> Dict[str, Any]
                Any dictionary which its keys are string.
                Dialogflow doesn't impose any structure on the values.
              play_audio --> str
                URI of the audio clip.
                Dialogflow does not impose any validation on this value.
              telephony_transfer_call --> str
                A phone number in E.164 format as a string.
                `<https://en.wikipedia.org/wiki/E.164>`
          response_type (str):
            Type of the response message. It should be one of the following:
            'text', 'payload', 'conversation_success', 'output_audio_text',
            'live_agent_handoff', 'play_audio', 'telephony_transfer_call'
          mode (str):
            This argument is only applicable for `output_audio_text`.
            It should be one of the following: 'text', 'ssml'

        Returns:
          A ResponseMessage object stored in proto_obj
        """
        if response_type == "text":
            resp = self._create_text_response(message)
        elif response_type == "payload":
            resp = self._create_payload_response(message)
        elif response_type == "conversation_success":
            resp = self._create_conversation_success_response(message)
        elif response_type == "output_audio_text":
            resp = self._create_output_audio_text_response(message, mode)
        elif response_type == "live_agent_handoff":
            resp = self._create_live_agent_handoff_response(message)
        elif response_type == "play_audio":
            resp = self._create_play_audio_response(message)
        elif response_type == "telephony_transfer_call":
            resp = self._create_telephony_transfer_call_response(message)
        else:
            raise ValueError(
                "response_type should be one of the following:"
                "\n['text', 'payload', 'conversation_success',"
                " 'output_audio_text', 'live_agent_handoff', 'play_audio',"
                " 'telephony_transfer_call']"
            )

        self.proto_obj = resp
        return self.proto_obj
