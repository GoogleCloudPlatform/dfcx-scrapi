"""Base for other SCRAPI classes."""

# Copyright 2024 Google LLC
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

import functools
import json
import logging
import re
import threading
import time
from collections import defaultdict
from typing import Any, Dict, Iterable, List, Optional

import requests
import vertexai
from google.api_core import exceptions
from google.auth import default
from google.auth.transport.requests import Request
from google.cloud.dialogflowcx_v3beta1 import types
from google.oauth2 import service_account
from google.protobuf import field_mask_pb2, json_format, struct_pb2
from proto.marshal.collections import maps, repeated
from vertexai.generative_models import (
    GenerativeModel,
    HarmBlockThreshold,
    HarmCategory,
    SafetySetting,
)
from vertexai.language_models import TextEmbeddingModel, TextGenerationModel

_INTERVAL_SENTINEL = object()

# The following models are supported for Metrics and Evaluations, either for
# Text Embeddings or used to provide Generations / Predictions.
SYS_INSTRUCT_MODELS = [
    "gemini-1.0-pro-002",
    "gemini-1.5-pro-001",
    "gemini-1.5-flash-001"
]

NON_SYS_INSTRUCT_GEM_MODELS = [
    "gemini-1.0-pro-001"
]

ALL_GEMINI_MODELS = SYS_INSTRUCT_MODELS + NON_SYS_INSTRUCT_GEM_MODELS

TEXT_GENERATION_MODELS = [
    "text-bison@002",
    "text-unicorn@001"
]
EMBEDDING_MODELS_NO_DIMENSIONALITY = [
    "textembedding-gecko@001",
    "textembedding-gecko@003",
    "textembedding-gecko-multilingual@001"
]
ALL_EMBEDDING_MODELS = EMBEDDING_MODELS_NO_DIMENSIONALITY + [
    "text-embedding-004"
]

ALL_GENERATIVE_MODELS = ALL_GEMINI_MODELS + TEXT_GENERATION_MODELS

# Define global scopes used for all Dialogflow CX Requests
GLOBAL_SCOPES = [
    "https://www.googleapis.com/auth/cloud-platform",
    "https://www.googleapis.com/auth/dialogflow",
    ]

