"""Test Class for Base Class Methods in SCRAPI."""

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
from unittest.mock import patch, MagicMock
from google.oauth2.credentials import Credentials as UserCredentials
from google.oauth2.service_account import Credentials as ServiceAccountCredentials
from google.api_core import exceptions
from google.protobuf import field_mask_pb2, struct_pb2
from google.cloud.dialogflowcx_v3beta1 import types

from dfcx_scrapi.core.scrapi_base import (
    api_call_counter_decorator, 
    should_retry,
    retry_api_call,
    handle_api_error,
    ScrapiBase
    )

@pytest.fixture
def test_config():
    project_id = "my-project-id-1234"
    default_id = "00000000-0000-0000-0000-000000000000"

    global_parent = f"projects/{project_id}/locations/global"
    global_agent_id = f"{global_parent}/agents/my-agent-1234"
    global_datastore_id = f"{global_parent}/dataStores/test-datastore"
    global_flow_id = f"{global_agent_id}/flows/{default_id}"

    non_global_parent = f"projects/{project_id}/locations/us-central1"
    non_global_agent_id = f"{non_global_parent}/agents/my-agent-1234"
    non_global_datastore_id = f"{non_global_parent}/dataStores/test-datastore"

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
    global_scopes = [
        "https://www.googleapis.com/auth/cloud-platform",
        "https://www.googleapis.com/auth/dialogflow",
        ]

    mock_signer = MagicMock()
    mock_signer.key_id = "mock_key_id"
    mock_signer.sign.return_value = b"mock_signature"

    creds_object = ServiceAccountCredentials(
        signer=mock_signer,
        token_uri="https://oauth2.googleapis.com/token",
        service_account_email=email,
        project_id=project_id,
        quota_project_id=project_id,
        scopes=[],
    )
    creds_object.token = "mock_token"
    creds_object.refresh = MagicMock()

    adc_creds = UserCredentials(
        token="mock_user_token",
        client_id="mock_client_id",
        client_secret="mock_client_secret",
        quota_project_id=project_id
    )
    adc_creds.refresh = MagicMock()

    return {
        "project_id": project_id,
        "global_scopes": global_scopes,
        "global_parent": global_parent,
        "global_agent_id": global_agent_id,
        "global_flow_id": global_flow_id,
        "global_datastore_id": global_datastore_id,
        "creds_path": creds_path,
        "creds_dict": creds_dict,
        "creds_object": creds_object,
        "adc_creds_object": adc_creds,
        "non_global_agent_id": non_global_agent_id,
        "non_global_datastore_id": non_global_datastore_id,
    }

@pytest.fixture
def mocked_scrapi_base(test_config):
    """Fixture to provide a ScrapiBase instance with mocked default creds."""
    with patch("dfcx_scrapi.core.scrapi_base.default") as mock_default:
        mock_adc_creds = test_config["adc_creds_object"]
        mock_default.return_value = (mock_adc_creds, "mock_project_id")
        yield ScrapiBase()


@patch("dfcx_scrapi.core.scrapi_base.default")
def test_init_no_creds(mock_default, test_config):
    """Test initialization with no credentials provided."""
    mock_adc_creds = test_config["adc_creds_object"]
    mock_default.return_value = (mock_adc_creds, "mock_project_id")

    scrapi_base = ScrapiBase()

    assert scrapi_base.creds == mock_adc_creds
    assert isinstance(scrapi_base.creds, UserCredentials)
    assert scrapi_base.token == mock_adc_creds.token
    assert scrapi_base.agent_id is None
    assert not scrapi_base.creds.requires_scopes
    mock_adc_creds.refresh.assert_called_once()
    mock_default.assert_called_once()

def test_init_with_creds(test_config):
    """Test initialization with user provided credentials."""
    mock_creds = test_config["creds_object"]

    scrapi_base = ScrapiBase(creds=mock_creds)

    assert scrapi_base.creds == mock_creds
    assert isinstance(scrapi_base.creds, ServiceAccountCredentials)
    assert scrapi_base.token == mock_creds.token
    assert scrapi_base.agent_id is None
    assert scrapi_base.creds.requires_scopes
    mock_creds.refresh.assert_called_once()


