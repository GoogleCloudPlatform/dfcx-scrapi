"""Pytest config file for builders."""

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

import pytest

from google.cloud.dialogflowcx_v3beta1 import types


@pytest.fixture
def default_agent_fixture():
    return types.Agent(
        display_name="MyAgent", time_zone="America/New_York",
        default_language_code="en",)

@pytest.fixture
def customized_agent_fixture():
    return types.Agent(
        display_name="CustomizedAgent", time_zone="Europe/Paris", locked=False,
        default_language_code="es", description="This is the description",)


@pytest.fixture
def empty_intent():
    intent = types.Intent(
        display_name="MyIntent", priority=30000, is_fallback=False,
        description="The descriptoin of the intent")

    return intent

@pytest.fixture
def intent_with_parameters(empty_intent):
    sys_ent = "projects/-/locations/-/agents/-/entityTypes/sys.date"
    custom_ent = (
        "projects/sample_project_id/locations/sample_location_id"
        "/agents/sample_agent_id/entityTypes/sample_entity_type_id")
    empty_intent.parameters = [
        types.Intent.Parameter(
            id="date_id", entity_type=sys_ent, is_list=False, redact=True),
        types.Intent.Parameter(
            id="some_id", entity_type=custom_ent, is_list=False, redact=False),
    ]
    return empty_intent

@pytest.fixture
def intent_with_labels(empty_intent):
    empty_intent.labels = {
        "label1": "label1", "sys-head": "sys-head", "label2": "l2"
    }

    return empty_intent

@pytest.fixture
def full_intent(intent_with_parameters):
    tp_cls = types.Intent.TrainingPhrase
    intent_with_parameters.training_phrases = [
        tp_cls(parts=[tp_cls.Part(text="first training phrase")]),
        tp_cls(parts=[tp_cls.Part(text="second training phrase")]),
        tp_cls(parts=[tp_cls.Part(text="third training phrase")]),
        tp_cls(parts=[
            tp_cls.Part(text="training phrase with date "),
            tp_cls.Part(text="Jan 1 2023", parameter_id="date_id")]),
        tp_cls(parts=[
            tp_cls.Part(text="training phrase with custom entity "),
            tp_cls.Part(text="Some Entity", parameter_id="some_id")]),
    ]
    return intent_with_parameters
