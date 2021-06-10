"""
Copyright 2021 Google LLC

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""
'''
Wrapper around all the subclasses so that you can use a single 
MegaAgent instance to walk through an agent and all its components
manages creds and agent ids in one place
'''

import logging
from typing import Dict

from dfcx_sapi.core.sapi_base import SapiBase
from dfcx_sapi.core.intents import Intents
from dfcx_sapi.core.flows import Flows
from dfcx_sapi.core.pages import Pages

class MegaAgent(SapiBase):
    def __init__(self, creds_path: str = None,
                creds_dict: Dict = None,
                creds=None,
                scope=False,
                agent_path=None):
        super().__init__(creds_path=creds_path,
                         creds_dict=creds_dict,
                         creds=creds,
                         scope=scope)

        self.intents_tracker = Intents(creds=self.creds)
        self.flows_tracker = Flows(creds=self.creds)
        self.pages_tracker = Pages(creds=self.creds)
        # TODO - tracker for phrases per intent

        if agent_path:
            self.agent_path = agent_path

    def list_intents(self):
        '''list intents for instantiated agent'''
        items = self.intents_tracker.list_intents(self.agent_path)
        logging.info('list intents: %s', len(items))
        return items

    def list_flows(self):
        '''list flows for instantiated agent'''
        items = self.flows_tracker.list_flows(self.agent_path)
        logging.info('list flows: %s', len(items))
        return items

    def list_pages(self, flow_id=None):
        '''list pages for instantiated agent'''
        items = self.pages_tracker.list_pages(flow_id)
        logging.info('list pages for flow %s: %s', flow_id, len(items))
        return items

    def all_pages(self):
        '''all pages for every flow'''
        flows = self.flows_tracker.list_flows()
        pages = []
        for flow in flows:
            pages += self.pages_tracker.list_pages(flow.name)
        return pages

    def stats(self):
        '''snapshot of an agents state'''
        info = {
            # 'phrases': self.count_phrases(),
            'flows': len(self.flows_tracker.list_flows()),
            'intents': len(self.intents_tracker.list_intents(self.agent_path)),
            'pages': len(self.all_pages() )
        }
        return info