@patch('google.oauth2.service_account.Credentials.from_service_account_file')
def test_init_with_creds_path(mock_from_service_account_file, test_config):
    """Test initialization with credentials path."""
    mock_creds = test_config["creds_object"]

    mock_from_service_account_file.return_value = mock_creds


    scrapi_base = ScrapiBase(creds_path=test_config["creds_path"])

    mock_from_service_account_file.assert_called_once_with(
        test_config["creds_path"], scopes=test_config["global_scopes"])
    assert scrapi_base.creds == mock_creds
    assert isinstance(scrapi_base.creds, ServiceAccountCredentials)
    assert scrapi_base.token == mock_creds.token
    assert scrapi_base.agent_id is None
    assert scrapi_base.creds.requires_scopes
    mock_creds.refresh.assert_called_once()

@patch('google.oauth2.service_account.Credentials.from_service_account_info')
def test_init_with_creds_dict(mock_from_service_account_info, test_config):
    """Test initialization with credentials dictionary."""
    mock_creds = test_config["creds_object"]
    mock_from_service_account_info.return_value = mock_creds

    scrapi_base = ScrapiBase(creds_dict=test_config["creds_dict"])

    mock_from_service_account_info.assert_called_once_with(
        test_config["creds_dict"], scopes=test_config["global_scopes"])
    assert scrapi_base.creds == mock_creds
    assert isinstance(scrapi_base.creds, ServiceAccountCredentials)
    assert scrapi_base.token == mock_creds.token
    assert scrapi_base.agent_id is None
    assert scrapi_base.creds.requires_scopes
    mock_creds.refresh.assert_called_once()

def test_set_region_non_global(test_config):
    """Test _set_region with a non-global location."""
    client_options = ScrapiBase._set_region(test_config["non_global_agent_id"])
    assert client_options["api_endpoint"] == "us-central1-dialogflow.googleapis.com:443"
    assert client_options["quota_project_id"] == test_config["project_id"]

def test_set_region_global(test_config):
    """Test _set_region with a global location."""
    client_options = ScrapiBase._set_region(test_config["global_agent_id"])
    assert client_options["api_endpoint"] == "dialogflow.googleapis.com:443"
    assert client_options["quota_project_id"] == test_config["project_id"]

def test_set_region_invalid_resource_id():
    """Test _set_region with an invalid resource ID."""
    resource_id = "invalid-resource-id"
    with pytest.raises(IndexError):
        ScrapiBase._set_region(resource_id)

def test_client_options_discovery_engine_non_global(test_config):
    """Test _client_options_discovery_engine with a non-global location."""
    client_options = ScrapiBase._client_options_discovery_engine(
        test_config["non_global_datastore_id"])

    assert client_options["api_endpoint"] == "us-central1-discoveryengine.googleapis.com:443"
    assert client_options["quota_project_id"] == test_config["project_id"]

def test_client_options_discovery_engine_global(test_config):
    """Test _client_options_discovery_engine with a global location."""
    client_options = ScrapiBase._client_options_discovery_engine(
        test_config["global_datastore_id"])
  
    assert client_options["api_endpoint"] == "discoveryengine.googleapis.com:443"
    assert client_options["quota_project_id"] == test_config["project_id"]

def test_client_options_discovery_engine_invalid_resource_id():
    """Test _client_options_discovery_engine with an invalid resource ID."""
    resource_id = "invalid-resource-id"
    with pytest.raises(IndexError):
        ScrapiBase._client_options_discovery_engine(resource_id)

def test_pbuf_to_dict():
    """Test pbuf_to_dict."""
    # Create a sample protobuf message
    message = struct_pb2.Struct()
    message["field1"] = "value1"
    message["field2"] = 123

    # Convert to dictionary
    result = ScrapiBase.pbuf_to_dict(message)

    # Assert the result
    assert isinstance(result, dict)
    assert result["field1"] == "value1"
    assert result["field2"] == 123

def test_dict_to_struct():
    """Test dict_to_struct."""
    input_dict = {"field1": "value1", "field2": 123}
    result = ScrapiBase.dict_to_struct(input_dict)
    assert isinstance(result, struct_pb2.Struct)
    assert result["field1"] == "value1"
    assert result["field2"] == 123

