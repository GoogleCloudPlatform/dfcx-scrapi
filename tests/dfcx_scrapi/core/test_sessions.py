"""Unit Tests for Sessions."""
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

from unittest.mock import MagicMock, patch
import uuid

import pytest
from google.protobuf import struct_pb2
from google.cloud.dialogflowcx_v3beta1 import types
from IPython.display import Markdown

from dfcx_scrapi.core.sessions import Sessions

@pytest.fixture
def test_config():
    project_id = "my-project-id-1234"
    location_id = "global"
    agent_id = f"projects/{project_id}/locations/{location_id}/agents/fcdecc6a-3f2e-4f8d-abca-63426024d8bb"
    intent_id = f"{agent_id}/intents/b1983e56-5c96-4b20-b15a-fb5c12b77500"
    flow_id = f"{agent_id}/flows/925c0042-686f-4422-bf34-2a2a37b1a3ee"
    tool_id = f"{agent_id}/tools/8e1205e8-bb5e-46ef-896c-1e4f72bb871c"
    page_id = f"{flow_id}/pages/8e1205e8-bb5e-46ef-896c-1e4f72bb871c"
    playbook_id = f"{agent_id}/playbooks/e79502db-78e0-4f54-8447-716107bb553e"
    playbook_name = "mock_playbook"
    environment_id = f"{agent_id}/environments/753de31b-a14b-45f3-a731-b40831ecfbc4"
    environment_name = "My Test Environment"
    session_id_plain = f"{agent_id}/sessions/a1b2c3d4-e5f6-7890-1234-567890abcdef"
    session_id_with_env = f"{environment_id}/sessions/a1b2c3d4-e5f6-7890-1234-567890abcdef"
    language_code = "en"
    text = "Hello!"
    tool_action = "my_tool_action"
    tool_input_params = {"param1": "value1", "param2": "value2"}
    tool_output_params = {"param3": "value3", "param4": "value4"}
    tool_input_params_nested = {"top_key": {"param1": "value1", "param2": "value2"}}
    tool_output_params_nested = {"top_key": {"param3": "value3", "param4": "value4"}}
    
    parameters = {"param1": "value1", "param2": "value2"}
    end_user_metadata = {"user_id": "user123"}
    
    return {
        "project_id": project_id,
        "location_id": location_id,
        "agent_id": agent_id,
        "session_id_plain": session_id_plain,
        "session_id_with_env": session_id_with_env,
        "intent_id": intent_id,
        "flow_id": flow_id,
        "page_id": page_id,
        "tool_id": tool_id,
        "playbook_id": playbook_id,
        "playbook_name": playbook_name,
        "environment_id": environment_id,
        "environment_name": environment_name,
        "language_code": language_code,
        "text": text,
        "tool_action": tool_action,
        "tool_input_params": tool_input_params,
        "tool_output_params": tool_output_params,
        "tool_input_params_nested": tool_input_params_nested,
        "tool_output_params_nested": tool_output_params_nested,
        "parameters": parameters,
        "end_user_metadata": end_user_metadata,
    }

@pytest.fixture
def mock_query_result(test_config):
    """Create a mock QueryResult object for testing, without generative info."""
    return types.session.QueryResult(
        text=test_config["text"],
        language_code=test_config["language_code"],
        parameters=struct_pb2.Struct(
            fields={
                "some_key": struct_pb2.Value(string_value="some_value")
            }
        ),
        response_messages=[
            types.ResponseMessage(
                text=types.ResponseMessage.Text(
                    text=["Greetings! How can I assist?"]
                )
            ),
              types.ResponseMessage(
                text=types.ResponseMessage.Text(
                    text=["Hey! What can I help you with today?"]
                )
            )
        ],
        intent_detection_confidence=1,
        match=types.session.Match(
            match_type=types.session.Match.MatchType.PLAYBOOK,
            confidence=1
        ),
        advanced_settings = types.AdvancedSettings(
           speech_settings = types.AdvancedSettings.SpeechSettings(
            endpointer_sensitivity=90,
           ),
           logging_settings = types.AdvancedSettings.LoggingSettings(
               enable_stackdriver_logging=True,
                enable_interaction_logging=True
            )
        ),
    )

