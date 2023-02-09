"""Utility file for utterance generator to work with CX resources."""

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
import string
from typing import List, Dict

import pandas as pd

from google.oauth2 import service_account
from dfcx_scrapi.core import scrapi_base
from dfcx_scrapi.core import intents
from dfcx_scrapi.core_ml import utterance_generator

# logging config
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


class UtteranceGeneratorUtils(scrapi_base.ScrapiBase):
    """Wrapper for utterance generator that creates new training phrases.

    Can be used to create independent test sets and net-new training phrases
    for intents.
    """

    def __init__(
        self,
        creds_path: str = None,
        creds_dict: Dict[str, str] = None,
        creds: service_account.Credentials = None,
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
    def _progress_bar(
        current: int, total: int, bar_length: int = 50, type_: str = "Progress"
    ):
        """Display progress bar for processing.

        Args:
          current: number for current iteration.
          total: number for total iterations.
          bar_length: number of spaces to make the progress bar, default 50.
          type_: label for the bar, default 'Progress'.
        """
        percent = float(current) * 100 / total
        arrow = "-" * int(percent / 100 * bar_length - 1) + ">"
        spaces = " " * (bar_length - len(arrow))
        print(
            f"{type_}({current}/{total})" + f"[{arrow}{spaces}] {percent}%",
            end="\r",
        )

    @staticmethod
    def _clean_string(string_raw: str) -> str:
        """Cleans a string for comparison.

        Cleans a string with the same steps for comparison whether
        the generated text exists or not, removes phrases which
        only differ by:
          case,
          punctuation, or
          leading and trailing spaces.

        Args:
          string_raw: phrase to clean

        Returns:
          Cleaned string
        """
        return (
            string_raw.translate(str.maketrans("", "", string.punctuation))
            .lower()
            .strip()
        )

    def _remove_training(
        self,
        synth_intent_dataset: pd.DataFrame,
        existing_phrases: List[str],
    ) -> pd.DataFrame:
        """Removes generated phrases that already exist as intent TPs.

        Internal function for removing generated phrases which already
        exist within intents as training phrases. This is done after applying
        clean_string to both.

        Args:
          synth_intent_dataset: dataframe containing generated training
            phrases.
          existing_phrases: list of phrases that already exist as intent
            training phrases.

        Returns:
          A dataframe of new only generated phrases.
        """
        existing_phrases_cleaned = [
            self._clean_string(phrase) for phrase in existing_phrases
        ]
        synth_intent_dataset.insert(
            0,
            "cleaned_synthetic_phrase",
            synth_intent_dataset["synthetic_phrases"].apply(
                self._clean_string
            ),
        )
        synth_intent_dataset = synth_intent_dataset.drop_duplicates(
            subset=["training_phrase", "cleaned_synthetic_phrase"]
        )

        synth_intent_dataset.insert(
            0,
            "synthetic_in_training",
            synth_intent_dataset.apply(
                lambda x: x["cleaned_synthetic_phrase"]
                in existing_phrases_cleaned,
                axis=1,
            ),
        )
        synth_intent_dataset = (
            synth_intent_dataset[
                ~(synth_intent_dataset["synthetic_in_training"])
            ]
            .drop(
                columns=["cleaned_synthetic_phrase", "synthetic_in_training"]
            )
            .reset_index(drop=True)
        )
        return synth_intent_dataset

    def _generate_phrases_intent(
        self,
        training_phrases_one_intent: pd.DataFrame,
        synthetic_phrases_per_intent: int,
    ) -> pd.DataFrame:
        """Generates new synthetic phrases.

        Main internal function for generating new synthetic phrases from
        the existing training phrases within an intent. The synthetic phrases
        are only as good as the training phrases in the intent.

        Args:
          training_phrases_one_intent: input phrases from which to generate
            new training phrases.
          synthetic_phrases_per_intent: number of phrases to generate.

        Returns:
          A DataFrame containing synthetic training phrases.
        """
        synthetic_instances = (
            synthetic_phrases_per_intent // len(training_phrases_one_intent)
        ) + 1
        existing_phrases = list(
            set(training_phrases_one_intent["training_phrase"])
        )
        if synthetic_instances == 1:
            training_phrases_one_intent = training_phrases_one_intent.sample(
                frac=1
            ).reset_index(drop=True)
            training_phrases_one_intent = training_phrases_one_intent.iloc[
                :synthetic_phrases_per_intent
            ]

        attempts = 0
        while True:
            synth_intent_dataset = self.utterance_generator.generate_utterances(
                training_phrases_one_intent,
                synthetic_instances=synthetic_instances,
            )
            # Check if exist in existing intents
            synth_intent_dataset = self._remove_training(
                synth_intent_dataset, existing_phrases
            )

            # check if dont have enough examples
            if len(synth_intent_dataset) >= (
                synthetic_phrases_per_intent - 1
            ):
                break
            synth_intent_dataset["synthetic_instances"] += 1
            attempts += 1
            if attempts > 3:
                break

        synth_intent_dataset = synth_intent_dataset.sample(
            frac=1
        ).iloc[:synthetic_phrases_per_intent]
        return synth_intent_dataset

    def _generate_phrases(
        self, training_phrases: pd.DataFrame, dataset_size: int
    ) -> pd.DataFrame:
        """Generates phrases for all user-specified intents.

        Internal function for running _generate_phrases_intent for all the
        user-specified intents.

        Args:
          training_phrases: df of training phrases for multiple intents with
            an Intent "display_name" column.
          dataset_size: number of requested phrases to generate over all
            specified intents.

        Returns:
            A DataFrame of generated training phrases.
        """
        # TODO: fix math for training phrase generation.
        synthetic_dataset = pd.DataFrame()
        intents_list = list(set(training_phrases["display_name"]))
        unique_intents_count = len(intents_list)

        synthetic_phrases_per_intent = dataset_size // unique_intents_count + 1

        i = 0
        for intent in intents_list:
            training_phrases_one_intent = training_phrases.copy()[
                training_phrases["display_name"] == intent
            ].reset_index(drop=True)
            intent_set = self._generate_phrases_intent(
                training_phrases_one_intent, synthetic_phrases_per_intent
            )
            synthetic_dataset = pd.concat([synthetic_dataset, intent_set])
            i += 1
            self._progress_bar(i, len(intents_list))

        return synthetic_dataset

    def create_synthetic_dataset(
        self, agent_id: str, intent_subset: List[str], dataset_size: int = 100
    ) -> pd.DataFrame:
        """Creates a synthetic test dataset.

        Creates a test dataset where none of the utterances in the test
        dataset are in the training of the existing phrases.

        Args:
          agent_id: ID of the DFCX agent.
          intent_subset: intents to generate a test dataset for.
          dataset_size: number of synthetic phrases to generate, default 100.

        Returns:
          DataFrame containing synthetic test dataset utterances with columns:
            id: IDs of original utterances.
            synthetic instances: number of synthetic phrases per
              original phrase.
            utterance: original utterances.
            synthetic_phrases: generated phrases.
            intent: intent the utterance is from.
        """
        training_phrases = self.intents.bulk_intent_to_df(
            agent_id=agent_id, intent_subset=intent_subset
        )
        training_phrases = training_phrases.copy().rename(
            columns={"tp": "utterance"}
        )
        test_dataset = self._generate_phrases(training_phrases, dataset_size)
        test_dataset = test_dataset[:dataset_size]

        return test_dataset.reset_index(drop=True)

    def create_test_dataset(
        self,
        agent_id: str,
        intent_subset: List[str],
        flow_display_name: str = "Default Start Flow",
        page_display_name: str = "START_PAGE",
        dataset_size: int = 100,
    ) -> pd.DataFrame:
        """Creates a test dataset for a given list of intents.

        The phrases in this dataset will not be exact string match phrases that
        exist in the training phrases but will be close semantically. This set
        is automatically labeled by the intent whose training was used to
        generate the new phrase. This can be used to run through the
        core.conversations run_intent_detection function. You may need to
        specify a flow_display_name and page_display_name in the dataframe to
        run the set at the correct location.

        Args:
          agent_id: name parameter of the agent to pull intents from
            full path to agent.
          intent_subset: display names of the intents to create a new
            phrases for, base phrases come from the training in the intent.
          flow_display_name: display name of the flow location at which
            to run the core.conversations run_intent_detection
            function, default Default Start Flow.
          page_display_name: display name of the page location at which
            to run the core.conversations run_intent_detection function,
            default START_PAGE.
          dataset_size: overall target size of the test set to create,
            may be less depending if new independent phrases can be
            generated from the data. The function tries to get even
            entries per intent, default 100.

        Returns:
          Dataframe with columns:
            flow_display_name: display name of the flow location at which
              to run the core.conversations run_intent_detection
              function.
            page_display_name: display name of the page location at which
              to run the core.conversations run_intent_detection function.
            utterance: original utterances.
        """
        synthetic_dataset = self.create_synthetic_dataset(
            agent_id, intent_subset, dataset_size
        )
        test_dataset = (
            synthetic_dataset.copy()[["synthetic_phrases", "display_name"]]
            .rename(columns={"synthetic_phrases": "utterance"})
            .reset_index(drop=True)
        )
        # Reformat test_dataset to fit run_intent_detection schema
        test_dataset["flow_display_name"] = flow_display_name
        test_dataset["page_display_name"] = page_display_name
        schema_dataset = test_dataset[
            ["flow_display_name", "page_display_name", "utterance"]
        ]

        return schema_dataset

    def create_new_training_phrases(
        self, agent_id: str, intent_subset: List[str], new_phrases: int = 100
    ) -> pd.DataFrame:
        """Creates new training phrases for a given list of intents.

        Generates phrases that are semantically similar to the input training
        phrases and returns them in a dataframe. The resulting dataframe can
        be used with the core.intents.modify_training_phrase_df method to
        create the appropriately formatted training phrase dataframe that will
        be ready to update to a CX agent. Using this newly formatted dataframe
        (and optionally a Parameters dataframe), the
        tools.dataframe_functions.bulk_update_intents_from_dataframe method can
        be used to make the final updates to the CX agent.

        Args:
          agent_id: name parameter of the agent to pull intents from - full
            path to agent.
          intent_subset: display names of the intents to create a new phrases
            for, base phrases come from the training in the intent.
          new_phrases: overall target size of new phrases to create, may be
            less depending if new independent phrases can be generated from
            the data. The function tries to get even entries per intent.

        Returns:
          Dataframe with columns:
            display_name: intent to add the phrase to.
            phrase: new phrase.
            action: "add".
        """
        synthetic_dataset = self.create_synthetic_dataset(
            agent_id, intent_subset, new_phrases
        )
        new_training = (
            synthetic_dataset.copy()[["display_name", "synthetic_phrases"]]
            .rename(columns={"synthetic_phrases": "phrase"})
            .reset_index(drop=True)
        )
        new_training.insert(len(new_training.columns), "action", "add")

        return new_training
