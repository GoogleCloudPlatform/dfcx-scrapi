"""Test Class for SearchUtil Methods in SCRAPI."""

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

from unittest.mock import MagicMock

import pytest
from google.cloud.dialogflowcx_v3beta1 import types

from dfcx_scrapi.tools.search_util import SearchUtil


def _text_fulfillment(text: str) -> types.Fulfillment:
    return types.Fulfillment(
        messages=[
            types.ResponseMessage(
                text=types.ResponseMessage.Text(text=[text])
            )
        ]
    )


def _conditional_fulfillment(condition: str, text: str) -> types.Fulfillment:
    return types.Fulfillment(
        conditional_cases=[
            types.Fulfillment.ConditionalCases(
                cases=[
                    types.Fulfillment.ConditionalCases.Case(
                        condition=condition,
                        case_content=[
                            types.Fulfillment.ConditionalCases.Case.CaseContent(
                                message=types.ResponseMessage(
                                    text=types.ResponseMessage.Text(text=[text])
                                )
                            )
                        ],
                    )
                ]
            )
        ]
    )


@pytest.fixture
def search_util():
    """Create a SearchUtil instance with mocked CX core clients."""
    agent_id = "projects/p/locations/l/agents/a"
    flow_id = f"{agent_id}/flows/00000000-0000-0000-0000-000000000000"
    intent_id = f"{agent_id}/intents/1111"

    flow = types.Flow(
        name=flow_id,
        display_name="Default Start Flow",
        transition_routes=[
            types.TransitionRoute(
                intent=intent_id,
                trigger_fulfillment=_text_fulfillment("Route hello"),
            )
        ],
        event_handlers=[
            types.EventHandler(
                event="sys.no-match-default",
                trigger_fulfillment=_text_fulfillment("No match"),
            )
        ],
    )

    page_entry_text = types.Page(
        name=f"{flow_id}/pages/page-1",
        display_name="Greeting Page",
        entry_fulfillment=_text_fulfillment("Welcome to Greeting Page"),
        form=types.Form(
            parameters=[
                types.Form.Parameter(
                    display_name="account_id",
                    fill_behavior=types.Form.Parameter.FillBehavior(
                        initial_prompt_fulfillment=_text_fulfillment(
                            "What is your account ID?"
                        )
                    ),
                )
            ]
        ),
    )

    page_conditional_only = types.Page(
        name=f"{flow_id}/pages/page-2",
        display_name="Conditional Page",
        entry_fulfillment=_conditional_fulfillment(
            "$session.params.vip = true", "Welcome VIP"
        ),
    )

    page_text_and_conditional = types.Page(
        name=f"{flow_id}/pages/page-3",
        display_name="Hybrid Page",
        entry_fulfillment=types.Fulfillment(
            messages=[
                types.ResponseMessage(
                    text=types.ResponseMessage.Text(text=["Base greeting"])
                )
            ],
            conditional_cases=_conditional_fulfillment(
                "$session.params.vip = true", "VIP addendum"
            ).conditional_cases,
        ),
    )

    util = object.__new__(SearchUtil)
    util.flows = MagicMock()
    util.flows.list_flows.return_value = [flow]
    util.pages = MagicMock()
    util.pages.list_pages = lambda _flow_id: [
        page_entry_text,
        page_conditional_only,
        page_text_and_conditional,
    ]
    util.route_groups = MagicMock()
    util.route_groups.list_transition_route_groups.return_value = []
    util.intents = MagicMock()
    util.intents.get_intents_map.return_value = {intent_id: "welcome.intent"}
    return util, agent_id


def test_get_agent_fulfillment_message_df_fulfillment_types(search_util):
    """Verify fulfillment_type identifies entry, event, route, and prompts."""
    util, agent_id = search_util
    df = util.get_agent_fulfillment_message_df(agent_id, message_format="dict")

    expected_cols = [
        "flow_name",
        "page_name",
        "parameter_name",
        "event",
        "route_group_name",
        "intent",
        "condition",
        "fulfillment_type",
        "response_type",
        "response_message",
        "conditional_cases",
    ]
    assert list(df.columns) == expected_cols

    entry_row = df[df["page_name"] == "Greeting Page"].loc[
        lambda d: d["fulfillment_type"] == "entry_fulfillment"
    ]
    assert len(entry_row) == 1
    assert entry_row.iloc[0]["response_type"] == "text"
    assert entry_row.iloc[0]["response_message"] == {
        "text": "Welcome to Greeting Page"
    }

    prompt_row = df[df["parameter_name"] == "account_id"]
    assert len(prompt_row) == 1
    assert (
        prompt_row.iloc[0]["fulfillment_type"] == "initial_prompt_fulfillment"
    )

    route_row = df[df["intent"] == "welcome.intent"]
    assert len(route_row) == 1
    assert route_row.iloc[0]["fulfillment_type"] == "route"

    event_row = df[df["event"] == "sys.no-match-default"]
    assert len(event_row) == 1
    assert event_row.iloc[0]["fulfillment_type"] == "event_handler"


@pytest.mark.parametrize("message_format", ["proto", "dict", "human-readable"])
def test_get_agent_fulfillment_message_df_conditional_response_type(
    search_util, message_format
):
    """Verify conditional-only fulfillments set conditional_response type."""
    util, agent_id = search_util
    df = util.get_agent_fulfillment_message_df(
        agent_id, message_format=message_format
    )

    cond_row = df[df["page_name"] == "Conditional Page"]
    assert len(cond_row) == 1
    assert cond_row.iloc[0]["fulfillment_type"] == "entry_fulfillment"
    assert cond_row.iloc[0]["response_type"] == "conditional_response"

    hybrid_row = df[df["page_name"] == "Hybrid Page"]
    assert len(hybrid_row) == 1
    assert hybrid_row.iloc[0]["fulfillment_type"] == "entry_fulfillment"
    assert hybrid_row.iloc[0]["response_type"] == "text"


def test_get_agent_fulfillment_message_df_invalid_format(search_util):
    """Verify invalid message_format raises ValueError."""
    util, agent_id = search_util
    with pytest.raises(ValueError, match="Arg message_format must be"):
        util.get_agent_fulfillment_message_df(agent_id, message_format="xml")
