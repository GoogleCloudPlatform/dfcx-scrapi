'''
Wrapper around all the subclasses so that you can use a single 
MegaAgent instance to walk through an agent and all its components
manages creds and agent ids in one place
'''

import logging

from .sapi_base import SapiBase
from .intents import Intents
from .flows import Flows
from .pages import Pages

class MegaAgent(SapiBase):
    '''Common base class for different SAPI objects'''

    def __init__(self, creds_path=None, agent_path=None, _language_code="en"):
        super().__init__(creds_path=creds_path, agent_path=agent_path)
        self.intents_tracker = Intents(creds_path=self.creds_path)
        self.flows_tracker = Flows(creds_path=self.creds_path)
        self.pages_tracker = Pages(creds_path=self.creds_path)
        # TODO - tracker for phrases per intent

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
        flows = self.list_flows()
        pages = []
        for flow in flows:
            pages += self.list_pages(flow.name)
        return pages

    # def count_phrases(self):
    #     '''just count the phrases for stats'''
    #     intents = self.list_intents()
    #     df = self.intents_tracker.intents_to_dataframe(intents)
    #     logging.info('intents[0] %s', intents[0])
    #     logging.info('len(intents) %s', len(intents))
    #     return len(intents)

    def stats(self):
        '''snapshot of an agents state'''
        info = {
            # 'phrases': self.count_phrases(),
            'flows': len(self.list_flows()),
            'intents': len(self.list_intents()),
            'pages': len(self.all_pages() )
        }
        return info

