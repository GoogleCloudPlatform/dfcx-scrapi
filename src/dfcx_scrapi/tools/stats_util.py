"""Utiliity functions to provide Agent Stats for a Dialogflow CX agent."""

# Copyright 2021 Google LLC
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

from typing import Dict

from dfcx_scrapi.core.scrapi_base import ScrapiBase
from dfcx_scrapi.core.intents import Intents
from dfcx_scrapi.core.flows import Flows
from dfcx_scrapi.core.pages import Pages
from dfcx_scrapi.core.entity_types import EntityTypes
from dfcx_scrapi.core.transition_route_groups import TransitionRouteGroups

class StatsUtil(ScrapiBase):
    """A util class to provide common stats for a CX Agent."""

    def __init__(
        self,
        creds_path: str = None,
        creds_dict: Dict = None,
        creds=None,
        scope=False,
        agent_id=None,
    ):
        super().__init__(
            creds_path=creds_path,
            creds_dict=creds_dict,
            creds=creds,
            scope=scope,
        )

        self.agent_id = agent_id

        self.intents_tracker = Intents(
            creds=self.creds, agent_id=self.agent_id)
        self.flows_tracker = Flows(
            creds=self.creds, agent_id=self.agent_id)
        self.pages_tracker = Pages(creds=self.creds)
        self.entity_tracker = EntityTypes(
            creds=self.creds, agent_id=self.agent_id)
        self.rg_tracker = TransitionRouteGroups(
            creds=self.creds, agent_id=self.agent_id
        )

    def _get_flows_map(self, agent_id: str = None):
        return self.flows_tracker.get_flows_map(agent_id)

    def _list_all_pages(self, flows):
        """Get a List of all pages from every flow."""
        pages = []
        for flow in flows:
            pages += self.pages_tracker.list_pages(flow)
        return pages

    def _list_all_rgs(self, flows):
        """Get a list of all route groups from every flow."""
        rgs = []
        for flow in flows:
            rgs += self.rg_tracker.list_transition_route_groups(flow)

        return rgs

    def stats(self, agent_id: str = None):
        """snapshot of an agents state"""

        if not agent_id:
            agent_id = self.agent_id

        flows_map = self._get_flows_map(agent_id)

        all_intents = self.intents_tracker.bulk_intent_to_df(agent_id=agent_id)
        all_entity_types = self.entity_tracker.list_entity_types(
            agent_id=agent_id)
        all_pages = self._list_all_pages(flows_map)
        all_rgs = self._list_all_rgs(flows_map)

        info = {
            "Total # of Flows": len(flows_map.keys()),
            "Total # of Pages": len(all_pages),
            "Total # of Intents": all_intents.intent.nunique(),
            "Total # of Training Phrases": all_intents.shape[0],
            "Total # of Entity Types": len(all_entity_types),
            "Total # of Route Groups": len(all_rgs)
        }
        return info
