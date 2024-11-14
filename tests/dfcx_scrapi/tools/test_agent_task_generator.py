"""Test Class for Agent Task Generator."""

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
import pytest
from unittest.mock import patch, MagicMock

from google.oauth2.service_account import Credentials

from google.cloud.dialogflowcx_v3beta1 import types
from vertexai.generative_models import GenerativeModel, GenerationResponse
from dfcx_scrapi.tools.gcs_utils import GcsUtils
from dfcx_scrapi.tools.agent_task_generator import AgentTaskGenerator, Prompts


@pytest.fixture
def test_config():
	project_id = "my-project-id-1234"
	email = "mock_email@testing.com"
	location_id = "global"
	parent = f"projects/{project_id}/locations/{location_id}"
	agent_id = f"{parent}/agents/my-agent-1234"
	playbook_id = f"{agent_id}/playbooks/1234"
	example_id = f"{playbook_id}/examples/9876"
	tool_id = f"{agent_id}/tools/4321"
	datastore_id = f"{parent}/dataStores/test-datastore"
	display_name = "test_example"
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

	sample_open_api_schema = """
  openapi: 3.0.0
  info:
  title: get_weather
  version: 1.0.0

  servers:
  - url: https://example.com

  paths:
  /get_weather_grid:
    get:
    summary: Returns the current grid information for a city and state
    operationId: get_weather_grid
    parameters:
      - name: latitude
      in: query
      required: true
      schema:
        type: string
      - name: longitude
      in: query
      required: true
      schema:
        type: string
    responses:
      '200':
      description: OK
      content:
        application/json:
        schema:
          type: object
          properties:
          data:
            type: string
  """

	expected_tasks = {
		"tasks": [
			{
				"name": "Order Pizza",
				"description": "Allows users to order a pizza.",
			},
			{
				"name": "Order Hamburger",
				"description": "Allows users to order a hamburger.",
			},
		]
	}
	user_task_input = """
This Agent is capable of the following: ordering a pizza, ordering a hamburger
"""

	expected_prompt_full_agent = "**APP DETAILS**\n{'name': 'Test Agent', 'supported_languages': ['es'], 'time_zone': 'America/New York'}\n\n**AGENT DETAILS**\n{'agent_0': {'name': 'Test Playbook 1', 'goal': 'Achieve Goal 1', 'instructions': ['Step 1', 'Step 2']}, 'agent_1': {'name': 'Test Playbook 2', 'goal': 'Achieve Goal 2', 'instructions': ['Step 3', 'Step 4']}}\n{'Start Flow': {'id': 'flows/12345678-90ab-cdef-0123-456789abcdef', 'pages': {'page1': {'id': 'pages/98765432-10fe-dcba-4321-0987654321fedcba'}, 'page2': {'id': 'pages/fedcba98-7654-3210-efcd-ab9876543210'}}}}\n[{'display_name': 'Test Intent 1', 'description': '', 'sample_utterances': ['Sample utterance 1']}, {'display_name': 'Test Intent 2', 'description': '', 'sample_utterances': ['Sample utterance 2']}]\n\n**TOOL DETAILS**\n{}\n"

	return {
		"project_id": project_id,
		"agent_id": agent_id,
		"playbook_id": playbook_id,
		"example_id": example_id,
		"tool_id": tool_id,
		"display_name": display_name,
		"creds_path": creds_path,
		"creds_dict": creds_dict,
		"creds_object": creds_object,
		"open_api_schema": sample_open_api_schema,
		"datastore_id": datastore_id,
		"user_task_input": user_task_input,
		"expected_tasks": expected_tasks,
		"expected_prompt_full_agent": expected_prompt_full_agent,
	}


