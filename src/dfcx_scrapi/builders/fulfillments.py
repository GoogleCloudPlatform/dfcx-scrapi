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
from typing import Dict

from google.cloud.dialogflowcx_v3beta1.types import Fulfillment
from google.cloud.dialogflowcx_v3beta1.types import ResponseMessage
from dfcx_scrapi.builders.builders_common import BuildersCommon
from dfcx_scrapi.builders.response_messages import ResponseMessageBuilder

# logging config
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


class FulfillmentBuilder(BuildersCommon):
    """Base Class for CX Fulfillment builder."""
    # TODO: ConditionalCases: def add_conditional_case(self) -> Fulfillment:

    _proto_type = Fulfillment
    _proto_type_str = "Fulfillment"


    def __str__(self) -> str:
        """String representation of the proto_obj."""
        try:
            self._check_proto_obj_attr_exist()
        except ValueError:
            return ""

        basic_info_str = self._show_basic_info()
        resp_msgs_str = self._show_response_messages()
        params_str = self._show_parameters()

        return (
            f"Fulfillment Basic Information:\n{'-'*20}\n{basic_info_str}"
            f"\n\n\nFulfillment ResponseMessages:\n{'-'*20}\n{resp_msgs_str}"
            f"\n\n\nFulfillment Parameters:\n{'-'*20}\n{params_str}"
        )


    def _show_basic_info(self) -> str:
        """String representation for the basic information of proto_obj."""
        self._check_proto_obj_attr_exist()

        partial_resp = self.proto_obj.return_partial_responses
        return (
            f"webhook: {self.proto_obj.webhook}"
            f"\ntag: {self.proto_obj.tag}"
            f"\nreturn_partial_responses: {partial_resp}"
        )


    def _show_parameters(self) -> str:
        """String representation for the parameters presets of proto_obj."""
        self._check_proto_obj_attr_exist()

        return "\n".join([
            f"{param.parameter}: {param.value if param.value else 'null'}"
            for param in self.proto_obj.set_parameter_actions
        ])


    def _show_response_messages(self) -> str:
        """String representation of response messages in proto_obj."""
        self._check_proto_obj_attr_exist()

        return "\n".join([
            f"ResponseMessage {i+1}:\n{str(ResponseMessageBuilder(msg))}"
            for i, msg in enumerate(self.proto_obj.messages)
        ])


    def show_fulfillment(self, mode: str = "whole"):
        """Show the proto_obj information.
        Args:
          mode (str):
            Specifies what part of the fulfillment to show.
            Options:
              ['basic', 'parameters',
                'messages' or 'response messages', 'whole']
        """
        self._check_proto_obj_attr_exist()

        if mode == "basic":
            print(self._show_basic_info())
        elif mode == "parameters":
            print(self._show_parameters())
        elif mode in ["messages", "response messages"]:
            print(self._show_response_messages())
        elif mode == "whole":
            print(self)
        else:
            raise ValueError(
                "mode should be in"
                "['basic', 'parameters',"
                " 'messages' or 'response messages', 'whole']"
            )


    def create_new_proto_obj(
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
        # Types error checking
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
        # webhook with tag presence check
        if webhook and not tag:
            raise ValueError(
                "tag is required when webhook is specified."
            )
        # `overwrite` parameter error checking
        if self.proto_obj and not overwrite:
            raise UserWarning(
                "proto_obj already contains a Fulfillment."
                " If you wish to overwrite it, pass overwrite as True."
            )
        # Create the fulfillment
        if overwrite or not self.proto_obj:
            self.proto_obj = Fulfillment(
                webhook=webhook,
                return_partial_responses=return_partial_responses,
                tag=tag
            )

        return self.proto_obj


    def add_response_message(
        self,
        response_message: ResponseMessage
    ) -> Fulfillment:
        """Add a rich message response to present to the user.

        Args:
          response_message (ResponseMessage):
            The ResponseMessage to add to the Fulfillment.
            Refer to `builders.response_message.ResponseMessageBuilder`
              to build one.

        Returns:
          A Fulfillment object stored in proto_obj
        """
        self._check_proto_obj_attr_exist()

        if not isinstance(response_message, ResponseMessage):
            raise ValueError(
                "`response_message` type should be ResponseMessage."
            )

        self.proto_obj.messages.append(response_message)

        return self.proto_obj


    def add_parameter_presets(
        self,
        parameter_map: Dict[str, str]
    ) -> Fulfillment:
        """Set parameter values before executing the webhook.

        Args:
          parameter_map (Dict[str, str]):
            A dictionary that represents parameters as keys
            and the parameter values as it's values.
            A `None` value clears the parameter.

        Returns:
          A Fulfillment object stored in proto_obj
        """
        self._check_proto_obj_attr_exist()

        # Type error checking
        if isinstance(parameter_map, dict):
            if not all((
                isinstance(key, str) and isinstance(val, str)
                for key, val in parameter_map.items()
            )):
                raise ValueError(
                    "Only strings are allowed as"
                    " dictionary keys and values in parameter_map."
                )
            for param, val in parameter_map.items():
                self.proto_obj.set_parameter_actions.append(
                    Fulfillment.SetParameterAction(parameter=param, value=val)
                )

            return self.proto_obj
        else:
            raise ValueError(
                "parameter_map should be a dictionary."
            )


    def remove_parameter_presets(
        self,
        parameter_map: Dict[str, str]
    ) -> Fulfillment:
        """Remove parameter values from the fulfillment.

        Args:
          parameter_map (Dict[str, str]):
            A dictionary that represents parameters as keys
            and the parameter values as it's values.
            A `None` value clears the parameter.

        Returns:
          A Fulfillment object stored in proto_obj
        """
        self._check_proto_obj_attr_exist()

        # Type error checking
        if isinstance(parameter_map, dict):
            if not all((
                isinstance(key, str) and isinstance(val, str)
                for key, val in parameter_map.items()
            )):
                raise ValueError(
                    "Only strings are allowed as"
                    " dictionary keys and values in parameter_map."
                )

            new_params = []
            for param in self.proto_obj.set_parameter_actions:
                if (
                    param.parameter in parameter_map and
                    param.value == parameter_map[param.parameter]
                ):
                    continue

                new_params.append(param)

            self.proto_obj.set_parameter_actions = new_params
            return self.proto_obj
        else:
            raise ValueError(
                "parameter_map should be a dictionary."
            )


    def has_webhook(self) -> bool:
        """Check whether the Fulfillment in proto_obj uses a Webhook.

        Returns:
          True if proto_obj uses a Webhook and False otherwise
        """
        try:
            self._check_proto_obj_attr_exist()
        except ValueError:
            return False

        return bool(self.proto_obj.webhook)
