"""Test Class for IntentBuilder in SCRAPI's builder package."""

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

from dfcx_scrapi.builders.intents import Intent
from dfcx_scrapi.builders.intents import IntentBuilder


def test_create_new_proto_obj():
    ib = IntentBuilder()
    ib.create_new_proto_obj(
        display_name="SomeIntent",
        priority=1234, is_fallback=False,
        description="Some Description")

    assert isinstance(ib.proto_obj, Intent)
    assert ib.proto_obj.display_name == "SomeIntent"
    assert ib.proto_obj.priority == 1234
    assert ib.proto_obj.description == "Some Description"

def test_create_new_proto_obj2(empty_intent):
    ib = IntentBuilder()
    ib.create_new_proto_obj(
        display_name="MyIntent", priority=30000, is_fallback=False,
        description="The descriptoin of the intent")

    assert ib.proto_obj == empty_intent

    # Create a new proto when there is an existing one
    ib2 = IntentBuilder(empty_intent)
    with pytest.raises(UserWarning):
        ib2.create_new_proto_obj(
            display_name="MyIntent", priority=30000, is_fallback=False,
            description="The descriptoin of the intent")

    # Overwrite check
    ib2 = IntentBuilder(empty_intent)
    ib2.create_new_proto_obj(
        display_name="MyIntent", priority=30000, is_fallback=False,
        description="The descriptoin of the intent", overwrite=True)
    assert ib2.proto_obj == empty_intent

def test_load_intent(empty_intent, intent_with_labels, default_agent_fixture):
    ib = IntentBuilder(empty_intent)
    assert isinstance(ib.proto_obj, Intent)
    assert ib.proto_obj == empty_intent

    ib2 = IntentBuilder()
    ib2.load_proto_obj(empty_intent)
    assert isinstance(ib2.proto_obj, Intent)
    assert ib2.proto_obj == empty_intent

    # Overwrite check
    with pytest.raises(UserWarning):
        ib.load_proto_obj(intent_with_labels)

    ib.load_proto_obj(obj=intent_with_labels, overwrite=True)
    assert ib.proto_obj == intent_with_labels

    # Load wrong obj type
    with pytest.raises(ValueError):
        IntentBuilder(default_agent_fixture)

def test_add_parameter(empty_intent, intent_with_parameters):
    ib = IntentBuilder(empty_intent)
    sys_ent = "projects/-/locations/-/agents/-/entityTypes/sys.date"
    custom_ent = (
        "projects/sample_project_id/locations/sample_location_id"
        "/agents/sample_agent_id/entityTypes/sample_entity_type_id")
    ib.add_parameter(
        parameter_id="date_id", entity_type=sys_ent,
        is_list=False, redact=True)
    ib.add_parameter(
        parameter_id="some_id", entity_type=custom_ent,
        is_list=False, redact=False)

    assert ib.proto_obj.parameters == intent_with_parameters.parameters
    assert ib.proto_obj == intent_with_parameters

    # Type checking test
    with pytest.raises(ValueError):
        ib.add_parameter(parameter_id=123, entity_type="some_ent")

    with pytest.raises(ValueError):
        ib.add_parameter(parameter_id="123", entity_type=123)

def test_add_label(empty_intent, intent_with_labels):
    ib = IntentBuilder(empty_intent)
    ib.add_label("sys-head")
    ib.add_label("label1")
    ib.add_label({"label2": "l2"})

    assert ib.proto_obj.labels == intent_with_labels.labels

    # Check constraints
    with pytest.raises(ValueError):
        ib.add_label("LABEL1")
    with pytest.raises(ValueError):
        ib.add_label("-label")
    with pytest.raises(ValueError):
        ib.add_label("label!")
    with pytest.raises(ValueError):
        ib.add_label("sys-label")
    with pytest.raises(ValueError):
        long_label = (
            "abcdabcdabcdabcdabcdabcdabcdabcdabcdabcd"
            "abcdabcdabcdabcdabcdabcdabcdabcdabcdabcd")
        ib.add_label(long_label)

def test_add_training_phrase(intent_with_parameters, full_intent):
    ib = IntentBuilder(intent_with_parameters)
    ib.add_training_phrase("first training phrase")
    ib.add_training_phrase("second training phrase")
    ib.add_training_phrase("third training phrase")
    ib.add_training_phrase(
        phrase=["training phrase with date", "Jan 1 2023"],
        annotations=["", "date_id"])
    ib.add_training_phrase(
        phrase=["training phrase with date", "Some Entity"],
        annotations=["", "some_id"])
    assert ib.proto_obj.training_phrases == full_intent.training_phrases
    assert ib.proto_obj == full_intent
