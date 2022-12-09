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
        self.test_cases = TestCases(creds=self.creds, agent_id=self.agent_id)

        # Generate maps
        self.intents_map = self.intents.get_intents_map(self.agent_id)
        self.flows_map = self.flows.get_flows_map(self.agent_id)
        self.pages_map = {}
        for flow_id in self.flows_map.keys():
            self.pages_map[flow_id] = self.pages.get_pages_map(flow_id)
        self.route_groups_map = {}
        for flow_id in self.flows_map.keys():
            self.route_groups_map[flow_id] = self.route_groups.get_route_groups_map(flow_id)

    def convert_intent(self, intent_id, agent_id, intents_map):
        intent_id_converted = str(agent_id) + '/intents/' + str(intent_id)
        if intent_id_converted in intents_map.keys():
            return intents_map[intent_id_converted]
        return ''

    def convert_flow(self, flow_id, agent_id, flows_map):
        if flow_id.split('/')[-1] == '-':
            return ''
        #flow_id_converted = str(agent_id) + '/flows/' + str(flow_id)
        if flow_id in flows_map.keys():
            return flows_map[flow_id]
        # TODO: Should throw error instead of returning default
        return 'Default Start Flow'

    # Note that flow id includes agent, normally...
    def convert_page(self, page_id, flow_id, pages_map):
        if page_id == 'END_SESSION':
            return 'End Session'
        elif page_id == 'END_FLOW':
            return 'End Flow'
        elif page_id == 'START_PAGE':
            return 'Start'
        page_id_converted = str(flow_id) + '/pages/' + str(page_id)
        if flow_id in pages_map.keys():
            if page_id_converted in pages_map[flow_id].keys():
                return pages_map[flow_id][page_id_converted]
            else:
                # TODO: Should throw error instead of returning default
                return 'Start'
        print('Flow not found')
        # TODO: Should throw error, but returning this probably will anyway
        return 'Invalid'
    
    def get_test_case_results(self, retest_all=False):
        test_case_results = dfcx_tc.list_test_cases(self.agent_id)
        retest = []
        retest_names = []

        display_names = []
        ids = []
        short_ids = []
        tags = []
        creation_times = []
        flows = []
        pages = []
        test_results = []
        test_times = []
        passed = []

        for response in test_case_results:
            # Collect untested cases to be retested (or all if retest_all is True)
            if retest_all or str(response.last_test_result.test_result) == 'TestResult.TEST_RESULT_UNSPECIFIED':
                retest.append(response.name)
                retest_names.append(response.display_name)
                # Collect additional information for dataframe
            display_names.append(response.display_name)
            ids.append(response.name)
            short_ids.append(response.name.split('/')[-1])
            tags.append(','.join(response.tags))
            creation_times.append(response.creation_time)
            flows.append(convert_flow(response.test_config.flow, self.agent_id, self.flows_map))
            pages.append(convert_page(response.test_config.page, response.test_config.flow, self.pages_map))
            test_results.append(str(response.last_test_result.test_result))
            test_times.append(response.last_test_result.test_time)
            passed.append(str(response.last_test_result.test_result) == 'TestResult.PASSED')

        # Create dataframe
        test_case_df = pd.DataFrame({
            'display_name': display_names, 
            'id': ids, 
            'short_id': short_ids, 
            'tags': tags, 
            'creation_time': creation_times, 
            'start_flow': flows, 
            'start_page': pages,
            'test_result': test_results, 
            'passed': passed, 
            'test_time': test_times})

        # Retest any that haven't been run yet
        print('To retest:', len(retest))
        if len(retest) > 0:
            response = self.test_cases.batch_run_test_cases(retest, self.agent_id)
            for result in response.results:
                # Results may not be in the same order as they went in (oh well)
                # Process the name a bit to remove the /results/id part at the end.
                testCaseId_full = '/'.join(result.name.split('/')[:-2])
                index = retest.index(testCaseId_full)
                testCaseId = testCaseId_full.split('/')[-1]

                # Update dataframe where id = testcaseId_full
                #row = test_case_df.loc[test_case_df['id'] == testCaseId_full]
                test_case_df.loc[test_case_df['id'] == testCaseId_full, 'short_id'] = testCaseId
                test_case_df.loc[test_case_df['id'] == testCaseId_full, 'test_result'] = str(result.test_result)
                test_case_df.loc[test_case_df['id'] == testCaseId_full, 'test_time'] = result.test_time
                test_case_df.loc[test_case_df['id'] == testCaseId_full, 'passed'] = str(result.test_result) == 'TestResult.PASSED'

        # This column is redundant, since we have passed (bool)
        test_case_df = test_case_df.drop(columns=['test_result'])
        return test_case_df
    
    """
    TODO: Methods to implement:
        - Run test cases and store results, and give a report
            - Need to include a reference agent for this to give useful info about new failing test cases
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
