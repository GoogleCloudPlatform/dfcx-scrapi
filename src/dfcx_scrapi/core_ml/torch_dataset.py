"""Utiliity functions to create PyTorch datset for training a Pegasus Model."""

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

from fileinput import filename
import os
import logging

import pandas as pd
import torch
from torch.utils.data import Dataset, DataLoader

from transformers import T5Tokenizer

import google.auth
import gspread
from gspread_dataframe import set_with_dataframe
from oauth2client.service_account import ServiceAccountCredentials

from google.cloud.dialogflowcx_v3beta1 import types

from typing import Dict, List

from dfcx_scrapi.core.scrapi_base import ScrapiBase

GLOBAL_SCOPE = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive",
]

# logging config
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

DATA_DIR = "data/final"
MODEL_NAME = "t5-small"

class PegasusDataset(torch.utils.data.Dataset):
    def __init__(
        self, 
        file_name: str = None, # must be 'train', 'val', or 'test'
        type_file: str = None, 
        tokenizer = None, 
        data_dir: str = None,  
        truncation: str= None,
        padding: str = None,
        return_tensors: str = None
        ) -> None:

        self.path = os.path.join(data_dir + "/" + file_name + type_file)
        self.source_column = "sentence1"
        self.target_column = "sentence2"
        
        if type_file == ".tsv":
            self.data = pd.read_csv(self.path, sep = "\t")
        elif type_file == ".csv":
            self.data = self.data = pd.read_csv(self.path)
        # TODO: build out sheets file reader.
        else:
            raise TypeError("File is not a .tsv or .csv file")

        self.inputs = []
        self.padding = padding
        self.return_tensors = return_tensors
        self.targets = []
        self.tokenizer = tokenizer
        self.truncation = truncation
        

        self._build()

    def __len__(self):
        """This returns the length of the dataset."""
        return len(self.inputs)

    def __getitem__(self, index):
        """This function returns a sample from 
        the dataset when we provide an index value to it."""
        source_ids = self.inputs[index]["input_ids"].squeeze()
        target_ids = self.targets[index]["input_ids"].squeeze()

        src_mask = self.inputs[index]["attention_mask"].squeeze()  # might need to squeeze
        target_mask = self.targets[index]["attention_mask"].squeeze()  # might need to squeeze

        return {"source_ids": source_ids, "source_mask": src_mask, "target_ids": target_ids, "target_mask": target_mask}

    def _build(self):
        for idx in range(len(self.data)):
            input_, target = self.data.loc[idx, self.source_column], self.data.loc[idx, self.target_column]

            input_ = "paraphrase: "+ input_
            target = target

            # tokenize inputs
            tokenized_inputs = self.tokenizer.batch_encode_plus(
                [input_], truncation=self.truncation, padding=self.padding, return_tensors=self.return_tensors
            )
            # tokenize targets
            tokenized_targets = self.tokenizer.batch_encode_plus(
                [target], truncation=self.truncation, padding=self.padding, return_tensors=self.return_tensors
            )

            self.inputs.append(tokenized_inputs)
            self.targets.append(tokenized_targets)


# dataset = PegasusDataset(file_name = "train", tokenizer=T5Tokenizer.from_pretrained(MODEL_NAME), data_dir=DATA_DIR, type_file = ".tsv", truncation="longest_first", padding = "longest", return_tensors="pt")
# print(len(dataset))

# data = dataset[100]
# print(PegasusDataset(file_name = "train", tokenizer=T5Tokenizer.from_pretrained(MODEL_NAME), data_dir=DATA_DIR, type_file = ".tsv", truncation="longest_first", padding = "longest", return_tensors="pt").tokenizer.decode(data['source_ids']))
# print(PegasusDataset(file_name = "train", tokenizer=T5Tokenizer.from_pretrained(MODEL_NAME), data_dir=DATA_DIR, type_file = ".tsv", truncation="longest_first", padding = "longest", return_tensors="pt").tokenizer.decode(data['target_ids']))