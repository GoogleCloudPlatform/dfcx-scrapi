"""Test Class for FulfillmentBuilder in SCRAPI's builder package."""

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

from dfcx_scrapi.builders.fulfillments import Fulfillment
from dfcx_scrapi.builders.fulfillments import FulfillmentBuilder


def test_create_new_proto_obj():
    fb = FulfillmentBuilder()
    assert fb.proto_obj is None

    fb.create_new_proto_obj()
    assert isinstance(fb.proto_obj, Fulfillment)
    assert fb.proto_obj.return_partial_responses == False
    assert fb.proto_obj.messages == []

    with pytest.raises(UserWarning):
        fb.create_new_proto_obj(return_partial_responses=True)

    fb.create_new_proto_obj(return_partial_responses=True, overwrite=True)
    assert fb.proto_obj.return_partial_responses == True


def test_create_new_proto_obj_with_webhook():
    fb = FulfillmentBuilder()
    custom_wbhk = (
        "projects/sample_project_id/locations/sample_location_id"
        "/agents/sample_agent_id/webhooks/sample_webhook_id")
    fb.create_new_proto_obj(
        webhook=custom_wbhk,
        tag="new_tag"
    )
    assert fb.proto_obj.webhook == custom_wbhk
    assert fb.proto_obj.tag == "new_tag"

    with pytest.raises(ValueError):
        fb.create_new_proto_obj(webhook=custom_wbhk, overwrite=True)


def test_add_parameter_presets_with_valid_dict():
    valid_param_map = {"p1": "v1", "p2": 123, "p3": True, "p4": None}
    fb = FulfillmentBuilder()
    fb.create_new_proto_obj()
    fb.add_parameter_presets(valid_param_map)

    for p in fb.proto_obj.set_parameter_actions:
        assert p.parameter in valid_param_map
        assert p.value == valid_param_map[p.parameter]


def test_add_parameter_presets_with_invalid_dict():
    invalid_param_map = {"p1": "v1", 123: "p2"}
    fb = FulfillmentBuilder()
    fb.create_new_proto_obj()
    with pytest.raises(ValueError):
        fb.add_parameter_presets(invalid_param_map)

    # passing a list instead of dict
    with pytest.raises(ValueError):
        fb.add_parameter_presets(list(invalid_param_map.keys()))
