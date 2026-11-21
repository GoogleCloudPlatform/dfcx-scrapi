"""Test Class for NLU Util Methods in SCRAPI."""

# pylint: disable=redefined-outer-name

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

import importlib
import sys
from unittest.mock import MagicMock

import pytest
from google.cloud.dialogflowcx_v3beta1 import types


@pytest.fixture
def nlu_util_module(monkeypatch):
    """Import nlu_util with optional heavy ML deps stubbed out."""
    if "scann" not in sys.modules:
        monkeypatch.setitem(sys.modules, "scann", MagicMock())
    if "tensorflow_hub" not in sys.modules:
        monkeypatch.setitem(sys.modules, "tensorflow_hub", MagicMock())
    return importlib.import_module("dfcx_scrapi.tools.nlu_util")


def _make_mock_util(nlu_util_module):
    util = object.__new__(nlu_util_module.NaturalLanguageUnderstandingUtil)
    util.creds = MagicMock()
    return util


def _patch_cx_loaders(
    monkeypatch, nlu_util_module, flow_obj, page_map, page_obj, all_intents
):
    mock_flows = MagicMock()
    mock_flows.get_flow_by_display_name.return_value = flow_obj
    monkeypatch.setattr(
        nlu_util_module.flows, "Flows", MagicMock(return_value=mock_flows)
    )

    mock_trgs = MagicMock()
    mock_trgs.list_transition_route_groups.return_value = []
    monkeypatch.setattr(
        nlu_util_module.transition_route_groups,
        "TransitionRouteGroups",
        MagicMock(return_value=mock_trgs),
    )

    mock_pages = MagicMock()
    mock_pages.get_pages_map.return_value = page_map
    mock_pages.get_page.return_value = page_obj
    monkeypatch.setattr(
        nlu_util_module.pages, "Pages", MagicMock(return_value=mock_pages)
    )

    mock_intents = MagicMock()
    mock_intents.list_intents.return_value = all_intents
    monkeypatch.setattr(
        nlu_util_module.intents, "Intents", MagicMock(return_value=mock_intents)
    )
    return mock_pages


@pytest.mark.parametrize("start_page_name", ["START_PAGE", "Start Page"])
def test_load_data_start_page_skips_get_page(
    monkeypatch, nlu_util_module, start_page_name
):
    """Verify START_PAGE and Start Page skip page lookup and use flow routes."""
    agent_id = "projects/p/locations/l/agents/a"
    flow_id = f"{agent_id}/flows/00000000-0000-0000-0000-000000000000"
    intent_id = f"{agent_id}/intents/1"

    flow_obj = types.Flow(
        name=flow_id,
        display_name="Default Start Flow",
        transition_routes=[types.TransitionRoute(intent=intent_id)],
    )
    intent_obj = types.Intent(name=intent_id, display_name="welcome")
    page_map = {"START_PAGE": f"{flow_id}/pages/START_PAGE"}

    mock_pages = _patch_cx_loaders(
        monkeypatch, nlu_util_module, flow_obj, page_map, None, [intent_obj]
    )

    util = _make_mock_util(nlu_util_module)
    util._load_data(agent_id, "Default Start Flow", start_page_name)

    mock_pages.get_pages_map.assert_not_called()
    mock_pages.get_page.assert_not_called()
    assert not hasattr(util, "page")
    assert [i.name for i in util.intents] == [intent_id]


def test_load_data_regular_page_fetches_page(monkeypatch, nlu_util_module):
    """Verify non-start pages are resolved via get_pages_map and get_page."""
    agent_id = "projects/p/locations/l/agents/a"
    flow_id = f"{agent_id}/flows/00000000-0000-0000-0000-000000000000"
    page_id = f"{flow_id}/pages/1234"
    flow_intent_id = f"{agent_id}/intents/1"
    page_intent_id = f"{agent_id}/intents/2"

    flow_obj = types.Flow(
        name=flow_id,
        display_name="Default Start Flow",
        transition_routes=[types.TransitionRoute(intent=flow_intent_id)],
    )
    page_obj = types.Page(
        name=page_id,
        display_name="Billing",
        transition_routes=[types.TransitionRoute(intent=page_intent_id)],
    )
    all_intents = [
        types.Intent(name=flow_intent_id, display_name="welcome"),
        types.Intent(name=page_intent_id, display_name="pay_bill"),
    ]
    page_map = {
        "START_PAGE": f"{flow_id}/pages/START_PAGE",
        "Billing": page_id,
    }

    mock_pages = _patch_cx_loaders(
        monkeypatch, nlu_util_module, flow_obj, page_map, page_obj, all_intents
    )

    util = _make_mock_util(nlu_util_module)
    util._load_data(agent_id, "Default Start Flow", "Billing")

    mock_pages.get_pages_map.assert_called_once_with(flow_id, reverse=True)
    mock_pages.get_page.assert_called_once_with(page_id)
    assert util.page == page_obj
    assert {i.name for i in util.intents} == {flow_intent_id, page_intent_id}


def test_load_data_unknown_page_raises_value_error(
    monkeypatch, nlu_util_module
):
    """Verify requesting a missing page raises ValueError."""
    agent_id = "projects/p/locations/l/agents/a"
    flow_id = f"{agent_id}/flows/00000000-0000-0000-0000-000000000000"
    flow_obj = types.Flow(name=flow_id, display_name="Default Start Flow")

    _patch_cx_loaders(
        monkeypatch,
        nlu_util_module,
        flow_obj,
        {"START_PAGE": f"{flow_id}/pages/START_PAGE"},
        None,
        [],
    )

    util = _make_mock_util(nlu_util_module)
    with pytest.raises(ValueError, match='Page "Missing Page" does not exist'):
        util._load_data(agent_id, "Default Start Flow", "Missing Page")
