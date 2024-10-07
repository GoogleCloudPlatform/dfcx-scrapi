"""Test Class for Test Cases in SCRAPI."""

# pylint: disable=redefined-outer-name
# pylint: disable=protected-access

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
import pandas as pd
from unittest.mock import patch, MagicMock
from dfcx_scrapi.core.test_cases import TestCases as PyTestCases
from google.cloud.dialogflowcx_v3beta1 import types
from google.cloud.dialogflowcx_v3beta1.services import test_cases


@pytest.fixture
def test_config():
    project_id = "my-project-id-1234"
    location_id = "global"
    parent = f"projects/{project_id}/locations/{location_id}"
    agent_id = f"{parent}/agents/my-agent-1234"
    flow_id = f"{agent_id}/flows/00000000-0000-0000-0000-000000000000"
    page_id = f"{flow_id}/pages/mock-page-1234"
    other_flow_id = f"{agent_id}/flows/other1234"
    other_page_id = f"{other_flow_id}/pages/other1234"
    test_case_id = f"{agent_id}/testCases/1234"
    test_case_result_id = f"{test_case_id}/results/9876"
    intent_id = f"{agent_id}/intents/12345678"
    flows_map = {flow_id: "MOCK FLOW"}
    pages_map = {
        flow_id: {page_id: "MOCK PAGE"},
        other_flow_id: {other_page_id: "OTHER PAGE"},
    }

    return {
        "project_id": project_id,
        "agent_id": agent_id,
        "flow_id": flow_id,
        "page_id": page_id,
        "other_flow_id": other_flow_id,
        "other_page_id": other_page_id,
        "test_case_id": test_case_id,
        "test_case_result_id": test_case_result_id,
        "intent_id": intent_id,
        "flows_map": flows_map,
        "pages_map": pages_map,
    }


@pytest.fixture
def mock_tc_obj_turns(test_config):
    return types.TestCase(
        name=test_config["test_case_id"],
        tags=["#required", "#testing"],
        display_name="mock test case object",
        notes="This is a note for the mock test case",
        test_config=types.TestConfig(flow=test_config["flow_id"]),
        test_case_conversation_turns=[
            types.ConversationTurn(
                user_input=types.ConversationTurn.UserInput(
                    input=types.QueryInput(
                        text=types.TextInput(text="Hello"), language_code="en"
                    ),
                    injected_parameters={"my_key": "my_value"},
                    is_webhook_enabled=False,
                    enable_sentiment_analysis=False,
                )
            ),
            types.ConversationTurn(
                virtual_agent_output=types.ConversationTurn.VirtualAgentOutput(
                    triggered_intent=types.Intent(
                        name=test_config["intent_id"]
                    ),
                    text_responses=[
                        types.ResponseMessage.Text(
                            text=["Hi, how can I help you today?"]
                        )
                    ],
                )
            ),
        ],
        last_test_result=types.TestCaseResult(
            name=test_config["test_case_result_id"],
            test_result=types.TestResult(value=0),
        ),
    )


@pytest.fixture
def mock_tc_obj_no_turns(test_config):
    return types.TestCase(
        name=test_config["test_case_id"],
        tags=["#required", "#testing"],
        display_name="mock test case object",
        notes="This is a note for the mock test case",
        test_config=types.TestConfig(flow=test_config["flow_id"]),
        last_test_result=types.TestCaseResult(
            name=test_config["test_case_result_id"],
            test_result=types.TestResult(value=0),
        ),
    )


