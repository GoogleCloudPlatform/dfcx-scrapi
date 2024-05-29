"""Test Class for ResponseMessageBuilder in SCRAPI's builder package."""

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

from dfcx_scrapi.builders.response_messages import ResponseMessage
from dfcx_scrapi.builders.response_messages import ResponseMessageBuilder


def test_create_new_proto_text_single():
    rmb = ResponseMessageBuilder()
    assert rmb.proto_obj is None

    rmb.create_new_proto_obj(response_type="text", message="foo")
    assert isinstance(rmb.proto_obj, ResponseMessage)
    assert rmb.proto_obj.text.text == ["foo"]


def test_create_new_proto_text_multiple():
    rmb = ResponseMessageBuilder()
    assert rmb.proto_obj is None

    msgs = ["foo", "bar", "baz"]
    rmb.create_new_proto_obj(response_type="text", message=msgs)
    assert rmb.proto_obj.text.text == msgs


def test_create_new_proto_valid_payload():
    rmb = ResponseMessageBuilder()
    assert rmb.proto_obj is None

    sample_payload = {
        "p1": 1, "p2": "test", "p3": 1.23,
        "p4": True, "p5": [1, 2]
    }
    rmb.create_new_proto_obj("payload", sample_payload)
    for k, v in rmb.proto_obj.payload.items():
        assert k in sample_payload
        assert v == sample_payload[k]


def test_create_new_proto_invalid_payload():
    rmb = ResponseMessageBuilder()
    assert rmb.proto_obj is None

    with pytest.raises(ValueError):
        rmb.create_new_proto_obj("payload", {1: "some_value"})

    with pytest.raises(ValueError):
        rmb.create_new_proto_obj("payload", {1.2: "some_value"})

    with pytest.raises(ValueError):
        rmb.create_new_proto_obj("payload", {"p1": "test", 1: "some_value"})


def test_create_new_proto_valid_conversation_success():
    rmb = ResponseMessageBuilder()
    assert rmb.proto_obj is None

    sample_payload = {
        "p1": 1, "p2": "test", "p3": 1.23,
        "p4": True, "p5": [1, 2]
    }
    rmb.create_new_proto_obj("conversation_success", sample_payload)
    for k, v in rmb.proto_obj.conversation_success.metadata.items():
        assert k in sample_payload
        assert v == sample_payload[k]


def test_create_new_proto_invalid_conversation_success():
    rmb = ResponseMessageBuilder()
    assert rmb.proto_obj is None

    with pytest.raises(ValueError):
        rmb.create_new_proto_obj("conversation_success", {1: "some_value"})

    with pytest.raises(ValueError):
        rmb.create_new_proto_obj("conversation_success", {1.2: "some_value"})

    with pytest.raises(ValueError):
        rmb.create_new_proto_obj(
            "conversation_success", {"p1": "test", 1: "some_value"})


def test_create_new_proto_valid_live_agent_handoff():
    rmb = ResponseMessageBuilder()
    assert rmb.proto_obj is None

    sample_payload = {
        "p1": 1, "p2": "test", "p3": 1.23,
        "p4": True, "p5": [1, 2]
    }
    rmb.create_new_proto_obj("live_agent_handoff", sample_payload)
    for k, v in rmb.proto_obj.live_agent_handoff.metadata.items():
        assert k in sample_payload
        assert v == sample_payload[k]


def test_create_new_proto_invalid_live_agent_handoff():
    rmb = ResponseMessageBuilder()
    assert rmb.proto_obj is None

    with pytest.raises(ValueError):
        rmb.create_new_proto_obj("live_agent_handoff", {1: "some_value"})

    with pytest.raises(ValueError):
        rmb.create_new_proto_obj("live_agent_handoff", {1.2: "some_value"})

    with pytest.raises(ValueError):
        rmb.create_new_proto_obj(
            "live_agent_handoff", {"p1": "test", 1: "some_value"})

