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

from collections import defaultdict
from typing import List, Dict, Union

from google.cloud.dialogflowcx_v3beta1.types import Intent


class IntentBuilder:
    """Base Class for CX Intent builder."""

    def __init__(self, obj: Intent = None):
        self.proto_obj = None
        if obj:
            self.load_intent(obj)


    def __str__(self) -> str:
        """String representation of the proto_obj."""
        self._check_intent_exist()

        return (f"{self._show_basic_info()}"
            f"\n\n{self._show_parameters()}"
            f"\n\n{self._show_training_phrases()}")


    def _check_intent_exist(self):
        """Check if the proto_obj exists otherwise raise an error."""
        if not self.proto_obj:
            raise ValueError(
                "There is no proto_obj!"
                "\nUse create_new_intent or load_intent to continue."
            )
        elif not isinstance(self.proto_obj, Intent):
            raise ValueError(
                "proto_obj is not an Intent type."
                "\nPlease create or load the correct type to continue."
            )


    def _show_basic_info(self) -> str:
        """String representation for the basic information of proto_obj."""
        self._check_intent_exist()

        labels = [
            str(key) if key == val else f"{key}: {val}"
            for key, val in self.proto_obj.labels.items()
        ]
        return (f"display_name: {self.proto_obj.display_name}"
            f"\ndescription: {self.proto_obj.description}"
            f"\npriority: {self.proto_obj.priority}"
            f"\nis_fallback: {self.proto_obj.is_fallback}"
            f"\nlabels: {labels}")


    def _show_parameters(self) -> str:
        """String representation for the parameters of proto_obj."""
        self._check_intent_exist()

        return "\n".join([
            (f"parameter_id: {str(param.id)}"
            f"\nentity_type: {str(param.entity_type)}"
            f"\n\tis_list: {bool(param.is_list)}"
            f"\n\tredact: {bool(param.redact)}")
            for param in self.proto_obj.parameters
        ])


    def _show_training_phrases(self, repeat_count: int = None) -> str:
        """String representation for the training phrases of proto_obj."""
        self._check_intent_exist()

        phrases = []
        for tp in self.proto_obj.training_phrases:
            if repeat_count and tp.repeat_count != repeat_count:
                continue
            phrase = "".join([part.text for part in tp.parts])
            annotations = {
                part.text: part.parameter_id
                for part in tp.parts
                if part.parameter_id
            }
            phrases.append(
                f"phrase: {phrase}"
                f"\nannotations: {str(annotations)}"
                f"\n\trepeat_count: {tp.repeat_count}"
            )

        return "\n".join(phrases)


    def show_intent(
        self, mode: str = "whole", repeat_count: int = None
    ) -> None:
        """Show the proto_obj information.

        Args:
          mode (str):
            Specifies what part of the intent to show.
              Options:
              ['basic', 'parameters', 'phrases' or 'training phrases', 'whole']
          repeat_count (int):
            Indicates how many times the training phrases
            was added to the intent.
        """
        self._check_intent_exist()

        if mode == "basic":
            print(self._show_basic_info())
        elif mode == "parameters":
            print(self._show_parameters())
        elif mode in ["phrases", "training phrases"]:
            print(self._show_training_phrases(repeat_count=repeat_count))
        elif mode == "whole":
            print(self.__str__())
        else:
            raise ValueError(
                "mode should be in"
                " ['basic', 'parameters',"
                " 'phrases', 'training phrases', 'whole']"
            )


    def show_stats(self):
        """Provide some stats about the intent."""
        repeat_count_dict = defaultdict(lambda: 0)
        annotated_count = 0
        for tp in self.proto_obj.training_phrases:
            repeat_count_dict[tp.repeat_count] += 1

            for part in tp.parts:
                if part.parameter_id:
                    annotated_count += 1
                    break

        phrases_count = len(self.proto_obj.training_phrases)
        params_count = len(self.proto_obj.parameters)
        annotated_pct = round(100*annotated_count/phrases_count, 1)
        uniques_count = repeat_count_dict[1]
        uniques_pct = round(100*uniques_count/phrases_count, 1)
        non_uniques_count = phrases_count - uniques_count
        non_uniques_pct = round(100*non_uniques_count/phrases_count, 1)

        phrases_str = f"# of training phrases: {phrases_count}"
        params_str = f"# of parameters: {params_count}"
        annotated_str = (
            "Annotated training phrases:"
            f" {annotated_pct}% ({annotated_count})"
        )

        uniques_str = (
            "Unique training phrases:"
            f" {uniques_pct}% ({uniques_count})"
        )
        non_uniques_str = (
            "Non-unique training phrases:"
            f" {non_uniques_pct}% ({non_uniques_count})"
        )

        repeat_count_srt = "\n\t".join([
            f"with repeat count {i}: {repeat_count_dict[i]}"
            for i in sorted(repeat_count_dict.keys())
        ])

        out = (
            f"{phrases_str}\n{annotated_str}\n{params_str}\n"
            f"\n{uniques_str}\n{non_uniques_str}\n\t{repeat_count_srt}"
        )
        print(out)


    def parameter_checking(self) -> bool:
        """Check if the annotated parameters exist
        in the Parameter attribute of proto_obj.
        """
        tp_params_set = set()
        for tp in self.proto_obj.training_phrases:
            for part in tp.parts:
                tp_params_set.add(part.parameter_id)
        # Remove the empty string for unannotated parts
        try:
            tp_params_set.remove("")
        except KeyError:
            pass

        # Get the parameters from proto_obj
        parameters_set = {param.id for param in self.proto_obj.parameters}

        # Check for not existing annotated parameters
        for tp_param in tp_params_set:
            if tp_param not in parameters_set:
                raise Exception(
                    f"parameter_id `{tp_param}` does not exist in parameters."
                    "\nPlease add it using add_parameter method to continue."
                )

        return True


    def load_intent(
        self, obj: Intent, overwrite: bool = False
    ) -> Intent:
        """Load an existing intent to proto_obj for further uses.

        Args:
          obj (Intent):
            An existing Intent obj.
          overwrite (bool)
            Overwrite the new proto_obj if proto_obj already
            contains an Intent.

        Returns:
          An Intent object stored in proto_obj
        """
        if not isinstance(obj, Intent):
            raise ValueError(
                "The object you're trying to load is not an Intent!"
            )
        if self.proto_obj and not overwrite:
            raise Exception(
                "proto_obj already contains an Intent."
                " If you wish to overwrite it, pass overwrite as True."
            )

        if overwrite or not self.proto_obj:
            self.proto_obj = obj

        return self.proto_obj


    def create_new_intent(
        self,
        display_name: str,
        priority: int = 500000,
        is_fallback: bool = False,
        description: str = None,
        overwrite: bool = False
    ) -> Intent:
        """Create a new Intent.

        Args:
          display_name (str):
            Required. The human-readable name of the
            intent, unique within the agent.
          priority (int):
            The priority of this intent. Higher numbers represent higher
            priorities.
            -  If the supplied value is unspecified or 0, the service
            translates the value to 500,000, which corresponds to the
            ``Normal`` priority in the console.
            -  If the supplied value is negative, the intent is ignored
            in runtime detect intent requests.
          is_fallback (bool):
            Indicates whether this is a fallback intent.
            Currently only default fallback intent is
            allowed in the agent, which is added upon agent
            creation.
            Adding training phrases to fallback intent is
            useful in the case of requests that are
            mistakenly matched, since training phrases
            assigned to fallback intents act as negative
            examples that triggers no-match event.
          description (str):
            Human readable description for better
            understanding an intent like its scope, content,
            result etc. Maximum character limit: 140
            characters.
          overwrite (bool)
            Overwrite the new proto_obj if proto_obj already
            contains an Intent.

        Returns:
          An Intent object stored in proto_obj
        """
        if self.proto_obj and not overwrite:
            raise Exception(
                "proto_obj already contains an Intent."
                " If you wish to overwrite it, pass overwrite as True."
            )

        if overwrite or not self.proto_obj:
            self.proto_obj = Intent(
                display_name=display_name,
                priority=priority,
                is_fallback=is_fallback,
                description=description
            )

        return self.proto_obj


    def add_training_phrase(
        self,
        phrase: Union[str, List[str]],
        annotations: List[str] = None,
        repeat_count: int = 1
    ) -> Intent:
        """Add a training phrase to proto_obj.

        Args:
          phrase (string or list of strings):
            The training phrase as a string without annotations or
            a list of strings that represents a single training phrase.
          annotations (list of strings):
            A list of strings that represents
              parameter_id of each part in phrase.
            Length of annotations list should be less than or equal to
              length of phrase list.
            If the length is less than length of phrase list it propagate
              the rest of the annotations automatically with no annotation.
          repeat_count (int):
            Indicates how many times this example was added to the intent.

        Example 1: phrase = "I want to check my balance"
        Example 2:
          phrase = [
              'one way', ' ticket leaving ', 'January 1',
              ' to ', 'LAX', ' from ', 'CDG'
          ]
          annotations = [
              'flight_type', '', 'departure_date',
              '', 'arrival_city', '', 'departure_city'
          ]
        Example 3:
          phrase = ["I'd like to buy a ", 'one way', ' ticket']
          annotations = ['', 'flight_type']

        Returns:
          An Intent object stored in proto_obj
        """

        self._check_intent_exist()

        # Add simple training phrase
        if isinstance(phrase, str):
            # Create the training phrase obj and add it to the others
            tp = Intent.TrainingPhrase(
                parts=[Intent.TrainingPhrase.Part(text=phrase)],
                repeat_count=repeat_count
            )
            self.proto_obj.training_phrases.append(tp)

            return self.proto_obj

        # Add annotated training phrase
        # Type / Error checking
        if not (isinstance(phrase, list) and isinstance(annotations, list)):
            raise ValueError(
                "Both phrase and annotations should be lists."
            )
        if not (
            all((isinstance(p, str) for p in phrase)) and
            all((isinstance(a, str) for a in annotations))
        ):
            raise ValueError(
                "Only strings allowed in phrase or annotations list."
            )
        if len(annotations) > len(phrase):
            raise IndexError(
                "Length of annotations list is more than phrase list!"
            )

        # Propagate the annotations list if needed
        if len(annotations) < len(phrase):
            annotations.extend([""] * (len(phrase) - len(annotations)))
        # Creating parts for the training phrase
        parts_list = []
        for text, parameter_id in zip(phrase, annotations):
            part = Intent.TrainingPhrase.Part(
                text=text, parameter_id=parameter_id
            )
            parts_list.append(part)

        # Create the training phrase obj and add it to the others
        tp = Intent.TrainingPhrase(
            parts=parts_list, repeat_count=repeat_count
        )
        self.proto_obj.training_phrases.append(tp)

        return self.proto_obj


    def add_parameter(
        self,
        parameter_id: str,
        entity_type: str,
        is_list: bool = False,
        redact: bool = False
    ) -> Intent:
        """Add a parameter to Parameter attribute of proto_obj.

        Args:
          parameter_id (str):
            Required. The unique identifier of the parameter.
          entity_type (str):
            Required. The entity type of the parameter. Format:
            ``projects/-/locations/-/agents/-/
              entityTypes/<System Entity Type ID>``
            for system entity types (for example,
            ``projects/-/locations/-/agents/-/entityTypes/sys.date``),
            or
            ``projects/<Project ID>/locations/<Location ID>/
              agents/<Agent ID>/entityTypes/<Entity Type ID>``
            for developer entity types.
          is_list (bool):
            Indicates whether the parameter represents a
            list of values.
          redact (bool):
            Indicates whether the parameter content should be redacted
            in log. If redaction is enabled, the parameter content will
            be replaced by parameter name during logging.

        Returns:
          An Intent object stored in proto_obj
        """
        self._check_intent_exist()

        if not (isinstance(parameter_id, str) or isinstance(entity_type, str)):
            raise ValueError(
                "parameter_id and entity_type should be string."
            )

        # Create the new parameter and add it to the proto_obj
        parameters = Intent.Parameter(
            id=parameter_id,
            entity_type=entity_type,
            is_list=is_list,
            redact=redact
        )
        self.proto_obj.parameters.append(parameters)

        return self.proto_obj


    def add_label(
        self, label: Union[Dict[str, str], str]
    ) -> Intent:
        """Add a label to proto_obj.

        Args:
          labels (Dict[str, str] | List[str]):
            labels can be assigned as key:value like driver:account
            or strings like 'head intent'.

        Returns:
          An Intent object stored in proto_obj
        """
        self._check_intent_exist()

        if isinstance(label, dict):
            if not all((
                isinstance(key, str) and isinstance(val, str)
                for key, val in label.items()
            )):
                raise ValueError(
                    "Keys and values in label's dictionary should be string."
                )
            self.proto_obj.labels.update(label)
        elif isinstance(label, str):
            self.proto_obj.labels.update({label: label})
        else:
            raise ValueError(
                "labels should be either a string or a dictionary."
            )

        return self.proto_obj
