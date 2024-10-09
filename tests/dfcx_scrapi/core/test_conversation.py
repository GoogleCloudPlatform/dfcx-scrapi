"""Test Class for DialogflowConversation Methods in SCRAPI."""

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

import pytest
import pandas as pd
from unittest.mock import patch, MagicMock
from google.oauth2.service_account import Credentials
from google.api_core.exceptions import InvalidArgument

from google.cloud.dialogflowcx_v3beta1 import types
from google.cloud.dialogflowcx_v3beta1 import services

from dfcx_scrapi.builders.flows import FlowBuilder
from dfcx_scrapi.builders.routes import TransitionRouteBuilder
from dfcx_scrapi.builders.fulfillments import FulfillmentBuilder
from dfcx_scrapi.builders.response_messages import ResponseMessageBuilder
from dfcx_scrapi.core.conversation import DialogflowConversation

@pytest.fixture
def test_config():
    project_id = "my-project-id-1234"
    location_id = "global"
    default_id = "00000000-0000-0000-0000-000000000000"
    another_id = "99999999-9999-9999-9999-999999999999"
    parent = f"projects/{project_id}/locations/{location_id}"
    agent_id = f"{parent}/agents/my-agent-1234"
    default_start_flow_id = f"{agent_id}/flows/{default_id}"
    another_flow_id = f"{agent_id}/flows/{another_id}"
    default_welcome_intent = f"{agent_id}/intents/{default_id}"
    email = "mock_email@testing.com"
    creds_path = "/Users/path/to/creds/credentials.json"
    creds_dict = {
        "type": "service_account",
        "project_id": project_id,
        "private_key_id": "1234",
        "private_key": "mock_key",
        "client_email": f"mock-account@{project_id}.iam.gserviceaccount.com",
        "client_id": "1234",
        "universe_domain": "googleapis.com",
    }

    mock_signer = MagicMock()
    mock_signer.key_id = "mock_key_id"
    mock_signer.sign.return_value = b"mock_signature"

    creds_object = Credentials(
        signer=mock_signer,
        token_uri="mock_token_uri",
        service_account_email=email,
        project_id=project_id,
        quota_project_id=project_id,
        scopes=[],
    )

    return {
        "project_id": project_id,
        "agent_id": agent_id,
        "default_welcome_intent": default_welcome_intent,
        "default_start_flow_id": default_start_flow_id,
        "another_flow_id": another_flow_id,
        "creds_path": creds_path,
        "creds_dict": creds_dict,
        "creds_object": creds_object,
    }

@pytest.fixture
def test_set_es():
    cols = ['flow_display_name', 'page_display_name', 'utterance']
    df = pd.DataFrame(columns=cols)
    df.loc[1] = ["Default Start Flow", "START_PAGE", "Hola!"]
    df.loc[2] = ["Default Start Flow", "START_PAGE", "Como estas?"]

    return df

@pytest.fixture
def test_set_en():
    cols = ['flow_display_name', 'page_display_name', 'utterance']
    df = pd.DataFrame(columns=cols)
    df.loc[1] = ["Default Start Flow", "START_PAGE", "Hi!"]
    df.loc[2] = ["Default Start Flow", "START_PAGE", "How are you?"]

    return df

@pytest.fixture
def es_response_message():
    rmb = ResponseMessageBuilder()
    msg = rmb.create_new_proto_obj(
        response_type="text",
        message=["¡Hola!", "¡Buenos días!"]
    )

    return msg

@pytest.fixture
def nlu_settings():
    fb = FlowBuilder()
    flow = fb.create_new_proto_obj(
        display_name="Default Start Flow",
        overwrite=True
    )
    flow = fb.nlu_settings(
        model_type=3,
        classification_threshold=0.3,
        model_training_mode=1
    )

    return flow.nlu_settings