@pytest.fixture
def mock_query_result_tools_playbooks_flows(test_config):
    """Create a mock QueryResult object for testing, with generative info."""
    return types.session.QueryResult(
        text=test_config["text"],
        language_code=test_config["language_code"],
        generative_info = types.session.GenerativeInfo(
            action_tracing_info=types.Example(
                actions=[
                    types.Action(
                        tool_use=types.example.ToolUse(
                            tool=test_config["tool_id"],
                            action=test_config["tool_action"],
                            input_action_parameters=test_config["tool_input_params"],
                            output_action_parameters=test_config["tool_output_params"],
                        ),
                    ),
                    types.Action(
                        playbook_invocation=types.example.PlaybookInvocation(
                            playbook=test_config["playbook_id"]
                        ),
                    ),
                    types.Action(
                        flow_invocation=types.example.FlowInvocation(
                            flow=test_config["flow_id"]
                        )
                    ),
                    types.Action(
                        agent_utterance=types.AgentUtterance(text="Hey there!")
                    )
                ]
            ),
        current_playbooks=[test_config["playbook_id"]]
        ),
    )

@pytest.fixture
def mock_query_result_datastore(test_config):
    """Create a mock QueryResult object for testing datastore responses."""
    return types.session.QueryResult(
        text="who is the ceo?",
        language_code="en",
        parameters=struct_pb2.Struct(
            fields={
                "some_key": struct_pb2.Value(string_value="some_value")
            }
        ),
        response_messages=[
            types.ResponseMessage(
                text=types.ResponseMessage.Text(
                    text=["Sundar Pichai is the CEO of Google.\nhttps://www.google.com"]
                )
            ),
            types.ResponseMessage(
                payload=struct_pb2.Struct(
                  fields={
                    "richContent": struct_pb2.Value(
                      list_value=struct_pb2.ListValue(
                        values=[
                            struct_pb2.Value(
                            list_value=struct_pb2.ListValue(
                              values=[
                                  struct_pb2.Value(
                                    struct_value=struct_pb2.Struct(
                                      fields={
                                          "type": struct_pb2.Value(string_value="info"),
                                          "title": struct_pb2.Value(string_value="CEO of Google"),
                                          "subtitle": struct_pb2.Value(string_value="Information on Google executive team."),
                                          "metadata": struct_pb2.Value(struct_value=struct_pb2.Struct()),
                                          "actionLink": struct_pb2.Value(string_value="https://www.google.com"),
                                        }
                                    )
                                  )
                                ]
                            )
                          )
                        ]
                      )
                   )
                  }
                )
            )
          ],
        intent_detection_confidence=1,
        match=types.session.Match(
            match_type=types.session.Match.MatchType.KNOWLEDGE_CONNECTOR,
            confidence=1
        ),
        advanced_settings = types.AdvancedSettings(
           logging_settings = types.AdvancedSettings.LoggingSettings(
               enable_stackdriver_logging=True,
                enable_interaction_logging=True
            )
        ),
        current_page = types.Page(
          name=test_config["page_id"],
          display_name="Start Page"
        )
    )

@pytest.fixture
def mock_query_result_params_no_text_input(test_config):
    """Create a mock QueryResult object for testing."""
    return types.session.QueryResult(
        language_code=test_config["language_code"],
    )

@pytest.fixture
def mock_detect_intent_response(mock_query_result):
    """Create a mock DetectIntentResponse object for testing."""
    return types.session.DetectIntentResponse(query_result=mock_query_result)

@pytest.fixture
def mock_detect_intent_response_no_text_input(
    mock_query_result_params_no_text_input):
    """Create a mock DetectIntentResponse object for testing."""
    return types.session.DetectIntentResponse(
        query_result=mock_query_result_params_no_text_input)

@pytest.fixture
def mock_detect_intent_response_tools_playbooks_flows(
    mock_query_result_tools_playbooks_flows):
    """Create a mock DetectIntentResponse object for testing."""
    return types.session.DetectIntentResponse(
        query_result=mock_query_result_tools_playbooks_flows)

@pytest.fixture
def mock_environment_obj(test_config):
    """Create a mock Environment object for testing."""
    return types.Environment(
        name=test_config["environment_id"],
        display_name=test_config["environment_name"]
    )

