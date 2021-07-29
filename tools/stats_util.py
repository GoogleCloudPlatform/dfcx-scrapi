"""Utiliity functions to provide Agent Stats for a Dialogflow CX agent."""
# Copyright 2021 Google LLC. This software is provided as-is, without warranty
# or representation for any use or purpose. Your use of it is subject to your
# agreement with Google.

from typing import Dict

from dfcx_scrapi.core.scrapi_base import ScrapiBase
from dfcx_scrapi.core.intents import Intents
from dfcx_scrapi.core.flows import Flows
from dfcx_scrapi.core.pages import Pages


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

        self.intents_tracker = Intents(creds=self.creds)
        self.flows_tracker = Flows(creds=self.creds)
        self.pages_tracker = Pages(creds=self.creds)

        if agent_id:
            self.agent_id = agent_id

    def list_all_pages(self):
        """Get a List of all pages from every flow."""
        flows = self.flows_tracker.list_flows()
        pages = []
        for flow in flows:
            pages += self.pages_tracker.list_pages(flow.name)
        return pages

    def stats(self, agent_id: str = None):
        """snapshot of an agents state"""

        if not agent_id:
            agent_id = self.agent_id

        all_intents = self.intents_tracker.bulk_intent_to_df(agent_id=agent_id)
        flows_map = self.flows_tracker.get_flows_map(agent_id)
        info = {
            "Total # of Flows": len(flows_map.keys()),
            "Total # of Intents": all_intents.intent.nunique(),
            "Total # of Training Phrases": all_intents.shape[0],
            "Total # of Pages": len(self.list_all_pages()),
        }
        return info