@pytest.fixture(autouse=True)
def mock_setup(monkeypatch, test_config):
	"""Fixture to create mock setup for Agent Task Generator"""

	# mocking all other classes used by DFFX
	mock_credentials_from_file = MagicMock(
		return_value=test_config["creds_object"]
	)

	monkeypatch.setattr(
		"google.oauth2.service_account.Credentials.from_service_account_file",
		mock_credentials_from_file,
	)

	# mocking all other classes used by DFFX
	def mock_scrapi_base_init(self, *args, **kwargs):
		# Simulate the original behavior
		if kwargs.get("creds_path"):
			self.creds = Credentials.from_service_account_file(
				kwargs.get("creds_path")
			)
		elif kwargs.get("creds_dict"):
			self.creds = Credentials.from_service_account_info(
				kwargs.get("creds_dict")
			)
		else:
			self.creds = kwargs.get("creds")

	def mock_agents_init(self, *args, **kwargs):
		pass

	def mock_intents_init(self, *args, **kwargs):
		pass

	def mock_flows_init(self, *args, **kwargs):
		pass

	def mock_playbooks_init(self, *args, **kwargs):
		pass

	def mock_tools_init(self, *args, **kwargs):
		pass

	def mock_generative_model_init(self, *args, **kwargs):
		self._model_name = "gemini-1.5-flash-001"

	monkeypatch.setattr(
		"dfcx_scrapi.core.scrapi_base.ScrapiBase.__init__",
		mock_scrapi_base_init,
	)

	monkeypatch.setattr(
		"dfcx_scrapi.core.agents.Agents.__init__", mock_agents_init
	)

	monkeypatch.setattr(
		"dfcx_scrapi.core.intents.Intents.__init__", mock_intents_init
	)

	monkeypatch.setattr(
		"dfcx_scrapi.core.flows.Flows.__init__", mock_flows_init
	)

	monkeypatch.setattr(
		"dfcx_scrapi.core.playbooks.Playbooks.__init__", mock_playbooks_init
	)

	monkeypatch.setattr(
		"dfcx_scrapi.core.tools.Tools.__init__", mock_tools_init
	)

	monkeypatch.setattr(
		"vertexai.generative_models.GenerativeModel.__init__",
		mock_generative_model_init,
	)

	yield mock_credentials_from_file


@pytest.fixture
def open_api_tool_obj(test_config):
	"""Fixture to create a mocked Tool object of types.Tool."""
	return types.Tool(
		name=test_config["tool_id"],
		display_name="Test Open API Tool",
		description="Description of Test Open API Tool",
		open_api_spec=types.Tool.OpenApiTool(
			text_schema=test_config["open_api_schema"]
		),
	)


@pytest.fixture
def mock_agent():
	return types.Agent(
		display_name="Test Agent",
		default_language_code="en",
		supported_language_codes=["es"],
		time_zone="America/New York",
		description="A test agent",
		start_flow="00000000-0000-0000-0000-000000000000",
		enable_stackdriver_logging=True,
		enable_spell_correction=True,
	)


@pytest.fixture
def mock_playbooks(mock_tools):
	"""Fixture to create a list of mock Playbook objects."""
	playbook1 = types.Playbook(
		name="playbooks/test-playbook-1",
		display_name="Test Playbook 1",
		goal="Achieve Goal 1",
		instruction=types.Playbook.Instruction(
			steps=[
				types.Playbook.Step(text="Step 1"),
				types.Playbook.Step(text="Step 2"),
			]
		),
		referenced_tools=[mock_tools[0].name],
	)
	playbook2 = types.Playbook(
		name="playbooks/test-playbook-2",
		display_name="Test Playbook 2",
		goal="Achieve Goal 2",
		instruction=types.Playbook.Instruction(
			steps=[
				types.Playbook.Step(text="Step 3"),
				types.Playbook.Step(text="Step 4"),
			]
		),
		referenced_tools=[mock_tools[0].name, mock_tools[1].name],
	)
	return [playbook1, playbook2]


@pytest.fixture
def mock_intents():
	"""Fixture to create a list of mock Intent objects."""
	default_welcome_intent = types.Intent(
		name="intents/default-welcome-intent",
		display_name="Default Welcome Intent",
		training_phrases=[
			types.Intent.TrainingPhrase(
				parts=[
					types.Intent.TrainingPhrase.Part(text="Hi"),
				]
			),
			types.Intent.TrainingPhrase(
				parts=[
					types.Intent.TrainingPhrase.Part(text="Hello!"),
				]
			),
		],
	)
	default_negative_intent = types.Intent(
		name="intents/default-negative-intent",
		display_name="Default Negative Intent",
		training_phrases=[],
	)

	intent1 = types.Intent(
		name="intents/test-intent-1",
		display_name="Test Intent 1",
		training_phrases=[
			types.Intent.TrainingPhrase(
				parts=[
					types.Intent.TrainingPhrase.Part(text="Sample utterance 1"),
				]
			)
		],
	)
	intent2 = types.Intent(
		name="intents/test-intent-2",
		display_name="Test Intent 2",
		training_phrases=[
			types.Intent.TrainingPhrase(
				parts=[
					types.Intent.TrainingPhrase.Part(text="Sample utterance 2"),
				]
			)
		],
	)

	return [intent1, intent2, default_welcome_intent, default_negative_intent]


