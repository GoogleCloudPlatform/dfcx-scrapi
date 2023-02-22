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
from datetime import timedelta
from typing import Dict

from google.cloud.dialogflowcx_v3beta1.types import Webhook
from dfcx_scrapi.builders.builders_common import BuildersCommon

# logging config
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


class WebhookBuilder(BuildersCommon):
    """Base Class for CX Webhook builder."""
    _proto_type = Webhook
    _proto_type_str = "Webhook"


    def __str__(self) -> str:
        """String representation of the proto_obj."""
        self._check_proto_obj_attr_exist()

        basic_info = self._show_basic_info()
        service_info = self._show_service_info()

        return f"{basic_info}\n{service_info}"


    def _show_basic_info(self) -> str:
        """String representation for the basic information of proto_obj."""
        self._check_proto_obj_attr_exist()

        return (
            f"display_name: {self.proto_obj.display_name}"
            f"\ntimeout: {self.proto_obj.timeout.seconds}"
            f"\ndisabled: {self.proto_obj.disabled}"
        )

    def _show_service_info(self) -> str:
        """String representation for the service information of proto_obj."""
        self._check_proto_obj_attr_exist()

        service_type = "Generic Web Service"
        gws = self.proto_obj.generic_web_service
        if self.proto_obj.service_directory:
            service_type = "Service Directory"
            gws = self.proto_obj.service_directory.generic_web_service

        have_ca_certs = bool(gws.allowed_ca_certs)

        return (
            f"service_type: {service_type}"
            f"\n\turi: {gws.uri}"
            f"\n\tusername: {gws.username}"
            f"\n\tpassword: {gws.password}"
            f"\n\trequest_headers: {gws.request_headers}"
            f"\n\thave_ca_certs: {have_ca_certs}"
        )


    def create_new_proto_obj(
        self,
        display_name: str,
        timeout: int = 5,
        disabled: bool = False,
        overwrite: bool = False
    ):
        """Create a new Webhook.

        Args:
          display_name (str):
            Required. The human-readable name of the webhook.
            It should be unique within the agent.
          timeout (int):
            Webhook execution timeout. Execution is
            considered failed if Dialogflow doesn't receive
            a response from webhook at the end of the
            timeout period. Defaults to 5 seconds, maximum
            allowed timeout is 30 seconds.
          disabled (bool):
            Indicates whether the webhook is disabled.
          overwrite (bool)
            Overwrite the new proto_obj if proto_obj already
            contains a Webhook.

        Returns:
          A Webhook object stored in proto_obj.
        """
        # Types error checking
        if not isinstance(display_name, str):
            raise ValueError("`display_name` should be a string.")
        if not(isinstance(timeout, int) and (0 <= timeout < 30)):
            raise ValueError(
                "`timeout` should be an int within the range [0, 30] seconds."
            )
        if not isinstance(disabled, bool):
            raise ValueError("`disabled` should be a bool.")

        # `overwrite` parameter error checking
        if self.proto_obj and not overwrite:
            raise UserWarning(
                "proto_obj already contains a Webhook."
                " If you wish to overwrite it, pass overwrite as True."
            )

        # Create the webhook
        if overwrite or not self.proto_obj:
            self.proto_obj = Webhook(
                display_name=display_name,
                timeout=timedelta(seconds=timeout),
                disabled=disabled
            )

        return self.proto_obj


    def add_web_service(
        self,
        uri: str,
        service: str = None,
        username: str = None,
        password: str = None,
        request_headers: Dict[str, str] = None
    ):
        """Add a configuration for a generic web service or a service directory.

        Args:
          uri (str):
            Required. The webhook URI for receiving POST
            requests. It must use https protocol.
          service (str):
            The name of the service directory. If it's None it'll configure a
            "generic web service" otherwise it'll configure a service.
            `Service Directory <https://cloud.google.com/service-directory>`
            Format for service directory:
            ``projects/<Project ID>/locations/<Location ID>/namespaces/
              <Namespace ID>/services/<Service ID>``.
            `Location ID` of the service directory must be the same as
            the location of the agent.
          username (str):
            The user name for HTTP Basic authentication.
          password (str):
            The password for HTTP Basic authentication.
          request_headers (Dict[str, str]):
            The HTTP request headers to send together
            with webhook requests.

        Returns:
          A Webhook object stored in proto_obj.
        """
        # TODO: allowed_ca_certs:
        # https://github.com/googleapis/python-dialogflow-cx/blob/f2d12c53804dec7b236509aa29b200aebcc53c8a/google/cloud/dialogflowcx_v3beta1/types/webhook.py#L103
        self._check_proto_obj_attr_exist()

        # Type error checking
        if ((not isinstance(uri, str)) or
            (username and not isinstance(username, str)) or
            (password and not isinstance(password, str))
        ):
            raise ValueError(
                "`uri`, `username`, and `password` if present should be string."
            )
        req_head_err_msg = (
            "`request_headers` should be a dict with string keys and values."
        )
        if not isinstance(request_headers, dict):
            raise ValueError(req_head_err_msg)
        for k, v in request_headers.items():
            if not(isinstance(k, str) and isinstance(v, str)):
                raise ValueError(req_head_err_msg)

        # Create a generic web service
        gws = Webhook.GenericWebService(
            uri=uri, username=username, password=password,
            request_headers=request_headers
        )
        if service:
            # TODO: Format checking for service
            sdc = Webhook.ServiceDirectoryConfig(
                service=service, generic_web_service=gws
            )
            self.proto_obj.service_directory = sdc
        else:
            self.proto_obj.generic_web_service = gws

        return self.proto_obj


    def show_webhook(self):
        """Show the proto_obj information."""
        self._check_proto_obj_attr_exist()

        print(self)
