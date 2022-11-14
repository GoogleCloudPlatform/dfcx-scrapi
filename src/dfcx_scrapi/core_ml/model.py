"""Utiliity functions to fine tine pretrained T5 summarization model for paraphrasing."""

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
#import torch_xla.core.xla_model as xm 
from torch.utils.data import Dataset, DataLoader
from transformers import (
    AdamW,
    T5ForConditionalGeneration,
    T5Tokenizer,
    get_linear_schedule_with_warmup
)
from torch_dataset import T5Dataset

# DATA_DIR = "data/final/"
# MODEL_NAME = "t5-base"
# OUTPUT_DIR = "src/dfcx_scrapi/core_ml/cpk"


# args_dict = dict(
#   data_dir=DATA_DIR, # path for data files
#   output_dir=OUTPUT_DIR, # path to save the checkpoints
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
#   seed=42,
# )


class LoggingCallback(pl.Callback):
  def __init__(self, logger = None) -> None:
      super().__init__()

      self.logger = logger # if this doesn't work. It's most likely this.
  def on_validation_end(self, trainer, pl_module):
    
    self.logger.info("***** Validation results *****")
    if pl_module.is_logger():
      metrics = trainer.callback_metrics
      # Log results
      for key in sorted(metrics):
        if key not in ["log", "progress_bar"]:
          self.logger.info("{} = {}\n".format(key, str(metrics[key])))

  def on_test_end(self, trainer, pl_module):
    self.logger.info("***** Test results *****")

    if pl_module.is_logger():
      metrics = trainer.callback_metrics

      # Log and save results to file
      output_test_results_file = os.path.join(pl_module.hparams.output_dir, "test_results.txt") # take a look at this.
      with open(output_test_results_file, "w") as writer:
        for key in sorted(metrics):
          if key not in ["log", "progress_bar"]:
            self.logger.info("{} = {}\n".format(key, str(metrics[key])))
            writer.write("{} = {}\n".format(key, str(metrics[key])))