@pytest.fixture
def mock_flows_list_es(test_config, nlu_settings, es_response_message):
    fulb = FulfillmentBuilder()
    trb = TransitionRouteBuilder()

    agent_msg = fulb.create_new_proto_obj()
    agent_msg = fulb.add_response_message(es_response_message)

    route = trb.create_new_proto_obj(
        intent=test_config["default_welcome_intent"],
        trigger_fulfillment=agent_msg
    )

    flow1 = types.Flow(
        name = test_config["default_start_flow_id"],
        display_name = "Default Start Flow",
        description = "Basic Flow in Spanish",
        transition_routes = [route],
        nlu_settings = nlu_settings
    )

    flow2 = types.Flow(
        name = test_config["another_flow_id"],
        display_name = "Flow #2",
        description = "Another Flow in Spanish",
        transition_routes = [route],
        nlu_settings = nlu_settings
    )

    return [flow1, flow2]


@pytest.fixture
def mock_pages_list(test_config):
    flow_id1 = test_config["default_start_flow_id"]
    flow_id2 = test_config["another_flow_id"]

    page1 = types.Page(
        name = f"{flow_id1}/pages/1234",
        display_name = "Test Page 1"
    )

    page2 = types.Page(
        name = f"{flow_id2}/pages/9876",
        display_name = "Test Page 2"
    )

    return [page1, page2]

@pytest.fixture
def mock_list_flows_pager(mock_flows_list_es):
    return services.flows.pagers.ListFlowsPager(
        services.flows.FlowsClient.list_flows,
        types.ListFlowsRequest(),
        types.ListFlowsResponse(
            flows=mock_flows_list_es),
    )

@pytest.fixture
def mock_list_pages_pager(mock_pages_list):
    return services.pages.pagers.ListPagesPager(
        services.pages.PagesClient.list_pages,
        types.ListPagesRequest(),
        types.ListPagesResponse(
            pages=mock_pages_list),
    )

@pytest.fixture(autouse=True)
def mock_client(test_config):
    """Fixture to create a mocked DialogflowConversation client."""
    with patch("dfcx_scrapi.core.scrapi_base.default") as mock_default, \
        patch("dfcx_scrapi.core.scrapi_base.Request") as mock_request, \
        patch("dfcx_scrapi.core.conversation.DialogflowConversation") as mock_client:

        mock_creds = MagicMock()
        mock_default.return_value = (mock_creds, test_config["project_id"])
        mock_request.return_value = MagicMock()

        yield mock_client

@patch("dfcx_scrapi.core.flows.services.flows.FlowsClient.list_flows")
@patch("dfcx_scrapi.core.pages.pages.PagesClient.list_pages")
def test_page_id_mapper_with_config_lang_code(
    mock_list_pages,
    mock_list_flows,
    test_config,
    mock_list_flows_pager,
    mock_list_pages_pager
    ):
    mock_list_pages.return_value = mock_list_pages_pager
    mock_list_flows.return_value = mock_list_flows_pager
    expected_request = types.flow.ListFlowsRequest(
        parent=test_config["agent_id"], language_code="es"
    )

    config = {
        "agent_path": test_config["agent_id"],
        "language_code": "es"
    }

    dc = DialogflowConversation(config=config)
    dc._page_id_mapper()

    assert dc.agent_id == test_config["agent_id"]
    assert dc.language_code == "es"
    assert dc.flows.language_code == "es"
    assert dc.pages.language_code == "es"
    assert "Default Start Flow" in dc.agent_pages_map.flow_display_name.unique()
    assert "Flow #2" in dc.agent_pages_map.flow_display_name.unique()
    mock_list_flows.assert_called_once_with(expected_request)

@patch("dfcx_scrapi.core.flows.services.flows.FlowsClient.list_flows")
@patch("dfcx_scrapi.core.pages.pages.PagesClient.list_pages")
def test_page_id_mapper_with_class_lang_code(
    mock_list_pages,
    mock_list_flows,
    test_config,
    mock_list_flows_pager,
    mock_list_pages_pager
    ):
    mock_list_pages.return_value = mock_list_pages_pager
    mock_list_flows.return_value = mock_list_flows_pager
    expected_request = types.flow.ListFlowsRequest(
        parent=test_config["agent_id"], language_code="es"
    )

    config = {"agent_path": test_config["agent_id"]}

    dc = DialogflowConversation(config=config, language_code="es")
    dc._page_id_mapper()

    assert dc.agent_id == test_config["agent_id"]
    assert dc.language_code == "es"
    assert dc.flows.language_code == "es"
    assert dc.pages.language_code == "es"
    assert "Default Start Flow" in dc.agent_pages_map.flow_display_name.unique()
    assert "Flow #2" in dc.agent_pages_map.flow_display_name.unique()
    mock_list_flows.assert_called_once_with(expected_request)

