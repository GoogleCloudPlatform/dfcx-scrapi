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
def default_agent_creator_fixture():
    return types.Agent(
        display_name="MyAgent", time_zone="America/New_York",
        default_language_code="en",)

@pytest.fixture
def customized_agent_creator_fixture():
    return types.Agent(
        display_name="CustomizedAgent", time_zone="Europe/Paris", locked=False,
        default_language_code="es", description="This is the description",)