def test_parse_agent_id(test_config):
    """Test parse_agent_id with a valid resource ID."""
    resource_id = test_config["global_flow_id"]
    agent_id = ScrapiBase.parse_agent_id(resource_id)
    assert agent_id == test_config["global_agent_id"]

def test_parse_agent_id_short_resource_id(test_config):
    """Test parse_agent_id with a short resource ID."""
    with pytest.raises(ValueError):
        ScrapiBase.parse_agent_id(test_config["global_parent"])

def test_parse_agent_id_invalid_resource_id(test_config):
    """Test parse_agent_id with an invalid resource ID."""
    with pytest.raises(ValueError):
        ScrapiBase.parse_agent_id(test_config["global_datastore_id"])

@patch('dfcx_scrapi.core.scrapi_base.api_call_counter_decorator') 
def test_api_call_counter_decorator(mock_decorator):
    """Test api_call_counter_decorator."""
    mock_decorator.side_effect = lambda func: func # noop

    def mock_api_call():
        pass

    decorated_func = api_call_counter_decorator(mock_api_call)
    assert hasattr(decorated_func, "calls_api")
    assert decorated_func.calls_api is True

def test_should_retry():
    """Test should_retry with different exception types."""
    assert should_retry(exceptions.TooManyRequests("Too many requests")) is True
    assert should_retry(exceptions.ServerError("Server Error")) is True
    assert should_retry(exceptions.BadRequest("Bad Request")) is False
    assert should_retry(ValueError("Value error")) is False

@patch('time.sleep')
def test_retry_api_call_success(mock_sleep):
    """Test retry_api_call with a successful API call."""

    @retry_api_call([1, 2])
    def mock_api_call():
        return "success"

    result = mock_api_call()
    assert result == "success"
    mock_sleep.assert_not_called()

@patch('time.sleep')
def test_retry_api_call_too_many_requests(mock_sleep):
    """Test retry_api_call with TooManyRequests exception."""

    @retry_api_call([1, 2])
    def mock_api_call():
        raise exceptions.TooManyRequests("Too many requests")

    with pytest.raises(exceptions.TooManyRequests):
        mock_api_call()

    mock_sleep.assert_called_with(2)  # Second retry interval

@patch('time.sleep')
def test_retry_api_call_server_error(mock_sleep):
    """Test retry_api_call with ServerError exception."""

    @retry_api_call([1, 2])
    def mock_api_call():
        raise exceptions.ServerError("Server error")

    with pytest.raises(exceptions.ServerError):
        mock_api_call()

    mock_sleep.assert_called_with(2)  # Second retry interval

@patch('time.sleep')
def test_retry_api_call_bad_request(mock_sleep):
    """Test retry_api_call with BadRequest exception."""

    @retry_api_call([1, 2])
    def mock_api_call():
        raise exceptions.BadRequest("Bad request")

    with pytest.raises(exceptions.BadRequest):
        mock_api_call()

    mock_sleep.assert_not_called()  # No retries for BadRequest

def test_handle_api_error_success():
    """Test handle_api_error with a successful API call."""

    @handle_api_error
    def mock_api_call():
        return "success"

    result = mock_api_call()
    assert result == "success"

def test_handle_api_error_google_api_call_error():
    """Test handle_api_error with GoogleAPICallError exception."""

    @handle_api_error
    def mock_api_call():
        raise exceptions.GoogleAPICallError("API error")

    result = mock_api_call()
    assert result is None


def test_handle_api_error_value_error():
    """Test handle_api_error with ValueError exception."""

    @handle_api_error
    def mock_api_call():
        raise ValueError("Value error")

    with pytest.raises(ValueError):
        mock_api_call()

def test_update_kwargs_with_kwargs():
    """Test _update_kwargs with kwargs provided."""
    environment = types.Environment()
    kwargs = {"display_name": "New Display Name", "description": "Updated Description"}
    field_mask = ScrapiBase._update_kwargs(environment, **kwargs)

    assert environment.display_name == "New Display Name"
    assert environment.description == "Updated Description"
    assert field_mask == field_mask_pb2.FieldMask(paths=["display_name", "description"])

