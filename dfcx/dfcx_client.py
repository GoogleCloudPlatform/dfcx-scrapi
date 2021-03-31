"""
client of DfCx agent
tracks session internally
"""

# import copy
import json
import logging
import os
import uuid
import time
import traceback

# import sys
# import pandas as pd
# import pathlib
# from collections import defaultdict
# from sys import stdout

# from profilehooks import profile

# from dfcx_api import Agents, Intents
# from ipynb.fs.full.dfcx import DialogflowCX
# from dfcx.dfcx import DialogflowCX
# from dfcx import DialogflowCX
# from google.cloud.dialogflowcx_v3beta1.services.agents import AgentsClient
from google.cloud.dialogflowcx_v3beta1.services.sessions import SessionsClient
from google.cloud.dialogflowcx_v3beta1.types import session


from google.protobuf import json_format  # type: ignore
from proto.marshal.collections.repeated import RepeatedComposite

DEFAULT_CREDS_PATH = 'creds/default-creds.json'

logger = logging

logging.basicConfig(
    format='[dfcx] %(levelname)s:%(message)s', level=logging.INFO)

MAX_RETRIES = 3  # JWT errors on CX API


class DialogflowClient:
    """wrapping client requests to a CX agent"""

    def __init__(self, config=None, creds_path=None, agent_path=None, language_code="en"):
        """
        one of:
            config: object with creds_path and agent_path
            creds_path: IAM creds file which sets which projects you can access
            creds: TODO - already loaded creds data
        agent_path = full path to project
        """
        # TODO implement using already loaded creds not setting env path
        # if creds_path:
        #     with open(creds_path) as json_file:
        #         creds = json.load(json_file)

        # FIXME - the creds are not used anywhere else?
        # so maybe the env is what is relied on
        # this env var gets changed OUTSIDE of here
        creds_path = creds_path or config['creds_path']
        if creds_path:
            logging.info('create agent client with custom creds %s \nconfig: \n%s', creds_path, config)
        else:
            creds_path = DEFAULT_CREDS_PATH

        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = creds_path

        # project_id = data['project_id']
        # self.project_id = f'projects/{project_id}/locations/global'

        # projects/*/locations/*/agents/*/
        self.agent_path = agent_path or config['agent_path']
        self.language_code = language_code or config['language_code']
        self.start_time = None
        self.qr = None
        self.agent_env = {}  # empty
        self.restart()


    def restart(self):
        """starts a new session/conversation for this agent"""
        self.session_id = uuid.uuid4()
        self.turn_count = 0
        # logging.info('restarted agent: session: %s', self.session_id)
        # print('restarted DFCX.client=>', self.agent_path)


    def _set_region(self, agent_id=None):
        '''non global agents require a special endpoint in client_options'''
        agent_id = agent_id or self.agent_path
        location = agent_id.split('/')[3]
        if location != 'global':
            api_endpoint = '{}-dialogflow.googleapis.com:443'.format(location)
            client_options = {
                'api_endpoint': api_endpoint
            }
            # logger.info('client options %s', client_options)
            return client_options
        
        # custom_environment = self.agent_env.get('environment')
        # if custom_environment:
        #     api_endpoint = f'https://dialogflow.googleapis.com/v3/{agent_id}/environments/{custom_environment}'
        #     client_options = {
        #         'api_endpoint': api_endpoint
        #     }
        #     logging.info('using custom endpoint: %s', api_endpoint)
        #     logging.info('agent_id %s', agent_id)
        #     logging.info('location %s', location)
        #     return client_options
        # else
        return None


    def set_agent_env(self, param, value):
        '''setting changes related to the environment'''
        logging.info('setting agent_env param:[%s] = value:[%s]', param, value)
        self.agent_env[param] = value


    def checkpoint(self, msg=None, start=False):
        '''print a checkpoint to time progress and debug bottleneck'''
        if start:
            start_time = time.perf_counter()
            self.start_time = start_time
        else:
            start_time = self.start_time
        duration = round((time.perf_counter() - start_time), 2)
        if duration > 2:
            if msg:
                print("{:0.2f}s {}".format(duration, msg))

    # TODO - refactor options as a dict?
    def reply(self, send_obj, restart=False, raw=False, retries=0, disable_webhook=True):
        """
        send_obj to bot and get reply
            text
            params
            dtmf

        Pass restart=True to start a new conv with a new session_id
        otherwise uses the agents continues conv with session_id
        """

        # if disable_webhook:
        #     logging.info('disable_webhook: %s', disable_webhook)

        text = send_obj.get("text")
        send_params = send_obj.get("params")
        # logging.info('send params %s', send_params)
        self.checkpoint(start=True)

        if restart:
            self.restart()

        client_options = self._set_region()
        session_client = SessionsClient(client_options=client_options)
        session_path = f"{self.agent_path}/sessions/{self.session_id}"
        
        # projects/*/locations/*/agents/*/environments/*/sessions/*

        custom_environment = self.agent_env.get('environment')
        if custom_environment:
            session_path = f"{self.agent_path}/environments/{custom_environment}/sessions/{self.session_id}"
        else:
            session_path = f"{self.agent_path}/sessions/{self.session_id}"

        # self.checkpoint('made client')
        logging.info('session_path %s', session_path)

        # set parameters separately with single query and an empty text
        # query_params = {'disable_webhook': True }

        if send_params:
            query_params = session.QueryParameters(
                disable_webhook=disable_webhook,
                parameters=send_params
            )
        else:
            query_params = session.QueryParameters(
                disable_webhook=disable_webhook,
            )

        dtmf = send_obj.get("dtmf")
        if dtmf:
            dtmf_input = session.DtmfInput(digits=dtmf)
            query_input = session.QueryInput(
                dtmf=dtmf_input,
                language_code=self.language_code,
            )
        else:
            logging.debug('text: %s', text)
            text_input = session.TextInput(text=text)
            query_input = session.QueryInput(
                text=text_input,
                language_code=self.language_code,
            )

        # self.checkpoint('<< prepared request')

        request = session.DetectIntentRequest(session=session_path,
                                              query_input=query_input,
                                              query_params=query_params)

        try:
            response = session_client.detect_intent(request=request)
            self.checkpoint('<< got response')
            qr = response.query_result
            logging.debug('dfcx>qr %s', qr)
            self.qr = qr # for debugging
            reply = {}

            # flatten array of text responses
            # seems like there should be a better interface to pull out the texts
            texts = []
            for msg in qr.response_messages:
                if msg.payload:
                    reply['payload'] = self.extract_payload(msg)
                if (len(msg.text.text)) > 0:
                    text = msg.text.text[-1]  # this could be multiple lines too?
                    # print('text', text)
                    texts.append(text)

            # print('texts', texts)

            # flatten params struct
            params = {}
            # print('parameters', json.dumps(qr.parameters))  ## not JSON
            # serialisable
            if qr.parameters:
                for param in qr.parameters:
                    # turn into key: value pairs
                    val = qr.parameters[param]
                    if isinstance(val, RepeatedComposite):
                        # some type of protobuf array - for now we just flatten as a string with spaces
                        # FIXME - how better to convert list types in params responses?
                        logging.info('converting param: %s val: %s', param, val)
                        # val = val[0]
                        val = " ".join(val)
                        logging.info('converted val to: %s', val)
                    params[param] = val

            # print('params', params)

            # TODO - pluck some other fields - but these are methods, not values so cannot be json.dump'd
            # fields = ['match', 'parameters', 'intent', 'current_page', 'intent_detection_confidence']
            # result = dict((k, getattr(qr, k)) for k in fields if hasattr(qr, k) )

            # add some more convenience fields to make result comparison easier
            #     if len(texts) == 1:
            #         result['text'] = texts[0]  # last text entry
            #     else:
            #         result['text'] = '\n'.join(texts)

            # payload = qr.response_messages.payload
            # logging.info('payload %s', payload)

            # reply['payload'] = payload
            reply["text"] = "\n".join(texts)
            reply["params"] = params
            reply["confidence"] = qr.intent_detection_confidence
            reply["page_name"] = qr.current_page.display_name
            reply["intent_name"] = qr.intent.display_name
            reply["other_intents"] = self.format_other_intents(qr)
            if raw:
                # self.qr = qr
                reply["qr"] = qr
                reply["json"] = self.to_json(qr)

            # self.checkpoint('<< formatted response')
            logging.debug('reply %s', reply)
            return reply

        # CX throws a 429 error
        except BaseException as err:
            logging.error("Exception on CX.detect %s", err)
            template = "An exception of type {0} occurred. Arguments:\n{1!r}"
            message = template.format(type(err).__name__, err.args)
            logging.error(message)

            logging.error("text %s", text)
            logging.error("query_params %s", query_params)
            logging.error("query_input %s", query_input)
            logging.error(traceback.print_exc())
            retries += 1
            if retries < MAX_RETRIES:
                logging.error("retrying")
                self.reply(send_obj, restart=restart, raw=raw, retries=retries)
            else:
                logging.error("MAX_RETRIES exceeded")
                raise err
                # return None ## try next one

        qr = response.query_result
        logging.debug('dfcx>qr %s', qr)
        self.qr = qr # for debugging
        reply = {}

        # flatten array of text responses
        # seems like there should be a better interface to pull out the texts
        texts = []
        for msg in qr.response_messages:
            if msg.payload:
                reply['payload'] = self.extract_payload(msg)
            if (len(msg.text.text)) > 0:
                text = msg.text.text[-1]  # this could be multiple lines too?
                # print('text', text)
                texts.append(text)

        # print('texts', texts)

        # flatten params struct
        params = {}
        # print('parameters', json.dumps(qr.parameters))  ## not JSON
        # serialisable
        if qr.parameters:
            for param in qr.parameters:
                # turn into key: value pairs
                actual = qr.parameters[param]
                if isinstance(actual, RepeatedComposite):
                    actual = ' '.join(actual)

                if not isinstance(actual, str) and not isinstance(actual, bool) and not isinstance(actual, int):
                    # FIXME - still not an actual recognized type just stringify it
                    logging.error('ERROR convert to string type for param %s | type: %s', param, type(actual))
                    logging.info("converted: [before: %s |after: %s]", actual, str(actual))
                    actual = str(actual)

                params[param] = actual

        reply["text"] = "\n".join(texts)
        reply["params"] = params
        reply["confidence"] = qr.intent_detection_confidence
        reply["page_name"] = qr.current_page.display_name
        reply["intent_name"] = qr.intent.display_name
        reply["other_intents"] = self.format_other_intents(qr)
        if raw:
            # self.qr = qr
            reply["qr"] = qr
            reply["json"] = self.to_json(qr)

        # self.checkpoint('<< formatted response')
        try:
            logging.info('reply: \n%s', json.dumps(reply, indent=2))
        except TypeError as err:
            logging.error('cannot JSON reply %s', err)
            logging.info('reply %s', reply)

        return reply


    # TODO - dfqr class that has convenience accessor methods for different properties
    # basically to unwind the protobut

    def extract_payload(self, msg):
        '''convert to json so we can get at the object'''
        blobstr = json_format.MessageToJson(msg._pb)
        blob = json.loads(blobstr)
        return blob.get('payload') # deref for nesting


    def format_other_intents(self, qr):
        """unwind protobufs into more friendly dict"""
        other_intents = qr.diagnostic_info.get("Alternative Matched Intents")
        items = []
        rank = 0
        for alt in other_intents:
            items.append({
                "name": alt.get("DisplayName"),
                "score": alt.get("Score"),
                "rank": rank,
            })
            rank += 1
        #             intents_map[alt['DisplayName']] = alt['Score']
        return items

    @staticmethod
    def to_json(pbuf):
        '''extractor of private fields
        '''
        blob = json_format.MessageToJson(pbuf) # i think this returns JSON as a string
        return blob

    def getpath(self, obj, xpath, default=None):
        '''get data at a pathed location out of object internals'''
        elem = obj
        try:
            for xpitem in xpath.strip("/").split("/"):
                try:
                    xpitem = int(xpitem)
                    elem = elem[xpitem]  # dict
                except ValueError:
                    elem = elem.get(xpitem)  # array
        except KeyError:
            logging.warning("failed to getpath: %s ", xpath)
            return default

        logging.info("OK getpath: %s", xpath)
        return elem
