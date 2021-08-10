"""client of DfCx agent - tracks session internally"""

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
import os
import uuid
import time
import traceback
from google.cloud.dialogflowcx_v3beta1.services.sessions import SessionsClient
from google.cloud.dialogflowcx_v3beta1.types import session
from google.api_core import exceptions as core_exceptions
from proto.marshal.collections.repeated import RepeatedComposite
from dfcx_scrapi.core.scrapi_base import ScrapiBase
logger = logging

logging.basicConfig(
    format="[dfcx] %(levelname)s:%(message)s", level=None
)

MAX_RETRIES = 3  # JWT errors on CX API
DEBUG_LEVEL = "info"  # silly for request/response


class DialogflowConversation(ScrapiBase):
    """
    wrapping client requests to a CX agent for a conversation
    with internally maintained session state
    """

    def __init__(
        self, config=None, creds_path=None, agent_path=None, language_code="en"
    ):
        """
        one of:
            config: object with creds_path and agent_path
            creds_path: IAM creds file which sets which projects you can access
            creds: TODO - already loaded creds data
        agent_path = full path to project
        """

        logging.info(
            "create conversation with creds_path: %s | agent_path: %s",
            creds_path,
            agent_path,
        )

        creds_path = creds_path or config["creds_path"]
        if not creds_path:
            raise KeyError("no creds give to create agent")
        logging.info("creds_path %s", creds_path)

        # FIX ME - remove this and use creds on every call instead
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = creds_path

        # format: projects/*/locations/*/agents/*/
        agent_path = agent_path or config["agent_path"]
        super().__init__(creds_path=creds_path, agent_path=agent_path)

        self.language_code = language_code or config["language_code"]
        self.start_time = None
        self.query_result = None
        self.session_id = None
        self.turn_count = None
        self.agent_env = {}  # empty
        self.restart()

    def restart(self):
        """starts a new session/conversation for this agent"""
        self.session_id = uuid.uuid4()
        self.turn_count = 0
        # logging.info("restarted agent: session: %s", self.session_id)
        # print("restarted DFCX.client=>", self.agent_path)

    def set_agent_env(self, param, value):
        """setting changes related to the environment"""
        logging.info("setting agent_env param:[%s] = value:[%s]", param, value)
        self.agent_env[param] = value

    def checkpoint(self, msg=None, start=False):
        """print a checkpoint to time progress and debug bottleneck"""
        if start:
            start_time = time.perf_counter()
            self.start_time = start_time
        else:
            start_time = self.start_time
        duration = round((time.perf_counter() - start_time), 2)
        if duration > 2:
            if msg:
                print("{:0.2f}s {}".format(duration, msg))

    def reply(self, send_obj, restart=False, raw=False, retries=0):
        """
        args:
            send_obj  {text, params, dtmf}
            restart: boolean
            raw: boolean
            retries: used for recurse calling this func if API fails

        Pass restart=True to start a new conv with a new session_id
        otherwise uses the agents continues conv with session_id
        """

        # if disable_webhook:
        #     logging.info("disable_webhook: %s", disable_webhook)

        text = send_obj.get("text")
        if not text:
            logger.warning("trying to reply to empty message %s", send_obj)

        if text and len(text) > 250:
            logging.error("text is too long %s", text)
            text = text[0:250]

        send_params = send_obj.get("params")
        # logging.info("send params %s", send_params)
        self.checkpoint(start=True)

        if restart:
            self.restart()

        # FIXME - use ScrapiBase but needs a param of item eg self.agent_id ?
        client_options = self._set_region(item_id=self.agent_path)
        session_client = SessionsClient(client_options=client_options)
        session_path = f"{self.agent_path}/sessions/{self.session_id}"

        # projects/*/locations/*/agents/*/environments/*/sessions/*
        custom_environment = self.agent_env.get("environment")

        if custom_environment:
            # just the environment and NOT experiment
            # (change to elif if experiment comes back)
            logging.info("req using env: %s", custom_environment)
            session_path = "{}/environments/{}/sessions/{}".format(
                self.agent_path, custom_environment, self.session_id
            )

        disable_webhook = self.agent_env.get("disable_webhook") or False

        if send_params:
            query_params = session.QueryParameters(
                disable_webhook=disable_webhook, parameters=send_params
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
            logging.debug("text: %s", text)
            text_input = session.TextInput(text=text)
            query_input = session.QueryInput(
                text=text_input,
                language_code=self.language_code,
            )

        # self.checkpoint("<< prepared request")

        request = session.DetectIntentRequest(
            session=session_path,
            query_input=query_input,
            query_params=query_params,
        )

#         logging.info("disable_webhook: %s", disable_webhook)
        logging.debug("query_params: %s", query_params)
        logging.debug("request %s", request)

        response = None
        try:
            response = session_client.detect_intent(request=request)

        # how to import this exception?
        # except com.google.apps.framework.request.BadRequestException as err:
        #     logging.error("BadRequestException %s", err)

        # CX throws a 429 error
        # catch Auth exceptions too separately - eg if creds are expired
        except core_exceptions.InternalServerError as err:
            logging.error(
                "---- ERROR --- InternalServerError caught on CX.detect %s",
                err)
            logging.error("text: %s", text)
            logging.error("query_params: %s", query_params)
            logging.error("query_input: %s", query_input)
            return {}

        except core_exceptions.ClientError as err:
            logging.error(
                "---- ERROR ---- ClientError caught on CX.detect %s", err)
            template = "An exception of type {0} occurred. \nArguments:\n{1!r}"
            message = template.format(type(err).__name__, err.args)
            logging.error("err name %s", message)

            logging.error("text %s", text)
            logging.error("query_params %s", query_params)
            logging.error("query_input %s", query_input)
            logging.error(traceback.print_exc())
            retries += 1
            if retries < MAX_RETRIES:
                # TODO - increase back off / delay? not needed for 3 retries
                logging.error("retrying")
                return self.reply(send_obj, restart=restart, raw=raw,
                                  retries=retries)
            else:
                logging.error("MAX_RETRIES exceeded")
                # try to continue but this may crash somewhere else
                return {}
                # raise err
                # return None ## try next one

        # format reply

        self.checkpoint("<< got response")
        query_result = response.query_result
        logging.debug("dfcx>qr %s", query_result)
        self.query_result = query_result  # for debugging
        reply = {}

        # flatten array of text responses
        # seems like there should be a better interface to pull out the texts
        texts = []
        for msg in query_result.response_messages:
            if msg.payload:
                reply["payload"] = ScrapiBase.extract_payload(msg)
            if (len(msg.text.text)) > 0:
                text = msg.text.text[-1]  # this could be multiple lines too?
                # print("text", text)
                texts.append(text)

        # flatten params struct
        params = {}
        # print("parameters", json.dumps(qr.parameters))  ## not JSON
        # serialisable until it"s not
        if query_result.parameters:
            for param in query_result.parameters:
                # turn into key: value pairs
                val = query_result.parameters[param]
                try:
                    if isinstance(val, RepeatedComposite):
                        # protobuf array - we flatten as a string with spaces
#                         logging.info(
#                             "converting param: %s val: %s", param, val)
                        val = " ".join(val)

                except TypeError as err:
                    logging.error("Exception on CX.detect %s", err)
                    template = (
                        "An exception of type {0} occurred. Arguments:\n{1!r}"
                    )
                    message = template.format(type(err).__name__, err.args)
                    logging.error(message)
                    logging.error("failed to extract params for: %s", text)

                params[param] = val

        reply["text"] = "\n".join(texts)
        reply["confidence"] = query_result.intent_detection_confidence
        reply["page_name"] = query_result.current_page.display_name
        reply["intent_name"] = query_result.intent.display_name
        reply["other_intents"] = self.format_other_intents(query_result)
        reply["params"] = params

        # if raw:
        # self.qr = qr
        # reply["qr"] = qr

        if DEBUG_LEVEL == "silly":
            blob = ScrapiBase.cx_object_to_json(query_result)
            logging.info(
                "response: %s", json.dumps(blob, indent=2)
            )  # do NOT deploy
            # logging.debug("response: %s", blob)

        # self.checkpoint("<< formatted response")
        logging.debug("reply %s", reply)
        return reply

    def format_other_intents(self, query_result):
        """unwind protobufs into more friendly dict"""
        other_intents = query_result.diagnostic_info.get(
            "Alternative Matched Intents"
        )
        items = []
        rank = 0
        for alt in other_intents:
            items.append(
                {
                    "name": alt.get("DisplayName"),
                    "score": alt.get("Score"),
                    "rank": rank,
                }
            )
            rank += 1
        # intents_map[alt["DisplayName"]] = alt["Score"]
        if self:  # keep as instance method and silence linter
            return items

        return None

    def getpath(self, obj, xpath, default=None):
        """get data at a pathed location out of object internals"""
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
        if self:
            return elem

        return None
