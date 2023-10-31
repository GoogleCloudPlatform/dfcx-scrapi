"""Agent Assist Resource functions."""

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

from dfcx_scrapi.core import scrapi_base
from typing import Dict
from google.cloud.dialogflow_v2beta1 import services
from google.cloud.dialogflow_v2beta1 import types
from google.cloud.dialogflow_v2beta1.services.knowledge_bases import KnowledgeBasesClient
from google.protobuf import field_mask_pb2

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
        self.conversation_profile_id = None

        if conversation_profile_id:
            self.conversation_profile_id = conversation_profile_id

    def _set_conversation_profile(
        self,
        conversation_profile_id: str,
        project_id: str = None
    ):
        """Updating the conversation profile for the object
        Args:
            conversation_profile_id (reqd):
                Unique identifier for the conversation profile.
            project_id (str):
                Optional Field. Required if the full conv path is not supplied.
        """
        logging.info(f"Setting Conversation Profile: {conversation_profile_id}")

        if len(conversation_profile_id.split("/")) >= 4:
            profile_path = conversation_profile_id
        else:
            logging.info("Inferring Profile Path using the Project ID")
            if not project_id:
                raise ValueError(
                    "Project ID is required if the full conevrsation profile"
                    " path is not provided."
                )
            project_path = f"projects/{project_id}"
            conv_path = f"/conversationProfiles/{conversation_profile_id}"
            profile_path = project_path + conv_path

        logging.info(f"Conversation Profile Path :{profile_path}")
        self.conversation_profile_id = profile_path

    def create_conversation_profile(
        self,
        display_name,
        knowledge_base_id: str,
        project_id,
        suggestion_type: str,
        no_small_talk: bool = True,
        only_end_user: bool = True,
        max_results: int = 3,
        language_code: str = "en-US") -> types.ConversationProfile:
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

        hac_config = types.HumanAgentAssistantConfig
        feature_config = hac_config.SuggestionFeatureConfig()

        # Configuring Suggestion Type
        suggestion_feature = types.SuggestionFeature()
        suggestion_feature.type_ = suggestion_type

        feature_config.suggestion_feature = suggestion_feature

        # Configuring the trigger settings
        trigger_settings = hac_config.SuggestionTriggerSettings()
        trigger_settings.no_small_talk = no_small_talk
        trigger_settings.only_end_user = only_end_user

        feature_config.suggestion_trigger_settings = trigger_settings

        # Configuring the query config.
        query_config = hac_config.SuggestionQueryConfig()

        kb_path = KnowledgeBasesClient.knowledge_base_path(
            project_id, knowledge_base_id
            )
        logging.info(f"Knowledge Base Path : {kb_path}")
        query_config.knowledge_base_query_source.knowledge_bases=[kb_path]

        query_config.max_results = max_results
        feature_config.query_config = query_config

        conversation_profile.human_agent_assistant_config.human_agent_suggestion_config.feature_configs = [feature_config] # pylint: disable=C0301

        request = types.conversation_profile.CreateConversationProfileRequest(
                    parent= project_path,
                    conversation_profile=conversation_profile,
                )

        # Make the request
        response = client.create_conversation_profile(request=request)
        logging.info("Conversation Profile created...")
        logging.info(f"Display Name: {response.display_name}")
        logging.info(f"Name: {response.name}")

        return response

    def get_conversation_profile(
        self,
        conversation_profile_id: str = None
    ) -> types.ConversationProfile:
        """Returns the conversation profile object
        Args:
            conversation_profile_id: str
                Optional Field. The profile id for requested object.

        Returns:
            Conversation profile Object.
            type: google.cloud.dialogflow_v2beta1.types.ConversationProfile
        """
        client = services.conversation_profiles.ConversationProfilesClient(
            credentials = self.creds
            )
        if not conversation_profile_id:
            conversation_profile_id = self.conversation_profile_id

        request = types.conversation_profile.GetConversationProfileRequest(
                    name=conversation_profile_id,
                )

        response = client.get_conversation_profile(request=request)

        return response

    def list_conversation_profiles(
        self,
        project_id: str
    ):
        """List all the existing conversation profile in the given project
        Args:
            project_id :
            Required. The project to list the conversation profile for.

        Returns:
            List of tuples [(profile display name, profile name)]
        """
        client = services.conversation_profiles.ConversationProfilesClient(
            credentials = self.creds
            )

        project_path = client.common_project_path(project_id)
        logging.info(f"Project Path : {project_path}")

        response = client.list_conversation_profiles(parent = project_path)

        profile_list = []
        for profile in response:
            profile_list.append((profile.display_name, profile.name))

        return profile_list

    def delete_conversation_profile(
        self,
        conversation_profile_id: str
    ):
        """Delete the given conversation profile
        Args:
            conversation_profile_id:
                The unique identifier of this conversation profile. Format:
                ``projects/<Project ID>/locations/<Location ID>
                  /conversationProfiles/<Conversation Profile ID>``.
        """
        client = services.conversation_profiles.ConversationProfilesClient(
            credentials = self.creds
            )

        logging.info(f"Deleting : {conversation_profile_id}")

        client.delete_conversation_profile(name = conversation_profile_id)

    def update_conversation_profile(
        self,
        conversation_profile_id: str = None,
        obj: types.ConversationProfile = None,
        **kwargs
    ) -> types.ConversationProfile:
        """
        Updates the conversation profile object based on the provided args.
        Args:
            conversation_profile_id: str
                The unique identifier of this conversation profile.
                Format:
                ``projects/<Project ID>/locations/<Location ID>/
                  conversationProfiles/<Conversation Profile ID>``.
            obj: The Conversation Profile object to be updated.

        Returns:
            The updated conversation profile object.
        """
        if obj:
            conversation_profile = obj
            conversation_profile.name = conversation_profile_id

        else:
            if not conversation_profile_id:
                conversation_profile_id = self.conversation_profile_id

            conversation_profile = self.get_conversation_profile(
                conversation_profile_id = conversation_profile_id
                )

        # set conversation profile attributes from kwargs
        for key, value in kwargs.items():
            setattr(conversation_profile, key, value)
            logging.info(f"Updating field {key} to {value}")

        paths = kwargs.keys()
        mask = field_mask_pb2.FieldMask(paths=paths)

        client = services.conversation_profiles.ConversationProfilesClient(
            credentials = self.creds
            )

        request = types.UpdateConversationProfileRequest()

        request.conversation_profile = conversation_profile
        request.update_mask = mask

        response = client.update_conversation_profile(request)

        return response

    def create_conversation(
        self,
        project_id: str,
        conversation_profile_id: str = None
        ) -> types.Conversation:
        """Creates a conversation with given values

        Args:
            project_id (str):
                Required. The project to create a conversation profile for.
            conversation_profile_id (str):
                Optional: If not set before, user can pass a profile id to
                be used for creating a conversation.

        Returns:
            Response for the created conversation.
            type: google.cloud.dialogflow_v2beta1.types.Conversation
        """

        client = services.conversations.ConversationsClient(
            credentials = self.creds
            )

        if conversation_profile_id:
            self._set_conversation_profile(
                conversation_profile_id = conversation_profile_id,
                project_id = project_id
                )

        if not self.conversation_profile_id and not conversation_profile_id:
            raise ValueError(
                "Conversation Profile ID required, as it isn't set for this"
                " instance of the AgentAssist class."
            )

        project_path = client.common_project_path(project_id)

        conversation = {"conversation_profile": self.conversation_profile_id}
        response =  client.create_conversation(
            parent=project_path,
            conversation=conversation
            )

        logging.info(f"Conversation Created: {response.name}")

        return response

    def complete_conversation(
        self,
        conversation_id
        ) -> types.Conversation:
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

    def create_participant(
        self,
        conversation_id,
        role) -> types.Participant:
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

        logging.info(f"Participant created for the role {role}")
        logging.info(f"Participant Name: {response.name}")

        return response

    def list_participants(
        self,
        conversation_id: str
    ):
        """list all the participants added to a coversation
        Args:
        conversation_id (str):
                Required. The conversation to list all participants
                from. Format:
                ``projects/<Project ID>/locations/<Location ID>/conversations
                /<Conversation ID>``.
        Returns:
            A dict object with the participant information:
            {participant role: participant name}
        """
        client = services.participants.ParticipantsClient(
            credentials=self.creds
            )
        response = client.list_participants(parent = conversation_id)

        participant_dict = {}
        for participant in response:
            participant_dict[participant.role.name] = participant.name

        return participant_dict

    def get_participant(
        self,
        participant_id: str
    ) -> types.Participant:
        """Returns the Participant object for the given participant name
        Args:
            participant_id: str
                The participant id for the requested object.
                ``projects/<Project ID>/locations/<Location ID>/
                conversations/<Conv. ID>/participants/<Participant ID>``.
        """
        client = services.participants.ParticipantsClient(
            credentials = self.creds
            )

        request = types.GetParticipantRequest(
                    name=participant_id,
                )

        response = client.get_participant(request=request)

        return response

    def update_participant(
        self,
        participant_id: str = None,
        obj: types.Participant = None,
        **kwargs
    ) -> types.Participant:
        """
        Updates the participant object based on the provided args.
        Args:
            participant_id: str
                Full id of the participant to be updated.
            obj:
                The participant object to be updated.
        """
        if obj:
            participant = obj
            participant.name = participant_id

        else:
            if not participant_id:
                raise ValueError(
                    "Atleast one of participant object or participant "
                    "name is required to make the update."
                )

            participant = self.get_participant(
                participant_id = participant_id
                )

        # set participant attributes from kwargs
        for key, value in kwargs.items():
            setattr(participant, key, value)

        paths = kwargs.keys()
        mask = field_mask_pb2.FieldMask(paths=paths)

        client = services.participants.ParticipantsClient(
            credentials = self.creds
            )

        request = types.UpdateParticipantRequest()

        request.participant = participant
        request.update_mask = mask

        response = client.update_participant(request = request)

        return response

    def analyze_content_text(
        self,
        text,
        participant_id,
        language_code = "en-US"
        ) -> types.AnalyzeContentResponse:
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
            participant = participant_id,
            text_input = text_input
            )

        return response
