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
from typing import List

from google.cloud.dialogflowcx_v3beta1.types import Agent
from google.cloud.dialogflowcx_v3beta1.types import SpeechToTextSettings
from dfcx_scrapi.builders.builders_common import BuildersCommon

# logging config
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


class AgentBuilder(BuildersCommon):
    """Base Class for CX Agent builder."""

    _proto_type = Agent
    _proto_type_str = "Agent"


    def __str__(self) -> str:
        """String representation of the proto_obj."""
        self._check_proto_obj_attr_exist()

        logs = self.proto_obj.advanced_settings.logging_settings
        speech_2_txt = self.proto_obj.speech_to_text_settings
        return (
            f"display_name: {self.proto_obj.display_name}"
            f"\ntime_zone: {self.proto_obj.time_zone}"
            f"\ndefault_language_code: {self.proto_obj.default_language_code}"
            f"\ndescription: {self.proto_obj.description}"
            f"\navatar_uri: {self.proto_obj.avatar_uri}"
            "\nenable_speech_adaptation:"
            f" {speech_2_txt.enable_speech_adaptation}"
            "\nenable_spell_correction:"
            f" {self.proto_obj.enable_spell_correction}"
            "\nsupported_language_codes:"
            f" {self.proto_obj.supported_language_codes}"
            "\nenable_stackdriver_logging:"
            f" {logs.enable_stackdriver_logging}"
            "\nenable_interaction_logging:"
            f" {logs.enable_interaction_logging}"
            f"\nsecurity_settings: {self.proto_obj.security_settings}")


    def show_agent_info(self):
        """Show the proto_obj information."""
        self._check_proto_obj_attr_exist()

        print(self)


    def create_new_proto_obj(
        self,
        display_name: str,
        time_zone: str,
        default_language_code: str = "en",
        description: str = None,
        avatar_uri: str = None,
        overwrite: bool = False
    ) -> Agent:
        """Create a new Agent.

        Args:
          display_name (str):
            Required. The human-readable name of the
            agent, unique within the location.
          time_zone (str):
            Required. The time zone of the agent from the
            `time zone database <https://www.iana.org/time-zones>`.
            e.g., America/New_York, Europe/Paris.
          default_language_code (str):
            Required. Immutable. The default language of the agent as a
            language tag. See `Language Support
              <https://cloud.google.com/dialogflow/cx/docs/reference/language>`
            for a list of the currently supported language codes. This
            field cannot be updated.
          description (str):
            The description of the agent. The maximum
            length is 500 characters. If exceeded, the
            request is rejected.
          avatar_uri (str):
            The URI of the agent's avatar. Avatars are used throughout
            the Dialogflow console and in the self-hosted `Web Demo
              <https://cloud.google.com/dialogflow/docs/integrations/web-demo>`
            integration.
          overwrite (bool)
            Overwrite the new proto_obj if proto_obj already
            contains an Agent.

        Returns:
          An Agent object stored in proto_obj
        """
        if ((display_name and not isinstance(display_name, str)) or
            (time_zone and not isinstance(time_zone, str))):
            raise ValueError(
                "display_name and time_zone should be string."
            )
        if self.proto_obj and not overwrite:
            raise UserWarning(
                "proto_obj already contains an Agent."
                " If you wish to overwrite it, pass overwrite as True."
            )
        if overwrite or not self.proto_obj:
            self.proto_obj = Agent(
                display_name=display_name,
                time_zone=time_zone,
                default_language_code=default_language_code,
                description=description,
                avatar_uri=avatar_uri,
                locked=False,
            )

        return self.proto_obj


    def language_and_speech_settings(
        self,
        enable_speech_adaptation: bool = False,
        enable_spell_correction: bool = False,
        supported_language_codes: List[str] = None,
    ) -> Agent:
        """Change the language and speech settings.

        Args:
          enable_speech_adaptation (bool):
            Whether to use speech adaptation for speech
            recognition.
          enable_spell_correction (bool):
            Indicates if automatic spell correction is
            enabled in detect intent requests.
          supported_language_codes (List[str]):
            The list of all languages supported by the agent
            (except for the ``default_language_code``).

        Returns:
          An Agent object stored in proto_obj
        """
        self._check_proto_obj_attr_exist()

        if isinstance(enable_speech_adaptation, bool):
            self.proto_obj.speech_to_text_settings=SpeechToTextSettings(
                enable_speech_adaptation=enable_speech_adaptation
            )
        if isinstance(enable_spell_correction, bool):
            self.proto_obj.enable_spell_correction = enable_spell_correction
        if supported_language_codes:
            if (isinstance(supported_language_codes, list) and
                all(
                    (isinstance(lang, str) for lang in supported_language_codes)
                )):
                the_obj = self.proto_obj
                the_obj.supported_language_codes = supported_language_codes
            else:
                raise ValueError(
                    "supported_language_codes should be a list of strings."
                )

        return self.proto_obj


    def security_and_logging_settings(
        self,
        enable_stackdriver_logging: bool = False,
        enable_interaction_logging: bool = False,
        security_settings: str = None,
    ) -> Agent:
        """ Change the security and logging settings.

        Args:
          enable_stackdriver_logging (bool):
            If true, StackDriver logging is currently
            enabled.
          enable_interaction_logging (bool):
            If true, DF Interaction logging is currently
            enabled.
          security_settings (str):
            Name of the
            ``[SecuritySettings]
              [google.cloud.dialogflow.cx.v3beta1.SecuritySettings]``
            reference for the agent.Format:
            ``projects/<Project ID>/locations/<Location ID>/
              securitySettings/<Security Settings ID>``.

        Returns:
          An Agent object stored in proto_obj
        """
        self._check_proto_obj_attr_exist()

        logs = self.proto_obj.advanced_settings.logging_settings
        if isinstance(enable_stackdriver_logging, bool):
            logs.enable_stackdriver_logging = enable_stackdriver_logging
        if isinstance(enable_interaction_logging, bool):
            logs.enable_interaction_logging = enable_interaction_logging
        if security_settings and isinstance(security_settings, str):
            self.proto_obj.security_settings = security_settings

        return self.proto_obj