@pytest.fixture(autouse=True)
def mock_sessions_client(test_config):
    """Fixture to create a mocked SessionsClient."""
    with patch("dfcx_scrapi.core.scrapi_base.default") as mock_default, \
        patch("dfcx_scrapi.core.scrapi_base.Request") as mock_request, \
        patch("dfcx_scrapi.core.sessions.services.sessions.SessionsClient") as mock_client, \
        patch("dfcx_scrapi.core.environments.Environments.__init__") as mock_env, \
        patch("dfcx_scrapi.core.tools.Tools.__init__") as mock_tools, \
        patch("dfcx_scrapi.core.playbooks.Playbooks.__init__") as mock_playbooks, \
        patch("dfcx_scrapi.core.flows.Flows.__init__") as mock_flows:
        
        mock_creds = MagicMock()
        mock_default.return_value = (mock_creds, test_config["project_id"])
        mock_request.return_value = MagicMock()
        mock_env.return_value = None
        mock_tools.return_value = None
        mock_playbooks.return_value = None
        mock_flows.return_value = None

        yield mock_client

@pytest.fixture
def mock_environments_client(test_config):
    """Fixture to create a mocked EnvironmentsClient."""
    with patch("dfcx_scrapi.core.scrapi_base.default") as mock_default, \
        patch("dfcx_scrapi.core.scrapi_base.Request") as mock_request, \
        patch("dfcx_scrapi.core.environments.services.environments.EnvironmentsClient") as mock_client:
        
        mock_creds = MagicMock()
        mock_default.return_value = (mock_creds, test_config["project_id"])
        mock_request.return_value = MagicMock()

        yield mock_client


@pytest.fixture
def mock_tools_client(test_config):
    """Fixture to create a mocked ToolsClient."""
    with patch("dfcx_scrapi.core.scrapi_base.default") as mock_default, \
        patch("dfcx_scrapi.core.scrapi_base.Request") as mock_request, \
        patch("dfcx_scrapi.core.tools.services.tools.ToolsClient") as mock_client:
        
        mock_creds = MagicMock()
        mock_default.return_value = (mock_creds, test_config["project_id"])
        mock_request.return_value = MagicMock()

        yield mock_client

@pytest.fixture
def mock_playbooks_client(test_config):
    """Fixture to create a mocked PlaybooksClient."""
    with patch("dfcx_scrapi.core.scrapi_base.default") as mock_default, \
        patch("dfcx_scrapi.core.scrapi_base.Request") as mock_request, \
        patch("dfcx_scrapi.core.playbooks.services.playbooks.PlaybooksClient") as mock_client:
        
        mock_creds = MagicMock()
        mock_default.return_value = (mock_creds, test_config["project_id"])
        mock_request.return_value = MagicMock()

        yield mock_client

@pytest.fixture
def mock_flows_client(test_config):
    """Fixture to create a mocked FlowsClient."""
    with patch("dfcx_scrapi.core.scrapi_base.default") as mock_default, \
        patch("dfcx_scrapi.core.scrapi_base.Request") as mock_request, \
        patch("dfcx_scrapi.core.flows.services.flows.FlowsClient") as mock_client:
        
        mock_creds = MagicMock()
        mock_default.return_value = (mock_creds, test_config["project_id"])
        mock_request.return_value = MagicMock()

        yield mock_client

@pytest.fixture
def mock_tools_instance(test_config):
    tools_instance = MagicMock()
    tools_instance.get_tools_map.return_value = {
        test_config["tool_id"]: "mock tool"
    }

    return tools_instance

def test_session_id_property_valid_id(test_config):
    """Test session_id property with a valid session ID."""
    session = Sessions(
        agent_id = test_config["agent_id"],
        session_id = test_config["session_id_plain"])
    assert session.session_id == test_config["session_id_plain"]

def test_printmd(test_config):
    session = Sessions()
    with patch("dfcx_scrapi.core.sessions.display") as mock_display:
        session.printmd("test string")
        mock_display.assert_called()

