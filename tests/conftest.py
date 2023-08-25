"""Pytest config file"""

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

def pytest_addoption(parser):
    """Method to add option for creds in tests."""
    parser.addoption("--creds", action="store")
    parser.addoption("--project_id", action="store")
    parser.addoption("--gcs_bucket", action="store")
    parser.addoption("--agent_id", action="store")


@pytest.fixture(scope="session")
def creds(request):
    """Fixture to share creds across the test class"""
    return request.config.getoption("--creds")

@pytest.fixture(scope="session")
def project_id(request):
    """Fixture to share project across the test class"""
    return request.config.getoption("--project_id")

@pytest.fixture(scope="session")
def gcs_bucket(request):
    """Fixture to share gcs_bucket across the test class"""
    return request.config.getoption("--gcs_bucket")

@pytest.fixture(scope="session")
def agent_id(request):
    return request.config.getoption("agent_id")
