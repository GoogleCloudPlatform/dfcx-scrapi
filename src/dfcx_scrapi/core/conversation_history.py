"""Conversation History class for Generative Agents."""

# Copyright 2024 Google LLC
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

import json
import logging
import os
from typing import Any, Dict, List

from google.cloud.dialogflowcx_v3beta1 import services, types
from tqdm.contrib.concurrent import thread_map

from dfcx_scrapi.core import scrapi_base

# logging config
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


class ConversationHistory(scrapi_base.ScrapiBase):
    """Used to get Conversation History Data."""
    def __init__(self,
                creds_path: str = None,
                creds_dict: Dict[str,str] = None,
                creds = None,
                scope = False,
                agent_id: str = None):
        super().__init__(creds_path, creds_dict, creds, scope)
        self.agent_id = agent_id

    @staticmethod
    def get_user_input(query_input: types.QueryInput):
        """Extract the input from the user."""
        if "text" in query_input:
            return query_input.text.text

        else:
            return None

    @staticmethod
    def get_query_result(query_result: types.QueryResult):
        """Extract the query result from the agent."""
        messages = []
        if "response_messages" in query_result:
            for rm in query_result.response_messages:
                if "text" in rm:
                    messages.append(rm.text.text[0])

        return " ".join(messages)

    def list_conversations(self, agent_id: str):
        request = types.conversation_history.ListConversationsRequest(
            parent=agent_id)

        client_options = self._set_region(agent_id)
        client = services.conversation_history.ConversationHistoryClient(
            credentials=self.creds, client_options=client_options)

        return list(client.list_conversations(request))

    def get_conversation(self, conversation_id: str):
        request = types.conversation_history.GetConversationRequest(
            name=conversation_id)
        client_options = self._set_region(conversation_id)
        client = services.conversation_history.ConversationHistoryClient(
            credentials=self.creds, client_options=client_options)

        return client.get_conversation(request)

    def delete_conversation(self, conversation_id: str) -> None:
        request = types.conversation_history.DeleteConversationRequest(
            name=conversation_id
        )
        client_options = self._set_region(conversation_id)
        client = services.conversation_history.ConversationHistoryClient(
            credentials=self.creds, client_options=client_options
        )

        client.delete_conversation(request)

    def process_single_conversation(self, current_convo: types.Conversation):
        """Extract details from single conversation for embed and cluster."""
        conversation = {}
        conversation["session_id"] = current_convo.name
        conversation["create_time"] = current_convo.start_time.rfc3339()
        conversation["turns"] = []
        for action in reversed(current_convo.interactions):
            turn = {}
            turn["user"] = self.get_user_input(action.request.query_input)
            turn["agent"] = self.get_query_result(action.response.query_result)
            conversation["turns"].append(turn)

        return conversation

    def write_conversations_to_file(
            self, convos: List[Dict[str, Any]], filename: str
            ):
        """Write conversations to file."""
        # Check if the file exists
        if not os.path.exists(filename):
            # If not, create an empty file
            with open(filename, "w", encoding="utf-8") as new_file:
                new_file.close()

        with open(filename, "w", encoding="utf-8") as json_file:
            for data_dict in convos:
                json.dump(data_dict, json_file)
                json_file.write("\n")

    def read_conversations_from_file(self, filename: str):
        """Loads a JSON Lines file and returns a list of dictionaries."""
        data = []
        with open(filename, "r", encoding="utf-8") as f:
            for line in f:
                data.append(json.loads(line))

        return data

    def conversation_history_to_file(self, agent_id: str, filename: str):
        """Process existing conversation history, with progress bar."""

        convo_ids = [convo.name for convo in self.list_conversations(agent_id)]

        def process_conversation(conversation_id: str):
            """Helper method to process single convo."""
            current_convo = self.get_conversation(conversation_id)
            return self.process_single_conversation(current_convo)

        # Use thread_map for progress visualization during parallel processing
        results = thread_map(
            process_conversation,
            convo_ids,
            desc="Processing Conversations"
            )

        self.write_conversations_to_file(list(results), filename)