def test_build_query_input(test_config):
    session = Sessions()
    query_input = session._build_query_input(
        text=test_config["text"], language_code=test_config["language_code"]
    )
    assert isinstance(query_input, types.session.QueryInput)
    assert query_input.text.text == test_config["text"]
    assert query_input.language_code == test_config["language_code"]


def test_build_intent_query_input(test_config):
    session = Sessions()
    query_input = session.build_intent_query_input(
        intent_id=test_config["intent_id"], language_code=test_config["language_code"]
    )
    assert isinstance(query_input, types.session.QueryInput)
    assert query_input.intent.intent == test_config["intent_id"]
    assert query_input.language_code == test_config["language_code"]

def test_get_tool_action(test_config):
    session = Sessions()
    mock_tool_use = types.example.ToolUse(action=test_config["tool_action"])
    action = session.get_tool_action(mock_tool_use)

    assert action == test_config["tool_action"]

def test_get_tool_params(test_config):
    session = Sessions()
    tool_use = types.ToolUse()
    tool_use.input_action_parameters = test_config["tool_input_params"]
    res = session.get_tool_params(tool_use.input_action_parameters)
    assert res == test_config["tool_input_params"]

def test_get_tool_params_empty():
    session = Sessions()
    params = {}
    res = session.get_tool_params(params)
    assert res == {}

def test_get_tool_params_nested(test_config):
    session = Sessions()
    tool_use = types.ToolUse()
    tool_use.input_action_parameters = test_config["tool_input_params_nested"]
    res = session.get_tool_params(tool_use.input_action_parameters)
    assert res == test_config["tool_input_params_nested"]

def test_get_playbook_name(test_config, monkeypatch):
    mock_playbooks_instance = MagicMock()
    mock_playbooks_instance.get_playbooks_map.return_value = {
        test_config["playbook_id"]: test_config["playbook_name"]
    }

    session = Sessions(agent_id=test_config["agent_id"])
    monkeypatch.setattr(session, "_playbooks_client", mock_playbooks_instance)
    
    name = session.get_playbook_name(playbook_id=test_config["playbook_id"])
    assert name == test_config["playbook_name"]


def test_get_tool_name(test_config, mock_tools_instance, monkeypatch):   
    session = Sessions(agent_id=test_config["agent_id"])
    monkeypatch.setattr(session, "_tools_client", mock_tools_instance)

    mock_tool_use = types.example.ToolUse(tool=test_config["tool_id"])
    name = session.get_tool_name(tool_use=mock_tool_use)
    assert name == "mock tool"

def test_get_flow_name(test_config, monkeypatch):
    mock_flows_instance = MagicMock()
    mock_flows_instance.get_flows_map.return_value = {
        test_config["flow_id"]: "mock flow"
    }

    session = Sessions(agent_id=test_config["agent_id"])
    monkeypatch.setattr(session, "_flows_client", mock_flows_instance)

    name = session.get_flow_name(flow_id=test_config["flow_id"])
    assert name == "mock flow"

def test_collect_tool_responses(
        test_config, mock_tools_instance,
        mock_query_result_tools_playbooks_flows, monkeypatch):

    session = Sessions(agent_id=test_config["agent_id"])
    monkeypatch.setattr(session, "_tools_client", mock_tools_instance)
    tool_responses = session.collect_tool_responses(
        mock_query_result_tools_playbooks_flows)
    
    assert len(tool_responses) == 1
    assert tool_responses[0]["tool_name"] == "mock tool"
    assert tool_responses[0]["tool_action"] == test_config["tool_action"]
    assert tool_responses[0]["input_params"] == test_config["tool_input_params"]
    assert tool_responses[0]["output_params"] == test_config["tool_output_params"]

def test_collect_playbook_responses(
        test_config, mock_query_result_tools_playbooks_flows, monkeypatch):
    mock_playbooks_instance = MagicMock()
    mock_playbooks_instance.get_playbooks_map.return_value = {
        test_config["playbook_id"]: test_config["playbook_name"]
    }
    session = Sessions(agent_id=test_config["agent_id"])
    monkeypatch.setattr(session, "_playbooks_client", mock_playbooks_instance)
    playbook_responses = session.collect_playbook_responses(
        mock_query_result_tools_playbooks_flows)

    assert len(playbook_responses) == 4
    assert playbook_responses[0]["playbook_name"] == test_config["playbook_name"]

