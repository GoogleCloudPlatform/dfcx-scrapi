"""Utility file for generating synthetic phrases from input phrases"""

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
import pandas as pd
import torch
from transformers import PegasusForConditionalGeneration, PegasusTokenizer


class UtteranceGenerator:
    """Class to generate synthetic phrases from user defined phrases"""

    def __init__(self):

        model_name = "tuner007/pegasus_paraphrase"
        self.torch_device = "cuda" if torch.cuda.is_available() else "cpu"
        self.tokenizer = PegasusTokenizer.from_pretrained(model_name)
        self.model = PegasusForConditionalGeneration.from_pretrained(
            model_name
        ).to(self.torch_device)

    def get_response(
        self,
        input_text,
        num_return_sequences,
        num_beams,
        max_length,
        truncation,
        temperature,
    ):
        """Individual instance of model to generate synthetic phrases"""
        batch = self.tokenizer(
            [input_text],
            truncation=truncation,
            padding="longest",
            max_length=max_length,
            return_tensors="pt",
        ).to(self.torch_device)
        translated = self.model.generate(
            **batch,
            max_length=max_length,
            num_beams=num_beams,
            num_return_sequences=num_return_sequences,
            temperature=temperature,
        )
        tgt_text = self.tokenizer.batch_decode(
            translated, skip_special_tokens=True
        )
        return tgt_text

    def generate_utterances(
        self,
        origin_utterances: pd.DataFrame,
        synthetic_instances: int = None,
        max_length: int = 60,
        truncation: bool = True,
        temperature: float = 1.5,
    ):
        """Make new phrases from a dataframe of existing ones.

        Args:
          origin_utterances: dataframe specifying the phrases
          to generate syntheic phrases from
              Columns:
                  utterance: utterance to generate synthetic phrases from
                  synthetic_instances (optional): if not set for each phrase
                  in the dataframe it must be set while calling this function
                  and will be appied to all phrases
          synthetic_instances (optional): int number of synthetic phrases to
            generate for each
          max_length (optional): int
          truncation (optional): boolean
          temperature (optional): float
          base phrase

        Returns:
          synthetic_phrases_df: dataframe with new synthetic phrases.
        """

        synthetic_phrases_df = pd.DataFrame()

        if (
            synthetic_instances
            and "synthetic_instances" not in origin_utterances.columns
        ):
            origin_utterances["synthetic_instances"] = synthetic_instances
        origin_utterances = origin_utterances.reset_index(drop=True)
        origin_utterances.insert(0, "id", origin_utterances.index)

        for _, row in origin_utterances.iterrows():
            iter_frame = pd.DataFrame()
            num_beams = int(row["synthetic_instances"])
            num_return_sequences = int(row["synthetic_instances"])
            utterance = row["utterance"]
            synthetic_phrases = self.get_response(
                utterance,
                num_return_sequences,
                num_beams,
                max_length=max_length,
                temperature=temperature,
                truncation=truncation,
            )
            iter_frame["synethic_phrases"] = synthetic_phrases
            for col in origin_utterances.columns:
                iter_frame[col] = row[col]
            synthetic_phrases_df = synthetic_phrases_df.append(iter_frame)
            ordered_cols = [
                "id",
                "synthetic_instances",
                "utterance",
                "synethic_phrases",
            ]
            remaineder_cols = list(
                set(origin_utterances.columns) - set(ordered_cols)
            )
            column_ordering = ordered_cols + remaineder_cols
        return synthetic_phrases_df[column_ordering]