@pytest.fixture
def mock_tools(test_config, open_api_tool_obj):
	"""Fixture to create a list of mock Tool objects."""
	function_tool_input_schema = {
		"type": "object",
		"required": ["text", "url"],
		"properties": {
			"url": {
				"type": "string",
				"description": "The URL for the button",
			},
			"text": {
				"description": "the display text of the button",
				"type": "string",
			},
		},
	}
	tool1 = types.Tool(
		name="tools/test-tool-1",
		display_name="Test Tool 1",
		description="Description of Test Tool 1",
		function_spec=types.Tool.FunctionTool(
			input_schema=function_tool_input_schema
		),
	)
	tool2 = types.Tool(
		name="tools/test-tool-2",
		display_name="Test Tool 2",
		description="Description of Test Tool 2",
		data_store_spec=types.Tool.DataStoreTool(
			data_store_connections=[
				types.DataStoreConnection(
					data_store=test_config["datastore_id"]
				)
			]
		),
	)
	return [tool1, tool2, open_api_tool_obj]


@pytest.fixture
def mock_flow_page_map():
	"""Fixture to create a mock flow page map."""
	return {
		"Start Flow": {
			"id": "flows/12345678-90ab-cdef-0123-456789abcdef",
			"pages": {
				"page1": {
					"id": "pages/98765432-10fe-dcba-4321-0987654321fedcba"
				},
				"page2": {"id": "pages/fedcba98-7654-3210-efcd-ab9876543210"},
			},
		}
	}


# Test init with creds_path
def test_atg_init_creds_path(mock_setup, test_config):
	mock_creds = mock_setup
	atg = AgentTaskGenerator(
		agent_id=test_config["agent_id"], creds_path=test_config["creds_path"]
	)

	assert atg.creds == test_config["creds_object"]
	mock_creds.assert_called_once_with(test_config["creds_path"])


# Test gather_tool_spec_details OpenAPI
def test_gather_tool_spec_details_openapi(test_config, open_api_tool_obj):
	atg = AgentTaskGenerator(test_config["agent_id"])
	actions, schema = atg.gather_tool_spec_details(open_api_tool_obj)

	assert actions is None
	assert schema == test_config["open_api_schema"]


def test_get_agent_tasks_from_user_input(test_config):
	atg = AgentTaskGenerator(test_config["agent_id"])

	mock_response = MagicMock(spec=GenerationResponse)
	mock_response.text = json.dumps(test_config["expected_tasks"])
	mock_generate_content = MagicMock(return_value=mock_response)
	atg.model.generate_content = mock_generate_content

	tasks = atg.get_agent_tasks_from_user_input(test_config["user_task_input"])

	assert isinstance(tasks, dict)
	assert isinstance(atg.model, GenerativeModel)
	assert atg.creds == None
	atg.model.generate_content.assert_called_once()
	assert tasks == test_config["expected_tasks"]


def test_get_agent_tasks(
	test_config,
	mock_agent,
	mock_playbooks,
	mock_tools,
	mock_intents,
	mock_flow_page_map,
):
	atg = AgentTaskGenerator(test_config["agent_id"])

	atg.agents.get_agent = MagicMock(return_value=mock_agent)
	atg.playbooks.list_playbooks = MagicMock(return_value=mock_playbooks)
	atg.tools.list_tools = MagicMock(return_value=mock_tools)
	atg.intents.list_intents = MagicMock(return_value=mock_intents)
	atg.flows.get_flow_page_map = MagicMock(return_value=mock_flow_page_map)

	mock_response = MagicMock(spec=GenerationResponse)
	mock_response.text = json.dumps(test_config["expected_tasks"])
	mock_generate_content = MagicMock(return_value=mock_response)
	atg.model.generate_content = mock_generate_content

	tasks = atg.get_agent_tasks()

	# assert types and values
	assert isinstance(tasks, dict)
	assert "tasks" in tasks
	assert isinstance(tasks["tasks"], list)
	assert len(tasks["tasks"]) > 0

	# assert that the necessary methods were called
	atg.agents.get_agent.assert_called_once_with(test_config["agent_id"])
	atg.playbooks.list_playbooks.assert_called_once_with(
		test_config["agent_id"]
	)
	atg.tools.list_tools.assert_called_once_with(test_config["agent_id"])
	atg.intents.list_intents.assert_called_once_with(test_config["agent_id"])
	atg.flows.get_flow_page_map.assert_called_once_with(test_config["agent_id"])

	mock_generate_content.assert_called_once()

