"""Utiliity functions to provide Agent Stats for a Dialogflow CX agent."""

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

from typing import Dict

from dfcx_scrapi.core.scrapi_base import ScrapiBase
from dfcx_scrapi.core.agents import Agents
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

        self._agents_tracker = Agents(
            creds=self.creds, agent_id=self.agent_id)
        self._intents_tracker = Intents(
            creds=self.creds, agent_id=self.agent_id)
        self._flows_tracker = Flows(
            creds=self.creds, agent_id=self.agent_id)
        self._pages_tracker = Pages(creds=self.creds)
        self._entity_tracker = EntityTypes(
            creds=self.creds, agent_id=self.agent_id)
        self._rg_tracker = TransitionRouteGroups(
            creds=self.creds, agent_id=self.agent_id
        )

    def _get_flows_map(self, agent_id: str = None):
        return self._flows_tracker.get_flows_map(agent_id)

    def _list_all_pages(self, flows):
        """Get a List of all pages from every flow."""
        pages = []
        for flow in flows:
            pages += self._pages_tracker.list_pages(flow)
        return pages

    def _list_all_rgs(self, flows):
        """Get a list of all route groups from every flow."""
        rgs = []
        for flow in flows:
            rgs += self._rg_tracker.list_transition_route_groups(flow)

        return rgs

    def get_agent_stats(self, agent_id: str = None, output="stdout"):
        """Provides a snapshot of resource stats from the specified CX Agent

        Pulls all resources from CX Agent and iterates over Flows/Pages to calc
        various design-time stats to be used for offline analysis, determining
        bot complexity, and various other tasks.

        Args:
          agent_id: the CX Agent ID to pull stats from
          output: Optional output format of the stats which can be ONEOF:
            'stdout', 'dict'
        """

        if not agent_id:
            agent_id = self.agent_id

        agent_obj = self._agents_tracker.get_agent(agent_id)

        flows_map = self._get_flows_map(agent_id)

        all_intents = self._intents_tracker.bulk_intent_to_df(
            agent_id=agent_id)
        all_entity_types = self._entity_tracker.list_entity_types(
            agent_id=agent_id)
        all_pages = self._list_all_pages(flows_map)
        all_rgs = self._list_all_rgs(flows_map)

        agent_display_name = agent_obj.display_name
        flows_count = len(flows_map.keys())
        pages_count = len(all_pages)
        intents_count = all_intents.display_name.nunique()
        tp_count = all_intents.shape[0]
        entity_types_count = len(all_entity_types)
        rg_count = len(all_rgs)

        if output == "stdout":
            print(f"Agent ID: {agent_id}")
            print(f"Agent Display Name: {agent_display_name}")
            print(f"Total # of Flows: {flows_count}")
            print(f"Total # of Pages: {pages_count}")
            print(f"Total # of Intents: {intents_count}")
            print(f"Total # of Training Phrases: {tp_count}")
            print(f"Total # of Entity Types: {entity_types_count}")
            print(f"Total # of Route Groups: {rg_count}")

        if output == "dict":
            stats = {
                "agent_id": agent_id,
                "display_name": agent_display_name,
                "flows": flows_count,
                "pages": pages_count,
                "intents": intents_count,
                "training_phrases": tp_count,
                "entity_types": entity_types_count,
                "route_groups": rg_count
            }

            return stats

        return None
