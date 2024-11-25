"""Examples class for Generative Agents."""

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

from typing import Any, Dict, List

from google.cloud.dialogflowcx_v3beta1 import services, types
from google.protobuf import field_mask_pb2

from dfcx_scrapi.core import playbooks, scrapi_base, tools


class Examples(scrapi_base.ScrapiBase):
    """Core Class for CX Examples Resource functions."""

    def __init__(
        self,
        agent_id: str,
        creds_path: str = None,
        creds_dict: Dict = None,
        creds=None,
        scope=False,
        example_id: str = None,
        playbook_id: str = None,
        playbooks_map: Dict[str, str] = None,
        tools_map: Dict[str, str] = None
    ):
        super().__init__(
            creds_path=creds_path,
            creds_dict=creds_dict,
            creds=creds,
            scope=scope,
        )

        self.agent_id = agent_id

        client_options = self._set_region(self.agent_id)
        self.examples_client = services.examples.ExamplesClient(
            credentials=self.creds, client_options=client_options
        )
        self.playbooks_client = playbooks.Playbooks(agent_id=self.agent_id)
        self.tools_client = tools.Tools(agent_id=self.agent_id)

        self.playbook_id = playbook_id
        self.example_id = example_id
        self.playbooks_map = playbooks_map
        self.tools_map = tools_map

    @staticmethod
    def get_playbook_state(playbook_state: str):
        """Simple converter for enum values on playbook state."""
        if playbook_state == "OK":
            return 1
        elif playbook_state == "CANCELLED":
            return 2
        elif playbook_state == "FAILED":
            return 3
        elif playbook_state == "ESCALATED":
            return 4
        elif playbook_state == "PENDING":
            return 5
        else:
            return 0

    def build_example_from_action_list(
        self,
        display_name: str,
        action_list: List[Dict],
        description: str = None
        ) -> types.Example:
        """Builds an Example from a list of action dictionaries."""

        example = types.Example()
        example.display_name = display_name
        example.description = description

        for action_dict in action_list:
            action_type, action_data = next(iter(action_dict.items()))

            if action_type == "user_utterance":
                example.actions.append(
                    types.Action(
                        user_utterance=types.UserUtterance(text=action_data)))

            elif action_type == "agent_utterance":
                example.actions.append(
                    types.Action(
                        agent_utterance=types.AgentUtterance(text=action_data)))

            elif action_type == "tool_use":
                if not self.tools_map:
                    self.tools_map = self.tools_client.get_tools_map(
                        self.agent_id, reverse=True
                    )

                tool_name = action_data.get("tool_name")

                action = types.Action()
                tool_use = types.ToolUse()
                tool_use.tool = self.tools_map.get(tool_name)
                tool_use.action = action_data.get("action")
                tool_use.input_action_parameters = action_data.get(
                    "input_action_parameters", None)
                tool_use.output_action_parameters = action_data.get(
                    "output_action_parameters", None)

                action.tool_use = tool_use
                example.actions.append(action)

            elif action_type == "playbook_invocation":
                example.actions.append(
                    types.Action(
                        playbook_invocation=self.build_playbook_invocation(
                            action_data)))

        return example

    def build_playbook_invocation(
        self, action: Dict[str, Any]) -> types.PlaybookInvocation:
        """Helper method for constructing Playbook invocation."""
        if not self.playbooks_map:
            self.playbooks_map = self.playbooks_client.get_playbooks_map(
                self.agent_id, reverse=True
            )

        pb_inv = types.PlaybookInvocation()
        pb_inv.playbook = self.playbooks_map[action.get("playbook_name", None)]

        pb_input = types.PlaybookInput()
        pb_input.preceding_conversation_summary = action.get(
            "playbook_input_summary", None)
        input_params = action.get("playbook_input_parameters", None)
        if input_params:
            pb_input.action_parameters = input_params

        pb_output = types.PlaybookOutput()
        pb_output.execution_summary = action.get(
            "playbook_output_summary", None)
        output_params = action.get("playbook_output_parameters", None)
        if output_params:
            pb_output.action_parameters = output_params

        pb_state = types.OutputState(
            self.get_playbook_state(action.get("playbook_state", None)))

        pb_inv.playbook_input = pb_input
        pb_inv.playbook_output = pb_output
        pb_inv.playbook_state = pb_state

        return pb_inv

    def get_examples_map(self, playbook_id: str = None, reverse=False):
        """Exports Agent Example Names and UUIDs into a user friendly dict.

        Args:
          playbook_id: the formatted CX Agent Playbook ID to use
          reverse: (Optional) Boolean flag to swap key:value -> value:key

        Returns:
          Dict containing Example UUIDs as keys and display names as values
        """
        if not playbook_id:
            playbook_id = self.playbook_id

        if reverse:
            examples_dict = {
                example.display_name: example.name
                for example in self.list_examples(playbook_id)
            }

        else:
            examples_dict = {
                example.name: example.display_name
                for example in self.list_examples(playbook_id)
            }

        return examples_dict

    @scrapi_base.api_call_counter_decorator
    def list_examples(
        self,
        playbook_id: str = None,
        language_code: str = "en") -> List[types.Example]:
        """Get a List of all Examples in the specified Playbook.

        Args:
          playbook_id: the properly formatted Playbook ID string
          language_code: Specifies the language of the Examples listed.

        Returns:
          A List of CX Example objects for the specific Playbook ID
        """
        if not playbook_id:
            playbook_id = self.playbook_id

        request = types.example.ListExamplesRequest()
        request.parent = playbook_id
        request.language_code = language_code

        client_options = self._set_region(playbook_id)
        client = services.examples.ExamplesClient(
            credentials=self.creds, client_options=client_options
        )
        response = client.list_examples(request)

        cx_examples = []
        for page in response.pages:
            for cx_example in page.examples:
                cx_examples.append(cx_example)

        return cx_examples

    @scrapi_base.api_call_counter_decorator
    def get_example(self, example_id: str = None) -> types.Example:
        """Get a single CX Example object based on the provided Example ID.

        Args:
          example_id: a properly formatted CX Example ID

        Returns:
          A single CX Example Object
        """
        if not example_id:
            example_id = self.example_id

        client_options = self._set_region(example_id)
        client = services.examples.ExamplesClient(
            credentials=self.creds, client_options=client_options
        )

        response = client.get_example(name=example_id)

        return response

    @scrapi_base.api_call_counter_decorator
    def create_example(
        self,
        playbook_id: str = None,
        obj: types.Example = None,
        **kwargs
        ) -> types.Example:
        """Create a single CX Example object in the specified Playbook ID.

        Args:
          playbook_id: the CX Playbook ID where the Example will be created
          obj: (Optional) a CX Example object of types.Example

        Returns:
          A copy of the successful Example object that was created
        """
        if not playbook_id:
            playbook_id = self.playbook_id

        if obj:
            example = obj
            example.name = ""
        else:
            example = types.example.Example()

        for key, value in kwargs.items():
            setattr(example, key, value)

        client_options = self._set_region(playbook_id)
        client = services.examples.ExamplesClient(
            credentials=self.creds, client_options=client_options
        )

        response = client.create_example(parent=playbook_id, example=example)

        return response

    @scrapi_base.api_call_counter_decorator
    def update_example(
        self,
        example_id: str = None,
        obj: types.Example = None,
        **kwargs
        ) -> types.Example:
        """Update a single CX Example object.

        Args:
          example_id: the CX Example ID to update
          obj: (Optional) a CX Example object of types.Example

        Returns:
          A copy of the successful Example object that was created
        """
        if obj:
            example = obj
            example.name = example_id
        else:
            if not example_id:
                example_id = self.example_id
            example = self.get_example(example_id)

        for key, value in kwargs.items():
            setattr(example, key, value)
        paths = kwargs.keys()
        mask = field_mask_pb2.FieldMask(paths=paths)

        client_options = self._set_region(example_id)
        client = services.examples.ExamplesClient(
            credentials=self.creds, client_options=client_options
        )

        response = client.update_example(example=example, update_mask=mask)

        return response

    @scrapi_base.api_call_counter_decorator
    def delete_example(
        self, example_id: str = None,
        obj: types.Example = None):
        """Deletes the specified Example.

        Args:
          example_id: The formatted CX Example ID to delete.
          obj: (Optional) a CX Example object of types.Example
        """
        if not example_id:
            example_id = self.example_id

        if obj:
            example_id = obj.name

        client_options = self._set_region(example_id)
        client = services.examples.ExamplesClient(
            credentials=self.creds, client_options=client_options)
        client.delete_example(name=example_id)
