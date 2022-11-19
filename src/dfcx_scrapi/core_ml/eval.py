"""Utility functions for fine tuning pretrained T5 summarization model for paraphrasing."""

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
#
#https://github.com/seduerr91/pawraphrase_public/blob/master/t5_pawraphrase_training.ipynb

import argparse
import glob
import os
import json
import time
import logging
import random
import re
from itertools import chain
from string import punctuation

import spacy
spacy.prefer_gpu()
nlp = spacy.load("en_core_web_sm")

# Construction 1
from spacy.tokenizer import Tokenizer
from spacy.lang.en import English
nlp = English()
# Create a blank Tokenizer with just the English vocab
spacy_tokenizer = Tokenizer(nlp.vocab)

import pandas as pd
import pytorch_lightning as pl
import numpy as np
import torch
# print(torch.backends.mps.is_available())
# print(torch.backends.mps.is_built()) # run if running on Mac OS
# print(torch.cuda.device_count()) # run if running on Mac OS

from torch.utils.data import Dataset, DataLoader
from transformers import (
    AdamW,
    T5ForConditionalGeneration,
    T5Tokenizer,
    get_linear_schedule_with_warmup
)
#from torch_dataset import PegasusDataset
from model import LoggingCallback, FineTuneT5Model

from torch_dataset import T5Dataset

MODEL_PATH = "src/dfcx_scrapi/core_ml/t5_base_paraphrase/"
CONFIG_PATH = "src/dfcx_scrapi/core_ml/t5_base_paraphrase/config.json"

def main(args: argparse.Namespace) -> None:
    
    model = T5ForConditionalGeneration.from_pretrained(MODEL_PATH, config=CONFIG_PATH)
    tokenizer = T5Tokenizer.from_pretrained("t5-small")
    
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print ("device ",device)
    model = model.to(device)

    #sentence = "Can you confirm no data charge?"
    # sentence = "What are the ingredients required to bake a perfect cake?"
    # sentence = "What is the best possible approach to learn aeronautical engineering?"
    # sentence = "Do apples taste better than oranges in general?"
    sentences =  ["billing and missing a credit", "where's my credit", "I'm missing a credit", "credit not applied", "missing credit", "credit charge off", "credit not received", "i was offered a credit on my account"]

    texts =  ["paraphrase: " + sentence + " </s>" for sentence in sentences]

    max_len = 256
    for text in texts:
        encoding = tokenizer.encode_plus(text,pad_to_max_length=True, return_tensors="pt")
        input_ids, attention_masks = encoding["input_ids"].to(device), encoding["attention_mask"].to(device)

        # set top_k = 50 and set top_p = 0.95 and num_return_sequences = 3
        beam_outputs = model.generate(
            input_ids=input_ids, attention_mask=attention_masks,
            do_sample=True,
            max_length=256,
            top_k=50,
            top_p=1,
            early_stopping=True,
            temperature = 0.90,
            num_return_sequences= 3
        )

        print ("\nOriginal Question ::")
        print (text)
        print ("\n")
        print ("Paraphrased Questions :: ")
        final_outputs =[]
        for beam_output in beam_outputs:
            sent = tokenizer.decode(beam_output, skip_special_tokens=True,clean_up_tokenization_spaces=True)
            if sent.lower() not in sentences and sent not in final_outputs:
                final_outputs.append(sent)

        for i, final_output in enumerate(final_outputs):
            print("{}: {}".format(i, final_output))

if __name__ == "__main__":
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument("data_dir", help="", nargs='?', type=str, const="data/final/", default="data/final/")
    parser.add_argument("output_dir", help="", nargs='?', type=str, const="src/dfcx_scrapi/core_ml/cpk", default="src/dfcx_scrapi/core_ml/cpk")
    parser.add_argument("model_name_or_path", help="", nargs='?', type=str, const="t5-small", default="t5-small")
    parser.add_argument("tokenizer_name_or_path", help="Debug", nargs='?', type=str, const="t5-small", default="t5-small")
    #parser.add_argument("max_seq_length", help="", nargs='?', type=int, const=512, default=512)
    parser.add_argument("learning_rate", help="", nargs='?', type=float, const=3e-4, default=3e-4)
    parser.add_argument("weight_decay", help="", nargs='?', type=float, const=0.0, default=0.0)
    parser.add_argument("adam_epsilon", help="", nargs='?', type=float, const=1e-8, default=1e-8)
    parser.add_argument("warmup_steps", help="", nargs='?', type=int, const=0, default=0)
    parser.add_argument("train_batch_size", help="", nargs='?', type=int, const=4, default=4)
    parser.add_argument("eval_batch_size", help="", nargs='?', type=int, const=4, default=4)
    parser.add_argument("num_train_epochs", help="Debug", nargs='?', type=int, const=10, default=10)
    parser.add_argument("gradient_accumulation_steps", help="", nargs='?', type=int, const=16, default=16)
    parser.add_argument("n_gpu", help="", nargs='?', type=int, const=1, default=1)
    parser.add_argument("early_stop_callback", help="", nargs='?', type=bool, const=False, default=False)
    parser.add_argument("fp_16", help="Debug", nargs='?', type=bool, const=False, default=False)
    parser.add_argument("opt_level", help="", nargs='?', type=str, const='O1', default='O1')
    parser.add_argument("max_grad_norm", help="", nargs='?', type=float, const=1.0, default=1.0)
    parser.add_argument("seed", help="", nargs='?', type=int, const=42, default=42)
    main(parser.parse_args())

    
    