class FineTuneT5Model(pl.LightningModule):
  def __init__(
    self, 
    adam_epsilon: float = None, 
    eval_batch_size: int = None,
    data_dir: str = None,
    gradient_accumulation_steps: int = None,
    file_type: str = None,
    learning_rate: float = None,
    model_name_or_path: str = None, 
    n_gpu: int = None, 
    num_train_epochs: int = None, 
    tokenizer_name_or_path: str = None, 
    train_batch_size: int = None,
    warmup_steps: int = None, 
    weight_decay: float = None,
    train_dataset_file_name: str = None,
    val_dataset_file_name: str = None,
    #test_dataset_file_name: str = None
    ):
    super(FineTuneT5Model, self).__init__()

    # self.hparams = hparams
    self.data_dir = data_dir
    self.eval_batch_size = eval_batch_size
    self.file_type = file_type
    self.model_name_or_path = model_name_or_path
    self.num_train_epochs = num_train_epochs
    self.tokenizer_name_or_path = tokenizer_name_or_path
    self.weight_decay = weight_decay
    self.learning_rate = learning_rate
    self.adam_epsilon = adam_epsilon
    self.n_gpu = n_gpu
    self.train_batch_size = train_batch_size
    self.gradient_accumulation_steps = gradient_accumulation_steps
    self.warmup_steps = warmup_steps
    self.train_dataset_file_name = train_dataset_file_name
    #self.test_dataset_file_name = test_dataset_file_name
    self.val_dataset_file_name = val_dataset_file_name

    self.model = T5ForConditionalGeneration.from_pretrained(self.model_name_or_path)
    self.tokenizer = T5Tokenizer.from_pretrained(self.tokenizer_name_or_path)
    
    
  def is_logger(self):
    return True
  
  def forward(
      self, input_ids, attention_mask=None, decoder_input_ids=None, decoder_attention_mask=None, lm_labels=None
  ):
    return self.model(
        input_ids,
        attention_mask=attention_mask,
        decoder_input_ids=decoder_input_ids,
        decoder_attention_mask=decoder_attention_mask,
        lm_labels=lm_labels,
    )

  def _step(self, batch):
    lm_labels = batch["target_ids"]
    lm_labels[lm_labels[:, :] == self.tokenizer.pad_token_id] = -100

    outputs = self(
        input_ids=batch["source_ids"],
        attention_mask=batch["source_mask"],
        lm_labels=lm_labels,
        decoder_attention_mask=batch['target_mask']
    )

    loss = outputs[0]

    return loss

  def training_step(self, batch, batch_idx):
    loss = self._step(batch)

    tensorboard_logs = {"train_loss": loss}
    return {"loss": loss, "log": tensorboard_logs}
  
  def training_epoch_end(self, outputs):
    avg_train_loss = torch.stack([x["loss"] for x in outputs]).mean()
    tensorboard_logs = {"avg_train_loss": avg_train_loss}
    return {"avg_train_loss": avg_train_loss, "log": tensorboard_logs, 'progress_bar': tensorboard_logs}

  def validation_step(self, batch, batch_idx):
    loss = self._step(batch)
    return {"val_loss": loss}
  
  def validation_epoch_end(self, outputs):
    avg_loss = torch.stack([x["val_loss"] for x in outputs]).mean()
    tensorboard_logs = {"val_loss": avg_loss}
    return {"avg_val_loss": avg_loss, "log": tensorboard_logs, 'progress_bar': tensorboard_logs}

  def configure_optimizers(self):
    "Prepare optimizer and schedule (linear warmup and decay)"

    model = self.model
    no_decay = ["bias", "LayerNorm.weight"]
    optimizer_grouped_parameters = [
        {
            "params": [p for n, p in model.named_parameters() if not any(nd in n for nd in no_decay)],
            "weight_decay": self.weight_decay,
        },
        {
            "params": [p for n, p in model.named_parameters() if any(nd in n for nd in no_decay)],
            "weight_decay": 0.0,
        },
    ]
    optimizer = AdamW(optimizer_grouped_parameters, lr=self.learning_rate, eps=self.adam_epsilon)
    self.opt = optimizer
    return [optimizer]
  
  def optimizer_step(self, epoch, batch_idx, optimizer, optimizer_idx, second_order_closure=None,using_native_amp=None):
    
    # if self.trainer.use_tpu:
    #   xm.optimizer_step(optimizer)
    # else:
    optimizer.step()
    optimizer.zero_grad()
    self.lr_scheduler.step()
  
  def get_tqdm_dict(self):
    tqdm_dict = {"loss": "{:.3f}".format(self.trainer.avg_loss), "lr": self.lr_scheduler.get_last_lr()[-1]}

    return tqdm_dict
  
  def get_dataset(self, tokenizer, data_dir: str, file_name: str, file_type:str):
      return T5Dataset(tokenizer=tokenizer, data_dir=data_dir, file_name=file_name, file_type=file_type)

  def train_dataloader(self):
    # calling T5Dataset
    train_dataset = T5Dataset(tokenizer=self.tokenizer, data_dir=self.data_dir, file_name=self.train_dataset_file_name, file_type = self.file_type) # figure out this interaction with data dir and file name
    # This loads the data with Dataloader
    dataloader = DataLoader(train_dataset, batch_size=self.train_batch_size, drop_last=True, shuffle=True, num_workers=4)
    t_total = (
        (len(dataloader.dataset) // (self.train_batch_size * max(1, self.n_gpu)))
        // self.gradient_accumulation_steps
        * float(self.num_train_epochs)
    )
    scheduler = get_linear_schedule_with_warmup(
        self.opt, num_warmup_steps=self.warmup_steps, num_training_steps=t_total
    )
    self.lr_scheduler = scheduler
    return dataloader

  def val_dataloader(self):
        val_dataset = T5Dataset(tokenizer=self.tokenizer, data_dir=self.data_dir, file_name=self.val_dataset_file_name, file_type = self.file_type)
        return DataLoader(val_dataset, batch_size=self.eval_batch_size, num_workers=4)
    
  # def test_dataloader(self):
  #   test_dataset = T5Dataset(tokenizer=self.tokenizer, data_dir=self.data_dir, file_name=self.test_dataset_file_name, file_type = self.file_type)
  #   return DataLoader(val_dataset, batch_size=self.eval_batch_size, num_workers=4)
    
    
  



