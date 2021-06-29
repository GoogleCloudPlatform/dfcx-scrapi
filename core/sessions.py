# Copyright 2021 Google LLC. This software is provided as-is, without warranty
# or representation for any use or purpose. Your use of it is subject to your
# agreement with Google.

import logging
import requests
import google.cloud.dialogflowcx_v3beta1.services as services
import google.cloud.dialogflowcx_v3beta1.types as types
from google.oauth2 import service_account
from google.auth.transport.requests import Request
from google.protobuf import field_mask_pb2

from dfcx_sapi.core.sapi_base import SapiBase
from typing import Dict, List

# logging config
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


class Sessions(SapiBase):
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

    # SESSION FX
    def run_conversation(
        self,
        agent_id,
        session_id,
        conversation,
        parameters=None,
        response_text=False,
    ):
        """Tests a full conversation with the bot.

        Using the same `session_id` between requests allows continuation
        of the conversation."""
        client_options = self._set_region(agent_id)
        session_client = services.sessions.SessionsClient(
            client_options=client_options
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
            qr = response.query_result

            print("=" * 20)
            print("Query text: {}".format(qr.text))
            if "intent" in qr:
                print("Triggered Intent: {}".format(qr.intent.display_name))

            if "intent_detection_confidence" in qr:
                print(
                    "Intent Confidence {}".format(
                        qr.intent_detection_confidence
                    )
                )

            print("Response Page: {}".format(qr.current_page.display_name))

            for param in qr.parameters:
                if param == "statusMessage":
                    print("Status Message: {}".format(qr.parameters[param]))

            if response_text:
                print(
                    "Response Text: {}\n".format(
                        " ".join(
                            [
                                " ".join(response_message.text.text)
                                for response_message in qr.response_messages
                            ]
                        )
                    )
                )

    def detect_intent(
        self, agent_id, session_id, text, parameters=None, response_text=False
    ):
        """Returns the result of detect intent with texts as inputs.

        Using the same `session_id` between requests allows continuation
        of the conversation."""
        client_options = self._set_region(agent_id)
        session_client = services.sessions.SessionsClient(
            client_options=client_options
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

        text_input = types.session.TextInput(text=text)
        query_input = types.session.QueryInput(
            text=text_input, language_code="en"
        )
        request = types.session.DetectIntentRequest(
            session=session_path, query_input=query_input
        )
        response = session_client.detect_intent(request=request)
        qr = response.query_result

        return qr

    def preset_parameters(self, agent_id, session_id, parameters):
        client_options = self._set_region(agent_id)
        session_client = services.sessions.SessionsClient(
            client_options=client_options
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
