"""CX Session Resource functions."""

# Copyright 2021 Google LLC
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
import google.cloud.dialogflowcx_v3beta1.services as services
import google.cloud.dialogflowcx_v3beta1.types as types

from dfcx_scrapi.core.scrapi_base import ScrapiBase

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
        scope=False,
        session_id: str = None,
    ):
        super().__init__(
            creds_path=creds_path, creds_dict=creds_dict, scope=scope
        )

        if session_id:
            self.session_id = session_id

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
          agent_id, the Agent ID of the CX Agent to have the conversation with.
          session_id, an RFC 4122 formatted UUID to be used as the unique ID
            for the duration of the conversation session. When using Python
            uuid library, uuid.uuid4() is preferred.
          conversation, a List of Strings that represent the USER utterances
            for the given conversation, in the order they would happen
            chronologically in the conversation.
            Ex:
              ['I want to check my bill', 'yes', 'no that is all', 'thanks!']
          parameters, (Optional) Dict of CX Session Parameters to set in the
            conversation. Typically this is set before a conversation starts.
          response_text, Will provide the Agent Response text if set to True.
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
        session_path = "{}/sessions/{}".format(agent_id, session_id)

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
            print("Query text: {}".format(query_result.text))
            if "intent" in query_result:
                print(
                    "Triggered Intent: {}".format(
                        query_result.intent.display_name
                    )
                )

            if "intent_detection_confidence" in query_result:
                print(
                    "Intent Confidence {}".format(
                        query_result.intent_detection_confidence
                    )
                )

            print(
                "Response Page: {}".format(
                    query_result.current_page.display_name
                )
            )

            for param in query_result.parameters:
                if param == "statusMessage":
                    print(
                        "Status Message: {}".format(
                            query_result.parameters[param]
                        )
                    )

            if response_text:
                print("Response Text: {}\n".format(" ".join(
                    [
                        " ".join(response_message.text.text)
                        for response_message in query_result.response_messages
                            ]
                        )
                    )
                )

    def detect_intent(self, agent_id, session_id, text, parameters=None):
        """Returns the result of detect intent with texts as inputs.

        Using the same `session_id` between requests allows continuation
        of the conversation."""
        client_options = self._set_region(agent_id)
        session_client = services.sessions.SessionsClient(
            client_options=client_options, credentials=self.creds
        )

        session_path = "{}/sessions/{}".format(agent_id, session_id)

        if parameters:
            query_params = types.session.QueryParameters(parameters=parameters)
            text_input = types.session.TextInput(text=text)
            query_input = types.session.QueryInput(
                text=text_input, language_code="en"
            )
            request = types.session.DetectIntentRequest(
                session=session_path,
                query_params=query_params,
                query_input=query_input,
            )

            response = session_client.detect_intent(request=request)

        text_input = types.session.TextInput(text=text)
        query_input = types.session.QueryInput(
            text=text_input, language_code="en"
        )
        request = types.session.DetectIntentRequest(
            session=session_path, query_input=query_input
        )
        response = session_client.detect_intent(request=request)
        query_result = response.query_result

        return query_result

    def preset_parameters(
        self, agent_id: str = None, session_id: str = None, parameters=None
    ):
        """Used to set session parameters before a conversation starts.

        agent_id, the Agent ID of the CX Agent to have the conversation with.
        session_id, an RFC 4122 formatted UUID to be used as the unique ID
            for the duration of the conversation session. When using Python
            uuid library, uuid.uuid4() is preferred.
        """
        client_options = self._set_region(agent_id)
        session_client = services.sessions.SessionsClient(
            client_options=client_options, credentials=self.creds
        )
        session_path = "{}/sessions/{}".format(agent_id, session_id)

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