def test_trim_playbook_data(test_config, mock_playbooks):
	atg = AgentTaskGenerator(test_config["agent_id"])
	playbook_info = atg.trim_playbook_data(mock_playbooks)

	assert isinstance(playbook_info, dict)
	assert len(playbook_info) == len(mock_playbooks)

	for i, playbook in enumerate(mock_playbooks):
		expected_key = f"agent_{i}"
		assert expected_key in playbook_info
		assert playbook_info[expected_key]["name"] == playbook.display_name
		assert playbook_info[expected_key]["goal"] == playbook.goal

		expected_instructions = atg.get_playbook_steps(playbook.instruction)
		assert (
			playbook_info[expected_key]["instructions"] == expected_instructions
		)

def test_trim_agent_data(test_config, mock_agent):
	atg = AgentTaskGenerator(test_config["agent_id"])
	trimmed_data = atg.trim_agent_data(mock_agent)

	assert isinstance(trimmed_data, dict)
	assert trimmed_data["name"] == mock_agent.display_name
	assert (
		trimmed_data["supported_languages"]
		== mock_agent.supported_language_codes
	)
	assert trimmed_data["time_zone"] == mock_agent.time_zone

def test_get_playbook_steps(test_config, mock_playbooks):
	atg = AgentTaskGenerator(test_config["agent_id"])

	for playbook in mock_playbooks:
		steps = atg.get_playbook_steps(playbook.instruction)
		assert isinstance(steps, list)
		expected_steps = [step.text for step in playbook.instruction.steps]
		assert steps == expected_steps

def test_get_intent_info(test_config, mock_intents):
	atg = AgentTaskGenerator(test_config["agent_id"])

	atg.intents.list_intents = MagicMock(return_value=mock_intents)
	intent_info = atg.get_intent_info()

	assert isinstance(intent_info, list)

	excluded_intent_names = [
		"Default Welcome Intent",
		"Default Negative Intent",
	]
	for intent_data in intent_info:
		assert intent_data["display_name"] not in excluded_intent_names

def test_trim_agent_tools(
	test_config, mock_playbooks, mock_tools, open_api_tool_obj
):
	"""Test for the trim_agent_tools method."""
	atg = AgentTaskGenerator(test_config["agent_id"])
	tool_info = atg.trim_agent_tools(mock_playbooks, mock_tools)

	assert isinstance(tool_info, dict)

	# Only playbook referenced tools should be included
	included_tool_names = {tool_info[key]["name"] for key in tool_info}
	assert len(tool_info) == 2  
	assert included_tool_names == {"Test Tool 1", "Test Tool 2"}

### Test cases for loading Agent Task variations ###
# Test case 1: GCS enabled, tasks exist, no force reload
def test_load_agent_tasks_gcs_exists_no_force(test_config, monkeypatch):
	mock_gcs_utils = MagicMock(spec=GcsUtils)
	atg = AgentTaskGenerator(test_config["agent_id"], gcs=mock_gcs_utils)
	atg.load_or_create_task_file_gcs = MagicMock(
		return_value=test_config["expected_tasks"])

	monkeypatch.setattr(atg, "get_agent_tasks", MagicMock())
	monkeypatch.setattr(atg, "write_agent_tasks_to_local", MagicMock())
	monkeypatch.setattr(atg, "write_agent_tasks_to_gcs", MagicMock())
	tasks = atg.load_agent_tasks()

	assert tasks == test_config["expected_tasks"]
	atg.get_agent_tasks.assert_not_called()  # get_agent_tasks should not be called
	atg.write_agent_tasks_to_local.assert_not_called()
	atg.write_agent_tasks_to_gcs.assert_not_called()

# Test case 2: GCS enabled, tasks exist, force reload
def test_load_agent_tasks_gcs_exists_force(test_config, monkeypatch):  # Remove caplog
	mock_gcs_utils = MagicMock(spec=GcsUtils)
	atg = AgentTaskGenerator(test_config["agent_id"], gcs=mock_gcs_utils)

	# Mock necessary methods 
	monkeypatch.setattr(atg, "load_or_create_task_file_gcs", MagicMock(return_value={"tasks": ["task1"]}))
	monkeypatch.setattr(atg, "get_agent_tasks", MagicMock(
		return_value=test_config["expected_tasks"]))
	monkeypatch.setattr(atg, "write_agent_tasks_to_local", MagicMock())
	monkeypatch.setattr(atg, "write_agent_tasks_to_gcs", MagicMock())

	tasks = atg.load_agent_tasks(force_reload=True)

	assert tasks == test_config["expected_tasks"]
	atg.get_agent_tasks.assert_called_once()
	atg.write_agent_tasks_to_local.assert_called_once_with(tasks)
	atg.write_agent_tasks_to_gcs.assert_called_once_with(tasks)

