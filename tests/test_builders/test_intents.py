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

    assert ib.proto_obj.display_name == "SomeIntent"
    assert ib.proto_obj.priority == 1234
    assert ib.proto_obj.description == "Some Description"


def test_load_intent(create_intent_fixture):
    ib = IntentBuilder(create_intent_fixture)
    assert isinstance(ib.proto_obj, Intent)
    assert ib.proto_obj == create_intent_fixture

    ib2 = IntentBuilder(create_intent_fixture)
    assert isinstance(ib2.proto_obj, Intent)
    assert ib2.proto_obj == create_intent_fixture
