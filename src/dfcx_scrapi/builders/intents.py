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
from string import ascii_lowercase
from string import digits
from collections import defaultdict
from dataclasses import dataclass
from dataclasses import field
from typing import List, Dict, Union

from google.cloud.dialogflowcx_v3beta1.types import Intent
from dfcx_scrapi.builders.builders_common import BuildersCommon

# logging config
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


class IntentBuilder(BuildersCommon):
    """Base Class for CX Intent builder."""

    _proto_type = Intent
    _proto_type_str = "Intent"


    def __str__(self) -> str:
        """String representation of the proto_obj."""
        self._check_proto_obj_attr_exist()

        return (f"{self._show_basic_info()}"
            f"\n\n{self._show_parameters()}"
            f"\n\n{self._show_training_phrases()}")


    def _include_spaces_to_phrase(self, phrase: List[str], annots: List[str]):
        """Internal method to add spaces to the training phrase list and
        make related changes to the annotations list.

        Args:
          phrase (List[str]):
            A list of strings that represents the training phrase.
          annots (List[str]):
            A list of strings that represents
              parameter_id of each part in phrase.
        """
        chars_to_ignore_at_beginning = ["'", ",", ".", "?", "!"]
        i = 0
        while True:
            p_curr, a_curr = phrase[i], annots[i]
            try:
                p_next, a_next = phrase[i+1], annots[i+1]
            except IndexError:
                break

            if a_curr and a_next:
                phrase.insert(i+1, " ")
                annots.insert(i+1, "")
                i += 2
            elif a_curr and not a_next:
                flag = any(
                    ch
                    for ch in chars_to_ignore_at_beginning
                    if p_next.startswith(ch)
                )
                if not flag:
                    phrase[i+1] = " " + p_next
                i += 1
            elif not a_curr and a_next:
                phrase[i] = p_curr + " "
                i += 1
            elif not a_curr and not a_next:
                phrase[i] = p_curr + " " + p_next
                del phrase[i+1]
                del annots[i+1]


    def _label_constraints_check(self, key: str, value: str):
        """Check constraints for the label's key and value
        and raise an error if needed.

        Args:
          key (str):
            Label's key.
          value (str):
            Label's value.
        """
        allowed_chars = ascii_lowercase + digits + "-_"
        # TODO Add International characteres to allowed_chars
        allowed_char_error_msg = (
            "Key and Value can only contain lowercase letters,"
            " numeric characters, underscores and dashes."
        )
        if not(isinstance(key, str) and isinstance(value, str)):
            raise ValueError(
                "Key and value should be string."
            )
        if len(key) > 63 or len(value) > 63:
            raise ValueError(
                "Key and value can be no longer than 63 characters"
            )
        if key.startswith("sys-") and key not in ["sys-head", "sys-contextual"]:
            raise ValueError(
                "Prefix `sys-` is reserved for Dialogflow defined labels."
            )
        if key[0] not in ascii_lowercase:
            raise ValueError("Key must start with a lowercase letter.")
        for s in key:
            if s not in allowed_chars:
                raise ValueError(allowed_char_error_msg)
        for s in value:
            if s not in allowed_chars:
                raise ValueError(allowed_char_error_msg)


    def _show_basic_info(self) -> str:
        """String representation for the basic information of proto_obj."""
        self._check_proto_obj_attr_exist()

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
        self._check_proto_obj_attr_exist()

        return "\n".join([
            (f"parameter_id: {str(param.id)}"
            f"\nentity_type: {str(param.entity_type)}"
            f"\n\tis_list: {bool(param.is_list)}"
            f"\n\tredact: {bool(param.redact)}")
            for param in self.proto_obj.parameters
        ])


    def _show_training_phrases(self, repeat_count: int = None) -> str:
        """String representation for the training phrases of proto_obj."""
        self._check_proto_obj_attr_exist()

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
        self._check_proto_obj_attr_exist()

        self.parameter_checking()

        if mode == "basic":
            print(self._show_basic_info())
        elif mode == "parameters":
            print(self._show_parameters())
        elif mode in ["phrases", "training phrases"]:
            print(self._show_training_phrases(repeat_count=repeat_count))
        elif mode == "whole":
            print(self)
        else:
            raise ValueError(
                "mode should be in"
                " ['basic', 'parameters',"
                " 'phrases', 'training phrases', 'whole']"
            )


    def show_stats(self):
        """Provide some stats about the intent."""
        self._check_proto_obj_attr_exist()

        stats_instance = IntentStats(self.proto_obj)
        stats_instance.generate_stats()


    def parameter_checking(self, raise_error: bool = False) -> bool:
        """Check if the annotated parameters exist
        in the Parameter attribute of proto_obj.

        Args:
          raise_error (bool):
            A flag to whether raise an error. If False, it will log a warning.

        Returns:
          True if annotated parameters are the same as parameters in proto_obj
        """
        self._check_proto_obj_attr_exist()

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
        return_flag = True
        for tp_param in tp_params_set:
            if tp_param not in parameters_set:
                return_flag = False
                msg = (
                    f"parameter_id `{tp_param}` does not exist in parameters."
                    "\nPlease add it using add_parameter method to continue."
                )
                if raise_error:
                    raise UserWarning(msg)
                else:
                    logging.warning(msg)

        return bool(return_flag)


    def create_new_proto_obj(
        self,
        display_name: str,
        priority: int = 500000,
        is_fallback: bool = False,
        description: str = None,
        overwrite: bool = False,
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
            raise UserWarning(
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
        repeat_count: int = 1,
        include_spaces: bool = True,
    ) -> Intent:
        """Add a training phrase to proto_obj.

        Args:
          phrase (str | List[str]):
            The training phrase as a string without annotations or
            a list of strings that represents a single training phrase.
          annotations (List[str]):
            A list of strings that represents
              parameter_id of each part in phrase.
            Length of annotations list should be less than or equal to
              length of phrase list.
            If the length is less than length of phrase list it propagate
              the rest of the annotations automatically with no annotation.
          repeat_count (int):
            Indicates how many times this example was added to the intent.
          include_spaces (bool):
            For the phrases with annotations, indicates whether the function
              should include spaces between each part of training phrase.

        Example 1: phrase = "I want to check my balance"
        Example 2:
          phrase = ['I want to order a', 'pizza']
          annotations = ['', 'food_type']
          include_spaces = True
        Example 3:
          phrase = [
              'one way', ' ticket leaving ', 'January 1',
              ' to ', 'LAX', ' from ', 'CDG'
          ]
          annotations = [
              'flight_type', '', 'departure_date',
              '', 'arrival_city', '', 'departure_city'
          ]
          include_spaces = False
        Example 4:
          phrase = ["I'd like to buy a", 'one way', 'ticket']
          annotations = ['', 'flight_type']
          include_spaces = True

        Returns:
          An Intent object stored in proto_obj
        """
        self._check_proto_obj_attr_exist()

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
        # Change the phrase and annotations lists to include spaces if needed
        if include_spaces:
            self._include_spaces_to_phrase(phrase, annotations)
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

        self.parameter_checking()

        return self.proto_obj


    def add_parameter(
        self,
        parameter_id: str,
        entity_type: str,
        is_list: bool = False,
        redact: bool = False,
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
        self._check_proto_obj_attr_exist()

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
          labels (Dict[str, str] | str):
            labels can be assigned as key:value like driver:account
            or strings like 'head intent'.
            Labels can contain lowercase letters, digits and
              the symbols '-' and'_'.
            International characters are allowed, including letters
              from unicase alphabets.
            Keys must start with a letter.
            Keys and values can be no longer than 63 characters and no more
              than 128 bytes.
            Prefix "sys-" is reserved for Dialogflow defined labels.
              Currently allowed Dialogflow defined labels include:
                - "sys-head" means the intent is a head intent.
                - "sys-contextual" means the intent is a contextual intent.

        Returns:
          An Intent object stored in proto_obj
        """
        self._check_proto_obj_attr_exist()

        if isinstance(label, str):
            self._label_constraints_check(key=label, value=label)
            self.proto_obj.labels.update({label: label})
        elif isinstance(label, dict):
            for key, val in label.items():
                self._label_constraints_check(key=key, value=val)
            self.proto_obj.labels.update(label)
        else:
            raise ValueError(
                "label should be either a string or a dictionary."
            )

        return self.proto_obj


    def remove_training_phrase(self, phrase: str) -> Intent:
        """Remove a training phrase from proto_obj.

        Args:
          phrase (str):
            The training phrase to remove from proto_obj.

        Returns:
          An Intent object stored in proto_obj
        """
        self._check_proto_obj_attr_exist()

        if not isinstance(phrase, str):
            raise ValueError("phrase should be a string.")

        for idx, tp in enumerate(self.proto_obj.training_phrases):
            # Construct the training phrase using parts
            the_phrase = "".join([part.text for part in tp.parts])
            if phrase == the_phrase:
                del self.proto_obj.training_phrases[idx]
                break

        return self.proto_obj


    def remove_parameter(self, parameter_id: str) -> Intent:
        """Remove a parameter from proto_obj.

        Args:
          parameter_id (str):
            The id of the parameter to remove from proto_obj.

        Returns:
          An Intent object stored in proto_obj
        """
        self._check_proto_obj_attr_exist()

        if not isinstance(parameter_id, str):
            raise ValueError("parameter_id should be a string.")

        for idx, param in enumerate(self.proto_obj.parameters):
            if parameter_id == param.id:
                del self.proto_obj.parameters[idx]
                break

        return self.proto_obj


    def remove_label(self, label: Union[Dict[str, str], str]) -> Intent:
        """Remove a single or multiple labels from proto_obj.

        Args:
          label (Dict[str, str] | str):
            A string or a dictionary of lables to remove.

        Returns:
          An Intent object stored in proto_obj
        """
        self._check_proto_obj_attr_exist()

        if isinstance(label, str):
            if self.proto_obj.labels.get(label) == label:
                self.proto_obj.labels.pop(label)
        elif isinstance(label, dict):
            for key, val in label.items():
                if not(isinstance(key, str) and isinstance(val, str)):
                    raise ValueError(
                        "Keys and values in label's dictionary"
                        " should be string."
                    )
                # Check if the keys and values in the `label`
                # are the same as labels in proto_obj
                if self.proto_obj.labels.get(key) == val:
                    self.proto_obj.labels.pop(key)
        else:
            raise ValueError(
                "labels should be either a string or a dictionary."
            )

        return self.proto_obj



@dataclass
class IntentStats():
    """A class for tracking the stats of CX Intent object."""
    intent_proto_obj: Intent

    # Training Phrases
    repeat_count_dict: Dict[int, int] = field(
        default_factory=lambda: defaultdict(int)
    )
    annotated_count: int = 0
    phrases_count: int = 0
    annotated_pct: int = 0
    uniques_count: int = 0
    uniques_pct: int = 0
    non_uniques_count: int = 0
    non_uniques_pct: int = 0

    # Parameters
    params_count: int = 0


    def calc_tps_stats(self):
        """Calculating stats related to training phrases."""
        for tp in self.intent_proto_obj.training_phrases: # pylint: disable=E1133
            self.repeat_count_dict[tp.repeat_count] += 1

            for part in tp.parts:
                if part.parameter_id:
                    self.annotated_count += 1
                    break


        self.phrases_count = len(self.intent_proto_obj.training_phrases)
        self.uniques_count = self.repeat_count_dict[1]
        self.non_uniques_count = self.phrases_count - self.uniques_count

        annot_pct = 100 * (self.annotated_count / self.phrases_count)
        uniq_pct = 100 * (self.uniques_count / self.phrases_count)
        non_uniq_pct = 100 * (self.non_uniques_count / self.phrases_count)
        self.annotated_pct = round(annot_pct, 1)
        self.uniques_pct = round(uniq_pct, 1)
        self.non_uniques_pct = round(non_uniq_pct, 1)

    def create_tps_str(self) -> str:
        """String representation of stats related to training phrases."""
        phrases_str = f"# of training phrases: {self.phrases_count}"
        annotated_str = (
            "Annotated training phrases:"
            f" {self.annotated_pct}% ({self.annotated_count})"
        )

        uniques_str = (
            "Unique training phrases:"
            f" {self.uniques_pct}% ({self.uniques_count})"
        )
        non_uniques_str = (
            "Non-unique training phrases:"
            f" {self.non_uniques_pct}% ({self.non_uniques_count})"
        )

        repeat_count_srt = "\n\t".join([
            f"with repeat count {i}: {self.repeat_count_dict[i]}"
            for i in sorted(self.repeat_count_dict.keys())
        ])

        return (
            f"{phrases_str}\n{annotated_str}\n"
            f"\n{uniques_str}\n{non_uniques_str}\n\t{repeat_count_srt}"
        )


    def create_parameter_str(self) -> str:
        """String representation Intent's parameters.."""
        self.params_count = len(self.intent_proto_obj.parameters)
        return f"# of parameters: {self.params_count}"


    def generate_stats(self):
        """Generate stats for the Intent."""
        self.calc_tps_stats()

        tps_str = self.create_tps_str()
        params_str = self.create_parameter_str()

        out = f"{params_str}\n{tps_str}"
        print(out)
