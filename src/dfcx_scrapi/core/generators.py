"""Generators Resource functions."""

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

import re
import logging
from typing import Dict, List, Any

from google.cloud.dialogflowcx_v3beta1 import services
from google.cloud.dialogflowcx_v3beta1 import types
from google.protobuf import field_mask_pb2

from dfcx_scrapi.core import scrapi_base

# logging config
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


class Generators(scrapi_base.ScrapiBase):
    """Core Class for CX Generators Resource functions."""

    def __init__(
        self,
        creds_path: str = None,
        creds_dict: Dict = None,
        creds=None,
        scope=False,
        agent_id: str = None,
    ):
        super().__init__(
            creds_path=creds_path,
            creds_dict=creds_dict,
            creds=creds,
            scope=scope,
        )

        if agent_id:
            self.agent_id = agent_id

    @staticmethod
    def __get_placeholders(
        prompt: str,
    ) -> List[types.generator.Generator.Placeholder]:
        """Parse any placeholders from the prompt."""
        placeholders = []
        pattern = r"\$(?:\s+)?([a-zA-Z0-9_]+)"
        matches = re.findall(pattern, prompt)
        for match in matches:
            placeholder = types.generator.Generator.Placeholder()
            placeholder.id = match
            placeholder.name = match
            placeholders.append(placeholder)

        return placeholders

    @staticmethod
    def __input_validation(
        display_name: str, prompt: str, obj: types.Generator
    ):
        """Validate incoming input for Create Generator."""
        if not display_name or obj:
            raise ValueError(
                "At least display_name or obj should be specified."
            )

        if display_name and not obj and not prompt:
            raise ValueError("`prompt` value should be specified.")

    @staticmethod
    def __clean_update_kwargs(
        kwargs: Dict[str, Any], generator: types.Generator
    ):
        """Clean up kwargs before adding to paths for updating the Generator.

        We're providing a few quality of life additions "under the hood" so the
        user doesn't have to recall all of the specific kwargs for the object.
        Specifically, they can pass `prompt` instead of `prompt_text` and we'll
        update appropriately. Additionally we'll detect any placeholders and
        make these updates as well.
        """
        if "prompt" in kwargs:
            kwargs["prompt_text"] = kwargs["prompt"]
            del kwargs["prompt"]

        if len(generator.placeholders) > 0:
            kwargs["placeholders"] = generator.placeholders

        return kwargs

    def get_generators_map(
        self, agent_id: str, reverse=False
    ) -> Dict[str, str]:
        """Put Generator Display Names and UUIDs into a user friendly map."""
        if reverse:
            gen_dict = {
                gen.display_name: gen.name
                for gen in self.list_generators(agent_id=agent_id)
            }

        else:
            gen_dict = {
                gen.name: gen.display_name
                for gen in self.list_generators(agent_id=agent_id)
            }

        return gen_dict

    @scrapi_base.api_call_counter_decorator
    def list_generators(self, agent_id: str) -> List[types.generator.Generator]:
        """Retrieves a list of Generators based on the Agent ID."""

        request = types.generator.ListGeneratorsRequest()
        request.parent = agent_id

        client_options = self._set_region(agent_id)
        client = services.generators.GeneratorsClient(
            credentials=self.creds, client_options=client_options
        )

        response = client.list_generators(request)

        generators = []
        for page in response.pages:
            for generator in page.generators:
                generators.append(generator)

        return generators

    @scrapi_base.api_call_counter_decorator
    def get_generator(self, generator_id: str) -> types.Generator:
        """Retrieves a single CX Generator resource object.

        Args:
          generator_id: The formatted CX Generator ID

        Returns:
          A single CX Generator resource object
        """

        request = types.generator.GetGeneratorRequest()
        request.name = generator_id

        client_options = self._set_region(generator_id)
        client = services.generators.GeneratorsClient(
            credentials=self.creds, client_options=client_options
        )

        response = client.get_generator(request)

        return response

    @scrapi_base.api_call_counter_decorator
    def create_generator(
        self,
        agent_id: str,
        display_name: str = None,
        prompt: str = None,
        obj: types.Generator = None,
    ):
        """Create a Dialogflow CX Generator."""
        self.__input_validation(display_name, prompt, obj)

        if obj:
            generator_obj = obj
            generator_obj.name = ""

        else:
            generator_obj = types.Generator()
            generator_obj.display_name = display_name
            generator_obj.prompt_text.text = prompt
            generator_obj.placeholders = self.__get_placeholders(prompt)

        client_options = self._set_region(agent_id)
        client = services.generators.GeneratorsClient(
            credentials=self.creds, client_options=client_options
        )
        response = client.create_generator(
            parent=agent_id, generator=generator_obj
        )

        return response

    @scrapi_base.api_call_counter_decorator
    def update_generator(
        self, generator_id: str, obj: types.Generator = None, **kwargs
    ) -> types.Generator:
        """Updates a single Generator object based on provided kwargs.

        Args:
          generator_id: CX Generator ID string in the following format
              projects/<PROJECT ID>/locations/<LOCATION ID>/
                generators/<GENERATOR ID>
          obj: (Optional) The CX Generator object in proper format. This can
            also be extracted by using the get_generator() method.
          kwargs: You may find a list of generator attributes here:
              https://cloud.google.com/python/docs/reference/dialogflow-cx/
                  latest/google.cloud.dialogflowcx_v3beta1.types.Generator
        Returns:
          The updated CX Generator resource object.
        """

        if obj:
            generator = obj
            generator.name = generator_id
        else:
            generator = self.get_generator(generator_id)

        # set generator attributes to args
        for key, value in kwargs.items():
            if key in ["prompt", "prompt_text"]:
                generator.prompt_text.text = value
                generator.placeholders = self.__get_placeholders(value)
            else:
                setattr(generator, key, value)

        kwargs = self.__clean_update_kwargs(kwargs, generator)
        paths = kwargs.keys()

        mask = field_mask_pb2.FieldMask(paths=paths)

        client_options = self._set_region(generator_id)
        client = services.generators.GeneratorsClient(
            credentials=self.creds, client_options=client_options
        )
        response = client.update_generator(
            generator=generator, update_mask=mask
        )

        return response

    @scrapi_base.api_call_counter_decorator
    def delete_generator(self, generator_id: str):
        """Deletes the specified Dialogflow CX Generator.

        Args:
          generator_id: CX Generator ID string in the following format
            projects/<PROJECT ID>/locations/<LOCATION ID>/
              generators/<GENERATOR ID>
        """
        client_options = self._set_region(generator_id)
        client = services.generators.GeneratorsClient(
            credentials=self.creds, client_options=client_options
        )
        client.delete_generator(name=generator_id)