def test_collect_playbook_responses_no_playbook_invocation(
        test_config, monkeypatch):
    mock_playbooks_instance = MagicMock()
    mock_playbooks_instance.get_playbooks_map.return_value = {
        test_config["playbook_id"]: test_config["playbook_name"]
    }
    session = Sessions(agent_id=test_config["agent_id"])
    monkeypatch.setattr(session, "_playbooks_client", mock_playbooks_instance)

    mock_query_result = types.session.QueryResult(
    generative_info = types.session.GenerativeInfo(
        action_tracing_info=types.Example(
            actions=[],
           ),
        current_playbooks=[test_config["playbook_id"]]
        )
    )
    playbook_responses = session.collect_playbook_responses(mock_query_result)

    assert len(playbook_responses) == 0

def test_collect_flow_responses(test_config, monkeypatch):
    mock_flows_instance = MagicMock()
    mock_flows_instance.get_flows_map.return_value = {
        test_config["flow_id"]: "mock flow"
    }
    session = Sessions(agent_id=test_config["agent_id"])
    monkeypatch.setattr(session, "_flows_client", mock_flows_instance)
   
    mock_query_result = types.session.QueryResult(
        generative_info = types.session.GenerativeInfo(
            action_tracing_info=types.Example(
                actions=[
                    types.Action(
                        flow_invocation=types.example.FlowInvocation(
                            flow=test_config["flow_id"]
                        ),
                    ),
                ],
            ),
        )
    )
    flow_responses = session.collect_flow_responses(mock_query_result)
    assert len(flow_responses) == 1
    assert flow_responses[0]["flow_name"] == "mock flow"

@patch("uuid.uuid4")
def test_build_session_id_no_environment(mock_uuid4, test_config):
    mock_uuid4.return_value = uuid.UUID("a1b2c3d4-e5f6-7890-1234-567890abcdef")

    session = Sessions()
    session_id = session.build_session_id(agent_id=test_config["agent_id"])

    assert session_id == test_config["session_id_plain"]
    assert session.session_id == test_config["session_id_plain"]

@patch("uuid.uuid4")
def test_build_session_id_with_environment(
    mock_uuid4, test_config, mock_environment_obj, monkeypatch):
    mock_uuid4.return_value = uuid.UUID("a1b2c3d4-e5f6-7890-1234-567890abcdef")

    mock_env_instance = MagicMock()
    mock_env_instance.get_environment_by_display_name.return_value = mock_environment_obj

    session = Sessions(agent_id=test_config["agent_id"])
    monkeypatch.setattr(session, "_env_client", mock_env_instance)

    session_id = session.build_session_id(
        agent_id=test_config["agent_id"],
        environment_name=test_config["environment_name"]
    )

    assert test_config["environment_id"] in session_id
    assert session.session_id == session_id
    assert session.session_id == test_config["session_id_with_env"]

def test_build_session_id_invalid_env(test_config, monkeypatch):
    mock_env_instance = MagicMock()
    mock_env_instance.get_environment_by_display_name.return_value = None

    session = Sessions(agent_id=test_config["agent_id"])
    monkeypatch.setattr(session, "_env_client", mock_env_instance)

    with pytest.raises(ValueError, match="Environment `BAD_ENV` does not exist."):
        session.build_session_id(
        agent_id=test_config["agent_id"],
        environment_name="BAD_ENV"
        )

@patch("uuid.uuid4")
def test_build_session_id_no_overwrite(mock_uuid4, test_config):
    mock_uuid4.return_value = uuid.UUID("a1b2c3d4-9999-9999-9999-567890abcdef")

    session = Sessions(session_id=test_config["session_id_plain"])
    session_id = session.build_session_id(agent_id=test_config["agent_id"], overwrite=False)

    assert session.session_id == test_config["session_id_plain"]
    assert session_id != session.session_id