class ScrapiBase:
    """Core Class for managing Auth and other shared functions."""

    def __init__(
        self,
        creds_path: str = None,
        creds_dict: Dict[str, str] = None,
        creds: service_account.Credentials = None,
        scope: List[str] = None,
        agent_id: str = None,
    ):

        self.scopes = GLOBAL_SCOPES
        if scope:
            self.scopes += scope

        if creds:
            self.creds = creds
            self.creds.refresh(Request())
            self.token = self.creds.token

        elif creds_path:
            self.creds = service_account.Credentials.from_service_account_file(
                creds_path, scopes=self.scopes
            )
            self.creds.refresh(Request())
            self.token = self.creds.token

        elif creds_dict:
            self.creds = service_account.Credentials.from_service_account_info(
                creds_dict, scopes=self.scopes
            )
            self.creds.refresh(Request())
            self.token = self.creds.token

        else:
            self.creds, _ = default()
            self.creds.refresh(Request())
            self.token = self.creds.token
            self._check_and_update_scopes(self.creds)

        self.agent_id = agent_id

        self.api_calls_dict = defaultdict(int)

    @staticmethod
    def _set_region(resource_id: str):
        """Different regions have different API endpoints

        Args:
          item_id: agent/flow/page - any type of long path id like
            `projects/<GCP PROJECT ID>/locations/<LOCATION ID>

        Returns:
          A dictionary containing the api_endpoint to use when
          instantiating other library client objects, or None
          if the location is "global"
        """
        if not resource_id:
            raise ValueError("resource_id must not be None.")

        try:
            location = resource_id.split("/")[3]
        except IndexError as err:
            logging.error("IndexError - path too short? %s", resource_id)
            raise err

        project_id = resource_id.split("/")[1]

        if location != "global":
            api_endpoint = f"{location}-dialogflow.googleapis.com:443"
            client_options = {
                "api_endpoint": api_endpoint,
                "quota_project_id": project_id}
            return client_options

        else:
            api_endpoint = "dialogflow.googleapis.com:443"
            client_options = {
                "api_endpoint": api_endpoint,
                "quota_project_id": project_id}

            return client_options

    @staticmethod
    def _client_options_discovery_engine(resource_id: str):
        """Different regions have different API endpoints

        Args:
          resource_id: any type of resource id associated with Discovery Engine
            resources. Ex: `projects/<GCP PROJECT ID>/locations/<LOCATION ID>`

        Returns:
          A dictionary containing the api_endpoint and quota project ID to use
          when calling Discovery Engine API endpoints.
        """
        try:
            location = resource_id.split("/")[3]
        except IndexError as err:
            logging.error("Please provide the fully qualified Resource ID: "
                          "%s", resource_id)
            raise err

        project_id = resource_id.split("/")[1]
        base_endpoint = "discoveryengine.googleapis.com:443"

        if location != "global":
            api_endpoint = f"{location}-{base_endpoint}"
            client_options = {
                "api_endpoint": api_endpoint,
                "quota_project_id": project_id}
            return client_options

        else:
            api_endpoint = base_endpoint
            client_options = {
                "api_endpoint": api_endpoint,
                "quota_project_id": project_id}

            return client_options

    @staticmethod
    def pbuf_to_dict(pbuf):
        """Extractor of json from a protobuf"""
        blobstr = json_format.MessageToJson(
            pbuf
        )
        blob = json.loads(blobstr)
        return blob

    @staticmethod
    def cx_object_to_json(cx_object):
        """Response objects have a magical _pb field attached"""
        return ScrapiBase.pbuf_to_dict(cx_object._pb)  # pylint: disable=W0212

    @staticmethod
    def cx_object_to_dict(cx_object):
        """Response objects have a magical _pb field attached"""
        return ScrapiBase.pbuf_to_dict(cx_object._pb)  # pylint: disable=W0212

    @staticmethod
    def extract_payload(msg):
        """Convert to json so we can get at the object"""
        blob = ScrapiBase.cx_object_to_dict(msg)
        return blob.get("payload")  # deref for nesting

    @staticmethod
    def dict_to_struct(some_dict: Dict[str, Any]):
        new_struct = struct_pb2.Struct()
        for k,v in some_dict.items():
            new_struct[k] = v

        return new_struct

    @staticmethod
    def str_to_dict(some_str: str) -> Dict[str, Any]:
        """Safe convert str to Dict or fail."""
        try:
            return json.loads(some_str)
        except json.JSONDecodeError as err:
            raise ValueError(f"Invalid JSON string: `{some_str}`") from err

    @staticmethod
    def parse_agent_id(resource_id: str):
        """Attempts to parse Agent ID from provided Resource ID."""
        parts = resource_id.split("/")
        if len(parts) < 6:
            raise ValueError(
                "Resource ID is too short to contain an Agent ID: {}".format(
                    resource_id
                )
            )

        if parts[4] != "agents":
            raise ValueError(
                "Resource ID does not contain an agent ID: {}".format(
                    resource_id
                )
            )

        return "/".join(parts[:6])

    @staticmethod
    def _parse_resource_path(
        resource_type,
        resource_id,
        validate=True) -> Dict[str, str]:
        # pylint: disable=line-too-long
        """Validates the provided Resource ID against known patterns.

        Args:
          resource_type, Must be one of the following resource types:
            `agent`, `entity_type`, `environmnet`, `flow`, `intent`, `page`,
            `project`, `security_setting`, `session`, `session_entity_type`,
            `test_case`, `transition_route_group`, `version`, `webhook`
          resource_id, The CX resource ID to check against the provided
            resource_type
          validate, allows the user to have their Resource ID validated along
            with returning the parts dictionary of the Resource ID. If set to
            True, this method will prompt the user with the correct format
            to utilize for the specified ID. If set to False, no validation
            will occur. If the input Resource ID is invalid when set to False,
            an empty Dictionary will be returned, allowing the caller to
            define their own ValueError message in a higher level class.
            Defaults to True.
        """

        data_store_match = r"[\w-]{1,947}"
        engine_match = r"[a-z0-9][a-z0-9-_]{0,62}"
        entity_id_match = r"[-@.0-9a-z]{1,36}"
        location_id_match = r"[-0-9a-z]{1,36}"
        page_id_match = r"[-0-9a-f]{1,36}|START_PAGE|END_SESSION|END_FLOW"
        session_id_match = r"[-0-9a-zA-Z!@#$%^&*()_+={}[\]:;\"'<>,.?]{1,36}"
        standard_id_match = r"[-0-9a-f]{1,36}"
        version_id_match = r"[0-9]{1,4}"

        matcher_root = f"^projects/(?P<project>.+?)/locations/(?P<location>{location_id_match})" # noqa: E501

        pattern_map = {
            "agent": {
                "matcher": fr"{matcher_root}/agents/(?P<agent>{standard_id_match})$", # noqa: E501
                "format": "`projects/<Project ID>/locations/<Location ID>/agents/<Agent ID>`", # noqa: E501
            },
            "data_store": {
                "matcher": fr"{matcher_root}/collections/default_collection/dataStores/(?P<data_store>{data_store_match})$", # noqa: E501
                "format": "`projects/<Project ID>/locations/<Location ID>/collections/default_collection/dataStores/<Data Store ID>`" # noqa: E501
            },
            "engine": {
                "matcher": fr"{matcher_root}/collections/default_collection/engines/(?P<engine>{engine_match})$", # noqa: E501
                "format": "`projects/<Project ID>/locations/<Location ID>/collections/default_collection/engines/<Engine ID>`" # noqa: E501
            },
            "entity_type": {
                "matcher": fr"{matcher_root}/agents/(?P<agent>{standard_id_match})/entityTypes/(?P<entity>{entity_id_match})$", # noqa: E501
                "format": "`projects/<Project ID>/locations/<Location ID>/agents/<Agent ID>/entityTypes/<Entity Types ID>`", # noqa: E501
            },
            "environment": {
                "matcher": fr"{matcher_root}/agents/(?P<agent>{standard_id_match})/environments/(?P<environment>{standard_id_match})$", # noqa: E501
                "format": "`projects/<Project ID>/locations/<Location ID>/agents/<Agent ID>/environments/<Environment ID>`", # noqa: E501
            },
            "flow": {
                "matcher": fr"{matcher_root}/agents/(?P<agent>{standard_id_match})/flows/(?P<flow>{standard_id_match})$", # noqa: E501
                "format": "`projects/<Project ID>/locations/<Location ID>/agents/<Agent ID>/flows/<Flow ID>`", # noqa: E501
            },
            "intent": {
                "matcher": fr"{matcher_root}/agents/(?P<agent>{standard_id_match})/intents/(?P<intent>{standard_id_match})$", # noqa: E501
                "format": "`projects/<Project ID>/locations/<Location ID>/agents/<Agent ID>/intents/<Intent ID>`", # noqa: E501
            },
            "page": {
                "matcher": fr"{matcher_root}/agents/(?P<agent>{standard_id_match})/flows/(?P<flow>{standard_id_match})/pages/(?P<page>{page_id_match})$", # noqa: E501
                "format": "`projects/<Project ID>/locations/<Location ID>/agents/<Agent ID>/flows/<Flow ID>/pages/<Page ID>`", # noqa: E501
            },
            "project": {
                "matcher": fr"{matcher_root}$",
                "format": "`projects/<Project ID>/locations/<Location ID>/`",
            },
            "security_setting": {
                "matcher": fr"{matcher_root}/securitySettings/(?P<security_setting>{standard_id_match})$", # noqa: E501
                "format": "`projects/<Project ID>/locations/<Location ID>/securitySettings/<Security Setting ID>`", # noqa: E501
            },
            "session": {
                "matcher": fr"{matcher_root}/agents/(?P<agent>{standard_id_match})(?:/environments/(?P<environment>{standard_id_match}))?/sessions/(?P<session>{session_id_match})$", # noqa: E501
                "format": "`projects/<Project ID>/locations/<Location ID>/agents/<Agent ID>/sessions/<Session ID>` or `projects/<Project ID>/locations/<Location ID>/agents/<Agent ID>/environments/<Environment ID>/sessions/<Session ID>`", # noqa: E501
            },
            "session_entity_type": {
                "matcher": fr"{matcher_root}/agents/(?P<agent>{standard_id_match})/sessions/(?P<session>{session_id_match})/entityTypes/(?P<entity>{entity_id_match})$", # noqa: E501
                "format": "`projects/<Project ID>/locations/<Location ID>/agents/<Agent ID>/sessions/<Session ID>/entityTypes/<Entity Type ID>`", # noqa: E501
            },
            "test_case": {
                "matcher": fr"{matcher_root}/agents/(?P<agent>{standard_id_match})/testCases/(?P<test_case>{standard_id_match})$", # noqa: E501
                "format": "`projects/<Project ID>/locations/<Location ID>/agents/<Agent ID>/testCases/<Test Case ID>`", # noqa: E501
            },
            "transition_route_group": {
                "matcher": fr"{matcher_root}/agents/(?P<agent>{standard_id_match})/flows/(?P<flow>{standard_id_match})/transitionRouteGroups/(?P<transition_route_group>{standard_id_match})$", # noqa: E501
                "format": "`projects/<Project ID>/locations/<Location ID>/agents/<Agent ID>/flows/<Flow ID>/transitionRouteGroups/<Transition Route Group ID>`", # noqa: E501
            },
            "version": {
                "matcher": fr"{matcher_root}/agents/(?P<agent>{standard_id_match})/flows/(?P<flow>{standard_id_match})/versions/(?P<version>{version_id_match})$", # noqa: E501
                "format": "`projects/<Project ID>/locations/<Location ID>/agents/<Agent ID>/flows/<Flow ID>`", # noqa: E501
            },
            "webhook": {
                "matcher": fr"{matcher_root}/agents/(?P<agent>{standard_id_match})/webhooks/(?P<webhook>{standard_id_match})$", # noqa: E501
                "format": "`projects/<Project ID>/locations/<Location ID>/agents/<Agent ID>`", # noqa: E501
            }
        }

        if resource_type not in pattern_map:
            raise KeyError(
                "`resource_type` must be one of the following resource types:"
                " `agent`, `data_store`, `engine`, `entity_type`, "
                "`environmnet`, `flow`, `intent`, `page`, `project`, "
                "`security_setting`, `session`, `session_entity_type`, "
                "`test_case`, `transition_route_group`, `version`, `webhook`"
            )

        match_res = re.match(pattern_map[resource_type]["matcher"], resource_id)
        dict_res = match_res.groupdict() if match_res else {}
        valid_parse = False

        if dict_res:
            valid_parse = True

        if validate and not valid_parse:
            raise ValueError(
                f"{resource_type.capitalize()} ID must be provided in the "
                f"following format: "
                f"{pattern_map[resource_type]['format']}"
            )

        # pylint: enable=line-too-long
        return dict_res

    @staticmethod
    def _validate_data_store_id(data_store_id: str):
        """Validate the data store ID and extract the ID if needed."""
        pattern = (r"^projects/(?P<project>.+?)/locations/"
                   r"(?P<location>[-0-9a-z]{1,36})/collections/"
                   r"default_collection/dataStores/"
                   r"(?P<data_store>[\w-]{1,947})$"
                   )
        match_res = re.match(pattern, data_store_id)
        if match_res:
            parts = match_res.groupdict()
            data_store_id = parts.get("data_store")

        return data_store_id

    @staticmethod
    def _get_solution_type(solution_type: str) -> int:
        """Get SOLUTION_TYPE from simple name reference."""
        solution_map = {
            "recommendation": 1,
            "search": 2,
            "chat": 3,
        }

        res = solution_map.get(solution_type, None)
        if not res:
            raise ValueError("Solution Type must be one of the following values"
                             ": `chat`, `search`, `recommendation`")

        return solution_map[solution_type]

    @staticmethod
    def is_valid_sys_instruct_model(llm_model: str) -> bool:
        valid_sys_instruct = True
        """Validate if model allows system instructions."""
        if llm_model in NON_SYS_INSTRUCT_GEM_MODELS:
            valid_sys_instruct = False

        return valid_sys_instruct

    @staticmethod
    def _update_kwargs(obj, **kwargs) -> field_mask_pb2.FieldMask:
        """Create a FieldMask for Environment, Experiment, TestCase, Version."""
        if kwargs:
            for key, value in kwargs.items():
                setattr(obj, key, value)
            return field_mask_pb2.FieldMask(paths=kwargs.keys())
        attrs_map = {
            "Environment": [
                "name", "display_name", "description", "version_configs",
                "update_time", "test_cases_config", "webhook_config",
            ],
            "Experiment": [
                "name", "display_name", "description", "state", "definition",
                "rollout_config", "rollout_state", "rollout_failure_reason",
                "result", "create_time", "start_time", "end_time",
                "last_update_time", "experiment_length", "variants_history",
            ],
            "TestCase": [
                "name", "tags", "display_name", "notes", "test_config",
                "test_case_conversation_turns", "creation_time",
                "last_test_result",
            ],
            "Version": [
                "name", "display_name", "description", "nlu_settings",
                "create_time", "state",
            ],
        }
        if isinstance(obj, types.Environment):
            paths = attrs_map["Environment"]
        elif isinstance(obj, types.Experiment):
            paths = attrs_map["Experiment"]
        elif isinstance(obj, types.TestCase):
            paths = attrs_map["TestCase"]
        elif isinstance(obj, types.Version):
            paths = attrs_map["Version"]
        else:
            raise ValueError(
                "`obj` should be one of the following:"
                " [Environment, Experiment, TestCase, Version]."
            )

        return field_mask_pb2.FieldMask(paths=paths)

    @staticmethod
    def set_logging_level(level: str):
        LOGGING_MAP = {
            "info": logging.INFO,
            "warn": logging.WARN,
            "error": logging.ERROR,
            "debug": logging.DEBUG
        }

        logging.basicConfig(
            level=LOGGING_MAP[level],
            format="%(asctime)s %(levelname)-8s %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
            force=True
        )

    def build_safety_settings(
            self,
            safety_config: Optional[Dict[str, str]] = None
            ):
        """Build a SafetyConfig payload for Gemini SDK calls.

        If a safety_config dict is not provided, we'll set the defaults to OFF.

        Args:
            safety_config: (Optional) A key / value pair dictionary containing
            the category names and thresholds to set for each category. If not
            provided, the default threshold will be used as defined below.
        """
        # https://cloud.google.com/vertex-ai/generative-ai/docs/multimodal/configure-safety-filters#harm_categories
        CATEGORY_MAP = {
            "hate_speech": HarmCategory.HARM_CATEGORY_HATE_SPEECH,
            "harassment": HarmCategory.HARM_CATEGORY_HARASSMENT,
            "sexually_explicit": HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
            "dangerous_content": HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT
        }

        # https://cloud.google.com/vertex-ai/generative-ai/docs/multimodal/configure-safety-filters#how_to_configure_safety_filters
        THRESHOLD_MAP = {
            "low": HarmBlockThreshold.BLOCK_LOW_AND_ABOVE,
            "medium": HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
            "high": HarmBlockThreshold.BLOCK_ONLY_HIGH,
            "off": HarmBlockThreshold.OFF,
            "none": HarmBlockThreshold.BLOCK_NONE
            }

        if not safety_config:
            safety_list = [
                SafetySetting(
                    category=HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
                    threshold=HarmBlockThreshold.OFF
                ),
                SafetySetting(
                    category=HarmCategory.HARM_CATEGORY_HATE_SPEECH,
                    threshold=HarmBlockThreshold.OFF
                ),
                SafetySetting(
                    category=HarmCategory.HARM_CATEGORY_HARASSMENT,
                    threshold=HarmBlockThreshold.OFF
                ),
                SafetySetting(
                    category=HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
                    threshold=HarmBlockThreshold.OFF
                )
            ]

        elif safety_config:
            safety_list: List[SafetySetting] = []
            for category, threshold in safety_config.items():
                try:
                    safety_list.append(
                        SafetySetting(
                            category=CATEGORY_MAP[category],
                            threshold=THRESHOLD_MAP[threshold]
                            )
                        )
                except KeyError as ke:
                    available_categories = ", ".join(CATEGORY_MAP.keys())
                    available_thresholds = ", ".join(THRESHOLD_MAP.keys())
                    raise KeyError(
                        f"Invalid key provided: {ke}. Available categories: "\
                        f"[{available_categories}]. Available thresholds: "\
                        f"[{available_thresholds}]") from ke

        return safety_list

    @staticmethod
    def _handle_requests_response(response: requests.Response):
        """Simple response wrapper for common directl requests API requests.

        Args:
          response: The Python requests.Response after directly invoking REST
          APIs without the Python SDK.

        Returns:
          The API response JSON data, or None.
        """
        if response.status_code == 200:
            data = response.json()
            return data
        elif response.status_code == 404:
            return None
        else:
            raise requests.exceptions.RequestException(
                "API request failed", response.status_code, response)

    def _set_request_headers(self, client_options: dict):
        """Different regions have different API endpoints

        Args:
          client_options: A dictionary containing the api_endpoint to use when
          instantiating other library client objects, or None
          if the location is "global"

        Returns:
          The HTTP headers for authenticating and setting the GCP quota project.
        """
        return {
            'Authorization': f'Bearer {self.token}',
            'x-goog-user-project': client_options['quota_project_id']
        }

    def _check_and_update_scopes(self, creds: Any):
        """Update Credentials scopes if possible based on creds type."""
        if creds.requires_scopes:
            self.creds.scopes.extend(GLOBAL_SCOPES)

        else:
            logging.info("Found user creds, skipping global scopes...")

    def build_generative_model(
            self,
            llm_model: str,
            system_instructions: str = None
            ) -> GenerativeModel:
        """Build the GenertiveModel object and sys instructions as required."""
        valid_sys_intruct = self.is_valid_sys_instruct_model(llm_model)

        if valid_sys_intruct and system_instructions:
            return GenerativeModel(
                llm_model, system_instruction=system_instructions)

        elif not valid_sys_intruct and system_instructions:
            raise ValueError(
                f"Model `{llm_model}` does not support System Instructions"
                )
        else:
            return GenerativeModel(llm_model)



    def model_setup(self, llm_model: str, system_instructions: str = None):
        """Create a new LLM instance from user inputs."""
        if llm_model in ALL_EMBEDDING_MODELS:
            return TextEmbeddingModel.from_pretrained(llm_model)

        elif llm_model in ALL_GEMINI_MODELS:
            return self.build_generative_model(llm_model, system_instructions)

        elif llm_model in TEXT_GENERATION_MODELS:
            return TextGenerationModel.from_pretrained(llm_model)

        else:
            raise ValueError(f"LLM Model `{llm_model}` not supported.")

    def init_vertex(self, agent_id: str):
        """Use the Agent ID to parse out relevant fields and init Vertex API."""
        parts = self._parse_resource_path("agent", agent_id)
        project_id = parts.get("project")
        location = parts.get("location")

        # Vertex doesn't support global region at this time, but Agent Builder
        # and DFCX do. If this method is used in conjunction with an agent_id
        # that is located in `global` region, we will fallback to `us-central1`
        # to init Vertex.
        location = "us-central1" if location == "global" else location

        vertexai.init(project=project_id, location=location)

    def _build_data_store_parent(self, location: str) -> str:
        """Build the Parent ID needed for Discovery Engine API calls."""
        return (f"projects/{self.project_id}/locations/{location}/collections/"
                  "default_collection")

    def recurse_proto_repeated_composite(self, repeated_object):
        repeated_list = []
        for item in repeated_object:
            if isinstance(item, repeated.RepeatedComposite):
                item = self.recurse_proto_repeated_composite(item)
                repeated_list.append(item)
            elif isinstance(item, maps.MapComposite):
                item = self.recurse_proto_marshal_to_dict(item)
                repeated_list.append(item)
            else:
                repeated_list.append(item)

        return repeated_list

    def recurse_proto_marshal_to_dict(self, marshal_object):
        new_dict = {}
        for k, v in marshal_object.items():
            if isinstance(v, maps.MapComposite):
                v = self.recurse_proto_marshal_to_dict(v)
            elif isinstance(v, repeated.RepeatedComposite):
                v = self.recurse_proto_repeated_composite(v)
            new_dict[k] = v

        return new_dict

    def get_api_calls_details(self) -> Dict[str, int]:
        """The number of API calls corresponding to each method.

        Returns:
          A dictionary with keys as the method names
          and values as the number of calls.
        """
        this_class_methods, sub_class_apis_dict = {}, {}

        for attr_name in dir(self):
            attr = getattr(self, attr_name)
            if callable(attr) and hasattr(attr, "calls_api"):
                this_class_methods[attr_name] = 0
            if any(
                isinstance(attr, sub_class)
                for sub_class in ScrapiBase.__subclasses__()
            ):
                sub_class_apis_dict.update(attr.get_api_calls_details())

        if hasattr(self, "api_calls_dict"):
            this_class_methods.update(getattr(self, "api_calls_dict"))

        return {**this_class_methods, **sub_class_apis_dict}

    def get_api_calls_count(self) -> int:
        """Show the total number of API calls for this resource.

        Returns:
          Total calls to the API so far as an int.
        """
        return sum(self.get_api_calls_details().values())

