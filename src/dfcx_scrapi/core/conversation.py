"""DFCX End to End Conversation Functions"""

# Copyright 2023 Google LLC
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
import time
import traceback
import uuid

from typing import Dict, Any
from operator import attrgetter
from threading import Thread

import pandas as pd

from google.cloud.dialogflowcx_v3beta1 import services
from google.cloud.dialogflowcx_v3beta1 import types
from google.api_core import exceptions as core_exceptions
from proto.marshal.collections import repeated
from proto.marshal.collections import maps

from dfcx_scrapi.core import scrapi_base
from dfcx_scrapi.core import flows
from dfcx_scrapi.core import pages

logging.basicConfig(
    format="[dfcx] %(levelname)s:%(message)s", level=logging.INFO
)

MAX_RETRIES = 3


class DialogflowConversation(scrapi_base.ScrapiBase):
    """Class that wraps the SessionsClient to hold end to end conversations
    and maintain internal session state
    """

    def __init__(
        self,
        config=None,
        creds_path: str = None,
        creds_dict: Dict = None,
        creds=None,
        agent_id: str = None,
        language_code: str = "en",
    ):

        super().__init__(
            creds_path=creds_path,
            creds_dict=creds_dict,
            creds=creds,
            agent_id=agent_id,
        )

        logging.debug(
            "create conversation with creds_path: %s | agent_id: %s",
            creds_path, agent_id)

        self.agent_id = self._set_agent_id(agent_id, config)
        self.language_code = self._set_language_code(language_code, config)
        self.start_time = None
        self.query_result = None
        self.session_id = None
        self.turn_count = None
        self.agent_env = {}  # empty
        self.restart()
        self.flows = flows.Flows(creds=self.creds)
        self.pages = pages.Pages(creds=self.creds)

    @staticmethod
    def _set_language_code(language_code: str, config: Dict[str, Any]) -> str:
        """Determines how to set the language_code based on user inputs.

        We implement this for backwards compatability.
        """
        # Config will take precedence if provided
        if config:
            config_lang_code = config.get("language_code", None)

            # We'll only return if it exist in the config on the off chance that
            # some users have provided the langauge_code as a top level arg in
            # addition to providing the config
            if config_lang_code:
                return config_lang_code

        return language_code

    @staticmethod
    def _set_agent_id(input_agent_id: str, config: Dict[str, Any]) -> str:
        """Determines how to set the agent_id based on user inputs.

        We implement this for backwards compatability.
        """

        # Config will take precedence if provided
        if config:
            config_agent_path = config.get("agent_path", None)

            # We'll only return if it exist in the config on the off chance that
            # some users have provided the agent_id as a top level arg in
            # addition to providing the config
            if config_agent_path:
                return config_agent_path

        elif input_agent_id:
            return input_agent_id

        return None

    @staticmethod
    def _get_match_type_from_map(match_type: int):
        """Translates the match_type enum int value into a more descriptive
        string.
        """
        match_type_map = {
            0: "MATCH_TYPE_UNSPECIFIED",
            1: "INTENT",
            2: "DIRECT_INTENT",
            3: "PARAMETER_FILLING",
            4: "NO_MATCH",
            5: "NO_INPUT",
            6: "EVENT",
            8: "KNOWLEDGE_CONNECTOR",
            9: "LLM"
        }

        return match_type_map[match_type]

    @staticmethod
    def _validate_test_set_input(test_set: pd.DataFrame):
        """Validates that all pages referenced in the test set exist in the
        agent.
        """
        mask = test_set.page_id.isna().to_list()
        invalid_pages = set(test_set.page_display_name[mask].to_list())

        if invalid_pages:
            raise UserWarning(
                "The following Pages are invalid and missing Page "
                f"IDs: \n{invalid_pages}\n\nPlease ensure that your Page "
                "Display Names do not contain typos.\nFor Default Start Page "
                "use the special page display name START_PAGE."
            )

    @staticmethod
    def progress_bar(current, total, bar_length=50, type_="Progress"):
        """Display progress bar for processing."""
        percent = float(current) * 100 / total
        arrow = "-" * int(percent / 100 * bar_length - 1) + ">"
        spaces = " " * (bar_length - len(arrow))
        logging.info(
            f"{type_}({current}/{total})" + f"[{arrow}{spaces}] {percent:.2f}%"
            )

    @staticmethod
    def _build_query_params_object(parameters, current_page, disable_webhook):
        if parameters:
            query_params = types.session.QueryParameters(
                disable_webhook=disable_webhook,
                parameters=parameters,
                current_page=current_page,
            )
        else:
            query_params = types.session.QueryParameters(
                disable_webhook=disable_webhook, current_page=current_page
            )

        return query_params

    @staticmethod
    def _build_query_input_object(input_obj, language_code):
        if "dtmf" in input_obj:
            digits = str(input_obj["dtmf"])

            finish_digit = None
            if "finish_digit" in input_obj:
                finish_digit = str(input_obj["finish_digit"])

            dtmf_input = types.session.DtmfInput(
                digits=digits, finish_digit=finish_digit
            )
            query_input = types.session.QueryInput(
                dtmf=dtmf_input,
                language_code=language_code,
            )

        elif "intent" in input_obj:
            intent_input = types.session.IntentInput(intent=input_obj["intent"])
            query_input = types.session.QueryInput(
                intent=intent_input, language_code=language_code
            )

        elif "event" in input_obj:
            event_input = types.session.EventInput(event=input_obj["event"])
            query_input = types.session.QueryInput(
                event=event_input, language_code=language_code
            )

        elif "text" in input_obj:
            text = input_obj["text"]
            logging.debug("Input text: %s", text)
            text_input = types.session.TextInput(text=text)
            query_input = types.session.QueryInput(
                text=text_input,
                language_code=language_code,
            )

        return query_input

    @staticmethod
    def _gather_text_responses(text_message):

        flat_texts = "\n".join(text_message.text)

        return flat_texts

    def _gather_response_messages(self, response_messages):
        rm_gathered = []
        for msg in response_messages:
            if msg.payload:
                msg = {
                    "payload": self.recurse_proto_marshal_to_dict(msg.payload)
                }

            elif msg.play_audio:
                msg = {"play_audio": {"audio_uri": msg.play_audio.audio_uri}}

            elif msg.live_agent_handoff:
                msg = {
                    "live_agent_handoff": self.recurse_proto_marshal_to_dict(
                        msg.live_agent_handoff.metadata
                    )
                }

            elif msg.conversation_success:
                msg = {
                    "conversation_success": self.recurse_proto_marshal_to_dict(
                        msg.conversation_success.metadata
                    )
                }

            elif msg.output_audio_text:
                msg = {"output_audio_text": msg.output_audio_text.text}

            elif msg.text:
                msg = {"text": self._gather_text_responses(msg.text)}

            rm_gathered.append(msg)

        return rm_gathered

    def _gather_query_result_parameters(self, input_parameters):
        output_parameters = {}
        for param in input_parameters:
            val = input_parameters[param]

            # If we find a RepeatedComposite (i.e. List) we will recurse
            # down and convert to lists/dics/str as needed.
            if isinstance(val, repeated.RepeatedComposite):
                val = self.recurse_proto_repeated_composite(val)

            elif isinstance(val, maps.MapComposite):
                val = self.recurse_proto_marshal_to_dict(val)

            output_parameters[param] = val

        return output_parameters

    def _page_id_mapper(self):
        """Initializes the agent_pages_map dataframe.

        This dataframe contains the flow_display_name, page_display_name,
        and page_id for each page in the agent.
        """
        agent_pages_map = pd.DataFrame()
        flow_map = self.flows.get_flows_map(agent_id=self.agent_id)
        for flow_id in flow_map.keys():

            page_map = self.pages.get_pages_map(flow_id=flow_id)

            flow_mapped = pd.DataFrame.from_dict(page_map, orient="index")
            flow_mapped["page_id"] = flow_mapped.index

            flow_mapped = flow_mapped.rename(columns={0: "page_display_name"})
            flow_mapped.insert(0, "flow_display_name", flow_map[flow_id])
            agent_pages_map = pd.concat([agent_pages_map, flow_mapped])

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

        target_page = response["page_name"]

        results["target_page"][i] = target_page
        results["match"][i] = response["match"]

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
            "target_page": [None] * len(utterances),
            "match":[None] * len(utterances),
        }
        for i, (utterance, page_id) in enumerate(zip(utterances, page_ids)):
            threads[i] = Thread(
                target=self._get_reply_results,
                args=(utterance, page_id, results, i),
            )
            threads[i].start()

        for _, thread in enumerate(threads):
            thread.join()

        test_set_mapped["target_page"] = results["target_page"]
        test_set_mapped["match"] = results["match"]
        test_set_mapped = test_set_mapped.drop(columns=["page_id"])
        intent_detection = test_set_mapped.copy()

        return intent_detection


    def restart(self):
        """Starts a new session/conversation for this agent"""
        self.session_id = uuid.uuid4()
        self.turn_count = 0

    def set_agent_env(self, param, value):
        """Setting changes related to the environment"""
        logging.info("setting agent_env param:[%s] = value:[%s]", param, value)
        self.agent_env[param] = value

    def checkpoint(self, msg=None, start=False):
        """Log a checkpoint to time progress and debug bottleneck"""
        if start:
            start_time = time.perf_counter()
            self.start_time = start_time
        else:
            start_time = self.start_time
        duration = round((time.perf_counter() - start_time), 2)
        if duration > 2:
            if msg:
                logging.info(f"{duration:0.2f}s {msg}")

    @scrapi_base.api_call_counter_decorator
    def reply(
        self,
        send_obj: Dict[str, str],
        restart: bool = False,
        retries: int = 0,
        current_page: str = None,
        checkpoints: bool = False,
    ):
        """Runs intent detection on one utterance and gets the agent reply.

        Args:
          send_obj: Dictionary with the following structure:
            {'text': str,
            'params': Dict[str,str],
            'dtmf': str}
          restart: Boolean flag that determines whether to use the existing
            session ID or start a new conversation with a new session ID.
            Passing True will create a new session ID on subsequent calls.
            Defaults to False.
          retries: used for recurse calling this func if API fails
          current_page: Specify the page id to start the conversation from
          checkpoints: Boolean flag to enable/disable Checkpoint timer
            debugging. Defaults to False.

        Returns:
          A dictionary for the agent reply to to the submitted text.
            Includes keys response_messages, confidence, page_name,
            intent_name, match_type, match, and params.
        """
        text = send_obj.get("text")
        send_params = send_obj.get("params")

        if not text:
            logging.warning(f"Input Text is empty. {send_obj}")

        if text and len(text) > 256:
            logging.warning(
                "Text input is too long. Truncating to 256 characters."
            )
            text = text[0:256]
            logging.warning(f"TRUNCATED TEXT: {text}")

        custom_environment = self.agent_env.get("environment")
        disable_webhook = self.agent_env.get("disable_webhook") or False

        if checkpoints:
            self.checkpoint(start=True)

        if restart:
            self.restart()

        client_options = self._set_region(self.agent_id)
        session_client = services.sessions.SessionsClient(
            credentials=self.creds, client_options=client_options
        )
        session_path = f"{self.agent_id}/sessions/{self.session_id}"

        if custom_environment:
            logging.info("req using env: %s", custom_environment)
            session_path = (
                f"{self.agent_id}/environments/"
                f"{custom_environment}/sessions/{self.session_id}"
            )

        # Build Query Params object
        query_params = self._build_query_params_object(
            send_params, current_page, disable_webhook
        )

        # Build Query Input object
        query_input = self._build_query_input_object(
            send_obj, self.language_code
        )

        request = types.session.DetectIntentRequest(
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
                logging.error("retrying")
                return self.reply(send_obj, restart=restart, retries=retries)
            else:
                logging.error("MAX_RETRIES exceeded")
                return {}

        if checkpoints:
            self.checkpoint("<< got response")
        query_result = response.query_result
        logging.debug("dfcx>qr %s", query_result)
        self.query_result = query_result
        reply = {}

        # Gather Response Messages into List of Dicts
        if query_result.response_messages:
            response_messages = self._gather_response_messages(
                query_result.response_messages
            )
        else:
            response_messages = None

        # Convert params structures from Proto to standard python data types
        if query_result.parameters:
            params = self._gather_query_result_parameters(
                query_result.parameters
            )
        else:
            params = None

        reply["response_messages"] = response_messages
        reply["confidence"] = query_result.intent_detection_confidence
        reply["page_name"] = query_result.current_page.display_name
        reply["intent_name"] = query_result.intent.display_name
        reply["match_type"] = self._get_match_type_from_map(
            query_result.match.match_type
        )
        reply["match"] = query_result.match
        reply["params"] = params

        logging.debug("reply %s", reply)

        return reply

    def getpath(self, obj, xpath, default=None):
        """Get data at a pathed location out of object internals"""
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
        rate_limit: float = 20,
    ):
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
          A Pandas DataFrame consisting of the original
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
            test_set_chunk = test_set.iloc[start : start + chunk_size]
            result_chunk = self._get_intent_detection(test_set=test_set_chunk)
            result = pd.concat([result, result_chunk])
            self.progress_bar(start, test_set.shape[0])
            time.sleep(rate_limit)
        self.progress_bar(test_set.shape[0], test_set.shape[0])

        result = self._unpack_match(result)
        return result

    def _unpack_match(self, df: pd.DataFrame):
        """ Unpacks a 'match' column into four component columns.

        Args:
          df: dataframe containing a column named match of types.Match

        Returns:
          A copy of df with columns match_type, confidence, parameters_set,
            and detected_intent instead of match.
        """
        df = (
            df
            .copy()
            .assign(
                match_type = lambda df: df.match.apply(
                    attrgetter("match_type._name_")),
                confidence = lambda df: df.match.apply(
                    attrgetter("confidence")),
                parameters_set = lambda df: df.match.apply(
                    attrgetter("parameters")),
                detected_intent = lambda df: df.match.apply(
                    attrgetter("intent.display_name"))
            )
            .assign(
                parameters_set = lambda df: df.parameters_set.apply(
                    lambda p: self.recurse_proto_marshal_to_dict(
                        p) if p else "")
            )
            .drop(columns="match")
        )
        return df
