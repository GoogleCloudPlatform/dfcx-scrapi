import logging
import requests
import google.cloud.dialogflowcx_v3beta1.services as services
import google.cloud.dialogflowcx_v3beta1.types as types
from google.oauth2 import service_account
from google.auth.transport.requests import Request
from google.protobuf import field_mask_pb2

from typing import Dict, List

# logging config
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)-8s %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S')

SCOPES = ['https://www.googleapis.com/auth/cloud-platform',
          'https://www.googleapis.com/auth/dialogflow']


class Sessions:
    def __init__(self, creds_path: str, session_id: str = None):
        self.creds = service_account.Credentials.from_service_account_file(
            creds_path, scopes=SCOPES)
        self.creds.refresh(Request())  # used for REST API calls
        self.token = self.creds.token  # used for REST API calls
        self.session_id = session_id

    @staticmethod
    def _set_region(item_id):
        """different regions have different API endpoints

        Args:
            item_id: agent/flow/page - any type of long path id like
                `projects/<GCP PROJECT ID>/locations/<LOCATION ID>

        Returns:
            client_options: use when instantiating other library client objects
        """
        try:
            location = item_id.split('/')[3]
        except IndexError as err:
            logging.error('IndexError - path too short? %s', item_id)
            raise err

        if location != 'global':
            api_endpoint = '{}-dialogflow.googleapis.com:443'.format(location)
            client_options = {'api_endpoint': api_endpoint}
            return client_options

        else:
            return None  # explicit None return when not required

    # SESSION FX
    def run_conversation(
            self,
            agent_id,
            session_id,
            conversation,
            parameters=None,
            response_text=False):
        """Tests a full conversation with the bot.

        Using the same `session_id` between requests allows continuation
        of the conversation."""
        client_options = self._set_region(agent_id)
        session_client = services.sessions.SessionsClient(
            client_options=client_options)
        session_path = "{}/sessions/{}".format(agent_id, session_id)

        if parameters:
            query_params = types.session.QueryParameters(parameters=parameters)
            text_input = types.session.TextInput(text='')
            query_input = types.session.QueryInput(
                text=text_input, language_code='en')
            request = types.session.DetectIntentRequest(
                session=session_path, query_params=query_params, query_input=query_input)

            response = session_client.detect_intent(request=request)

        for text in conversation:
            text_input = types.session.TextInput(text=text)
            query_input = types.session.QueryInput(
                text=text_input, language_code='en')
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
                        qr.intent_detection_confidence))

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
            self,
            agent_id,
            session_id,
            text,
            parameters=None,
            response_text=False):
        """Returns the result of detect intent with texts as inputs.

        Using the same `session_id` between requests allows continuation
        of the conversation."""
        client_options = self._set_region(agent_id)
        session_client = services.sessions.SessionsClient(
            client_options=client_options)
        session_path = "{}/sessions/{}".format(agent_id, session_id)

        if parameters:
            query_params = types.session.QueryParameters(parameters=parameters)
            text_input = types.session.TextInput(text='')
            query_input = types.session.QueryInput(
                text=text_input, language_code='en')
            request = types.session.DetectIntentRequest(
                session=session_path, query_params=query_params, query_input=query_input)

            response = session_client.detect_intent(request=request)

        text_input = types.session.TextInput(text=text)
        query_input = types.session.QueryInput(
            text=text_input, language_code='en')
        request = types.session.DetectIntentRequest(
            session=session_path, query_input=query_input
        )
        response = session_client.detect_intent(request=request)
        qr = response.query_result

        return qr

    def preset_parameters(self, agent_id, session_id, parameters):
        client_options = self._set_region(agent_id)
        session_client = services.sessions.SessionsClient(
            client_options=client_options)
        session_path = "{}/sessions/{}".format(agent_id, session_id)

        query_params = types.session.QueryParameters(parameters=parameters)
        text_input = types.session.TextInput(text=None)
        query_input = types.session.QueryInput(
            text=text_input, language_code='en')
        request = types.session.DetectIntentRequest(session=session_path,
                                                    query_params=query_params,
                                                    query_input=query_input)

        response = session_client.detect_intent(request=request)

        return response
