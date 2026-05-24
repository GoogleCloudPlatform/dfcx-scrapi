"""Test evaluation data loading helpers."""

# Copyright 2024 Google LLC
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
import pytest

from dfcx_scrapi.tools.evaluations import DataLoader


@pytest.fixture
def data_loader():
    loader = DataLoader.__new__(DataLoader)
    loader.required_columns = [
        "eval_id",
        "action_id",
        "action_type",
        "action_input",
    ]
    return loader


def valid_eval_dataframe() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "eval_id": [1, 1],
            "action_id": ["1", "2"],
            "action_type": ["User Utterance", "Agent Response"],
            "action_input": ["hello", "hi"],
        }
    )


def test_validate_and_prep_inputs_casts_required_values(data_loader):
    df = valid_eval_dataframe()

    result = data_loader.validate_and_prep_inputs(df)

    assert result["action_id"].tolist() == [1, 2]
    assert result["eval_id"].tolist() == ["1", "1"]
    assert result["action_type"].tolist() == ["User Utterance", "Agent Response"]
    assert result["action_input"].tolist() == ["hello", "hi"]


def test_validate_and_prep_inputs_adds_missing_action_id(data_loader):
    df = valid_eval_dataframe().drop(columns=["action_id"])

    result = data_loader.validate_and_prep_inputs(df)

    assert result["action_id"].tolist() == [1, 1]


def test_validate_and_prep_inputs_rejects_empty_required_values(data_loader):
    df = valid_eval_dataframe()
    df.loc[1, "action_input"] = "  "

    with pytest.raises(ValueError, match="action_input"):
        data_loader.validate_and_prep_inputs(df)


def test_validate_and_prep_inputs_rejects_invalid_action_id(data_loader):
    df = valid_eval_dataframe()
    df.loc[1, "action_id"] = "not-an-int"

    with pytest.raises(ValueError, match="action_id"):
        data_loader.validate_and_prep_inputs(df)


def test_validate_and_prep_inputs_rejects_fractional_action_id(data_loader):
    df = valid_eval_dataframe()
    df.loc[1, "action_id"] = 1.5

    with pytest.raises(ValueError, match="Invalid row indices"):
        data_loader.validate_and_prep_inputs(df)
