"""CX Session Resource functions."""

# Copyright 2023 Google LLC
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
from typing import Dict, List
from google.cloud.dialogflowcx_v3beta1 import services
from google.cloud.dialogflowcx_v3beta1 import types
from google.protobuf.json_format import MessageToDict

from dfcx_scrapi.core import scrapi_base

# logging config
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

class Sessions(scrapi_base.ScrapiBase):
    """Core Class for CX Session Resource functions."""

    def __init__(
        self,
        creds_path: str = None,
        creds_dict: Dict = None,
        scope=False,
        agent_id: str = None,
        session_id: str = None
    ):
        super().__init__(
            creds_path=creds_path, creds_dict=creds_dict, scope=scope
        )

        self.session_id = session_id
        self.agent_id = agent_id

    @property
    def session_id(self):
        return self._session_id

    @session_id.setter
    def session_id(self, value):
        if value:
            self._parse_resource_path("session", value)

        self._session_id = value

    @staticmethod
    def _build_query_input(text, language_code):
        """Build out the query_input object for the Query Request.

        Args:
          text, the text to use for the Detect Intent request.
          language_code, the language code to use for Detect Intent request.
          """
        text_input = types.session.TextInput(text=text)
        query_input = types.session.QueryInput(
            text=text_input, language_code=language_code)

        return query_input

    def build_session_id(
        self, agent_id:str = None, overwrite:bool = True) -> str:
        """Creates a valid UUID-4 Session ID to use with other methods.

        Args:
          overwrite (Optional), if a session_id already exists, this will
            overwrite the existing Session ID parameter. Defaults to True.
        """

        agent_parts = self._parse_resource_path("agent", agent_id)
        session_id = f"projects/{agent_parts['project']}/"\
            f"locations/{agent_parts['location']}/agents/"\
            f"{agent_parts['agent']}/sessions/{uuid.uuid4()}"

        if overwrite:
            self.session_id = session_id

        return session_id

    def run_conversation(
        self,
        agent_id: str = None,
        session_id: str = None,
        conversation: List[str] = None,
        parameters=None,
        response_text=False,
    ):
        """Tests a full conversation with the specified CX Agent.

        Args:
          agent_id: the Agent ID of the CX Agent to have the conversation with.
          session_id: an RFC 4122 formatted UUID to be used as the unique ID
            for the duration of the conversation session. When using Python
            uuid library, uuid.uuid4() is preferred.
          conversation: a List of Strings that represent the USER utterances
            for the given conversation, in the order they would happen
            chronologically in the conversation.
            Ex:
              ['I want to check my bill', 'yes', 'no that is all', 'thanks!']
          parameters: (Optional) Dict of CX Session Parameters to set in the
            conversation. Typically this is set before a conversation starts.
          response_text: Will provide the Agent Response text if set to True.
            Default value is False.

        Returns:
          None, the conversation Request/Response is printed to console.
        """
        if not session_id:
            session_id = self.session_id

        client_options = self._set_region(agent_id)
        session_client = services.sessions.SessionsClient(
            client_options=client_options, credentials=self.creds
        )
        session_path = f"{agent_id}/sessions/{session_id}"

        if parameters:
            query_params = types.session.QueryParameters(parameters=parameters)
            text_input = types.session.TextInput(text="")
            query_input = types.session.QueryInput(
                text=text_input, language_code="en"
            )
            request = types.session.DetectIntentRequest(
                session=session_path,
                query_params=query_params,
                query_input=query_input,
            )

            response = session_client.detect_intent(request=request)

        for text in conversation:
            text_input = types.session.TextInput(text=text)
            query_input = types.session.QueryInput(
                text=text_input, language_code="en"
            )
            request = types.session.DetectIntentRequest(
                session=session_path, query_input=query_input
            )
            response = session_client.detect_intent(request=request)
            query_result = response.query_result

            print("=" * 20)
            print(f"Query text: {query_result.text}")
            if "intent" in query_result:
                print(
                    f"Triggered Intent: {query_result.intent.display_name}"
                )

            if "intent_detection_confidence" in query_result:
                print(
                    f"Intent Confidence: \
                        f{query_result.intent_detection_confidence}"
                )

            print(
                f"Response Page: {query_result.current_page.display_name}"
            )

            for param in query_result.parameters:
                if param == "statusMessage":
                    print(
                        f"Status Message: {query_result.parameters[param]}"
                    )

            if response_text:
                concat_messages = " ".join(
                    [
                        " ".join(response_message.text.text)
                        for response_message in query_result.response_messages
                            ]
                        )
                print(f"Response Text: {concat_messages}\n")


    def detect_intent(
        self,
        agent_id,
        session_id,
        text,
        language_code="en",
        parameters=None):
        """Returns the result of detect intent with texts as inputs.

        Using the same `session_id` between requests allows continuation
        of the conversation.

        Args:
          agent_id: the Agent ID of the CX Agent to have the conversation with.
          session_id: an RFC 4122 formatted UUID to be used as the unique ID
            for the duration of the conversation session. When using Python
            uuid library, uuid.uuid4() is preferred.
          text: the user utterance to run intent detection on
          parameters: (Optional) Dict of CX Session Parameters to set in the
            conversation. Typically this is set before a conversation starts.

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
                "`projects/<Project ID>/locations/<Location ID>/agents/"\
                "<Agent ID>/sessions/<Session ID>`.\n\n"\
                "Utilize `build_session_id` to create a new Session ID.")

        logging.info(f"Starting Session ID {session_id}")

        if parameters:
            query_params = types.session.QueryParameters(parameters=parameters)

            query_input = self._build_query_input(text, language_code)

            request = types.session.DetectIntentRequest()
            request.session = session_id
            request.query_input = query_input
            request.query_params = query_params

            response = session_client.detect_intent(request=request)

        else:
            query_input = self._build_query_input(text, language_code)

            request = types.session.DetectIntentRequest()
            request.session = session_id
            request.query_input = query_input

        response = session_client.detect_intent(request)
        query_result = response.query_result

        return query_result

    def preset_parameters(
        self, agent_id: str = None, session_id: str = None, parameters=None
    ):
        """Used to set session parameters before a conversation starts.

        Args:
          agent_id: the Agent ID of the CX Agent to have the conversation with.
          session_id: an RFC 4122 formatted UUID to be used as the unique ID
            for the duration of the conversation session. When using Python
            uuid library, uuid.uuid4() is preferred.
          parameters: Dict of CX Session Parameters to set in the
            conversation. Typically this is set before a conversation starts.

        Returns:
          The CX query result from intent detection run with no text input
        """
        client_options = self._set_region(agent_id)
        session_client = services.sessions.SessionsClient(
            client_options=client_options, credentials=self.creds
        )
        session_path = f"{agent_id}/sessions/{session_id}"

        query_params = types.session.QueryParameters(parameters=parameters)
        text_input = types.session.TextInput(text=None)
        query_input = types.session.QueryInput(
            text=text_input, language_code="en"
        )
        request = types.session.DetectIntentRequest(
            session=session_path,
            query_params=query_params,
            query_input=query_input,
        )

        response = session_client.detect_intent(request=request)

        return response

    def get_agent_answer(self, user_query: str) -> str:
        """Extract the answer/citation from a Vertex Conversation response."""

        session_id = self.build_session_id(self.agent_id)
        res = MessageToDict(self.detect_intent( # pylint: disable=W0212
            self.agent_id, session_id, user_query)._pb)

        answer_text = res["responseMessages"][0]["text"]["text"][0]
        answer_link = res["responseMessages"][1]["payload"][
            "richContent"][0][0]["actionLink"] if len(
                res["responseMessages"]) > 1 else ""

        return f"{answer_text} ({answer_link})"