@patch("dfcx_scrapi.core.flows.services.flows.FlowsClient.list_flows")
@patch("dfcx_scrapi.core.pages.pages.PagesClient.list_pages")
def test_page_id_mapper_with_default_lang_code(
    mock_list_pages,
    mock_list_flows,
    test_config,
    mock_list_flows_pager,
    mock_list_pages_pager
    ):
    mock_list_pages.return_value = mock_list_pages_pager
    mock_list_flows.return_value = mock_list_flows_pager
    expected_request = types.flow.ListFlowsRequest(
        parent=test_config["agent_id"], language_code="en"
    )

    config = {"agent_path": test_config["agent_id"]}

    dc = DialogflowConversation(config=config)
    dc._page_id_mapper()

    assert dc.agent_id == test_config["agent_id"]
    assert dc.language_code == "en"
    assert dc.flows.language_code == "en"
    assert dc.pages.language_code == "en"
    assert "Default Start Flow" in dc.agent_pages_map.flow_display_name.unique()
    assert "Flow #2" in dc.agent_pages_map.flow_display_name.unique()
    mock_list_flows.assert_called_once_with(expected_request)

@patch("dfcx_scrapi.core.flows.services.flows.FlowsClient.list_flows")
@patch("dfcx_scrapi.core.agents.Agents.get_agent")
def test_page_id_mapper_config_invalid_lang_code(
    mock_get_agent,
    mock_list_flows,
    test_config
    ):
    mock_agent = types.Agent(supported_language_codes=["es", "fr"])
    mock_get_agent.return_value = mock_agent
    expected_request = types.flow.ListFlowsRequest(
        parent=test_config["agent_id"], language_code="en"
    )
    
    # Mock the list_flows method to raise an InvalidArgument exception
    # with the specific error message you want to test for.
    mock_list_flows.side_effect = InvalidArgument(
        "400 com.google.apps.framework.request.BadRequestException: "
        "Agent does not support language: 'en'."
    )

    config = {
        "agent_path": test_config["agent_id"],
        "language_code": "en"
    }

    with pytest.raises(InvalidArgument) as excinfo:
        dc = DialogflowConversation(config=config)
        dc._page_id_mapper()

    assert "Agent does not support language: 'en'." in str(excinfo.value)
    mock_list_flows.assert_called_once_with(expected_request)

@patch("dfcx_scrapi.core.flows.services.flows.FlowsClient.list_flows")
@patch("dfcx_scrapi.core.agents.Agents.get_agent")
def test_page_id_mapper_class_invalid_lang_code(
    mock_get_agent,
    mock_list_flows,
    test_config
    ):
    mock_agent = types.Agent(supported_language_codes=["es", "fr"])
    mock_get_agent.return_value = mock_agent
    expected_request = types.flow.ListFlowsRequest(
        parent=test_config["agent_id"], language_code="en"
    )
    
    # Mock the list_flows method to raise an InvalidArgument exception
    # with the specific error message you want to test for.
    mock_list_flows.side_effect = InvalidArgument(
        "400 com.google.apps.framework.request.BadRequestException: "
        "Agent does not support language: 'en'."
    )

    config = {
        "agent_path": test_config["agent_id"],
    }

    with pytest.raises(InvalidArgument) as excinfo:
        dc = DialogflowConversation(config=config, language_code="en")
        dc._page_id_mapper()

    assert "Agent does not support language: 'en'." in str(excinfo.value)
    mock_list_flows.assert_called_once_with(expected_request)
