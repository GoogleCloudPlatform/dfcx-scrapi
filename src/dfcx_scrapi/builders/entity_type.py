"""A set of builder methods to create CX proto resource objects"""

# Copyright 2022 Google LLC
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

from typing import List, Union

from google.cloud.dialogflowcx_v3beta1 import types


class EntityTypeBuilder:
    """Base Class for CX EntityType builder."""

    def __init__(self, obj: types.EntityType = None):
        self.proto_obj = None
        if obj:
            self.load_entity_type(obj)


    def _check_entity_type_exist(self):
        """Check if the proto_obj exists otherwise raise an error."""

        if not self.proto_obj:
            raise ValueError(
                "There is no proto_obj!\nUse create_empty_entity_type"
                " or load_entity_type to continue."
            )
        elif not isinstance(self.proto_obj, types.EntityType):
            raise ValueError(
                "proto_obj is not an EntityType."
                "\nPlease create or load the correct type to continue."
            )


    def load_entity_type(
        self, obj: types.EntityType, overwrite: bool = False
    ) -> types.EntityType:
        """Load an existing EntityType to proto_obj for further uses.

        Args:
          obj (EntityType):
            An existing EntityType obj.
          overwrite (bool)
            Overwrite the new proto_obj if proto_obj already
            contains an EntityType.

        Returns:
          An EntityType object stored in proto_obj
        """
        if not isinstance(obj, types.EntityType):
            raise ValueError(
                "The object you're trying to load is not an EntityType!"
            )
        if self.proto_obj and not overwrite:
            raise Exception(
                "proto_obj already contains an EntityType."
                " If you wish to overwrite it, pass overwrite as True."
            )

        if overwrite or not self.proto_obj:
            self.proto_obj = obj

        return self.proto_obj


    def create_empty_entity_type(
        self,
        display_name: str,
        kind: int,
        auto_expansion_mode: int = 0,
        enable_fuzzy_extraction: bool = False,
        redact: bool = False,
        overwrite: bool = False
    ) -> types.EntityType:
        """Create an empty EntityType.

        Args:
          display_name (str)
            The human-readable name of the
            entity type, unique within the agent.
          kind (int)
            Represents kinds of entities.
              0 = KIND_UNSPECIFIED
              1 = KIND_MAP
              2 = KIND_LIST
              3 = KIND_REGEXP
          auto_expansion_mode (Optional int)
            Indicates whether the entity type can be
            automatically expanded.
              AUTO_EXPANSION_MODE_UNSPECIFIED = 0
              AUTO_EXPANSION_MODE_DEFAULT = 1
          enable_fuzzy_extraction (bool):
            Enables fuzzy entity extraction during
            classification.
          redact (bool):
            Indicates whether parameters of the entity
            type should be redacted in log. If redaction is
            enabled, page parameters and intent parameters
            referring to the entity type will be replaced by
            parameter name during logging.
          overwrite (bool)
            Overwrite the new proto_obj if proto_obj already
            contains an EntityType.

        Returns:
          An EntityType object stored in proto_obj
        """
        if self.proto_obj and not overwrite:
            raise Exception(
                "proto_obj already contains an EntityType."
                " If you wish to overwrite it, pass overwrite as True."
            )
        if overwrite or not self.proto_obj:
            self.proto_obj = types.EntityType(
                display_name=display_name,
                kind=kind,
                auto_expansion_mode=auto_expansion_mode,
                enable_fuzzy_extraction=enable_fuzzy_extraction,
                redact=redact
            )

        return self.proto_obj


    def add_excluded_phrase(
        self, phrase: Union[str, List[str]]
    ) -> types.EntityType:
        """Add one or more phrases to be excluded in the EntityType
        Args:
          phrase (str | List[str]):
            A single phrase as a string
              or multiple phrases as a list of strings

        Returns:
          An EntityType object stored in proto_obj
        """
        self._check_entity_type_exist()

        if isinstance(phrase, str):
            self.proto_obj = self.proto_obj.excluded_phrases.append(
                types.entity_type.EntityType.ExcludedPhrase(value=phrase)
            )
        elif isinstance(phrase, list):
            if not all((isinstance(p, str) for p in phrase)):
                raise ValueError(
                    "Only strings allowed in phrase list."
                )

            self.proto_obj = self.proto_obj.excluded_phrases.extend([
                types.entity_type.EntityType.ExcludedPhrase(value=value)
                for value in phrase
            ])
        else:
            raise ValueError(
                "phrase should be either a string or a list of strings."
            )

        return self.proto_obj


    def add_entity(
        self, value: str, synonyms: List[str] = None
    ) -> types.EntityType:
        """docs here!"""
        self._check_entity_type_exist()

        if not isinstance(value, str):
            raise ValueError(
                "value should be string."
            )

        if self.proto_obj.kind.name in ["KIND_LIST", "KIND_REGEXP"]:
            self.proto_obj.entities.append(
                types.EntityType.Entity(
                    value=value, synonyms=[value]
                )
            )
        elif self.proto_obj.kind.name == "KIND_MAP":
            if not (
                isinstance(synonyms, list) and
                all((isinstance(s, str) for s in synonyms))
            ):
                raise ValueError(
                    "synonyms should be a list of strings."
                )

            self.proto_obj.entities.append(
                types.EntityType.Entity(
                    value=value, synonyms=synonyms
                )
            )
        else:
            raise Exception(
                "The kind of entity type is not correct."
            )

        return self.proto_obj


    def show_entity_type_info(self):
        """Shows the information of proto_obj."""
        self._check_entity_type_exist()

        print(
            f"display_name: {self.proto_obj.display_name}"
            f"\nkind: {self.proto_obj.kind.name}"
            f"\nauto_expansion_mode: {self.proto_obj.auto_expansion_mode}"
            "\nenable_fuzzy_extraction:"
            f" {self.proto_obj.enable_fuzzy_extraction}"
            f"\nredact: {self.proto_obj.redact}"
            # Excluded Phrases
            # Entities
        )
