"""Test Class for AgentBuilder in SCRAPI's builder package."""

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

from dfcx_scrapi.builders.agents import Agent
from dfcx_scrapi.builders.agents import AgentBuilder


def test_create_new_agent():
    ab = AgentBuilder()
    ab.create_new_proto_obj(
        display_name="MyAgent", time_zone="America/New_York")

    assert isinstance(ab.proto_obj, Agent)
    assert ab.proto_obj.display_name == "MyAgent"
    assert ab.proto_obj.time_zone == "America/New_York"
    assert ab.proto_obj.default_language_code == "en"

def test_load_agent(default_agent_creator_fixture):
    # a = Agent(display_name="MyAgent", time_zone="America/New_York")
    ab = AgentBuilder(default_agent_creator_fixture)

    assert isinstance(ab.proto_obj, Agent)
    assert ab.proto_obj.display_name == "MyAgent"
    assert ab.proto_obj.time_zone == "America/New_York"
    assert ab.proto_obj.default_language_code == "en"

def test_overwrite(default_agent_creator_fixture):
    ab = AgentBuilder(default_agent_creator_fixture)
    with pytest.raises(UserWarning):
        ab.create_new_proto_obj(
            display_name="test_name", time_zone="Europe/Paris")

    ab2 = AgentBuilder()
    ab2.create_new_proto_obj(
        display_name="MyAgent", time_zone="America/New_York")
    with pytest.raises(UserWarning):
        ab2.load_proto_obj(default_agent_creator_fixture)

def test_set_lang_and_speech_settings(default_agent_creator_fixture):
    ab = AgentBuilder(default_agent_creator_fixture)
    assert ab.proto_obj.enable_spell_correction is False
    spch_adapt = ab.proto_obj.speech_to_text_settings.enable_speech_adaptation
    assert spch_adapt is False
    assert ab.proto_obj.supported_language_codes == []


    supported_lang_codes = ["es", "fr", "de"]
    ab.language_and_speech_settings(
        enable_speech_adaptation=True,
        enable_spell_correction=True,
        supported_language_codes=supported_lang_codes)

    assert ab.proto_obj.enable_spell_correction is True
    spch_adapt = ab.proto_obj.speech_to_text_settings.enable_speech_adaptation
    assert spch_adapt is True
    for lang in supported_lang_codes:
        assert lang in ab.proto_obj.supported_language_codes