@pytest.fixture
def mock_tc_df(test_config):
    data = {
        "display_name": ["Mock Test 1", "Mock Test 2", "Mock Test 3"],
        "id": [
            f"{test_config['agent_id']}/testCases/12345",
            f"{test_config['agent_id']}/testCases/54321",
            f"{test_config['agent_id']}/testCases/67890",
        ],
        "short_id": ["12345", "54321", "67890"],
        "tags": [["tag1", "tag2"], ["tag3", "tag4"], ["tag5", "tag6"]],
        "creation_time": ["2023-01-01", "2023-01-02", "2023-01-03"],
        "start_flow": ["Mock Flow", "Mock Flow", "Default Start Flow"],
        "start_page": ["Mock Page", "Mock Page", "START_PAGE"],
        "passed": [True, False, True],
        "test_time": ["10:00", "11:00", "12:00"],
    }

    return pd.DataFrame(data)


@pytest.fixture
def mock_updated_tc_obj(mock_tc_obj_turns):
    mock_tc_obj_turns.display_name = "mock test case object updated"

    return mock_tc_obj_turns


@pytest.fixture
def mock_list_tc_pager(mock_tc_obj_turns):
    return test_cases.pagers.ListTestCasesPager(
        test_cases.TestCasesClient.list_test_cases,
        types.test_case.ListTestCasesRequest(),
        types.test_case.ListTestCasesResponse(test_cases=[mock_tc_obj_turns]),
    )


@pytest.fixture
def mock_list_tc_pager_no_turns(mock_tc_obj_no_turns):
    return test_cases.pagers.ListTestCasesPager(
        test_cases.TestCasesClient.list_test_cases,
        types.test_case.ListTestCasesRequest(),
        types.test_case.ListTestCasesResponse(
            test_cases=[mock_tc_obj_no_turns]
        ),
    )

@pytest.fixture(autouse=True)
def mock_client(test_config):
    """Fixture to create a mocked TestCasesClient."""
    with patch("dfcx_scrapi.core.scrapi_base.default") as mock_default, \
        patch("dfcx_scrapi.core.scrapi_base.Request") as mock_request, \
        patch("dfcx_scrapi.core.test_cases.services.test_cases.TestCasesClient") as mock_client:

        mock_creds = MagicMock()
        mock_default.return_value = (mock_creds, test_config["project_id"])
        mock_request.return_value = MagicMock()

        yield mock_client

def test_convert_test_result_to_string(mock_tc_obj_turns):
    tests = [(0, "TEST_RESULT_UNSPECIFIED"), (1, "PASSED"), (2, "FAILED")]
    tc = PyTestCases()

    for int_value, str_value in tests:
        mock_tc_obj_turns.last_test_result.test_result = types.TestResult(
            value=int_value
        )
        res = tc._convert_test_result_to_string(mock_tc_obj_turns)
        assert res == str_value
        assert isinstance(res, str)


def test_convert_test_result_to_bool(mock_tc_obj_turns):
    tests = [(0, None), (1, True), (2, False)]
    tc = PyTestCases()
    for int_value, res_value in tests:
        if int_value in [1, 2]:
            mock_tc_obj_turns.last_test_result.test_result = types.TestResult(
                value=int_value
            )
            res = tc._convert_test_result_to_bool(mock_tc_obj_turns)
            assert res == res_value
            assert isinstance(res_value, bool)
        else:
            mock_tc_obj_turns.last_test_result.test_result = types.TestResult(
                value=int_value
            )
            res = tc._convert_test_result_to_bool(mock_tc_obj_turns)
            assert res == res_value
            assert res_value is None


def test_get_flow_id_from_test_config(mock_tc_obj_turns, test_config):
    tests = [
        ("flow", test_config["flow_id"]),
        ("page", test_config["page_id"]),
        (None, ""),
    ]
    tc = PyTestCases()
    for str_value, test_case_id in tests:
        if str_value == "flow":
            mock_tc_obj_turns.test_config.flow = test_case_id
        elif str_value == "page":
            mock_tc_obj_turns.test_config.page = test_case_id
        else:
            mock_tc_obj_turns.test_config = types.TestConfig()

        res = tc._get_flow_id_from_test_config(mock_tc_obj_turns)
        assert isinstance(res, str)
        assert res == test_config["flow_id"]


