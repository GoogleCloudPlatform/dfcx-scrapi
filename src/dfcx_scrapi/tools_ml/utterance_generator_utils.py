"""Utility file for utterance generator to work with CX resources."""

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
import logging
import string
import pandas as pd
from dfcx_scrapi.core import scrapi_base, intents
from dfcx_scrapi.core_ml import utterance_generator

# logging config
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


class UtteranceGeneratorUtils(scrapi_base.ScrapiBase):
    """Wrapper for utterance generator. Can be used to create
    independent test sets and net-new training phrases for intents."""

    def __init__(
        self,
        creds_path: str = None,
        creds_dict: dict = None,
        creds=None,
        scope=False,
    ):

        super().__init__(
            creds_path=creds_path,
            creds_dict=creds_dict,
            creds=creds,
            scope=scope,
        )

        logging.info("setting up utils....")
        self.intents = intents.Intents(creds_path, creds_dict)
        logging.info("downloading model....")
        self.utterance_generator = utterance_generator.UtteranceGenerator()
        logging.info("utterance generator utils setup")

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

    @staticmethod
    def clean_string(string_raw):
        """
        Clean a string with the same steps for comparison whether the generated
        ext exists or not, removes phrases which only differ by:
            -case
            -punctuation
            -leading and trailing spaces
        """
        return " ".join(
            string_raw.translate(str.maketrans("", "", string.punctuation))
            .lower()
            .split()
        )

    def _remove_training(self, synthetic_intent_set, existing_phrases: list):
        """
        Internal function for removing generated phrases which already
        exist within intents as training phrases. This is done after applying
        clean_string to both.
        """
        existing_phrases_cleaned = [
            self.clean_string(phrase) for phrase in existing_phrases
        ]
        synthetic_intent_set.insert(
            0,
            "cleaned_synthetic_phrase",
            synthetic_intent_set["synethic_phrases"].apply(self.clean_string),
        )
        synthetic_intent_set = synthetic_intent_set.drop_duplicates(
            subset=["utterance", "cleaned_synthetic_phrase"]
        )
        synthetic_intent_set.insert(
            0,
            "synthetic_in_training",
            synthetic_intent_set.apply(
                lambda x: True
                if x["cleaned_synthetic_phrase"] in existing_phrases_cleaned
                else False,
                axis=1,
            ),
        )
        synthetic_intent_set = (
            synthetic_intent_set[~(synthetic_intent_set["synthetic_in_training"])]
            .drop(columns=["cleaned_synthetic_phrase", "synthetic_in_training"])
            .reset_index(drop=True)
        )
        return synthetic_intent_set

    def _generate_phrases_intent(
        self,
        training_phrases_one_intent: pd.DataFrame,
        synthetic_phrases_per_intent: int,
    ):
        """
        main internal function for generating new syntehtic phrases from
        the existing training phrases within an intent. The synthetic phrases
        are only as good as the training in the intent.
        """
        synthetic_instances = (
            int(
                float(synthetic_phrases_per_intent)
                / float(len(training_phrases_one_intent))
            )
            + 1
        )
        existing_phrases = list(set(training_phrases_one_intent["utterance"]))
        if synthetic_instances == 1:
            training_phrases_one_intent = training_phrases_one_intent.sample(
                frac=1
            ).reset_index(drop=True)
            training_phrases_one_intent = training_phrases_one_intent.iloc[
                :synthetic_phrases_per_intent
            ]

        attempts = 0
        while True:
            synthetic_intent_set = self.utterance_generator.generate_utterances(
                training_phrases_one_intent,
                synthetic_instances=synthetic_instances,
            )
            # Check if exist in existing intents
            synthetic_intent_set = self._remove_training(
                synthetic_intent_set, existing_phrases
            )

            # check if dont have enough examples
            if len(synthetic_intent_set) >= (synthetic_phrases_per_intent - 1):
                break
            synthetic_intent_set["synthetic_instances"] = (
                synthetic_intent_set["synthetic_instances"] + 1
            )
            attempts += 1
            if attempts > 3:
                break

        synthetic_intent_set = synthetic_intent_set.sample(frac=1).iloc[
            :synthetic_phrases_per_intent
        ]
        return synthetic_intent_set

    def _generate_phrases(self, training_phrases: pd.DataFrame, set_size: int):
        """
        Internal function for running _generate_phrases_intent for all the
        user specified intents.
        """
        synthetic_set = pd.DataFrame()
        intents_list = list(set(training_phrases["intent"]))
        unique_intents_count = len(intents_list)
        synthetic_phrases_per_intent = (
            int((float(set_size) / float(unique_intents_count))) + 1
        )

        i = 0
        for intent in intents_list:
            training_phrases_one_intent = training_phrases.copy()[
                training_phrases["intent"] == intent
            ].reset_index(drop=True)
            intent_set = self._generate_phrases_intent(
                training_phrases_one_intent, synthetic_phrases_per_intent
            )
            synthetic_set = synthetic_set.append(intent_set)
            i += 1
            self.progress_bar(i, len(intents_list))
            

        return synthetic_set

    def create_synthetic_set(
        self, agent_id: str, intent_subset: list, set_size: int = 100
    ):
        """Create a test set where none of the utterances in the test set
        are in the training of the existing phrases"""
        training_phrases = self.intents.bulk_intent_to_df(
            agent_id=agent_id, intent_subset=intent_subset
        )
        training_phrases = training_phrases.copy().rename(columns={"tp": "utterance"})

        test_set = self._generate_phrases(training_phrases, set_size)
        test_set = test_set[:set_size]
        return test_set.reset_index(drop=True)

    def create_test_set(self, agent_id: str, intent_subset: list, set_size: int = 100):
        """
        Create a test set for a given list of intents. The phrases in this set will not
        be exact string match phrases which exist in the training phrases but will be close
        semantically.This set is automatically labeled by the intent whose training was
        used to generate the new phrase. This can be used to run through the core.conversations
        run_intent_detection function. You may need to specify a flow_display_name and
        page_display_name in the dataframe to run the set at the correct location.


        Args:
            agent_id: (string) name parameter of the agent to pull intents from - full path to
                agent
            intent_subset: (list) display names of the intents to create a test for, base
                phrases come from the training in the
                intent.
            set_size: (int) overall target size of the test set to create, may be less
                depending if new independent phrases can be generated from the data.
                The function tries to get even entries per intent.




        Returns:
          test_set: (DataFrame) a pandas dataframe consisting of rows of the utterance and
          the intent which it was generated from. This generated from intent can be used as
          the true label.
        """
        synthetic_set = self.create_synthetic_set(agent_id, intent_subset, set_size)
        test_set = (
            synthetic_set.copy()[["synethic_phrases", "intent"]]
            .rename(columns={"synethic_phrases": "utterance"})
            .reset_index(drop=True)
        )
        return test_set

    def create_new_training_phrases(
        self, agent_id: str, intent_subset: list, new_phrases: int = 100
    ):
        """
        Create a new training phrasese for a given list of intents. The phrases in
        this set will not be exact string match phrases which exist in the training
        phrases but will be close semantically. This can be used to run through the
        core.intents modify_training_phrase_df function to create a new training phrase
        dataframe. This and a parameters dataframe can be run through tools.dataframe_functions
        bulk_update_intents_from_dataframe function to make the updates in a dialogflow agent.
        The new_training output dataframe can be used as the input actions dataframe in the
        bulk_update_intents_from_dataframe function.


        Args:
            agent_id: (string) name parameter of the agent to pull intents from - full path to
                agent
            intent_subset: (list) display names of the intents to create a new phrases for, base
                phrases come from the training in the intent.
            new_phrases: (int) overall target size of new phrases to create, may be less depending
                if new independent phrases can be generated from the data. The function tries to get
                even entries per intent.

        Returns:
          new_training: (DataFrame) a pandas dataframe consisting of rows of the new
              training phrase,the intent to add to and the add action.
        """
        synthetic_set = self.create_synthetic_set(agent_id, intent_subset, new_phrases)
        new_training = (
            synthetic_set.copy()[
                [
                    "intent",
                    "synethic_phrases",
                ]
            ]
            .rename(columns={"intent": "display_name", "synethic_phrases": "phrase"})
            .reset_index(drop=True)
        )
        new_training.insert(len(new_training.columns), "action", "add")
        return new_training
