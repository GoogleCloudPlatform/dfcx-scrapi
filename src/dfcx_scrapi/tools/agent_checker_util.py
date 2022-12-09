"""A set of Utility methods to check DFCX Agents."""

# Copyright 2022 Google LLC
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



# logging config
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)-8s %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)

class AgentCheckerUtil(ScrapiBase):
    """Utility class for checking DFCX Agents."""
    def __init__(
        self,
        creds_path: str = None,
        creds_dict: Dict = None,
        creds = None,
        scope = False,
        agent_id: str = None
    ):
        super().__init__(
            creds_path=creds_path,
            creds_dict=creds_dict,
            creds=creds,
            scope=scope,
        )

        self.agent_id = agent_id

        self.intents = Intents(creds=self.creds, agent_id=self.agent_id)
        self.entities = EntityTypes(creds=self.creds, agent_id=self.agent_id)
        self.flows = Flows(creds=self.creds, agent_id=self.agent_id)
        self.pages = Pages(creds=self.creds)
        self.webhooks = Webhooks(creds=self.creds, agent_id=self.agent_id)
        self.route_groups = TransitionRouteGroups(
            creds=self.creds, agent_id=self.agent_id)

    """
    TODO: Methods to implement:
        x Restore from reference agent
            - Beyond the scope of this class
        x Retrain flows
            - Easy enough to do manually
        - Run test cases and store results, and give a report
            - Eeed to include a reference agent for this to give useful info about new failing test cases
        - Get condensed changelog compared to a reference
            - Ideally include test case changes, to include info that the CX UI can't provide
        - Find unreachable/unused pages, intents, route groups, and possibly routes
            - Finding unreachable routes is hard, but the other problems have already been figured out
        - Find invalid test cases
            - Test cases referencing pages or intents that don't exist, for example
        - Check true routes
            - Pages with only conditional routes, and no intents or parameter filling, should have the last route be "true" to prevent getting stuck on the page
        - Check events
            - Pages with user input should have a no-input-default and no-match-default event handler. 
            - Not sure if this applies to all agents in the same way
        - Check infinite loops
            - Not possible to solve in general because of webhooks, but can find likely candidates
        - Probably other things
    """