# Test case 3: GCS enabled, tasks do not exist
def test_load_agent_tasks_gcs_not_exists(test_config, monkeypatch):
	mock_gcs_utils = MagicMock(spec=GcsUtils)
	atg = AgentTaskGenerator(test_config["agent_id"], gcs=mock_gcs_utils)

	# Mock necessary methods
	monkeypatch.setattr(atg, "load_or_create_task_file_gcs", MagicMock(return_value={"tasks": None}))
	monkeypatch.setattr(atg, "get_agent_tasks", MagicMock(return_value=test_config["expected_tasks"]))
	monkeypatch.setattr(atg, "write_agent_tasks_to_local", MagicMock())
	monkeypatch.setattr(atg, "write_agent_tasks_to_gcs", MagicMock())

	tasks = atg.load_agent_tasks()

	assert tasks == test_config["expected_tasks"]
	atg.get_agent_tasks.assert_called_once()
	atg.write_agent_tasks_to_gcs.assert_called_once_with(test_config["expected_tasks"]) 
	atg.write_agent_tasks_to_local.assert_not_called()


# # Test case 4: GCS disabled, tasks exist, no force reload
def test_load_agent_tasks_local_exists_no_force(test_config, monkeypatch):
	atg = AgentTaskGenerator(test_config["agent_id"])

	# Mock necessary methods
	monkeypatch.setattr(atg, "load_or_create_task_file_local", MagicMock(return_value=test_config["expected_tasks"]))
	monkeypatch.setattr(atg, "get_agent_tasks", MagicMock())
	monkeypatch.setattr(atg, "write_agent_tasks_to_local", MagicMock())
	monkeypatch.setattr(atg, "write_agent_tasks_to_gcs", MagicMock())

	tasks = atg.load_agent_tasks()

	assert tasks == test_config["expected_tasks"]  # Assert against expected_tasks
	# Removed caplog assertions
	atg.get_agent_tasks.assert_not_called()
	atg.write_agent_tasks_to_local.assert_not_called()
	atg.write_agent_tasks_to_gcs.assert_not_called()


# # Test case 5: GCS disabled, tasks exist, force reload
def test_load_agent_tasks_local_exists_force(test_config, monkeypatch):
	atg = AgentTaskGenerator(test_config["agent_id"])

	# Mock necessary methods
	monkeypatch.setattr(atg, "load_or_create_task_file_local", MagicMock(return_value={"tasks": ["task4"]})) 
	monkeypatch.setattr(atg, "get_agent_tasks", MagicMock(return_value=test_config["expected_tasks"]))  # Use expected_tasks
	monkeypatch.setattr(atg, "write_agent_tasks_to_local", MagicMock())
	monkeypatch.setattr(atg, "write_agent_tasks_to_gcs", MagicMock())

	tasks = atg.load_agent_tasks(force_reload=True)

	assert tasks == test_config["expected_tasks"]  # Assert against expected_tasks
	# Removed caplog assertions
	atg.get_agent_tasks.assert_called_once()
	atg.write_agent_tasks_to_local.assert_called_once_with(test_config["expected_tasks"])  # Use expected_tasks
	atg.write_agent_tasks_to_gcs.assert_not_called()


# # Test case 6: GCS disabled, tasks do not exist
def test_load_agent_tasks_local_not_exists(test_config, monkeypatch):
    atg = AgentTaskGenerator(test_config["agent_id"])
    
    # Mock necessary methods
    monkeypatch.setattr(atg, "load_or_create_task_file_local", MagicMock(return_value={"tasks": None}))
    monkeypatch.setattr(atg, "get_agent_tasks", MagicMock(return_value=test_config["expected_tasks"]))  # Use expected_tasks
    monkeypatch.setattr(atg, "write_agent_tasks_to_local", MagicMock())
    monkeypatch.setattr(atg, "write_agent_tasks_to_gcs", MagicMock())

    tasks = atg.load_agent_tasks()

    assert tasks == test_config["expected_tasks"]  # Assert against expected_tasks
    # Removed caplog assertions
    atg.get_agent_tasks.assert_called_once()
    atg.write_agent_tasks_to_local.assert_called_once_with(test_config["expected_tasks"])  # Use expected_tasks
    atg.write_agent_tasks_to_gcs.assert_not_called()
