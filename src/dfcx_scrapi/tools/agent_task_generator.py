"""Methods to Generator Agent Tasks for arbitrary Agent inputs."""

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
import random
from pathlib import Path
from typing import Any, Dict, List

from google.cloud.dialogflowcx_v3beta1 import types
from google.oauth2 import service_account
from vertexai.generative_models import GenerationConfig, GenerativeModel

from dfcx_scrapi.core.agents import Agents
from dfcx_scrapi.core.flows import Flows
from dfcx_scrapi.core.intents import Intents
from dfcx_scrapi.core.playbooks import Playbooks
from dfcx_scrapi.core.scrapi_base import ScrapiBase
from dfcx_scrapi.core.tools import Tools
from dfcx_scrapi.tools.gcs_utils import GcsUtils


class AgentTaskGenerator(ScrapiBase):

    def __init__(
        self,
        agent_id: str,
        creds_path: str = None,
        creds_dict: Dict = None,
        creds: service_account.Credentials = None,
        scope=False,
        gcs: GcsUtils = None,
        debug: bool = False
    ):
        super().__init__(
            creds_path=creds_path,
            creds_dict=creds_dict,
            creds=creds,
            scope=scope,
        )

        self.agent_id = agent_id
        self.debug = debug
        if self.debug:
            self.set_logging_level("debug")

        self.agents = Agents(agent_id=self.agent_id, creds=self.creds)
        self.intents = Intents(agent_id=self.agent_id, creds=self.creds)
        self.flows = Flows(agent_id=self.agent_id, creds=self.creds)
        self.playbooks = Playbooks(agent_id=self.agent_id, creds=self.creds)
        self.tools = Tools(agent_id=self.agent_id, creds=self.creds)

        self.model = GenerativeModel(
            "gemini-1.5-flash-001",
            system_instruction=Prompts.task_system
            )

        self.gcs = gcs
        self.task_file = "agent_tasks.json"

        if self.gcs:
            self.short_id = self.agent_id.split("/")[-1]
            self.filename = f"testwiz/{self.short_id}/data/{self.task_file}"
            self.full_path = self.gcs.get_fully_qualified_path(self.filename)

    @staticmethod
    def write_agent_tasks_to_local(tasks: Dict[str, Any]):
        """Write Agent Task list to Local file."""
        task_file = "agent_tasks.json"
        data_dir = os.path.join(Path(__file__).resolve().parents[2], "data")
        cached_path = f"{data_dir}/{task_file}"

        # Write data back to file
        with open(cached_path, "w", encoding="UTF-8") as outfile:
            data_str = json.dumps(tasks)
            outfile.write(data_str)
            outfile.close()

    @staticmethod
    def get_sample_utterances(intent: Any):
        """Get 5 or less sample utterances from the intent."""
        num_to_select = min(len(intent.training_phrases), 5)
        intents = random.sample(intent.training_phrases, num_to_select)
        utterances = []

        for tp in intents:
            utterances.append(tp.parts[0].text)

        return utterances

    def gather_tool_spec_details(self, tool: types.Tool):
        """Determine Tool type and extract actions."""

        # Datastore Type
        connections = tool.data_store_spec.data_store_connections
        if len(connections) > 0:
            return tool.display_name, connections

        # Extension Type
        elif tool.extension_spec.name != "":
            return None, None

        # Function Call Type
        elif tool.function_spec.input_schema:
            input_schema = self.recurse_proto_marshal_to_dict(
                tool.function_spec.input_schema
            )
            return None, input_schema

        # OpenAPI Spec Type
        elif tool.open_api_spec.text_schema != "":
            return None, tool.open_api_spec.text_schema

    def _call_generate_content(self, prompt: str):
        return self.model.generate_content(
            prompt,
            safety_settings=self.build_safety_settings(),
            generation_config = GenerationConfig(
                temperature=0.1,
                top_p=0.95,
                candidate_count=1,
                max_output_tokens=8192,
                response_mime_type="application/json",
                response_schema=Schemas.task_schema,
                )
        )

    def load_or_create_task_file_gcs(self):
        """Load or create Agent Task file from GCS."""
        data = {"tasks": None}

        data_from_file = self.gcs.load_file_if_exists(
            bucket_name=self.gcs.bucket_name,
            filename=self.full_path
        )

        if data_from_file:
            logging.info("Loading Task List from GCS cache...")
            data = json.loads(data_from_file)

        else:
            self.gcs.write_dict_to_gcs(
                bucket_name=self.gcs.bucket_name,
                data=data,
                filename=self.full_path
            )

        return data

    def load_or_create_task_file_local(self):
        """Load or create Agent task file from Local."""
        data_dir = os.path.join(Path(__file__).resolve().parents[2], "data")
        cached_path = f"{data_dir}/{self.task_file}"
        data = {"tasks": None}

        # Create local if file doesn't exist
        if self.task_file not in os.listdir(data_dir):
            logging.info("Creating Agent Task File...")
            with open(cached_path, "w", encoding="UTF-8") as newfile:
                data_str = json.dumps(data)
                newfile.write(data_str)
                newfile.close()

        else:
            with open(cached_path, "r", encoding="UTF-8") as infile:
                data = json.load(infile)

        return data

    def write_agent_tasks_to_gcs(self, tasks: Dict[str, Any]):
        """Write Agent Task list to GCS file."""

        # write back to file
        self.gcs.write_dict_to_gcs(
            bucket_name=self.gcs.bucket_name,
            data=tasks,
            filename=self.full_path
        )

    def load_agent_tasks(self, force_reload: bool = False):
        """Check for cached Agent Task map or load new."""
        if self.gcs:
            data = self.load_or_create_task_file_gcs()
        else:
            data = self.load_or_create_task_file_local()

        tasks = data.get("tasks", None)

        # If the task metadata exists, but user wants to force reload anyways
        if tasks and force_reload:
            logging.info("Forcing reload of Agent Tasks...")
            tasks = self.get_agent_tasks()
            self.write_agent_tasks_to_local(tasks)
            if self.gcs:
                self.write_agent_tasks_to_gcs(tasks)

        # Check if tasks exists and if not, create
        if not tasks:
            logging.info("Agent Task list does not exist. Creating...")
            tasks = self.get_agent_tasks()

            if self.gcs:
                self.write_agent_tasks_to_gcs(tasks)
            else:
                self.write_agent_tasks_to_local(tasks)

        if isinstance(tasks, list):
            tasks = {"tasks": tasks}

        return tasks

    def trim_agent_tools(
            self, playbooks: List[Any], tools: List[Any]
            ) -> List[Any]:
        """Trim down the list of agent tools to only those that are ref'd."""
        playbook_tools = set()
        for playbook in playbooks:
            for tool in playbook.referenced_tools:
                playbook_tools.add(tool)

        tool_info = {}
        i = 0
        for tool in tools:
            if tool.name in playbook_tools:
                actions, schema = self.gather_tool_spec_details(tool)
                tool_info[f"tool_{i}"] = {
                    "name": tool.display_name,
                    "description": tool.description,
                    "actions": actions,
                    "schemas": schema
                }
            i += 1

        return tool_info

    def get_intent_info(self):
        """Get structured intent info from Agent to use in prompt."""
        EXCLUDE_INTENTS = [
            "Default Welcome Intent",
            "Default Negative Intent"
        ]

        all_intents = self.intents.list_intents(self.agent_id)
        intent_info = []
        for intent in all_intents:
            if intent.display_name in EXCLUDE_INTENTS:
                continue

            intent_info.append(
                {
                    "display_name": intent.display_name,
                    "description": intent.description,
                    "sample_utterances": self.get_sample_utterances(intent)
                }
            )

        return intent_info

    def get_playbook_steps(self, instruction: types.Playbook.Instruction):
        """Extract the playbook plain text steps."""
        all_steps = []
        for text in instruction.steps:
            all_steps.append(text.text)

        return all_steps

    def trim_agent_data(self, agent: Any):
        """Select only the relevant info from the agent proto."""
        return {
            "name": agent.display_name,
            "supported_languages": agent.supported_language_codes,
            "time_zone": agent.time_zone,
        }

    def trim_playbook_data(self, playbooks: Any):
        """Select only the relevant info from the playbook protos."""
        playbook_info = {}
        i = 0
        for playbook in playbooks:
            playbook_info[f"agent_{i}"] = {
                "name": playbook.display_name,
                "goal": playbook.goal,
                "instructions": self.get_playbook_steps(playbook.instruction)
            }
            i += 1

        return playbook_info

    def get_agent_tasks(self) -> Dict[str, Any]:
        """Extract App/Agent details and determine Agent's task list."""
        task_msg = "*** AUTO-GENERATING AGENT TASK LIST ***"
        logging.info(task_msg)

        agent = self.agents.get_agent(self.agent_id)
        agent = self.trim_agent_data(agent)

        playbooks = self.playbooks.list_playbooks(self.agent_id)
        tools = self.tools.list_tools(self.agent_id)
        tools = self.trim_agent_tools(playbooks, tools)

        # Order matters so that Tool trim can happen before playbook trim
        playbooks = self.trim_playbook_data(playbooks)
        intent_info = self.get_intent_info()
        flow_page_info = self.flows.get_flow_page_map(self.agent_id)

        prompt = Prompts.task_main.replace("{AGENT}", str(agent))
        prompt = prompt.replace("{PLAYBOOKS}", str(playbooks))
        prompt = prompt.replace("{TOOLS}", str(tools))
        prompt = prompt.replace("{INTENTS}", str(intent_info))
        prompt = prompt.replace("{FLOWS_AND_PAGES}", str(flow_page_info))

        if self.debug:
            logging.debug(prompt)

        res = self._call_generate_content(prompt)
        tasks_dict = json.loads(res.text)

        return tasks_dict

    def get_agent_tasks_from_user_input(
            self, tasks: Any) -> Dict[str, Any]:
        """Given an arbitrary user input, clean and format with LLM."""
        task_msg = "*** FORMATTING AGENT TASK LIST ***"
        logging.info(task_msg)

        prompt = Prompts.user_task_main.replace("{USER_DETAILS}", str(tasks))

        if self.debug:
            logging.debug(prompt)

        res = self._call_generate_content(prompt)
        tasks_dict = json.loads(res.text)

        return tasks_dict