def test_detect_intent(
    test_config, mock_sessions_client, mock_detect_intent_response
):
    mock_detect_intent = MagicMock(return_value=mock_detect_intent_response)
    mock_sessions_client.return_value.detect_intent = mock_detect_intent

    session = Sessions()
    query_result = session.detect_intent(
        agent_id=test_config["agent_id"],
        session_id=test_config["session_id_plain"],
        text=test_config["text"],
        language_code=test_config["language_code"],
    )

    assert query_result == mock_detect_intent_response.query_result
    assert isinstance(query_result, types.QueryResult)
    assert query_result.language_code == "en" #default lang code

    mock_detect_intent.assert_called_once()
    request = mock_detect_intent.call_args.kwargs['request']
    assert not request.query_params.end_user_metadata
    assert not request.query_params.parameters
    assert not request.query_params.time_zone

def test_detect_intent_params_and_end_user_metadata(
    test_config, mock_sessions_client, mock_detect_intent_response
):
    mock_detect_intent = MagicMock(return_value=mock_detect_intent_response)
    mock_sessions_client.return_value.detect_intent = mock_detect_intent

    session = Sessions()
    query_result = session.detect_intent(
        agent_id=test_config["agent_id"],
        session_id=test_config["session_id_plain"],
        text=test_config["text"],
        language_code=test_config["language_code"],
        parameters=test_config["parameters"],
        end_user_metadata=test_config["end_user_metadata"]
    )

    assert query_result == mock_detect_intent_response.query_result
    assert isinstance(query_result, types.QueryResult)
    assert query_result.language_code == "en" #default lang code
    
    mock_detect_intent.assert_called_once()
    request = mock_detect_intent.call_args.kwargs['request']
    assert request.query_params.end_user_metadata == test_config["end_user_metadata"]
    assert request.query_params.parameters == test_config["parameters"]
    assert not request.query_params.time_zone


def test_detect_intent_with_timezone(
    test_config, mock_sessions_client, mock_detect_intent_response
):
    mock_detect_intent = MagicMock(return_value=mock_detect_intent_response)
    mock_sessions_client.return_value.detect_intent = mock_detect_intent

    session = Sessions()
    query_result = session.detect_intent(
        agent_id=test_config["agent_id"],
        session_id=test_config["session_id_plain"],
        text=test_config["text"],
        language_code=test_config["language_code"],
        timezone="America/Los_Angeles"
    )

    assert query_result == mock_detect_intent_response.query_result
    assert isinstance(query_result, types.QueryResult)
    assert query_result.language_code == "en" #default lang code

    mock_detect_intent.assert_called_once()
    request = mock_detect_intent.call_args.kwargs['request']
    assert request.query_params.time_zone == "America/Los_Angeles"

# TODO (pmarlow): Tracking b/384222123 which causes Data Store Signals to
# "fail open", meaning they are always populated. Revise tests once this is
# resolved.
def test_detect_intent_with_data_store_signals(
    test_config, mock_sessions_client, mock_detect_intent_response
):
    mock_detect_intent = MagicMock(return_value=mock_detect_intent_response)
    mock_sessions_client.return_value.detect_intent = mock_detect_intent

    session = Sessions()
    query_result = session.detect_intent(
        agent_id=test_config["agent_id"],
        session_id=test_config["session_id_plain"],
        text=test_config["text"],
        language_code=test_config["language_code"],
        populate_data_store_connection_signals=True
    )

    assert query_result == mock_detect_intent_response.query_result

    mock_detect_intent.assert_called_once()
    request = mock_detect_intent.call_args.kwargs['request']
    assert request.query_params.populate_data_store_connection_signals

def test_detect_intent_with_intent_id(
    test_config, mock_sessions_client, mock_detect_intent_response
):
    mock_detect_intent = MagicMock(return_value=mock_detect_intent_response)
    mock_sessions_client.return_value.detect_intent = mock_detect_intent

    session = Sessions()
    query_result = session.detect_intent(
        agent_id=test_config["agent_id"],
        session_id=test_config["session_id_plain"],
        intent_id=test_config["intent_id"],
        language_code=test_config["language_code"]
    )

    assert query_result == mock_detect_intent_response.query_result

    mock_detect_intent.assert_called_once()
    request = mock_detect_intent.call_args.kwargs['request']
    assert request.query_input.intent.intent == test_config["intent_id"]

