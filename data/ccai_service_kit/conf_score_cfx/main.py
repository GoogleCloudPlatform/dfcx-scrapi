"""Sample Cloud Function code to extract and return DFCX Confidence Score."""

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

import json
import logging
from dfcx_scrapi.tools.webhook_utils import WebhookUtils

# logging config
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)-8s %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S')


def conf_score(request, debugging=False):
    """Extract the Confidence Score and return as a Session Parameter.

    This Cloud Function code is meant to work in conjunction with a Dialogflow
    CX agent. The `conf_score` function is the main entry point and receives
    the incoming webhook request from Dialogflow CX. The request is then parsed
    and
    """
    logging.info('###### [cx_webhook] - CFX Triggered! ######')
    wu = WebhookUtils()

    if debugging:
        req = request

    else:
        req = request.get_json()
        logging.info('* [cx_webhook] Incoming Request: %s', req)

    webhook_tag = wu.get_tag(req)

    if webhook_tag == 'conf_test':
        logging.info('* [cx_webhook] CONF TEST TAG RECEIVED.')
        score = wu.get_conf_score(req)
        session_info = wu.build_session_info({'webhook_conf': score})
        message = wu.build_response('The Confidence Score is: {}'.format(
          score), session_info=session_info)

    else:
        logging.info('* [cx_webhook] No Webhook Tag Received.')

    res = json.dumps(message)
    logging.info(res)

    return res

if __name__ == '__main__':
    FILE = '/Users/pmarlow/eng/cloud_functions/tests/conf_score_payload.json'
    with open(FILE) as json_file:
        data = json.load(json_file)

    conf_score(data, False)
