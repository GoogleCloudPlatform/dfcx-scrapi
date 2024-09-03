"""Test Class for Dataframe Function Methods in SCRAPI."""

# pylint: disable=redefined-outer-name

# Copyright 2024 Google LLC
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
from unittest.mock import MagicMock

from google.oauth2.service_account import Credentials
from dfcx_scrapi.tools.dataframe_functions import DataframeFunctions


@pytest.fixture
def test_config():
    project_id = "my-project-id-1234"
    email = "mock_email@testing.com"
    creds_path = "/Users/path/to/creds/credentials.json"
    creds_dict = {
        "type": "service_account",
        "project_id": project_id,
        "private_key_id": "1234",
        "private_key": "mock_key",
        "client_email": f"mock-account@{project_id}.iam.gserviceaccount.com",
        "client_id": "1234",
        "universe_domain": "googleapis.com",
    }

    mock_signer = MagicMock()
    mock_signer.key_id = "mock_key_id"
    mock_signer.sign.return_value = b"mock_signature"

    creds_object = Credentials(
        signer=mock_signer,
        token_uri="mock_token_uri",
        service_account_email=email,
        project_id=project_id,
        quota_project_id=project_id,
        scopes=[],
    )

    return {
        "project_id": project_id,
        "creds_path": creds_path,
        "creds_dict": creds_dict,
        "creds_object": creds_object,
    }


@pytest.fixture
def mock_dffx_setup(monkeypatch, test_config):
    """Fixture to create mock DataframeFunctions object w/ mocked clients."""

    # mocking all other classes used by DFFX
    mock_credentials_from_file = MagicMock(
        return_value=test_config["creds_object"]
    )

    monkeypatch.setattr(
        "google.oauth2.service_account.Credentials.from_service_account_file",
        mock_credentials_from_file,
    )

    # mocking all other classes used by DFFX
    def mock_scrapi_base_init(self, *args, **kwargs):
        # Simulate the original behavior
        if kwargs.get("creds_path"):
            self.creds = Credentials.from_service_account_file(
                kwargs.get("creds_path")
            )
        elif kwargs.get("creds_dict"):
            self.creds = Credentials.from_service_account_info(
                kwargs.get("creds_dict")
            )
        else:
            self.creds = kwargs.get("creds")

    def mock_entities_init(self, *args, **kwargs):
        pass

    def mock_intents_init(self, *args, **kwargs):
        pass

    def mock_flows_init(self, *args, **kwargs):
        pass

    def mock_pages_init(self, *args, **kwargs):
        pass

    def mock_route_groups_init(self, *args, **kwargs):
        pass

    monkeypatch.setattr(
        "dfcx_scrapi.core.scrapi_base.ScrapiBase.__init__",
        mock_scrapi_base_init,
    )

    monkeypatch.setattr(
        "dfcx_scrapi.core.entity_types.EntityTypes.__init__", mock_entities_init
    )

    monkeypatch.setattr(
        "dfcx_scrapi.core.intents.Intents.__init__", mock_intents_init
    )

    monkeypatch.setattr(
        "dfcx_scrapi.core.flows.Flows.__init__", mock_flows_init
    )

    monkeypatch.setattr(
        "dfcx_scrapi.core.pages.Pages.__init__", mock_pages_init
    )

    monkeypatch.setattr(
        "dfcx_scrapi.core.transition_route_groups.TransitionRouteGroups.__init__",
        mock_route_groups_init,
    )

    yield mock_credentials_from_file


# Test init with creds_path
def test_dffx_init_creds_path(mock_dffx_setup, test_config):
    mock_creds = mock_dffx_setup
    dffx = DataframeFunctions(creds_path=test_config["creds_path"])

    assert dffx.creds == test_config["creds_object"]
    mock_creds.assert_called_once_with(test_config["creds_path"])


# Test init with creds_dict
def test_dffx_init_creds_dict(mock_dffx_setup, test_config):
    mock_creds = mock_dffx_setup
    dffx = DataframeFunctions(creds_path=test_config["creds_dict"])

    assert dffx.creds == test_config["creds_object"]
    mock_creds.assert_called_once_with(test_config["creds_dict"])


# Test init with creds object
def test_dffx_init_creds_object(mock_dffx_setup, test_config):
    dffx = DataframeFunctions(creds=test_config["creds_object"])

    assert dffx.creds == test_config["creds_object"]
