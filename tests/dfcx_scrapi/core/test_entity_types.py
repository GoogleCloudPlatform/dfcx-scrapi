"""Test Class for Entity Type Methods in SCRAPI."""

# Copyright 2026 Google LLC
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

from dfcx_scrapi.core.entity_types import (
    ADVANCED_ENTITY_TYPE_COLUMNS,
    BASIC_ENTITY_TYPE_COLUMNS,
    EXCLUDED_PHRASES_COLUMNS,
    EntityTypes,
)


def _entity_types_with_list(monkeypatch, entity_types):
    client = EntityTypes.__new__(EntityTypes)
    client.agent_id = "projects/test/locations/global/agents/test"
    monkeypatch.setattr(
        client, "list_entity_types", lambda agent_id: entity_types
    )
    return client


def test_entity_types_to_df_returns_empty_basic_schema(monkeypatch):
    client = _entity_types_with_list(monkeypatch, [])

    df = client.entity_types_to_df(mode="basic")

    assert df.empty
    assert list(df.columns) == BASIC_ENTITY_TYPE_COLUMNS


def test_entity_types_to_df_returns_empty_advanced_schema(monkeypatch):
    client = _entity_types_with_list(monkeypatch, [])

    result = client.entity_types_to_df(mode="advanced")

    assert result["entity_types"].empty
    assert list(result["entity_types"].columns) == ADVANCED_ENTITY_TYPE_COLUMNS
    assert result["excluded_phrases"].empty
    assert list(result["excluded_phrases"].columns) == EXCLUDED_PHRASES_COLUMNS
