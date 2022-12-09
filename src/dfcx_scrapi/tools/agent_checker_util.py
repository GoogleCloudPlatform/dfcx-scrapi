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
        - Restore from reference agent
        - Retrain flows
        - Run test cases and store results, and give a report
        - Get condensed changelog
        - Find unreachable/unused pages, intents, route groups, and possibly routes
        - Find invalid test cases
        - Check true routes
        - Check events
        - Check infinite loops
        - Probably other things
    """