class Prompts:
    # Main prompt template for task generation
    task_main: str = """**APP DETAILS**
{AGENT}

**AGENT DETAILS**
{PLAYBOOKS}
{FLOWS_AND_PAGES}
{INTENTS}

**TOOL DETAILS**
{TOOLS}
"""

    # System prompt for task generation
    task_system: str = """You are a senior virtual agent evaluator.
Your job is to determine the core tasks that a virtual agent can handle based on its provided details, playbook, and available tools.
Focus on the main functionalities that would be useful to an end user rather than individual steps or specific details within the process. Do not include generic functionalities such as "Intent Detection" or "Sentiment Analysis" unless those features provide a tangible outcome for the end user.  Explain each functionality clearly and concisely.
Return a concise list of the primary capabilities.

The information will be provided in a format like this:

**AGENT DETAILS**
<AGENT INFORMATION>

TOOL DETAILS:
<TOOL INFORMATION>

The resulting information should be returned in JSON format which will follow this schema:
```json
{
  "type": "object",
  "properties": {
    "tasks": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "name": {
            "type": "string"
          },
          "description": {
            "type": "string"
          }
        },
        "required": [
          "name",
          "description"
        ]
      }
    }
  },
  "required": [
    "tasks"
  ]
}
```
""" # noqa: E501

    user_task_main: str = """APP DETAILS PROVIDED BY USER:
{USER_DETAILS}
"""

class Schemas:
    task_schema = {
            "type": "object",
            "properties": {
                "tasks": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {
                                "type": "string"
                                },
                            "description": {
                                "type": "string"
                                }
                            },
                        "required": [
                            "name",
                            "description"
                            ]
                    }
                }
            },
            "required": [
                "tasks"
                ]
            }