def test_update_kwargs_no_kwargs():
    """Test _update_kwargs with no kwargs provided."""
    environment = types.Environment()
    field_mask = ScrapiBase._update_kwargs(environment)

    # Assert that the field mask includes all expected paths for Environment
    expected_paths = [
        "name", "display_name", "description", "version_configs",
        "update_time", "test_cases_config", "webhook_config",
    ]
    assert field_mask == field_mask_pb2.FieldMask(paths=expected_paths)

def test_update_kwargs_experiment():
    """Test _update_kwargs with an Experiment object."""
    experiment = types.Experiment()
    field_mask = ScrapiBase._update_kwargs(experiment)

    # Assert that the field mask includes all expected paths for Experiment
    expected_paths = [
        "name", "display_name", "description", "state", "definition",
        "rollout_config", "rollout_state", "rollout_failure_reason",
        "result", "create_time", "start_time", "end_time",
        "last_update_time", "experiment_length", "variants_history",
    ]
    assert field_mask == field_mask_pb2.FieldMask(paths=expected_paths)

def test_update_kwargs_test_case():
    """Test _update_kwargs with a TestCase object."""
    test_case = types.TestCase()
    field_mask = ScrapiBase._update_kwargs(test_case)

    # Assert that the field mask includes all expected paths for TestCase
    expected_paths = [
        "name", "tags", "display_name", "notes", "test_config",
        "test_case_conversation_turns", "creation_time",
        "last_test_result",
    ]
    assert field_mask == field_mask_pb2.FieldMask(paths=expected_paths)

def test_update_kwargs_version():
    """Test _update_kwargs with a Version object."""
    version = types.Version()
    field_mask = ScrapiBase._update_kwargs(version)

    # Assert that the field mask includes all expected paths for Version
    expected_paths = [
        "name", "display_name", "description", "nlu_settings",
        "create_time", "state",
    ]
    assert field_mask == field_mask_pb2.FieldMask(paths=expected_paths)

def test_update_kwargs_invalid_object():
    """Test _update_kwargs with an invalid object type."""
    with pytest.raises(ValueError) as err:
        ScrapiBase._update_kwargs("invalid_object")

    assert str(err.value) == (
        "`obj` should be one of the following: "
        "[Environment, Experiment, TestCase, Version]."
    )

def test_get_api_calls_details_no_calls(mocked_scrapi_base):
    """Test get_api_calls_details with no API calls made."""
    api_calls_details = mocked_scrapi_base.get_api_calls_details()

    # Assert that the dictionary is empty, as no API calls have been made
    assert api_calls_details == {}

def test_get_api_calls_details_with_calls(mocked_scrapi_base):
    """Test get_api_calls_details with API calls made."""
    @api_call_counter_decorator
    def mock_api_call(self):
        pass

    # Simulate API calls
    mock_api_call(mocked_scrapi_base)  # Call once
    mock_api_call(mocked_scrapi_base)  # Call again

    api_calls_details = mocked_scrapi_base.get_api_calls_details()

    # Assert that the dictionary contains the correct counts
    assert api_calls_details["mock_api_call"] == 2

def test_get_api_calls_count_no_calls(mocked_scrapi_base):
    """Test get_api_calls_count with no API calls made."""
    api_calls_count = mocked_scrapi_base.get_api_calls_count()

    # Assert that the count is 0, as no API calls have been made
    assert api_calls_count == 0

@patch("dfcx_scrapi.core.scrapi_base.default")
def test_get_api_calls_count_with_calls(mocked_scrapi_base):
    """Test get_api_calls_count with API calls made."""
    with patch.object(mocked_scrapi_base, "get_api_calls_count") as mock_count:
        mock_count.return_value = 2

        @api_call_counter_decorator
        def mock_api_call(self):
            pass

        # Simulate API calls
        mock_api_call(mocked_scrapi_base)  # Call once
        mock_api_call(mocked_scrapi_base)  # Call again

        api_calls_count = mocked_scrapi_base.get_api_calls_count()

        # Assert that the count is correct
        assert api_calls_count == 2
