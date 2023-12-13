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

from google.cloud.dialogflowcx_v3beta1.types.generative_settings import GenerativeSettings
from google.cloud.dialogflowcx_v3beta1.types.safety_settings import SafetySettings
from dfcx_scrapi.builders.builders_common import BuildersCommon

# logging config
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


class GenerativeSettingsBuilder(BuildersCommon):
    """Base Class for Generative Settings builder."""

    _proto_type = GenerativeSettings
    _proto_type_str = "GenerativeSettings"

    def __str__(self) -> str:
        """String representation of the proto_obj."""
        self._check_proto_obj_attr_exist()

        return (
            f"\nlanguage_code: {self.proto_obj.language_code}"
            f"\nfallback_settings: {self.proto_obj.fallback_settings}"
            f"\ngenerative_safety_settings: "
                f"{self.proto_obj.generative_safety_settings}"
            f"\nknowledge_connector_settings: "
                f"{self.proto_obj.knowledge_connector_settings}"
            )

    def fallback_settings(
            self, selected_prompt: str,
            prompt_templates: List[
                GenerativeSettings.FallbackSettings.PromptTemplate]
                ) -> GenerativeSettings.FallbackSettings:
        """Build the Fallback Settings proto."""
        return GenerativeSettings.FallbackSettings(
            selected_prompt=selected_prompt,
            prompt_templates=prompt_templates
        )

    def prompt_template(
            self, display_name: str, prompt_text: str, frozen: bool = False
    ):
        """Build the Prompt Template proto."""
        return GenerativeSettings.FallbackSettings.PromptTemplate(
            display_name=display_name,
            prompt_text=prompt_text,
            frozen=frozen
        )

    def banned_phrases(self, phrases: List[str],
                       language_code: str = "en") -> SafetySettings:
        """Build the SafetySettings proto with banned phrases."""
        banned_phrases = []
        for phrase in phrases:
            phrase_proto = SafetySettings.Phrase(
                text=phrase,
                language_code=language_code
            )
            banned_phrases.append(phrase_proto)

        safety_settings = SafetySettings(
            banned_phrases=banned_phrases
        )

        return safety_settings

    def knowledge_connector_settings(
            self, business_name: str, agent_name: str = None,
            agent_identity: str = None, business_description: str = None,
            agent_scope: str = None
            ) -> GenerativeSettings.KnowledgeConnectorSettings:
        """Build the knowledge settings proto.

        Args:
          business_name: The name of the company or business that corresponds
            most closely with the documents in the Data Store(s).
          agent_name: The name or identify of the conversational Agent. Ex:
            Bard, Fred, Julia, MedBot, etc.
          agent_identity: General description of the type of conversational
            Agent that this is. Ex: AI Assistant, Travel Concierge, Medical
            Assistant, etc.
          business_description: A brief description of the business and what it
            does
          agent_scope: The defined scope of this conversational Agent and how
            it should (or should not) interact with users.
        """
        return GenerativeSettings.KnowledgeConnectorSettings(
            business=business_name,
            agent=agent_name,
            agent_identity=agent_identity,
            business_description=business_description,
            agent_scope=agent_scope
        )