def api_call_counter_decorator(func):
    """Counts the number of API calls for the function `func`."""

    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        self.api_calls_dict[func.__name__] += 1
        return func(self, *args, **kwargs)

    wrapper.calls_api = True

    return wrapper

def should_retry(err: exceptions.GoogleAPICallError) -> bool:
  """Helper function for deciding whether we should retry the error or not."""
  return isinstance(err, (exceptions.TooManyRequests, exceptions.ServerError))

def ratelimit(rate: float):
  """Decorator that controls the frequency of function calls."""
  seconds_per_event = 1.0 / rate
  lock = threading.Lock()
  bucket = 0
  last = 0

  def decorate(func):
    def rate_limited_function(*args, **kwargs):
      nonlocal last, bucket
      while True:
        with lock:
          now = time.time()
          bucket += now - last
          last = now

          # capping the bucket in order to avoid accumulating too many
          bucket = min(bucket, seconds_per_event)

          # if bucket is less than `seconds_per_event` then we have to wait
          # `seconds_per_event` - `bucket` seconds until a new "token" is
          # refilled
          delay = max(seconds_per_event - bucket, 0)

          if delay == 0:
            # consuming a token and breaking out of the delay loop to perform
            # the function call
            bucket -= seconds_per_event
            break
        time.sleep(delay)
      return func(*args, **kwargs)
    return rate_limited_function
  return decorate

def retry_api_call(retry_intervals: Iterable[float]):
  """Decorator for retrying certain GoogleAPICallError exception types."""
  def decorate(func):
    def retried_api_call_func(*args, **kwargs):
      interval_iterator = iter(retry_intervals)
      while True:
        try:
          return func(*args, **kwargs)
        except exceptions.GoogleAPICallError as err:
          print(f"retrying api call: {err}")
          if not should_retry(err):
            raise

          interval = next(interval_iterator, _INTERVAL_SENTINEL)
          if interval is _INTERVAL_SENTINEL:
            raise
          time.sleep(interval)
    return retried_api_call_func
  return decorate

def handle_api_error(func):
  """Decorator that chatches GoogleAPICallError exception and returns None."""
  def handled_api_error_func(*args, **kwargs):
    try:
      return func(*args, **kwargs)
    except exceptions.GoogleAPICallError as err:
      print(f"failed api call: {err}")
      return None

  return handled_api_error_func
