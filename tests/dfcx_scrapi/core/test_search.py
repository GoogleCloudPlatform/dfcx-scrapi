"""Unit tests for Search helpers."""

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

from google.cloud.discoveryengine import SearchRequest

from dfcx_scrapi.core.search import Search


def test_build_boost_spec_accepts_snake_case_dict():
    search = Search.__new__(Search)

    boost_spec = search.build_boost_spec({
        "boost_spec": {
            "condition_boost_specs": [
                {
                    "condition": 'color: ANY("red")',
                    "boost": 0.5,
                }
            ]
        }
    })

    assert isinstance(boost_spec, SearchRequest.BoostSpec)
    assert boost_spec.condition_boost_specs[0].condition == 'color: ANY("red")'
    assert boost_spec.condition_boost_specs[0].boost == 0.5


def test_build_boost_spec_accepts_camel_case_dict():
    search = Search.__new__(Search)

    boost_spec = search.build_boost_spec({
        "boostSpec": {
            "conditionBoostSpecs": [
                {
                    "condition": 'category: ANY("shoes")',
                    "boost": 1.0,
                }
            ]
        }
    })

    assert isinstance(boost_spec, SearchRequest.BoostSpec)
    assert (
        boost_spec.condition_boost_specs[0].condition
        == 'category: ANY("shoes")'
    )
    assert boost_spec.condition_boost_specs[0].boost == 1.0


def test_build_boost_spec_accepts_proto():
    search = Search.__new__(Search)
    proto_boost_spec = SearchRequest.BoostSpec(
        condition_boost_specs=[
            SearchRequest.BoostSpec.ConditionBoostSpec(
                condition='brand: ANY("google")',
                boost=0.25,
            )
        ]
    )

    boost_spec = search.build_boost_spec({"boost_spec": proto_boost_spec})

    assert boost_spec is proto_boost_spec

