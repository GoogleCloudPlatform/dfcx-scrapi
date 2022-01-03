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
import pandas as pd
from typing import Dict
import uuid
from threading import Thread
import time
import traceback
from google.cloud.dialogflowcx_v3beta1.services.sessions import SessionsClient
from google.cloud.dialogflowcx_v3beta1.types import session
from google.api_core import exceptions as core_exceptions
from proto.marshal.collections.repeated import RepeatedComposite

from dfcx_scrapi.core.scrapi_base import ScrapiBase
from dfcx_scrapi.core.flows import Flows
from dfcx_scrapi.core.pages import Pages

logger = logging

logging.basicConfig(format="[dfcx] %(levelname)s:%(message)s", level=None)

MAX_RETRIES = 3  # JWT errors on CX API
DEBUG_LEVEL = "info"


class DialogflowConversation(ScrapiBase):
    """
    wrapping client requests to a CX agent for a conversation
    with internally maintained session state
    """

    def __init__(
        self,
        config=None,
        creds_path: str = None,
        creds_dict: Dict = None,
        creds=None,
        agent_path: str = None,
        language_code: str = "en",
    ):

        super().__init__(
            creds_path=creds_path,
            creds_dict=creds_dict,
            creds=creds,
            agent_path=agent_path,
        )

        logging.info(
            "create conversation with creds_path: %s | agent_path: %s",
            creds_path,
            agent_path,
        )

        # format: projects/*/locations/*/agents/*/
        self.agent_path = agent_path or config["agent_path"]
        self.language_code = language_code or config["language_code"]
        self.start_time = None
        self.query_result = None
        self.session_id = None
        self.turn_count = None
        self.agent_env = {}  # empty
        self.restart()
        self.flows = Flows(creds=self.creds)
        self.pages = Pages(creds=self.creds)

    @staticmethod
    def _validate_test_set_input(test_set: pd.DataFrame):
        mask = test_set.page_id.isna().to_list()
        invalid_pages = set(test_set.page_display_name[mask].to_list())

        if invalid_pages:
            raise Exception("The following Pages are invalid and missing Page "
                "IDs: \n%s\n\nPlease ensure that your Page Display Names do "
                "not contain typos.\nFor Default Start Page use the special "
                "page display name START_PAGE." % invalid_pages)


    @staticmethod
    def progress_bar(current, total, bar_length=50, type_="Progress"):
        """Display progress bar for processing."""
        percent = float(current) * 100 / total
        arrow = "-" * int(percent / 100 * bar_length - 1) + ">"
        spaces = " " * (bar_length - len(arrow))
        print(
            "{2}({0}/{1})".format(current, total, type_)
            + "[%s%s] %d %%" % (arrow, spaces, percent),
            end="\r",
        )

    def _page_id_mapper(self):
        agent_pages_map = pd.DataFrame()
        flow_map = self.flows.get_flows_map(agent_id=self.agent_path)
        for flow_id in flow_map.keys():

            page_map = self.pages.get_pages_map(flow_id=flow_id)

            flow_mapped = pd.DataFrame.from_dict(page_map, orient="index")
            flow_mapped["page_id"] = flow_mapped.index

            flow_mapped = flow_mapped.rename(columns={0: "page_display_name"})

            # add start page
            start_page_id = flow_id + "/pages/START_PAGE"
            flow_mapped = flow_mapped.append(
                pd.DataFrame(
                    columns=["page_display_name", "page_id"],
                    data=[["START_PAGE", start_page_id]],
                )
            )

            flow_mapped.insert(0, "flow_display_name", flow_map[flow_id])
            agent_pages_map = agent_pages_map.append(flow_mapped)

        self.agent_pages_map = agent_pages_map.reset_index(drop=True)


    def _get_reply_results(self, utterance, page_id, results, i):
        """Get results of single text utterance to CX Agent.

        Args:
          utterance: Text to send to the bot for testing.
          page_id: Specified CX Page to send the utterance request to
          results: Pandas Dataframe to capture and store the results
          i: Internal tracking for Python Threading
        """
        response = self.reply(
            send_obj={"text": utterance}, current_page=page_id, restart=True
        )

        intent = response["intent_name"]
        confidence = response["confidence"]
        target_page = response["page_name"]

        results["detected_intent"][i] = intent or "no match"
        results["confidence"][i] = confidence
        results["target_page"][i] = target_page


    def _get_intent_detection(self, test_set: pd.DataFrame):
        """Gets the results of a subset of Intent Detection tests.

        NOTE - This is an internal method used by run_intent_detection to
        manage parallel intent detection requests and should not be used as a
        standalone function.
        """

        self._page_id_mapper()
        test_set_mapped = pd.merge(
            test_set,
            self.agent_pages_map,
            on=["flow_display_name", "page_display_name"],
            how="left",
        )
        utterances = list(test_set_mapped["utterance"])
        page_ids = list(test_set_mapped["page_id"])

        self._validate_test_set_input(test_set_mapped)

        threads = [None] * len(utterances)
        results = {
            "detected_intent": [None] * len(utterances),
            "confidence": [None] * len(utterances),
            "target_page": [None] * len(utterances),
        }
        for i, (utterance, page_id) in enumerate(zip(utterances, page_ids)):
            threads[i] = Thread(
                target=self._get_reply_results,
                args=(utterance, page_id, results, i),
            )
            threads[i].start()

        for idx, _ in enumerate(threads):
            threads[idx].join()

        test_set_mapped["detected_intent"] = results["detected_intent"]
        test_set_mapped["confidence"] = results["confidence"]
        test_set_mapped["target_page"] = results["target_page"]
        test_set_mapped = test_set_mapped.drop(columns=["page_id"])

        intent_detection = test_set_mapped.copy()

        return intent_detection


    def restart(self):
        """starts a new session/conversation for this agent"""
        self.session_id = uuid.uuid4()
        self.turn_count = 0

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

    def reply(
        self,
        send_obj,
        restart: bool = False,
        raw: bool = False,
        retries: int = 0,
        current_page: str = None,
        checkpoints: bool = False
    ):
        """
        args:
            send_obj  {text, params, dtmf}
            restart: Boolean flag that determines whether to use the existing
              session ID or start a new conversation with a new session ID.
              Passing True will create a new session ID on subsequent calls.
              Defaults to False.
            raw: boolean
            retries: used for recurse calling this func if API fails
            current_page: Specify the page id to start the conversation from
            checkpoints: Boolean flag to enable/disable Checkpoint timer
              debugging. Defaults to False.
        """
        text = send_obj.get("text")
        if not text:
            logger.warning("trying to reply to empty message %s", send_obj)

        if text and len(text) > 250:
            logging.error("text is too long %s", text)
            text = text[0:250]

        send_params = send_obj.get("params")

        if checkpoints:
            self.checkpoint(start=True)

        if restart:
            self.restart()

        client_options = self._set_region(self.agent_path)
        session_client = SessionsClient(
            credentials=self.creds, client_options=client_options
        )
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

        if send_params and current_page:
            query_params = session.QueryParameters(
                disable_webhook=disable_webhook,
                parameters=send_params,
                current_page=current_page,
            )
        elif send_params and not current_page:
            query_params = session.QueryParameters(
                disable_webhook=disable_webhook, parameters=send_params
            )
        elif not send_params and current_page:
            query_params = session.QueryParameters(
                disable_webhook=disable_webhook, current_page=current_page
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

        logging.debug("query_params: %s", query_params)
        logging.debug("request %s", request)

        response = None
        try:
            response = session_client.detect_intent(request=request)

        except core_exceptions.InternalServerError as err:
            logging.error(
                "---- ERROR --- InternalServerError caught on CX.detect %s", err
            )
            logging.error("text: %s", text)
            logging.error("query_params: %s", query_params)
            logging.error("query_input: %s", query_input)
            return {}

        except core_exceptions.ClientError as err:
            logging.error(
                "---- ERROR ---- ClientError caught on CX.detect %s", err
            )
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
                return self.reply(
                    send_obj, restart=restart, raw=raw, retries=retries
                )
            else:
                logging.error("MAX_RETRIES exceeded")
                # try to continue but this may crash somewhere else
                return {}
                # raise err
                # return None ## try next one

        # format reply
        if checkpoints:
            self.checkpoint("<< got response")
        query_result = response.query_result
        logging.debug("dfcx>qr %s", query_result)
        self.query_result = query_result  # for debugging
        reply = {}

        # flatten array of text responses
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
        if query_result.parameters:
            for param in query_result.parameters:
                # turn into key: value pairs
                val = query_result.parameters[param]
                try:
                    # protobuf array - we flatten as a string with spaces
                    if isinstance(val, RepeatedComposite):
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


    def run_intent_detection(
        self,
        test_set: pd.DataFrame,
        chunk_size: int = 300,
        rate_limit: float = 20):
        """Tests a set of utterances for intent detection against a CX Agent.

        This function uses Python Threading to run tests in parallel to
        expedite intent detection testing for Dialogflow CX agents. The default
        quota for Text requests/min is 1200. Ref:
          https://cloud.google.com/dialogflow/quotas#table

        Args:
          test_set: A Pandas DataFrame with the following schema.
            flow_display_name: str
            page_display_name: str
              - NOTE, when using the Default Start Page of a Flow you must
                define it as the special display name START_PAGE
            utterance: str
          chunk_size: Determines the number of text requests to send in
            parallel. This should be adjusted based on your test_set size and
            the Quota limits set for your GCP project. Default is 300.
          rate_limit: Number of seconds to wait between running test set chunks

        Returns:
          intent_detection: A Pandas DataFrame consisting of the original
            DataFrame plus an additional column for the detected intent with
            the following schema.
              flow_display_name: str
              page_display_name: str
              utterance: str
              detected_intent: str
              confidence: float
              target_page: str
        """

        result = pd.DataFrame()
        for start in range(0, test_set.shape[0], chunk_size):
            test_set_chunk = test_set.iloc[start:start + chunk_size]
            result_chunk = self._get_intent_detection(test_set=test_set_chunk)
            result = result.append(result_chunk)
            self.progress_bar(start, test_set.shape[0])
            time.sleep(rate_limit)

        return result
