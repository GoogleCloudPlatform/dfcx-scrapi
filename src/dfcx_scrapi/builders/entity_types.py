"""A set of builder methods to create CX proto resource objects"""

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
from typing import List, Union

from google.cloud.dialogflowcx_v3beta1.types import EntityType
from dfcx_scrapi.builders.builders_common import BuildersCommon

# logging config
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


class EntityTypeBuilder(BuildersCommon):
    """Base Class for CX EntityType builder."""

    _proto_type = EntityType
    _proto_type_str = "EntityType"


    def __str__(self) -> str:
        """String representation of the proto_obj."""
        self._check_proto_obj_attr_exist()

        return (
            f"{self._show_entity_type_basic_info()}"
            f"\n{self._show_excluded_phrases()}"
            f"\n{self._show_entities()}")


    def _show_entity_type_basic_info(self) -> str:
        """Shows the information of proto_obj."""
        self._check_proto_obj_attr_exist()

        return (
            f"display_name: {self.proto_obj.display_name}"
            f"\nkind: {self.proto_obj.kind.name}"
            f"\nauto_expansion_mode: {self.proto_obj.auto_expansion_mode}"
            "\nenable_fuzzy_extraction:"
            f" {self.proto_obj.enable_fuzzy_extraction}"
            f"\nredact: {self.proto_obj.redact}")

    def _show_excluded_phrases(self) -> str:
        """Shows the excluded phrases of proto_obj."""
        self._check_proto_obj_attr_exist()

        excluded_phrases = "\n\t".join([
            phrase.value
            for phrase in self.proto_obj.excluded_phrases
        ])

        return f"excluded phrases:\n\t{excluded_phrases}"

    def _show_entities(self) -> str:
        """Shows the entities of proto_obj."""
        self._check_proto_obj_attr_exist()

        entities =  "\n".join([
            f"  {entity.value}:\n\t{', '.join(entity.synonyms)}"
            for entity in self.proto_obj.entities
        ])

        return f"entities:\n{entities}"


    def show_entity_type(self, mode: str = "whole"):
        """Show the proto_obj information.

        Args:
          mode (str):
            Specifies what part of the entity type to show.
            Options:
              ['basic', 'entities', 'excluded' or 'excluded phrases', 'whole']
        """
        self._check_proto_obj_attr_exist()

        if mode == "basic":
            print(self._show_entity_type_basic_info())
        elif mode == "entities":
            print(self._show_entities())
        elif mode in ["excluded", "excluded phrases"]:
            print(self._show_excluded_phrases())
        elif mode == "whole":
            print(self)
        else:
            raise ValueError(
                "mode should be in"
                "['basic', 'entities',"
                " 'excluded' or 'excluded phrases', 'whole']"
            )


    def create_new_proto_obj(
        self,
        display_name: str,
        kind: int,
        auto_expansion_mode: int = 0,
        enable_fuzzy_extraction: bool = False,
        redact: bool = False,
        overwrite: bool = False
    ) -> EntityType:
        """Create a new EntityType.

        Args:
          display_name (str):
            The human-readable name of the
            entity type, unique within the agent.
          kind (int):
            Represents kinds of entities.
              1 = KIND_MAP
              2 = KIND_LIST
              3 = KIND_REGEXP
          auto_expansion_mode (int):
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
        if not isinstance(display_name, str):
            raise ValueError(
                "display_name should be a string."
            )
        if not (isinstance(kind, int) and 1 <= kind <= 3):
            raise ValueError(
                "kind should be an int between 0 and 3."
            )
        if self.proto_obj and not overwrite:
            raise UserWarning(
                "proto_obj already contains an EntityType."
                " If you wish to overwrite it, pass overwrite as True."
            )
        if overwrite or not self.proto_obj:
            self.proto_obj = EntityType(
                display_name=display_name,
                kind=kind,
                auto_expansion_mode=auto_expansion_mode,
                enable_fuzzy_extraction=enable_fuzzy_extraction,
                redact=redact
            )

        return self.proto_obj


    def add_excluded_phrase(
        self, phrase: Union[str, List[str]]
    ) -> EntityType:
        """Add one or more phrases to be excluded in the EntityType.

        Args:
          phrase (str | List[str]):
            A single phrase as a string
            or multiple phrases as a list of strings

        Returns:
          An EntityType object stored in proto_obj
        """
        self._check_proto_obj_attr_exist()

        if isinstance(phrase, str):
            self.proto_obj.excluded_phrases.append(
                EntityType.ExcludedPhrase(value=phrase)
            )
        elif isinstance(phrase, list):
            if not all((isinstance(p, str) for p in phrase)):
                raise ValueError(
                    "Only strings are allowed in the phrase list."
                )

            self.proto_obj.excluded_phrases.extend([
                EntityType.ExcludedPhrase(value=value)
                for value in phrase])

        else:
            raise ValueError(
                "phrase should be either a string or a list of strings."
            )

        return self.proto_obj


    def remove_excluded_phrase(
        self, phrase: Union[str, List[str]]
    ) -> EntityType:
        """Remove one or more phrases from excluded phrases in the EntityType.

        Args:
          phrase (str | List[str]):
            A single phrase as a string
            or multiple phrases as a list of strings

        Returns:
          An EntityType object stored in proto_obj
        """
        self._check_proto_obj_attr_exist()

        excl_phrases = {
            excl_phrase.value
            for excl_phrase in self.proto_obj.excluded_phrases
        }
        if isinstance(phrase, str):
            excl_phrases -= {phrase}
        elif isinstance(phrase, list):
            if not all((isinstance(p, str) for p in phrase)):
                raise ValueError(
                    "Only strings are allowed in the phrase list."
                )
            excl_phrases -= set(phrase)
        else:
            raise ValueError(
                "phrase should be either a string or a list of strings."
            )
        # Remove all excluded phrases and add new ones from the excl_phrases set
        self.proto_obj.excluded_phrases.clear()
        self.proto_obj.excluded_phrases.extend([
            EntityType.ExcludedPhrase(value=excl_phrase)
            for excl_phrase in excl_phrases
        ])

        return self.proto_obj


    def add_entity(
        self, value: str, synonyms: List[str] = None
    ) -> EntityType:
        """Add an entity to the EntityType stored in proto_obj

        Args:
          value (str):
            Required. The primary value associated with this entity
            entry. For example, if the entity type is *vegetable*, the
            value could be *scallions*.
            For ``KIND_MAP`` entity types:
            -  A canonical value to be used in place of synonyms.
          synonyms (List[str]):
            Required only for ``KIND_MAP``.
            A collection of value synonyms. For example, if
            the entity type is *vegetable*, and ``value`` is
            *scallions*, a synonym could be *green onions*.

        Returns:
          An EntityType object stored in proto_obj
        """
        self._check_proto_obj_attr_exist()

        if not isinstance(value, str):
            raise ValueError(
                "value should be string."
            )

        if self.proto_obj.kind.name in ["KIND_LIST", "KIND_REGEXP"]:
            self.proto_obj.entities.append(
                EntityType.Entity(
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
                EntityType.Entity(
                    value=value, synonyms=synonyms
                )
            )
        else:
            raise ValueError(
                "Entity type's kind is not correct and should be specified."
            )

        return self.proto_obj


    def remove_entity(
        self, value: str, synonyms: List[str] = None
    ) -> EntityType:
        """Remove an entity or synonym from the EntityType stored in proto_obj.
        For `KIND_MAP` if synonym was not provided, the whole entity
        will be removed, otherwise the synonyms associated with
        the value will be removed.

        Args:
          value (str):
            Required. The primary value associated with this entity
            entry to remove. For example, if the entity type is *vegetable*,
            the value could be *scallions*.
            For `KIND_MAP` entity types:
            -  A canonical value to be used in place of synonyms.
          synonyms (List[str]):
            Required only for `KIND_MAP`.
            A collection of value synonyms to be removed. For example, if
            the entity type is *vegetable*, and `value` is
            *scallions*, a synonym could be *green onions*.

        Returns:
          An EntityType object stored in proto_obj
        """
        self._check_proto_obj_attr_exist()

        if not isinstance(value, str):
            raise ValueError(
                "value should be string."
            )

        if not synonyms:
            for idx, entity in enumerate(self.proto_obj.entities):
                if entity.value == value:
                    del self.proto_obj.entities[idx]
                    break
        elif self.proto_obj.kind.name == "KIND_MAP":
            if not (
                isinstance(synonyms, list) and
                all((isinstance(s, str) for s in synonyms))
            ):
                raise ValueError(
                    "synonyms should be a list of strings."
                )

            for entity in self.proto_obj.entities:
                if entity.value == value:
                    new_synonyms = list(set(entity.synonyms) - set(synonyms))
                    entity.synonyms.clear()
                    entity.synonyms.extend(new_synonyms)
                    break

        return self.proto_obj