def test_get_page_id_from_test_config(mock_tc_obj_turns, test_config):
    tests = [
        ("page", test_config["page_id"]),
        ("start_page", f"{test_config['flow_id']}/pages/START_PAGE"),
    ]
    tc = PyTestCases()
    for str_value, page_id in tests:
        if str_value == "page":
            mock_tc_obj_turns.test_config.page = page_id
            res = tc._get_page_id_from_test_config(
                mock_tc_obj_turns, test_config["flow_id"]
            )
            assert isinstance(str_value, str)
            assert res == page_id

        elif str_value == "start_page":
            mock_tc_obj_turns.test_config = types.TestConfig()
            res = tc._get_page_id_from_test_config(
                mock_tc_obj_turns, test_config["flow_id"]
            )
            assert isinstance(str_value, str)
            assert res == page_id


def test_get_page_display_name_flow_exists(test_config):
    tc = PyTestCases()

    res = tc._get_page_display_name(
        test_config["flow_id"], test_config["page_id"], test_config["pages_map"]
    )
    assert isinstance(res, str)
    assert res == "MOCK PAGE"


def test_get_page_display_name_flow_exists_no_page_map(test_config):
    tc = PyTestCases()

    res = tc._get_page_display_name(
        test_config["other_flow_id"], None, test_config["pages_map"]
    )
    assert res is None


def test_get_page_display_name_flow_does_not_exist(test_config):
    tc = PyTestCases()

    res = tc._get_page_display_name(
        f"{test_config['agent_id']}/flows/doesnt-exist-1234",
        None,
        test_config["pages_map"],
    )
    assert isinstance(res, str)
    assert res == "START_PAGE"


def test_process_test_case(mock_tc_obj_turns, test_config):
    cols = [
        "display_name",
        "id",
        "short_id",
        "tags",
        "creation_time",
        "start_flow",
        "start_page",
        "passed",
        "test_time",
    ]
    tc = PyTestCases()

    res = tc._process_test_case(
        mock_tc_obj_turns, test_config["flows_map"], test_config["pages_map"]
    )
    assert isinstance(res, pd.DataFrame)
    assert set(res.columns.to_list()) == set(cols)


@patch("dfcx_scrapi.core.test_cases.TestCases.batch_run_test_cases")
def test_retest_cases(mock_batch_run, mock_tc_df):
    cols = [
        "display_name",
        "id",
        "short_id",
        "tags",
        "creation_time",
        "start_flow",
        "start_page",
        "passed",
        "test_time",
    ]

    mock_batch_run.return_value.batch_run_test_cases.return_value = mock_tc_df

    retest_ids = mock_tc_df.id.to_list()[:1]
    tc = PyTestCases()
    res = tc._retest_cases(mock_tc_df, retest_ids)
    assert isinstance(res, pd.DataFrame)
    assert set(res.columns.to_list()) == set(cols)


# List Test Cases
def test_list_test_cases_agent_id_not_in_instance(
        mock_client, mock_tc_obj_turns):
    mock_client.return_value.list_test_cases.return_value = [mock_tc_obj_turns]

    tc = PyTestCases()

    with pytest.raises(AttributeError):
        _ = tc.list_test_cases()


def test_list_test_cases_agent_id_in_instance(
    mock_client, mock_list_tc_pager, test_config
):
    mock_client.return_value.list_test_cases.return_value = mock_list_tc_pager

    tc = PyTestCases(agent_id=test_config["agent_id"])
    res = tc.list_test_cases()

    assert isinstance(res, list)
    assert isinstance(res[0], types.TestCase)


def test_list_test_cases_agent_id_in_method(
    mock_client, mock_list_tc_pager_no_turns, test_config
):
    mock_client.return_value.list_test_cases.return_value = (
        mock_list_tc_pager_no_turns
    )

    tc = PyTestCases()
    res = tc.list_test_cases(test_config["agent_id"])

    assert isinstance(res, list)
    assert isinstance(res[0], types.TestCase)
    assert res[0].test_case_conversation_turns == ""


