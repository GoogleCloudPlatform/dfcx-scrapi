"""Utiliity functions for fine tuning pretrained T5 summarization model for paraphrasing."""

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
print(torch.backends.mps.is_available())
print(torch.backends.mps.is_built()) # run if running on Mac OS
print(torch.cuda.device_count()) # run if running on Mac OS

from torch.utils.data import Dataset, DataLoader
from transformers import (
    AdamW,
    T5ForConditionalGeneration,
    T5Tokenizer,
    get_linear_schedule_with_warmup
)
from torch_dataset import PegasusDataset
from model import LoggingCallback, FineTuneT5Model

DATA_DIR = "data/final/"
MODEL_NAME = "t5-small"

# args_dict = dict(
#   data_dir="data/final", # path for data files
#   output_dir="output", # path to save the checkpoints
#   model_name_or_path='t5-small',
#   tokenizer_name_or_path='t5-small',
#   max_seq_length=512,
#   learning_rate=3e-4,
#   weight_decay=0.0,
#   adam_epsilon=1e-8,
#   warmup_steps=0,
#   train_batch_size=8,
#   eval_batch_size=8,
#   num_train_epochs=2,
#   gradient_accumulation_steps=16,
#   n_gpu=1,
#   # early_stop_callback=False,
#   fp_16=False, # if you want to enable 16-bit training then install apex and set this to true
#   opt_level='O1', # you can find out more on optimisation levels here https://nvidia.github.io/apex/amp.html#opt-levels-and-properties
#   max_grad_norm=1.0, # if you enable 16-bit training then set this to a sensible value, 0.5 is a good default
#   seed=args.seed,
# )

DATA_DIR = "data/final/"
MODEL_NAME = "t5-base"
OUTPUT_DIR = "src/dfcx_scrapi/core_ml/cpk"

def get_dataset(tokenizer, data_dir: str, file_name: str):
  return PegasusDataset(tokenizer=tokenizer, data_dir=data_dir, file_name=file_name)


def main(args: argparse.Namespace) -> None:
    logger = logging.getLogger(__name__)

    # Load Data
    # args_dict = dict(
    #     # data_dir=args.data_dir, # path for data files
    #     # output_dir=args.output_dir, # path to save the checkpoints
    #     model_name_or_path=args.model_name_or_path,
    #     tokenizer_name_or_path=args.tokenizer_name_or_path,
    #     #max_seq_length=512,
    #     learning_rate=args.learning_rate,
    #     weight_decay=args.weight_decay,
    #     adam_epsilon=args.adam_epsilon,
    #     warmup_steps=args.warmup_steps, # probably need to change this.
    #     train_batch_size=args.train_batch_size,
    #     eval_batch_size=args.eval_batch_size,
    #     num_train_epochs=args.num_train_epochs,
    #     gradient_accumulation_steps=args.gradient_accumulation_steps,
    #     n_gpu=args.n_gpu,
    #     # early_stop_callback=False,
    #     fp_16=args.fp_16, # if you want to enable 16-bit training then install apex and set this to true
    #     opt_level=args.opt_level, # you can find out more on optimisation levels here https://nvidia.github.io/apex/amp.html#opt-levels-and-properties
    #     max_grad_norm=args.max_grad_norm, # if you enable 16-bit training then set this to a sensible value, 0.5 is a good default
    #     seed=args.seed
    # )
    
    print("Loading Training Data...")
    train_data = PegasusDataset(file_name = "train", tokenizer=T5Tokenizer.from_pretrained(args.tokenizer_name_or_path), data_dir=args.data_dir, type_file = ".tsv", truncation="longest_first", padding = "longest", return_tensors="pt")
    print("Loading Validation Data...")
    val_data = PegasusDataset(file_name = "val", tokenizer=T5Tokenizer.from_pretrained(args.tokenizer_name_or_path), data_dir=args.data_dir, type_file = ".tsv", truncation="longest_first", padding = "longest", return_tensors="pt")  

    checkpoint_callback = pl.callbacks.ModelCheckpoint(
        filepath=args.output_dir, prefix="checkpoint", monitor="val_loss", mode="min", save_top_k=5
        ) 

    train_params = dict(
        accumulate_grad_batches=args.gradient_accumulation_steps,
        gpus=args.n_gpu,
        max_epochs=args.num_train_epochs,
        # early_stop_callback=False,
        # precision=32,
        # amp_level=args.opt_level,
        gradient_clip_val=args.max_grad_norm,
        checkpoint_callback=checkpoint_callback,
        callbacks=[LoggingCallback(logger=logger)],
    )
    # Initialize Model
    print("Intializing Model...")
    model = FineTuneT5Model(
        adam_epsilon = args.adam_epsilon,
        eval_batch_size = args.eval_batch_size,
        gradient_accumulation_steps = args.gradient_accumulation_steps,
        learning_rate = args.learning_rate,
        model_name_or_path = args.model_name_or_path,
        n_gpu = args.n_gpu,
        num_train_epochs = args.num_train_epochs,
        tokenizer_name_or_path = args.tokenizer_name_or_path,
        train_batch_size = args.train_batch_size,
        warmup_steps = args.warmup_steps,
        weight_decay = args.weight_decay
    )
    #Initalize Trainer
    print("Initalizing Trainer...")
    trainer = pl.Trainer(**train_params)

    # Start Fine-Tuning
    print("Starting Fine Tuning...") # TODO: add timing
    trainer.fit(model)
    print("Fine Tuning Complete in: ")

    print("Saving model...")
    #model.model.save_pretrained('t5_base_paraphrase/')
    print('Saved model...')



if __name__ == "__main__":
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument("data_dir", help="", nargs='?', type=str, const="data/final", default="data/final")
    parser.add_argument("output_dir", help="", nargs='?', type=str, const="src/dfcx_scrapi/core_ml/cpk", default="src/dfcx_scrapi/core_ml/cpk")
    parser.add_argument("model_name_or_path", help="", nargs='?', type=str, const="t5-small", default="t5-small")
    parser.add_argument("tokenizer_name_or_path", help="Debug", nargs='?', type=str, const="t5-small", default="t5-small")
    #parser.add_argument("max_seq_length", help="", nargs='?', type=int, const=512, default=512)
    parser.add_argument("learning_rate", help="", nargs='?', type=float, const=3e-4, default=3e-4)
    parser.add_argument("weight_decay", help="", nargs='?', type=float, const=0.0, default=0.0)
    parser.add_argument("adam_epsilon", help="", nargs='?', type=float, const=1e-8, default=1e-8)
    parser.add_argument("warmup_steps", help="", nargs='?', type=int, const=0, default=0)
    parser.add_argument("train_batch_size", help="", nargs='?', type=int, const=8, default=8)
    parser.add_argument("eval_batch_size", help="", nargs='?', type=int, const=8, default=8)
    parser.add_argument("num_train_epochs", help="Debug", nargs='?', type=int, const=2, default=2)
    parser.add_argument("gradient_accumulation_steps", help="", nargs='?', type=int, const=16, default=16)
    parser.add_argument("n_gpu", help="", nargs='?', type=int, const=1, default=1)
    parser.add_argument("early_stop_callback", help="", nargs='?', type=bool, const=False, default=False)
    parser.add_argument("fp_16", help="Debug", nargs='?', type=bool, const=False, default=False)
    parser.add_argument("opt_level", help="", nargs='?', type=str, const='O1', default='O1')
    parser.add_argument("max_grad_norm", help="", nargs='?', type=float, const=1.0, default=1.0)
    parser.add_argument("seed", help="", nargs='?', type=int, const=42, default=42)
    main(parser.parse_args())