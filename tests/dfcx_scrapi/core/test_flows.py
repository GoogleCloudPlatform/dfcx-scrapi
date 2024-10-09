"""Test Class for core Flow Methods in SCRAPI."""

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
from typing import Dict
from unittest.mock import patch, MagicMock

from google.cloud.dialogflowcx_v3beta1 import types
from google.cloud.dialogflowcx_v3beta1.services.flows import pagers, FlowsClient

from dfcx_scrapi.core.flows import Flows

@pytest.fixture
def test_config():
    project_id = "my-project-id-1234"
    location_id = "global"
    parent = f"projects/{project_id}/locations/{location_id}"
    agent_id = f"{parent}/agents/my-agent-1234"
    display_name = "My Agent Display Name"
    default_id = "00000000-0000-0000-0000-000000000000"
    another_id = "99999999-9999-9999-9999-999999999999"
    start_flow_id = f"{agent_id}/flows/{default_id}"
    another_flow_id = f"{agent_id}/flows/{another_id}"

    return {
        "project_id": project_id,
        "agent_id": agent_id,
        "display_name": display_name,
        "location_id": location_id,
        "start_flow_id": start_flow_id,
        "another_flow_id": another_flow_id
    }

@pytest.fixture
def nlu_settings():
    return types.NluSettings(
        model_type=types.NluSettings.ModelType.MODEL_TYPE_ADVANCED,
        classification_threshold=0.3,
        model_training_mode=types.NluSettings.ModelTrainingMode.MODEL_TRAINING_MODE_AUTOMATIC
    )

@pytest.fixture
def mock_flows_list(test_config, nlu_settings):
    flow1 = types.Flow(
        name = test_config["start_flow_id"],
        display_name = "Default Start Flow",
        description = "This is the default start flow.",
        nlu_settings = nlu_settings
    )

    flow2 = types.Flow(
        name = test_config["another_flow_id"],
        display_name = "Flow #2",
        description = "Another Flow",
        nlu_settings = nlu_settings
    )

    return [flow1, flow2]

@pytest.fixture
def mock_list_flows_pager(mock_flows_list):
    return pagers.ListFlowsPager(
        FlowsClient.list_flows,
        types.ListFlowsRequest(),
        types.ListFlowsResponse(
            flows=mock_flows_list),
    )

@pytest.fixture(autouse=True)
def mock_creds(test_config: Dict[str, str]):
    """Setup fixture for Flows Class to be used with all tests."""
    with patch("dfcx_scrapi.core.scrapi_base.default") as mock_default, \
        patch("dfcx_scrapi.core.scrapi_base.Request") as mock_request:
        mock_creds = MagicMock()
        mock_default.return_value = (mock_creds, test_config["project_id"])
        mock_request.return_value = MagicMock()

        yield mock_creds

def test_build_nlu_settings_standard():
   nlu_settings = Flows._build_nlu_settings()
   assert nlu_settings.model_type == types.NluSettings.ModelType.MODEL_TYPE_STANDARD
   assert round(nlu_settings.classification_threshold, 1) == 0.3
   assert nlu_settings.model_training_mode == types.NluSettings \
    .ModelTrainingMode.MODEL_TRAINING_MODE_MANUAL

def test_build_nlu_settings_advanced():
    nlu_settings = Flows._build_nlu_settings(
       model_type="ADVANCED",
       classification_threshold=0.7,
       model_training_mode="AUTOMATIC"
       )

    assert nlu_settings.model_type == types.NluSettings.ModelType.MODEL_TYPE_ADVANCED
    assert round(nlu_settings.classification_threshold,1) == 0.7
    assert nlu_settings.model_training_mode == types.NluSettings \
        .ModelTrainingMode.MODEL_TRAINING_MODE_AUTOMATIC

def test_build_nlu_settings_invalid_model_type():
    with pytest.raises(KeyError):
       Flows._build_nlu_settings(model_type="INVALID")


def test_build_nlu_settings_invalid_training_mode():
    with pytest.raises(KeyError):
        Flows._build_nlu_settings(model_training_mode="INVALID")

@patch("dfcx_scrapi.core.flows.services.flows.FlowsClient.list_flows")
def test_get_flows_map(mock_list_flows, mock_list_flows_pager, test_config):
    mock_list_flows.return_value = mock_list_flows_pager

    flow = Flows()
    flows_map = flow.get_flows_map(agent_id=test_config["agent_id"])

    assert flows_map == {
        test_config["start_flow_id"]: "Default Start Flow",
        test_config["another_flow_id"]: "Flow #2"
        }
