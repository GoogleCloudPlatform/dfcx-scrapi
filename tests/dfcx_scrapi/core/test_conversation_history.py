"""Unit Tests for Conversation History."""

# pylint: disable=redefined-outer-name
# pylint: disable=protected-access
# pylint: disable=unused-argument

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

import os
import json
import pytest
from unittest.mock import patch, MagicMock

from dfcx_scrapi.core.conversation_history import ConversationHistory
from google.cloud.dialogflowcx_v3beta1 import types
from google.cloud.dialogflowcx_v3beta1 import services
from google.protobuf import timestamp_pb2


@pytest.fixture
def test_config():
    project_id = "my-project-id-1234"
    location_id = "global"
    parent = f"projects/{project_id}/locations/{location_id}"
    agent_id = f"{parent}/agents/my-agent-1234"
    conversation_id = f"{agent_id}/conversations/1234"
    return {
        "project_id": project_id,
        "agent_id": agent_id,
        "conversation_id": conversation_id,
    }

@pytest.fixture
def test_conversation(test_config):
    conversation = types.Conversation(
        name=f"{test_config['conversation_id']}",
        start_time=timestamp_pb2.Timestamp(seconds=1678886400)
        )
    interaction_1 = types.Conversation.Interaction(
        request=types.DetectIntentRequest(
            query_input=types.QueryInput(
                text=types.TextInput(text="Hello"))),
        response=types.DetectIntentResponse(
            query_result=types.QueryResult(
                response_messages=[
                    types.ResponseMessage(
                        text=types.ResponseMessage.Text(
                            text=["Hello there!"]))])))
    interaction_2 = types.Conversation.Interaction(
        request=types.DetectIntentRequest(
            query_input=types.QueryInput(
                text=types.TextInput(text="How are you?"))),
        response=types.DetectIntentResponse(
            query_result=types.QueryResult(
                response_messages=[
                    types.ResponseMessage(
                        text=types.ResponseMessage.Text(
                            text=["I'm doing well, thanks for asking."]
                            ))])))

    conversation.interactions.extend([interaction_1, interaction_2])

    return conversation

@pytest.fixture
def mock_list_conversations_pager(test_conversation):
    return services.conversation_history.pagers\
        .ListConversationsPager(
        services.conversation_history.ConversationHistoryClient\
            .list_conversations,
        types.conversation_history.ListConversationsRequest(),
        types.conversation_history.ListConversationsResponse(
            conversations=[test_conversation]
        ),
    )

@pytest.fixture(autouse=True)
def mock_client(test_config):
    """Setup mock client for all tests."""
    with patch("dfcx_scrapi.core.scrapi_base.default") as mock_default, \
        patch("dfcx_scrapi.core.scrapi_base.Request") as mock_request, \
        patch("dfcx_scrapi.core.conversation_history.services.conversation_history.ConversationHistoryClient") as mock_client:
        mock_creds = MagicMock()
        mock_default.return_value = (mock_creds, test_config["project_id"])
        mock_request.return_value = MagicMock()

        yield mock_client # Return control to test method

# Test get_user_input
def test_get_user_input():
    query_input = types.QueryInput(text=types.TextInput(text="test input"))
    user_input = ConversationHistory.get_user_input(query_input)
    assert user_input == "test input"

# Test get_query_result
def test_get_query_result():
    query_result = types.QueryResult(response_messages=[
        types.ResponseMessage(
            text=types.ResponseMessage.Text(text=["test result"]))
    ])
    agent_response = ConversationHistory.get_query_result(query_result)
    assert agent_response == "test result"

# Test list_conversations
def test_list_conversations(
    mock_client, mock_list_conversations_pager, test_config
    ):
    mock_client.return_value.list_conversations.return_value = \
        mock_list_conversations_pager
    ch = ConversationHistory(agent_id=test_config["agent_id"])
    res = ch.list_conversations(agent_id=test_config["agent_id"])

    assert isinstance(res, list)
    assert isinstance(res[0], types.Conversation)

# Test get_conversation
def test_get_conversation(
    mock_client, test_conversation, test_config
    ):
    mock_client.return_value.get_conversation.return_value = \
        test_conversation
    ch = ConversationHistory(agent_id=test_config["agent_id"])
    res = ch.get_conversation(
        conversation_id=test_config["conversation_id"]
    )

    assert isinstance(res, types.Conversation)

# Test delete_conversation
def test_delete_conversation(mock_client, test_config):
    ch = ConversationHistory(agent_id=test_config["agent_id"])
    ch.delete_conversation(
        conversation_id=test_config["conversation_id"]
    )
    mock_client.return_value.delete_conversation.assert_called()

# Test process_single_conversation
def test_process_single_conversation(test_conversation):
    ch = ConversationHistory()
    conversation = ch.process_single_conversation(test_conversation)
    assert isinstance(conversation, dict)
    assert "session_id" in conversation
    assert "create_time" in conversation
    assert "turns" in conversation
    assert isinstance(conversation["turns"], list)

# Test write_conversations_to_file
def test_write_conversations_to_file(tmpdir):
    ch = ConversationHistory()
    conversations = [{"test": "data"}]
    filename = os.path.join(tmpdir, "test.json")
    ch.write_conversations_to_file(conversations, filename)
    assert os.path.exists(filename)

# Test read_conversations_from_file
def test_read_conversations_from_file(tmpdir):
    ch = ConversationHistory()
    data = [{"test": "data"}]
    filename = os.path.join(tmpdir, "test.json")
    with open(filename, "w", encoding="utf-8") as f:
        for item in data:
            json.dump(item, f)
            f.write("\n")
    loaded_data = ch.read_conversations_from_file(filename)
    assert loaded_data == data

# Test conversation_history_to_file
@patch("dfcx_scrapi.core.conversation_history.thread_map")
def test_conversation_history_to_file(
    mock_thread_map, mock_client, test_conversation, tmpdir, test_config
    ):
    mock_client.return_value.list_conversations.return_value = [
        test_conversation
    ]
    mock_client.return_value.get_conversation.return_value = \
        test_conversation
    mock_thread_map.return_value = [{"test": "data"}]
    agent_id = test_config["agent_id"]
    ch = ConversationHistory()
    filename = os.path.join(tmpdir, "test.json")
    ch.conversation_history_to_file(agent_id, filename)
    assert os.path.exists(filename)
