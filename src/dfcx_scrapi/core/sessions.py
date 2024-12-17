"""CX Session Resource functions."""

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
import uuid
from typing import Any, Dict, List

from google.cloud.dialogflowcx_v3beta1 import services, types
from google.protobuf.json_format import MessageToDict
from IPython.display import Markdown, display
from proto.marshal.collections import maps

from dfcx_scrapi.core.environments import Environments
from dfcx_scrapi.core.flows import Flows
from dfcx_scrapi.core.playbooks import Playbooks
from dfcx_scrapi.core.scrapi_base import ScrapiBase
from dfcx_scrapi.core.tools import Tools

# logging config
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


class Sessions(ScrapiBase):
    """Core Class for CX Session Resource functions."""

    def __init__(
        self,
        creds_path: str = None,
        creds_dict: Dict = None,
        creds=None,
        scope=False,
        agent_id: str = None,
        session_id: str = None,
        tools_map: Dict[str, str] = None,
        playbooks_map: Dict[str, str] = None,
        flows_map: Dict[str, str] = None
    ):
        super().__init__(
            creds_path=creds_path, creds_dict=creds_dict,
            creds=creds, scope=scope
        )

        self._session_id = session_id
        self.agent_id = agent_id
        self.tools_map = tools_map
        self.playbooks_map = playbooks_map
        self.flows_map = flows_map
        self._env_client = None
        self._tools_client = None
        self._playbooks_client = None
        self._flows_client = None

    @property
    def session_id(self):
        """Property for the session ID, parses the resource path if needed."""
        if self._session_id:
            self._parse_resource_path("session", self._session_id)

        return self._session_id

    @property
    def playbooks_client(self):
        """Property for Playbooks client."""
        if self._playbooks_client is None:
            if not self.agent_id:
                raise ValueError(
                    "agent_id must be set to use Playbooks Client.")
            self._playbooks_client = Playbooks(
                agent_id=self.agent_id, creds=self.creds
            )
        return self._playbooks_client

    @property
    def tools_client(self):
        """Property for Tools client."""
        if self._tools_client is None:
            self._tools_client = Tools(creds=self.creds)

        return self._tools_client

    @property
    def flows_client(self):
        """Property for Flows client."""
        if self._flows_client is None:
            self._flows_client = Flows(creds=self.creds)

        return self._flows_client

    @property
    def env_client(self):
        """Property for Environments client."""
        if self._env_client is None:
            self._env_client = Environments(creds=self.creds)

        return self._env_client

    @staticmethod
    def printmd(string):
        display(Markdown(string))

    @staticmethod
    def _build_query_input(text, language_code):
        """Build out the query_input object for the Query Request.

        Args:
          text, the text to use for the Detect Intent request.
          language_code, the language code to use for Detect Intent request.
        """
        text_input = types.session.TextInput(text=text)
        query_input = types.session.QueryInput(
            text=text_input, language_code=language_code
        )

        return query_input

    @staticmethod
    def build_intent_query_input(intent_id: str, language_code: str):
        """Build the query_input object for direct Intent request."""
        intent_input = types.session.IntentInput(intent=intent_id)
        query_input = types.session.QueryInput(
            intent=intent_input, language_code=language_code
        )

        return query_input

    @staticmethod
    def get_tool_action(tool_use: types.example.ToolUse) -> str:
        return tool_use.action

    def get_tool_params(self, params: maps.MapComposite):
        "Handle various types of param values from Tool input/outputs."
        param_map = {}
        if isinstance(params, maps.MapComposite):
            param_map = self.recurse_proto_marshal_to_dict(params)

        # Clean up resulting param map. This is because I/O params from Agent
        # Builder proto will have a blank top level key, but the main value
        # info is what is important for return to the user in this tool.
        empty_top_key = param_map.get("", None)
        if len(param_map.keys()) == 1 and empty_top_key:
            param_map = param_map[""]

        return param_map

    def get_playbook_name(self, playbook_id: str):
        agent_id = self.parse_agent_id(playbook_id)
        if not self.playbooks_map:
            self.playbooks_map = self.playbooks_client.get_playbooks_map(
                agent_id)

        return self.playbooks_map[playbook_id]

    def get_tool_name(self, tool_use: types.example.ToolUse) -> str:
        agent_id = self.parse_agent_id(tool_use.tool)
        if not self.tools_map:
            self.tools_map = self.tools_client.get_tools_map(agent_id)

        return self.tools_map[tool_use.tool]

    def get_flow_name(self, flow_id: str):
        agent_id = self.parse_agent_id(flow_id)
        if not self.flows_map:
            self.flows_map = self.flows_client.get_flows_map(agent_id)

        return self.flows_map[flow_id]

    def collect_tool_responses(
        self, res: types.session.QueryResult
    ) -> List[Dict[str, str]]:
        """Gather all the tool responses into a list of dicts."""
        tool_responses = []
        for action in res.generative_info.action_tracing_info.actions:
            if action.tool_use:
                tool_responses.append(
                    {
                        "tool_name": self.get_tool_name(action.tool_use),
                        "tool_action": self.get_tool_action(action.tool_use),
                        "input_params": self.get_tool_params(
                            action.tool_use.input_action_parameters),
                        "output_params": self.get_tool_params(
                            action.tool_use.output_action_parameters),
                    }
                )

        return tool_responses

    def collect_playbook_responses(
        self, res: types.session.QueryResult
    ) -> List[Dict[str, str]]:
        """Gather all the playbook responses into a list of dicts."""
        playbook_responses = []
        for action in res.generative_info.action_tracing_info.actions:
            if action.playbook_invocation:
                playbook_responses.append(
                    {
                        "playbook_name": self.get_playbook_name(
                            action.playbook_invocation.playbook
                        )
                    }
                )
            # If no playbook invocation was found try to return the current
            # Playbook
            elif len(res.generative_info.current_playbooks) > 0:
                playbook_responses.append(
                    {
                        "playbook_name": self.get_playbook_name(
                            res.generative_info.current_playbooks[-1]
                            )
                    }
                )

        return playbook_responses

    def collect_flow_responses(
        self, res: types.session.QueryResult
    ) -> List[Dict[str, str]]:
        """Gather all the flow repsonses into a list of dicts."""
        flow_responses = []
        for action in res.generative_info.action_tracing_info.actions:
            if action.flow_invocation:
                flow_responses.append(
                    {
                        "flow_name": self.get_flow_name(
                            action.flow_invocation.flow
                        )
                    }
                )

        return flow_responses

    def build_session_id(
        self, agent_id: str = None, overwrite: bool = True,
        environment_name: str = None
    ) -> str:
        """Creates a valid UUID-4 Session ID to use with other methods.

        Args:
          agent_id: the Agent ID of the CX Agent.
          overwrite (Optional), if a session_id already exists, this will
            overwrite the existing Session ID parameter. Defaults to True.
          environment_name: (Optional) the human readable Environment name to
            use when building the session ID. If this is not provided, DRAFT is
            assumed.
        """

        # Parse and validate the incoming agent_id
        _ = self._parse_resource_path("agent", agent_id)


        if environment_name:
            env = self.env_client.get_environment_by_display_name(
                environment_name, agent_id
            )
            if not env:
                raise ValueError(f"Environment `{environment_name}` does not"
                                 " exist.")
            session_id = f"{env.name}/sessions/{uuid.uuid4()}"

        else:
            session_id = f"{agent_id}/sessions/{uuid.uuid4()}"

        if overwrite:
            self._session_id = session_id

        return session_id

    def detect_intent(
        self,
        agent_id,
        session_id,
        text: str = None,
        language_code: str = "en",
        parameters: Dict[str, Any] = None,
        end_user_metadata: Dict[str, Any] = None,
        populate_data_store_connection_signals: bool = False,
        intent_id: str = None,
        timezone: str = None
    ):
        """Returns the result of detect intent with texts as inputs.

        Using the same `session_id` between requests allows continuation
        of the conversation.

        Args:
          agent_id: the Agent ID of the CX Agent to have the conversation with.
          session_id: an RFC 4122 formatted UUID to be used as the unique ID
            for the duration of the conversation session. When using Python
            uuid library, uuid.uuid4() is preferred.
          text: (Optional) the user utterance to run intent detection on
          language_code: (Optional) corresponds to the language code to use with
            query inputs to the agent.
          parameters: (Optional) Dict of CX Session Parameters to set in the
            conversation. Typically this is set before a conversation starts.
          end_user_metadata: (Optional) Dict of CX Session endUserMetadata to
            set in the conversation.
          populate_data_store_connection_signals: If set to true and data
            stores are involved in serving the request then query result will
            be populated with data_store_connection_signals field which
            contains data that can help evaluations.
          intent_id: fully qualified Intent ID path to pass in for query
            input instead of text. This allows for the direct triggering of a
            specific Intent, and will bypass the NLU engine.
          timezone: (Optional) IANA Timezone database code to pass in with query
            input   which can be used by the agent runtime. For example, when
            capturing datetime via system functions, they can be modified to
            user the provied timezone vs. the default agent timezone.
            Refs: https://www.iana.org/time-zones

        Returns:
          The CX query result from intent detection
        """
        client_options = self._set_region(agent_id)
        session_client = services.sessions.SessionsClient(
            client_options=client_options, credentials=self.creds
        )

        res = self._parse_resource_path("session", str(session_id), False)
        if not res:
            raise ValueError(
                "Session ID must be provided in the following format: "
                "`projects/<Project ID>/locations/<Location ID>/agents/"
                "<Agent ID>/sessions/<Session ID>`.\n\n"
                "Utilize `build_session_id` to create a new Session ID."
            )

        if intent_id:
            query_input = self.build_intent_query_input(
                intent_id, language_code)
        else:
            query_input = self._build_query_input(text, language_code)

        request = types.session.DetectIntentRequest()
        request.session = session_id
        request.query_input = query_input

        query_param_mapping = {}

        if parameters:
            query_param_mapping["parameters"] = parameters

        if end_user_metadata:
            query_param_mapping["end_user_metadata"] = end_user_metadata

        if populate_data_store_connection_signals:
            query_param_mapping[
                "populate_data_store_connection_signals"
            ] = populate_data_store_connection_signals

        if timezone:
            query_param_mapping["time_zone"] = timezone

        if query_param_mapping:
            query_params = types.session.QueryParameters(query_param_mapping)
            request.query_params = query_params

        response = session_client.detect_intent(request=request)
        query_result = response.query_result

        return query_result

    def get_agent_answer(self, user_query: str) -> str:
        """Extract the answer/citation from a Vertex Conversation response."""

        session_id = self.build_session_id(self.agent_id)
        res = MessageToDict(
            self.detect_intent(  # pylint: disable=W0212
                self.agent_id, session_id, user_query
            )._pb
        )

        answer_text = res["responseMessages"][0]["text"]["text"][0]
        answer_link = (
            res["responseMessages"][1]["payload"]["richContent"][0][0][
                "actionLink"
            ]
            if len(res["responseMessages"]) > 1
            else ""
        )

        return f"{answer_text} ({answer_link})"

    def parse_result(self, res):

        tool_call_font = "<font color='dark red'>TOOL CALL:</font></b>"
        tool_res_font = "<font color='yellow'>TOOL RESULT:</font></b>"
        query_font = "<font color='green'><b> USER QUERY:</font></b>"
        response_font = "<font color='green'><b>AGENT RESPONSE:</font></b>"

        self.printmd(f"{query_font} {res.text}")

        for action in res.generative_info.action_tracing_info.actions:

            if "tool_use" in action:
                tool_name = action.tool_use.action
                input_params = {}
                output_params = {}

                input_param = action.tool_use.input_action_parameters
                output_param = action.tool_use.output_action_parameters

                if isinstance(input_param, maps.MapComposite):
                    processed_input_params = self.recurse_proto_marshal_to_dict(
                        input_param
                    )
                    input_keys = list(processed_input_params.keys())
                    first_key = input_keys[0] if input_keys else None
                    input_params = processed_input_params.get(first_key, {})

                if isinstance(output_param, maps.MapComposite):
                    processed_output_params = (
                        self.recurse_proto_marshal_to_dict(output_param)
                    )
                    output_keys = list(processed_output_params.keys())
                    first_key = output_keys[0] if output_keys else None

                    output_params = processed_output_params.get(first_key, {})

                self.printmd(f"{tool_call_font} {tool_name} -> {input_params}")
                self.printmd(f"{tool_res_font} {output_params}")

            elif "agent_utterance" in action:
                self.printmd(f"{response_font} {action.agent_utterance.text}")
