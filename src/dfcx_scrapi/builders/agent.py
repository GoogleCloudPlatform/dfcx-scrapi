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

from typing import List

from google.cloud.dialogflowcx_v3beta1 import types


class AgentBuilder:
    """Base Class for CX Agent builder."""


    def __init__(self, obj: types.Agent = None):
        if self.proto_obj:
            self.load_agent(obj)


    def _check_agent_exist(self):
        """Check if the proto_obj exists otherwise raise an error."""

        if not self.proto_obj:
            raise ValueError(
                "There is no proto_obj!"
                "\nUse create_empty_agent or load_agent to continue."
            )
        elif not isinstance(self.proto_obj, types.Agent):
            raise ValueError(
                "proto_obj is not an Agent type."
                "\nPlease create or load the correct type to continue."
            )


    def load_agent(self, obj: types.Agent) -> types.Agent:
        """Load an existing agent to proto_obj for further uses.

        Args:
          obj (Agent):
            An existing Agent obj.

        Returns:
          An Agent object stored in proto_obj
        """
        if not isinstance(obj, types.Agent):
            raise ValueError(
                "The object you're trying to load is not an Agent!"
            )
        # self.proto_obj = copy.deepcopy(obj)
        self.proto_obj = obj

        return self.proto_obj


    def create_empty_agent(
        self,
        display_name: str,
        time_zone: str,
        default_language_code: str = "en",
        description: str = None,
        avatar_uri: str = None,
    ) -> types.Agent:
        """Create an empty Agent.

        Args:
          display_name (str):
            Required. The human-readable name of the
            agent, unique within the location.
          time_zone (str):
            Required. The time zone of the agent from the `time zone
            database <https://www.iana.org/time-zones>`__, e.g.,
            America/New_York, Europe/Paris.
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

        Returns:
          An Agent object stored in proto_obj
        """
        if (
            (description and not isinstance(description, str)) or
            (avatar_uri and not isinstance(avatar_uri, str))
        ):
            raise ValueError(
                "description and avatar_uri should be string."
            )

        self.proto_obj = types.Agent(
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
    ) -> types.Agent:
        """Change the language and speech settings.

        Args:
          supported_language_codes (List[str]):
            The list of all languages supported by the agent
            (except for the ``default_language_code``).
          enable_speech_adaptation (bool):
            Whether to use speech adaptation for speech
            recognition.
          enable_spell_correction (bool):
            Indicates if automatic spell correction is
            enabled in detect intent requests.

        Returns:
          An Agent object stored in proto_obj
        """
        self._check_agent_exist()

        if isinstance(enable_speech_adaptation, bool):
            self.proto_obj.speech_to_text_settings=types.SpeechToTextSettings(
                enable_speech_adaptation=enable_speech_adaptation
            )
        else:
            raise ValueError(
                "enable_speech_adaptation should be bool."
            )

        if isinstance(enable_spell_correction, bool):
            self.proto_obj.enable_spell_correction = enable_spell_correction
        else:
            raise ValueError(
                "enable_spell_correction should be bool."
            )

        if supported_language_codes:
            if (isinstance(supported_language_codes, list) and
                all(
                    (isinstance(lang, str) for lang in supported_language_codes)
                )):
                self.proto_obj.supported_language_codes = supported_language_codes
            else:
                raise ValueError(
                    "enable_spell_correction should be a list of strings."
                )

        return self.proto_obj


    def security_and_logging_settings(
        self,
        enable_stackdriver_logging: bool = False,
        enable_interaction_logging: bool = False,
        security_settings: str = None,
    ) -> types.Agent:
        """ Change the security and logging settings.

        Args:
          security_settings (str):
            Name of the
            ``[SecuritySettings]
              [google.cloud.dialogflow.cx.v3beta1.SecuritySettings]``
            reference for the agent.Format:
            ``projects/<Project ID>/locations/<Location ID>/
              securitySettings/<Security Settings ID>``.
          enable_stackdriver_logging (bool):
            If true, StackDriver logging is currently
            enabled.
          enable_interaction_logging (bool):
            If true, DF Interaction logging is currently
            enabled.

        Returns:
          An Agent object stored in proto_obj
        """
        self._check_agent_exist()

        if isinstance(enable_stackdriver_logging, bool):
            self.proto_obj.advanced_settings.logging_settings.enable_stackdriver_logging = enable_stackdriver_logging
            # self.proto_obj.enable_stackdriver_logging = enable_stackdriver_logging
        if isinstance(enable_interaction_logging, bool):
            self.proto_obj.advanced_settings.logging_settings.enable_interaction_logging = enable_interaction_logging
        if security_settings and isinstance(security_settings, str):
            self.proto_obj.security_settings = security_settings

        return self.proto_obj


    def show_agent_info(self):
        """Shows the information of proto_obj."""
        self._check_agent_exist()

        print(
            f"display_name: {self.proto_obj.display_name}"
            f"\ntime_zone: {self.proto_obj.time_zone}"
            f"\ndefault_language_code: {self.proto_obj.default_language_code}"
            f"\ndescription: {self.proto_obj.description}"
            f"\navatar_uri: {self.proto_obj.avatar_uri}"
            "\nenable_speech_adaptation:"
            f" {self.proto_obj.speech_to_text_settings.enable_speech_adaptation}"
            "\nenable_spell_correction:"
            f" {self.proto_obj.enable_spell_correction}"
            "\nsupported_language_codes:"
            f" {self.proto_obj.supported_language_codes}"
            "\nenable_stackdriver_logging:"
            f" {self.proto_obj.advanced_settings.logging_settings.enable_stackdriver_logging}"
            "\nenable_interaction_logging:"
            f" {self.proto_obj.advanced_settings.logging_settings.enable_interaction_logging}"
            f"\nsecurity_settings: {self.proto_obj.security_settings}"
        )
