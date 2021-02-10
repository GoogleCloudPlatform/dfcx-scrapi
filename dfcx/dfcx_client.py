'''
client of DfCx agent
tracks session internally
'''

# import copy
import json
import logging
import os
import uuid
# import sys
# import pandas as pd
# import pathlib
# import time
# from collections import defaultdict
from sys import stdout

# from dfcx_api import Agents, Intents
# from ipynb.fs.full.dfcx import DialogflowCX
# from dfcx.dfcx import DialogflowCX
# from dfcx import DialogflowCX
# from google.cloud.dialogflowcx_v3beta1.services.agents import AgentsClient
from google.cloud.dialogflowcx_v3beta1.services.sessions import SessionsClient
from google.cloud.dialogflowcx_v3beta1.types import session
# from google.cloud.dialogflowcx_v3beta1 import types as CxTypes
# import google.cloud.dialogflowcx_v3beta1.types as CxTypes

from google.protobuf import json_format  # type: ignore

# import google.protobuf.json_format
# import google.protobuf.message.Message


logger = logging.getLogger('dfcx')
formatter = logging.Formatter('[dfcx    ] %(message)s')
handler = logging.StreamHandler(stdout)
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.propagate = False


MAX_RETRIES = 10 # JWT errors on CX API


class DialogflowClient:
    '''wrapping client requests to a CX agent'''

    def __init__(self, creds_path=None, agent_path=None, language_code='en'):
        """
        one of:
            creds_path: IAM creds file which sets which projects you can access
            creds: already loaded creds data 
        agent_path = full path to project
        """
        # TODO implement using already loaded creds not setting env path
        # if creds_path:
        #     with open(creds_path) as json_file:
        #         creds = json.load(json_file)

        # FIXME - the creds are not used anywhere else?
        # so maybe the env is what is relied on
        # this env var gets changed OUTSIDE of here
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = creds_path

        # project_id = data['project_id']
        # self.project_id = f'projects/{project_id}/locations/global'

        # projects/*/locations/*/agents/*/
        self.agent_path = agent_path
        self.language_code = language_code
        self.restart()


    def restart(self):
        """starts a new session/conversation for this agent"""
        self.session_id = uuid.uuid4()
        # print('restarted DFCX.client=>', self.agent_path)


### SESSION FX
    def reply(self, send_obj, restart=False, raw=False, retries=0):
        """
        send_obj to bot and get reply
            text
            params
            dtmf
        
        Pass restart=True to start a new conv with a new session_id 
        otherwise uses the agents continues conv with session_id
        """
        if restart:
            self.restart()

        session_client = SessionsClient()
        session_path = f"{self.agent_path}/sessions/{self.session_id}"
        
        text = send_obj.get('text')
        send_params = send_obj.get('params')

        # set parameters separately with single query and an empty text
        query_params = None
        if send_params:
            query_params = session.QueryParameters(parameters=send_params)

        dtmf = send_obj.get('dtmf')
        if dtmf:
            dtmf_input = session.DtmfInput(digits=dtmf)
            query_input = session.QueryInput(
                dtmf=dtmf_input,
                language_code=self.language_code,
            )
        else:
            text_input = session.TextInput(text=text)
            query_input = session.QueryInput(
                text=text_input,
                language_code=self.language_code,
            )

        request = session.DetectIntentRequest(
            session=session_path, 
            query_input=query_input,
            query_params=query_params
        )

        try:
            response = session_client.detect_intent(request=request)

        except Exception as err:
            logging.error('Exception on CX.detect %s', err)
            retries += 1
            if (retries < MAX_RETRIES):
                self.reply(send_obj, restart=restart, raw=raw, retries=retries)
            else:
                logging.error('MAX_RETRIES exceeded')
                raise err
                # return None ## try next one

        qr = response.query_result

        # flatten array of text responses
        # seems like there should be a better interface to pull out the texts
        texts = []
        for msg in qr.response_messages:
            if (len(msg.text.text)) > 0:
                text = msg.text.text[-1] # this could be multiple lines too?
                # print('text', text)
                texts.append(text)

        # print('texts', texts)

        # flatten params struct
        params = {}
        # print('parameters', json.dumps(qr.parameters))  ## not JSON serialisable
        if qr.parameters:
            for param in qr.parameters:
                # turn into key: value pairs
                params[param] = qr.parameters[param]

        # print('params', params)

        # TODO - pluck some other fields - but these are methods, not values so cannot be json.dump'd
        # fields = ['match', 'parameters', 'intent', 'current_page', 'intent_detection_confidence']
        # result = dict((k, getattr(qr, k)) for k in fields if hasattr(qr, k) )

        # add some more convenience fields to make result comparison easier
    #     if len(texts) == 1:
    #         result['text'] = texts[0]  # last text entry
    #     else:
    #         result['text'] = '\n'.join(texts)

        reply = {}
        reply['text'] = '\n'.join(texts)
        reply['params'] = params
        reply['confidence'] = qr.intent_detection_confidence
        reply['page_name'] = qr.current_page.display_name
        reply['intent_name'] = qr.intent.display_name
        reply['other_intents'] = self.format_other_intents(qr)
        if raw:
            # self.qr = qr
            reply['qr'] = qr 
            reply['json'] = self.to_json(qr)
        return reply


    # TODO - dfqr class that has convenience accessor methods for different properties
    # basically to unwind the protobut
    def format_other_intents(self, qr):
        '''unwind protobufs into more friendly dict'''
        other_intents = qr.diagnostic_info.get('Alternative Matched Intents')
        items = []
        rank = 0
        for alt in other_intents:
            items.append({
                'name': alt.get('DisplayName'),
                'score': alt.get('Score'),
                'rank': rank
            })
            rank += 1
#             intents_map[alt['DisplayName']] = alt['Score']
        return items


    def to_json(self, qr):
        blob = json_format.MessageToJson(qr._pb) # AttributeError: 'DESCRIPTOR'
        return blob


    # get value at path in object
    def getpath(self, obj, xpath, default=None):
        elem = obj
        try:
            for x in xpath.strip("/").split("/"):
                try:
                    x = int(x)
                    elem = elem[x]  # dict
                except ValueError:
                    elem = elem.get(x) # array
        except:
            logging.warning('failed to getpath: %s ', xpath)
            return default

        logging.info('OK getpath: %s', xpath)
        return elem