def test_detect_intent_invalid_session_id(test_config):
    session = Sessions()
    with pytest.raises(
        ValueError,
        match="Session ID must be provided in the following format:"):
        session.detect_intent(
           agent_id=test_config["agent_id"],
           session_id="invalid_session_id",
           text=test_config["text"],
           language_code=test_config["language_code"],
        )

def test_detect_intent_preset_parameters_no_text_input(
        test_config, mock_sessions_client,
        mock_detect_intent_response_no_text_input):
  mock_detect_intent = MagicMock(
      return_value=mock_detect_intent_response_no_text_input)
  mock_sessions_client.return_value.detect_intent = mock_detect_intent

  session = Sessions()
  query_result = session.detect_intent(
      agent_id=test_config["agent_id"],
      session_id=test_config["session_id_plain"],
      parameters=test_config["parameters"],
  )

  assert query_result == mock_detect_intent_response_no_text_input.query_result
  mock_detect_intent.assert_called_once()
  request = mock_detect_intent.call_args.kwargs['request']
  assert request.query_params.parameters == test_config["parameters"]
  assert not request.query_input.text.text

def test_preset_parameters_no_agent_id(test_config):
  session = Sessions()
  with pytest.raises(ValueError, match="resource_id must not be None"):
    session.detect_intent(
        agent_id=None,
        session_id=test_config["session_id_plain"],
        parameters=test_config["parameters"],
    )

def test_preset_parameters_no_session_id(test_config):
  session = Sessions()
  with pytest.raises(ValueError, match="Session ID must be provided in the following format:"):
    session.detect_intent(
        agent_id=test_config["agent_id"],
        session_id=None,
        parameters=test_config["parameters"],
    )

def test_get_agent_answer(test_config, mock_sessions_client, monkeypatch, mock_query_result_datastore):
    mock_detect_intent_response = MagicMock()
    mock_detect_intent_response.query_result = mock_query_result_datastore

    mock_detect_intent = MagicMock(return_value=mock_detect_intent_response)
    mock_sessions_client.return_value.detect_intent = mock_detect_intent

    session = Sessions(agent_id=test_config["agent_id"])
    monkeypatch.setattr(session, "build_session_id",
        MagicMock(return_value=test_config["session_id_plain"]))

    answer = session.get_agent_answer(user_query="who is the ceo?")
    assert answer == "Sundar Pichai is the CEO of Google.\nhttps://www.google.com (https://www.google.com)"
    mock_detect_intent.assert_called_once()

def test_get_agent_answer_no_citation(test_config, mock_sessions_client, monkeypatch):
    mock_detect_intent_response = MagicMock()
    mock_detect_intent_response.query_result = types.session.QueryResult(
        response_messages=[
            types.ResponseMessage(
                text=types.ResponseMessage.Text(
                    text=["Test Response"]
                    )
                    )
            ]
        )

    mock_detect_intent = MagicMock(return_value=mock_detect_intent_response)
    mock_sessions_client.return_value.detect_intent = mock_detect_intent

    session = Sessions(agent_id=test_config["agent_id"])
    monkeypatch.setattr(session, "build_session_id",
                        MagicMock(return_value=test_config["session_id_plain"]))

    answer = session.get_agent_answer(user_query="test query")
    assert answer == "Test Response ()"
    mock_detect_intent.assert_called_once()

def test_parse_result(
    test_config, mock_query_result_tools_playbooks_flows, monkeypatch
):
    session = Sessions(agent_id=test_config["agent_id"])
    mock_printmd = MagicMock()
    monkeypatch.setattr(session, "printmd", mock_printmd)

    session.parse_result(mock_query_result_tools_playbooks_flows)

    mock_printmd.assert_called()
    calls = mock_printmd.mock_calls

    tool_call_font = "<font color='dark red'>TOOL CALL:</font></b>"
    tool_res_font = "<font color='yellow'>TOOL RESULT:</font></b>"
    query_font = "<font color='green'><b> USER QUERY:</font></b>"
    response_font = "<font color='green'><b>AGENT RESPONSE:</font></b>"

    # Check for the user query
    assert any(query_font in call.args[0] for call in calls)
    assert any(tool_call_font in call.args[0] for call in calls)
    assert any(tool_res_font in call.args[0] for call in calls)
    assert any(response_font in call.args[0] for call in calls)
