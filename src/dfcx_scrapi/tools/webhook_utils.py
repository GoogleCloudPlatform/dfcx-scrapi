"""Util class for building DFCX webhook payloads."""

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
import string

# logging config
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)-8s %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S')

class WebhookUtils():
    """Utils class for quickly building DFCX webhook payloads."""

    @staticmethod
    def build_page_info(param_name, param_state):
        """Builds a Page Info object for Dialogflow CX.

        JSON format expected by Dialogflow CX as a Response payload.

        Args:
          param_name: The name of the Dialogflow CX parameter to update
          param_state: One of the following states [EMPTY, INVALID, FILLED]

        Returns:
          page_info: A JSON object in the appropriate Response format
        """
        page_info = {
            'formInfo': {
                'parameterInfo': [
                    {
                        'displayName': param_name,
                        'state': param_state
                    }
                ]
            }
        }

        return page_info

    @staticmethod
    def build_session_info(parameters):
        """Builds a Session Info object for Dialogflow CX Response.

        Provides the ability to perform CRUD functions for the DFCX Session
        parameters by building a JSON object to be included in the final build
        Response sent back to DFCX.

        Args:
          paramters: JSON formatted key:value pairs to be updated in the
            session params

        Returns:
          session_info: JSON object formatted for the DFCX Fulfillment Response
            Body

        Example Input: {'key1':'value1', 'key2':'value2'}
        """
        session_info = {'parameters': parameters}

        return session_info

    @staticmethod
    def build_response(response_text=None, page_info=None, session_info=None):
        """Builds a Response object for Dialogflow CX.

        Provides the JSON object structure expected by DFCX for the Response
        payload, including optional paload for pageInfo and sessionInfo
        depending on the use case.

        Args:
          response_text: The text response to be displayed to the user. Can
            also be empty string if no response to the user is required.
          page_info: (Optional) The JSON object returned by build_page_info()
          session_info: (Optiona) The JSON object returned by
            build_session_info()
        """
        if response_text:
            response_object = {
                'mergeBehavior': 'REPLACE',
                'messages': [
                    {
                        'text': {
                            'text': [response_text]
                        }
                    }
                ]
            }

        else:
            response_object = None

        message = {
            'fulfillmentResponse': response_object,
            'pageInfo': page_info,
            'sessionInfo': session_info
        }

        return message

    @staticmethod
    def get_tag(request):
        """Get the incoming DFCX webhook tag."""

        return request['fulfillmentInfo']['tag']

    @staticmethod
    def get_parameters(request):
        """Get the incoming DFCX webhook params."""
        params = None

        if 'parameters' in request['sessionInfo']:
            params = request['sessionInfo']['parameters']

        return params

    @staticmethod
    def get_conf_score(request):
        """Get the intent confidence score of the last triggered intent."""

        return request['intentInfo']['confidence']

    @staticmethod
    def get_user_utterance(request, cleaned=False):
        """Get the user utterance delivered with the webhook Request.

        Args:
          request: The incoming DFCX Request
          cleaned: Boolean flag with the following functions
            False - The user utterance is returned verbatim.
            True - The user utterance is stripped of whitespace,
              punctuation, and returned as lowercase.

        Returns:
          user_utterance: The final user utterance that was captured.
        """

        if cleaned:
            user_utterance = request['text'].lower().translate(str.maketrans(
                '', '', string.punctuation))

        else:
            user_utterance = request['text']

        return user_utterance
        