def test_list_test_cases_include_conversation_turns(
    mock_client, mock_list_tc_pager, test_config
):
    mock_client.return_value.list_test_cases.return_value = mock_list_tc_pager

    tc = PyTestCases()
    res = tc.list_test_cases(
        test_config["agent_id"], include_conversation_turns=True
    )

    assert isinstance(res, list)
    assert isinstance(res[0], types.TestCase)
    assert res[0].test_case_conversation_turns != ""

def test_update_test_case_no_args(mock_client, mock_tc_obj_turns):
    mock_client.return_value.update_test_case.return_value = mock_tc_obj_turns

    tc = PyTestCases()

    # Assertions
    with pytest.raises(ValueError):
        _ = tc.update_test_case()

def test_update_test_case_kwargs_only(mock_client, mock_tc_obj_turns):
    mock_client.return_value.update_test_case.return_value = mock_tc_obj_turns

    tc = PyTestCases()

    # Assertions
    with pytest.raises(ValueError):
        _ = tc.update_test_case(display_name="mock test case object update")

def test_update_test_case_id_only(mock_client, test_config, mock_tc_obj_turns):

    mock_client.return_value.update_test_case.return_value = mock_tc_obj_turns

    tc = PyTestCases()

    # Assertions
    with pytest.raises(ValueError):
        _ = tc.update_test_case(test_case_id=test_config["test_case_id"])

def test_update_test_case_obj_only(mock_client, mock_tc_obj_turns):
    mock_client.return_value.update_test_case.return_value = mock_tc_obj_turns

    tc = PyTestCases()
    result = tc.update_test_case(obj=mock_tc_obj_turns)

    # Assertions
    assert result.display_name == "mock test case object"
    assert result == mock_tc_obj_turns

def test_update_test_case_obj_only_empty_name(mock_client, mock_tc_obj_turns):
    mock_tc_obj_turns.name = ""

    mock_client.return_value.update_test_case.return_value = mock_tc_obj_turns

    tc = PyTestCases()

    # Assertions
    with pytest.raises(ValueError):
        _ = tc.update_test_case(obj=mock_tc_obj_turns)

def test_update_test_case_with_obj_and_kwargs(
    mock_client, mock_tc_obj_turns, mock_updated_tc_obj
):

    mock_client.return_value.update_test_case.return_value = mock_updated_tc_obj

    tc = PyTestCases()
    result = tc.update_test_case(
        obj=mock_tc_obj_turns, display_name="mock test case object updated"
    )

    # Assertions
    assert result.display_name == mock_updated_tc_obj.display_name
    assert result == mock_updated_tc_obj

def test_update_test_case_with_id_and_kwargs(
    mock_client, test_config, mock_tc_obj_turns
):

    tc = PyTestCases()

    mock_client.return_value.get_test_case.return_value = mock_tc_obj_turns
    mock_client.return_value.update_test_case.return_value = mock_tc_obj_turns

    result = tc.update_test_case(
        test_case_id=test_config["test_case_id"],
        display_name="mock test case object update",
    )

    # Assertions
    assert result.display_name == "mock test case object update"

def test_update_test_case_with_obj_id_and_kwargs(
    mock_client, test_config, mock_tc_obj_turns
):
    """For this case, kwargs should be ignored in favor of the obj."""

    tc = PyTestCases()

    mock_client.return_value.get_test_case.return_value = mock_tc_obj_turns
    mock_client.return_value.update_test_case.return_value = mock_tc_obj_turns

    result = tc.update_test_case(
        test_case_id=test_config["test_case_id"],
        obj=mock_tc_obj_turns,
        display_name="mock test case object update",
    )

    # Assertions
    assert result.display_name == "mock test case object"
    assert result == mock_tc_obj_turns
