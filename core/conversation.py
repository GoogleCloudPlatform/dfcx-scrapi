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
from proto.marshal.collections.repeated import RepeatedComposite
# from proto.marshal.collections.repeated import RepeatedComposite


from .sapi_base import SapiBase

logger = logging

logging.basicConfig(
    format='[dfcx] %(levelname)s:%(message)s', level=logging.INFO)

MAX_RETRIES = 3  # JWT errors on CX API


class DialogflowConversation(SapiBase):
    """
    wrapping client requests to a CX agent for a conversation
    with internally maintained session state
    """

    def __init__(self, config=None, creds_path=None, agent_path=None, language_code="en"):
        """
        one of:
            config: object with creds_path and agent_path
            creds_path: IAM creds file which sets which projects you can access
            creds: TODO - already loaded creds data
        agent_path = full path to project
        """

        logging.info('create conversation with creds_path: %s | agent_path: %s', 
            creds_path, agent_path)

        # FIXME - the creds are not used anywhere else?
        creds_path = creds_path or config['creds_path']
        if not creds_path:
            raise KeyError('no creds give to create agent')
        logging.info('creds_path %s', creds_path)

        # FIX ME - remove this and use creds on every call instead
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = creds_path

        # project_id = data['project_id']
        # self.project_id = f'projects/{project_id}/locations/global'

        # projects/*/locations/*/agents/*/
        # TODO - use 'name' instead of path for fields
        agent_path = agent_path or config['agent_path']
        super().__init__(creds_path=creds_path, agent_path=agent_path)

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
    def reply(self, send_obj, restart=False, raw=False, retries=0):
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

        # FIXME - use SapiBase but needs a param of item eg self.agent_id ?
        client_options = self._set_region(item_id=self.agent_path)
        session_client = SessionsClient(client_options=client_options)
        session_path = f"{self.agent_path}/sessions/{self.session_id}"
        
        # projects/*/locations/*/agents/*/environments/*/sessions/*
        custom_environment = self.agent_env.get('environment')

        if custom_environment:
            # just the environment and NOT experiment (change to elif if experiment comes back)
            logging.info('req using env: %s', custom_environment)
            session_path = f"{self.agent_path}/environments/{custom_environment}/sessions/{self.session_id}"
        else:
            session_path = f"{self.agent_path}/sessions/{self.session_id}"

        # self.checkpoint('made client')
        # logging.info('session_path %s', session_path)

        disable_webhook = self.agent_env.get('disable_webhook') or False

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

        logging.info('disable_webhook: %s', disable_webhook)
        logging.info('query_params: %s', query_params)
        logging.info('request %s', request)

        try:
            response = session_client.detect_intent(request=request)

        # CX throws a 429 error
        # TODO - more specific exception
        except BaseException as err:
            logging.error("BaseException caught on CX.detect %s", err)
            template = "An exception of type {0} occurred. Arguments:\n{1!r}"
            message = template.format(type(err).__name__, err.args)
            logging.error(message)

            logging.error("text %s", text)
            logging.error("query_params %s", query_params)
            logging.error("query_input %s", query_input)
            logging.error(traceback.print_exc())
            retries += 1
            if retries < MAX_RETRIES:
                # TODO - increase back off / delay? not needed for 3 retries
                logging.error("retrying")
                self.reply(send_obj, restart=restart, raw=raw, retries=retries)
            else:
                logging.error("MAX_RETRIES exceeded")
                raise err
                # return None ## try next one

        # format reply

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
                reply['payload'] = SapiBase.extract_payload(msg)
            if (len(msg.text.text)) > 0:
                text = msg.text.text[-1]  # this could be multiple lines too?
                # print('text', text)
                texts.append(text)

        # flatten params struct
        params = {}
        # print('parameters', json.dumps(qr.parameters))  ## not JSON
        # serialisable until it's not
        if qr.parameters:
            for param in qr.parameters:
                # turn into key: value pairs
                val = qr.parameters[param]
                try:
                    if isinstance(val, RepeatedComposite):
                        # some type of protobuf array - for now we just flatten as a string with spaces
                        # FIXME - how better to convert list types in params responses?
                        logging.info('converting param: %s val: %s', param, val)
                        # val = val[0]
                        val = " ".join(val)
                        logging.info('converted val to: %s', val)

                except TypeError as err:
                    logging.error("Exception on CX.detect %s", err)
                    template = "An exception of type {0} occurred. Arguments:\n{1!r}"
                    message = template.format(type(err).__name__, err.args)
                    logging.error(message)
                    logging.error('failed to extract params for: %s', text)

                # give up on params

                # if isinstance(val, MapComposite):
                #     # some type of protobuf array - for now we just flatten as a string with spaces
                #     # FIXME - how better to convert list types in params responses?
                #     logging.info('converting param: %s val: %s', param, val)
                #     # val = val[0]
                #     val = " ".join(val)
                #     logging.info('converted val to: %s', val)
                params[param] = val

        # reply['payload'] = payload
        reply["text"] = "\n".join(texts)
        reply["confidence"] = qr.intent_detection_confidence
        reply["page_name"] = qr.current_page.display_name
        reply["intent_name"] = qr.intent.display_name
        reply["other_intents"] = self.format_other_intents(qr)
        reply["params"] = params

        # if raw:
            # self.qr = qr
            # reply["qr"] = qr
        blob = SapiBase.response_to_json(qr)
        logging.info('response: %s', json.dumps(blob, indent=2))
        # logging.info('response: %s', blob)

        # self.checkpoint('<< formatted response')
        logging.debug('reply %s', reply)
        return reply



    # TODO - dfqr class that has convenience accessor methods for different properties
    # basically to unwind the protobut



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
