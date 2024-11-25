"""Playbooks class for Generative Agents."""

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

import logging
from typing import Dict, List

from google.cloud.dialogflowcx_v3beta1 import services, types
from google.protobuf import field_mask_pb2

from dfcx_scrapi.core import scrapi_base

# logging config
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


class Playbooks(scrapi_base.ScrapiBase):
    """Core Class for CX Playbooks Resource functions."""

    def __init__(
        self,
        agent_id: str,
        creds_path: str = None,
        creds_dict: Dict = None,
        creds=None,
        scope=False,
        playbooks_map: Dict[str, str] = None
    ):
        super().__init__(
            creds_path=creds_path,
            creds_dict=creds_dict,
            creds=creds,
            scope=scope,
        )

        self.agent_id = agent_id

        client_options = self._set_region(self.agent_id)
        self.playbooks_client = services.playbooks.PlaybooksClient(
            credentials=self.creds, client_options=client_options
        )
        self.agents_client = services.agents.AgentsClient(
            credentials=self.creds, client_options=client_options
        )

        self.playbooks_map = playbooks_map

    @staticmethod
    def build_instructions_from_list(
        instructions: List[str]) -> List[types.Playbook.Step]:
        """Helper method to create the playbook instruction set protos."""
        final_instructions = types.Playbook.Instruction(steps=[])

        for instruction in instructions:
            final_instructions.steps.append(
                types.Playbook.Step(text=instruction)
                )

        return final_instructions

    @staticmethod
    def clean_line(step_text: str):
        """Helper method to clean the current line that is being parsed."""
        step_text = step_text.strip() # clear any whitespace
        step_text = step_text.strip("-") # clear `-` if exists
        step_text = step_text.strip() # clear remaining whitespace if exists

        return step_text

    def parse_steps(
            self, lines: List[str], start_index: int, indent_level: int):
        """Recursively parse instructions and build Playbook.Step objects.

        Args:
            lines: The list of instruction lines.
            start_index: The index to start parsing from.
            indent_level: The current indentation level.

        Returns:
            A tuple containing:
                - A list of parsed Playbook.Step objects at the current level.
                - The index of the next line to parse.
        """
        steps: List[types.Playbook.Step] = []
        i = start_index
        while i < len(lines):
            line = lines[i]
            current_indent = len(line) - len(line.lstrip())
            if current_indent == indent_level:
                step_text = self.clean_line(line)
                step = types.Playbook.Step(text=step_text)
                steps.append(step)
                i += 1
            elif current_indent > indent_level:
                # Recursively parse child steps
                child_steps, next_index = self.parse_steps(
                    lines, i, current_indent)
                steps[-1].steps.extend(child_steps)
                i = next_index
            else:
                # Reached a line with lower indentation
                # stop parsing at this level
                break

        return steps, i

    def build_instructions_from_string(
            self,
            instructions: str) -> types.Playbook.Instruction:

        instruction_obj = types.Playbook.Instruction()
        lines = instructions.strip().splitlines()
        parsed_steps, _ = self.parse_steps(lines, 0, 0)
        instruction_obj.steps.extend(parsed_steps)

        return instruction_obj

    def process_playbook_kwargs(
            self,
            playbook: types.Playbook,
            **kwargs):
        """Process incoming kwargs and create the proper update mask."""
        paths = []
        for key, value in kwargs.items():
            if key in ["instruction", "instructions"]:
                if isinstance(value, list):
                    instructions = self.build_instructions_from_list(value)
                    setattr(playbook, "instruction", instructions)
                elif isinstance(value, str):
                    instructions = self.build_instructions_from_string(value)
                    setattr(playbook, "instruction", instructions)
                elif isinstance(value, types.Playbook.Instruction):
                    setattr(playbook, "instruction", value)
                paths.append("instruction")
            else:
                setattr(playbook, key, value)
                paths.append(key)

        # paths = kwargs.keys()
        mask = field_mask_pb2.FieldMask(paths=paths)

        return playbook, mask

    def set_default_playbook(self, playbook_id: str):
        """Sets the default Playbook for the Agent."""
        # Get the current Agent object and assign the new start_playbook ID
        agent = self.agents_client.get_agent(
            request=types.GetAgentRequest(
                name=self.agent_id
            )
        )
        agent.start_playbook = playbook_id

        # set the field mask for updating and update
        paths = {"start_playbook": playbook_id}.keys()
        mask = field_mask_pb2.FieldMask(paths=paths)

        response = self.agents_client.update_agent(
            agent=agent, update_mask=mask)

        return response

    def get_playbooks_map(self, agent_id: str, reverse=False):
        """Exports Agent Playbook Names and UUIDs into a user friendly dict.

        Args:
          agent_id: the formatted CX Agent ID to use
          reverse: (Optional) Boolean flag to swap key:value -> value:key

        Returns:
          Dictionary containing Playbook UUIDs as keys and display names as
          values. If Optional reverse=True, the output will return playbook
          name:ID mapping instead of ID:playbook_name
        """
        if reverse:
            playbooks_dict = {
                playbook.display_name: playbook.name
                for playbook in self.list_playbooks(agent_id)
            }

        else:
            playbooks_dict = {
                playbook.name: playbook.display_name
                for playbook in self.list_playbooks(agent_id)
            }

        return playbooks_dict

    @scrapi_base.api_call_counter_decorator
    def list_playbooks(self, agent_id: str = None):
        """Get a List of all Playbooks in the current Agent.

        Args:
          agent_id: CX Agent ID string in the proper format
            projects/<PROJECT ID>/locations/<LOCATION ID>/agents/<AGENT ID>

        Returns:
          List of Playbook objects
        """
        if not agent_id:
            agent_id = self.agent_id

        request = types.playbook.ListPlaybooksRequest()
        request.parent = agent_id

        response = self.playbooks_client.list_playbooks(request)

        playbooks = []
        for page in response.pages:
            for playbook in page.playbooks:
                playbooks.append(playbook)
        return playbooks

    @scrapi_base.api_call_counter_decorator
    def get_playbook(self, playbook_id: str = None):
        """Get a single CX Playbook object.

        Args:
          playbook_id: CX Playbook ID in the proper format

        Returns:
          A single CX Playbook object
        """
        if not playbook_id:
            playbook_id = self.playbook_id

        response = self.playbooks_client.get_playbook(name=playbook_id)

        return response

    @scrapi_base.api_call_counter_decorator
    def create_playbook(
        self,
        agent_id: str,
        obj: types.Playbook = None,
        **kwargs,
    ):
        """Create a Dialogflow CX Playbook with given display name.

        If the user provides an existing Playbook object, a new CX Playbook
        will be created based on this object and any other input/kwargs will be
        discarded.

        Args:
          agent_id: DFCX Agent id where the Playbook will be created
          obj: (Optional) Playbook object to create in proto format

        Returns:
          The newly created CX Playbook resource object.
        """
        request = types.playbook.CreatePlaybookRequest()
        request.parent = agent_id

        if obj:
            playbook = obj
            playbook.name = ""
        else:
            playbook = types.Playbook()

            # set optional args as playbook attributes
            playbook, _ = self.process_playbook_kwargs(playbook, **kwargs)

        request.playbook = playbook
        response = self.playbooks_client.create_playbook(request)

        return response

    @scrapi_base.api_call_counter_decorator
    def update_playbook(
        self,
        playbook_id: str,
        obj: types.Playbook = None,
        **kwargs
    ) -> types.Playbook:
        """Update a single specific CX Playbook object.

        Args:
          playbook_id: CX Playbook ID in the proper format
          obj: (Optional) a single CX Playbook object of types.Playbook
          overwrite_instructions: if True this will overwrite all instructions
            for the specific playbook. By default this is set to False and will
            append new instructions.

        Returns:
          A copy of the updated Playbook object
        """

        if obj:
            playbook = obj
            playbook.name = playbook_id
        else:
            playbook = self.get_playbook(playbook_id)

        # set optional args as playbook attributes
        playbook, mask = self.process_playbook_kwargs(playbook, **kwargs)

        response = self.playbooks_client.update_playbook(
            playbook=playbook, update_mask=mask)

        return response

    @scrapi_base.api_call_counter_decorator
    def delete_playbook(
        self, playbook_id: str = None, obj: types.Playbook = None):
        """Deletes a single CX Playbook Object resource.

        Args:
          playbook_id: The formatted CX Playbook ID to delete.
          obj: (Optional) a CX Playbook object of types.Playbook
        """
        if not playbook_id:
            playbook_id = self.playbook_id

        if obj:
            playbook_id = obj.name

        self.playbooks_client.delete_playbook(name=playbook_id)

    @scrapi_base.api_call_counter_decorator
    def create_playbook_version(
        self, playbook_id: str, description: str = None
        ) -> types.PlaybookVersion:
        """Creates a Playbook Version of the specific Playbook ID."""
        playbook_version = types.PlaybookVersion()
        playbook_version.name = playbook_id
        playbook_version.description = description

        request = types.CreatePlaybookVersionRequest()
        request.parent = playbook_id
        request.playbook_version = playbook_version

        response = self.playbooks_client.create_playbook_version(request)

        return response
