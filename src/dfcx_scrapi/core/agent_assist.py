"""Agent Assist Resource functions."""

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

import logging
from typing import Dict
from google.cloud.dialogflow_v2beta1 import services
from google.cloud.dialogflow_v2beta1 import types

from dfcx_scrapi.core import scrapi_base

# logging config
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


class AgentAssist(scrapi_base.ScrapiBase):
    """Core Class for Agent Assist Resource functions."""

    def __init__(
        self,
        creds_path: str = None,
        creds_dict: Dict = None,
        creds=None,
        scope=False,
        conversation_profile_id: str = None,
    ):
        super().__init__(
            creds_path=creds_path,
            creds_dict=creds_dict,
            creds=creds,
            scope=scope,
        )

        if conversation_profile_id:
            self.conversation_profile_id = conversation_profile_id

    def create_conversation_profile(
        self,
        display_name,
        project_id,
        knowledge_base_id: str = None,
        suggestion_type: str = "TYPE_UNSPECIFIED",
        no_small_talk: bool = True,
        only_end_user: bool = True,
        max_results: int = 3,
        language_code: str = "en-US"):
        """ Create & configure a conversation profile as per the given input.

        Args:
            display_name (str):
                Required. Human readable name for this
                profile. Max length 1024 bytes.
            project_id (str):
                Required. The project to create a conversation profile for.
            knowledge_base_id (str):
                The knowledge base id of the knowledge base to be configured
                with the conversation profile.
            suggestion_type (str):
                The agent assist feature to be configured with the
                conversation profile.
                Allowed values are: ARTICLE_SUGGESTION, FAQ & SMART_REPLY.
            no_small_talk (bool):
                Do not trigger if last utterance is small talk.
            only_end_user (bool):
                Only trigger suggestion if participant role of last
                utterance is END_USER.
            max_results (int):
                Maximum number of results to return.
                Currently, if unset, defaults to 10. And the max number is 20.
            language_code (str):
                Language code for the conversation profile. If not
                specified, the language is en-US. Language at
                ConversationProfile should be set for all non en-us
                languages. This should be a
                `BCP-47 <https://www.rfc-editor.org/rfc/bcp/bcp47.txt>`__
                language tag. Example: "en-US".

        Returns:
            Conversation profile to be used for incoming
            Dialogueflow conversations.
            type: google.cloud.dialogflow_v2beta1.types.ConversationProfile
        """

        client = services.conversation_profiles.ConversationProfilesClient(
            credentials = self.creds
            )

        project_path = client.common_project_path(project_id)
        logging.info(f"Project Path : {project_path}")

        conversation_profile = types.ConversationProfile()
        conversation_profile.display_name = display_name
        conversation_profile.language_code = language_code

        feature_config = types.conversation_profile.HumanAgentAssistantConfig.SuggestionFeatureConfig()

        # Configuring Suggestion Type
        suggestion_feature = types.participant.SuggestionFeature()
        suggestion_feature.type_ = suggestion_type

        feature_config.suggestion_feature = suggestion_feature

        # Configuring the trigger settings
        trigger_settings = types.conversation_profile.HumanAgentAssistantConfig.SuggestionTriggerSettings()
        trigger_settings.no_small_talk = no_small_talk
        trigger_settings.only_end_user = only_end_user

        feature_config.suggestion_trigger_settings = trigger_settings

        # Configuring the query config.
        query_config = types.conversation_profile.HumanAgentAssistantConfig.SuggestionQueryConfig()

        if knowledge_base_id is not None:
            as_kb_path = services.knowledge_bases.KnowledgeBasesClient.knowledge_base_path(
                project_id, knowledge_base_id
                )
            logging.info(f"Knowledge Base Path : {as_kb_path}")
            query_config.knowledge_base_query_source.knowledge_bases = [as_kb_path]

        query_config.max_results = max_results
        feature_config.query_config = query_config

        conversation_profile.human_agent_assistant_config.human_agent_suggestion_config.feature_configs = [feature_config]

        request = types.conversation_profile.CreateConversationProfileRequest(
                    parent= project_path,
                    conversation_profile=conversation_profile,
                )
        # Make the request
        response = client.create_conversation_profile(request=request)
        logging.info(response)
        logging.info("Conversation Profile created...")
        logging.info(f"Display Name: {response.display_name}")
        logging.info(f"Name: {response.name}")

        # Updating the conversation profile name in the current object
        self.conversation_profile_id = response.name.split("/")[-1]

        return response

    def create_conversation(
        self,
        project_id
        ):
        """Creates a conversation with given values

        Args:
            project_id (str):
                Required. The project to create a conversation profile for.

        Returns:
            Response for the created conversation.
            type: google.cloud.dialogflow_v2beta1.types.Conversation
        """

        client = services.conversations.ConversationsClient(
            credentials = self.creds
            )
        conversation_profile_client = services.conversation_profiles.ConversationProfilesClient()
        conversation_profile_path = conversation_profile_client.conversation_profile_path(
            project_id, self.conversation_profile_id
            )
        project_path = client.common_project_path(project_id)

        conversation = {"conversation_profile": conversation_profile_path}
        response =  client.create_conversation(
            parent=project_path,
            conversation=conversation
            )

        logging.info(response)
        logging.info(f"Conversation Created: {response.name}")

        return response

    def create_participant(
        self,
        conversation_id,
        role):
        """Creates a participant in a given conversation.

        Args:
            conversation_id (str):
                Required. The id of the conversation to which to
                add the participant.
            role (str):
                The role of the added participant.
                Allowed Values: HUMAN_AGENT, AUTOMATED_AGENT, END_USER

        Returns:
            Response for the created participant.
            type: google.cloud.dialogflow_v2beta1.types.Participant
        """

        client = services.participants.ParticipantsClient(
            credentials=self.creds
            )

        response = client.create_participant(
            parent = conversation_id,
            participant = {"role": role},
            timeout=600
            )

        logging.info(response)
        logging.info(f"Participant created for the role {role}")
        logging.info(f"Participant Name: {response.name}")
        return response

    def analyze_content_text(
        self,
        text,
        participant,
        language_code = "en-US"
        ):
        """Analyze text message content from a participant.

        Args:
            text (str):
                The input text string that needs to be analyzed.
            participant (str):
                The participant id of the participant for the
                corresponding text utterance being analyzed.
            language_code (str):
                Language of the inputted text.

        Returns:
            Response message from the analyze content.
            type: google.cloud.dialogflow.v2beta1.Participants.AnalyzeContent
        """

        client = services.participants.ParticipantsClient(
            credentials= self.creds
            )
        text_input = {"text": text, "language_code": language_code}

        logging.info("Running analyze content...")
        response = client.analyze_content(
            participant = participant,
            text_input = text_input
            )
        logging.info(f"analyze content response: {response}")

        return response

    def complete_conversation(
        self,
        conversation_id
        ):
        """Completes the specified conversation.
            Finished conversations are purged from the database after 30 days.

        Args:
            conversation_id (str)
                The conversation id that needs to be completed.

        Returns:
            Response for the completed conversation.
            type: google.cloud.dialogflow_v2beta1.types.Conversation
        """

        client = services.conversations.ConversationsClient(
            credentials = self.creds
            )
        conversation =  client.complete_conversation(
            name = conversation_id
            )
        logging.info(f"Closed Conversation {conversation_id}")

        return conversation
