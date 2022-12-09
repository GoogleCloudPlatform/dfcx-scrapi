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

from __future__ import annotations

import logging
from typing import Dict, List, Optional
import pandas as pd

import google.cloud.dialogflowcx_v3beta1.types as dfcx_types

from dfcx_scrapi.core.scrapi_base import ScrapiBase
from dfcx_scrapi.core.intents import Intents
from dfcx_scrapi.core.entity_types import EntityTypes
from dfcx_scrapi.core.flows import Flows
from dfcx_scrapi.core.pages import Pages
from dfcx_scrapi.core.webhooks import Webhooks
from dfcx_scrapi.core.transition_route_groups import TransitionRouteGroups
from dfcx_scrapi.core.test_cases import TestCases

# Type aliases
DFCXFlow = dfcx_types.flow.Flow
DFCXPage = dfcx_types.page.Page
DFCXRoute = dfcx_types.page.TransitionRoute

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
        if not self.agent_id:
            raise Exception("agent_id parameter is required")

        self.intents = Intents(creds=self.creds, agent_id=self.agent_id)
        self.entities = EntityTypes(creds=self.creds, agent_id=self.agent_id)
        self.flows = Flows(creds=self.creds, agent_id=self.agent_id)
        self.pages = Pages(creds=self.creds)
        self.webhooks = Webhooks(creds=self.creds, agent_id=self.agent_id)
        self.route_groups = TransitionRouteGroups(
            creds=self.creds, agent_id=self.agent_id)
        self.test_cases = TestCases(creds=self.creds, agent_id=self.agent_id)

        # Generate maps
        self.intents_map = self.intents.get_intents_map(agent_id=self.agent_id)
        self.flows_map = self.flows.get_flows_map(agent_id=self.agent_id)
        self.flows_map_rev = self.flows.get_flows_map(agent_id=self.agent_id, reverse=True)
        self.pages_map = {}
        for flow_id in self.flows_map.keys():
            self.pages_map[flow_id] = self.pages.get_pages_map(flow_id=flow_id)
        self.route_groups_map = {}
        for flow_id in self.flows_map.keys():
            self.route_groups_map[flow_id] = self.route_groups.get_route_groups_map(flow_id=flow_id)

    # Conversion utilities
    
    def convert_intent(self, intent_id):
        """Gets an intent display name from an intent ID"""
        intent_id_converted = str(self.agent_id) + '/intents/' + str(intent_id)
        if intent_id_converted in self.intents_map.keys():
            return self.intents_map[intent_id_converted]
        return ''

    def convert_flow(self, flow_id):
        """Gets a flow display name from a flow ID"""
        if flow_id.split('/')[-1] == '-':
            return ''
        #flow_id_converted = str(agent_id) + '/flows/' + str(flow_id)
        if flow_id in self.flows_map.keys():
            return self.flows_map[flow_id]
        # TODO: Should throw error instead of returning default
        return 'Default Start Flow'

    # Note that flow id includes agent, normally...
    def convert_page(self, page_id, flow_id):
        """Gets a page display name from a page and flow ID"""
        if page_id == 'END_SESSION':
            return 'End Session'
        elif page_id == 'END_FLOW':
            return 'End Flow'
        elif page_id == 'START_PAGE':
            return 'Start'
        page_id_converted = str(flow_id) + '/pages/' + str(page_id)
        if flow_id in self.pages_map.keys():
            if page_id_converted in self.pages_map[flow_id].keys():
                return self.pages_map[flow_id][page_id_converted]
            else:
                # TODO: Should throw error instead of returning default
                return 'Start'
        print('Flow not found')
        # TODO: Should throw error, but returning this probably will anyway
        return 'Invalid'
    
    def get_page(self, flow_id: str = None, flow_name: str = None, page_id: str = None, page_name: str = None) -> DFCXPage | DFCXFlow:
        """Gets the page data for a specified page within
        a specified flow. The flow and page can be specified
        by ID or by display name.
        
        Args:
          flow_id OR flow_name: The ID or display name of the flow 
          page_id OR page_name: The ID or display name of the page
        
        Returns:
          A DFCX Page object for this page, or DFCX Flow object if it's the start page
        
        Raises:
          KeyError, if the page is not found
        """
        if flow_id is None and flow_name is None:
            raise Exception('Please specify a flow')
        elif flow_name is not None:
            if flow_name in self.flows_map_rev.keys():
                flow_id = self.flows_map_rev[flow_name]
            else:
                raise Exception(f'Flow not found: {flow_name}')
        # Now that flow_id is set, look up the page
        if page_id is None and page_name is None:
            raise Exception('Please specify a page')
        elif page_name is not None:
            if page_name == 'Start':
                return self.flow_data[flow_id]
            if page_name in self.pages_map_rev[flow_id].keys():
                page_id = self.pages_map_rev[flow_id][page_name]
                return self.page_data[flow_id][page_id]
            else:
                raise KeyError('Page not found. Did you forget "page_name="?')
        else:
            if 'START_PAGE' in page_id:
                return self.flow_data[flow_id]
            elif page_id not in self.pages_map[flow_id].keys():
                raise KeyError('Page not found.')
            else:
                return self.page_data[flow_id][page_id]
    
    # Test case results
    
    # TODO: Should this function be in the base test_cases class, 
    # as get_test_case_results_df or something?
    def get_test_case_results(self, retest_all=False):
        """Gets the test case results for this agent,
        and generates a dataframe with their details.
        Any tests without a result will be run in a batch.
        
        Args:
          retest_all: if true, all test cases are re-run,
            regardless of whether or not they had a result
        
        Returns:
          DataFrame of test case results for this agent, with columns:
            display_name, id, short_id (excluding agent ID), 
            tags (comma-separated string), creation_time,
            start_flow, start_page, passed, test_time
        """
        test_case_results = self.test_cases.list_test_cases(self.agent_id)
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
            flows.append(self.convert_flow(response.test_config.flow))
            pages.append(self.convert_page(response.test_config.page, response.test_config.flow))
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
    
    # Test case comparison/report
    
    # Changelogs
    
    # Reachable and unreachable pages
    
    def find_reachable_pages_rec_helper(self, page: DFCXPage | DFCXFlow, route: DFCXRoute, reachable: List[str], conversation_path: List[str], min_intent_counts: List[int], presets: Dict[str,str], intent_route_count: int = 0, intent_route_limit: Optional[int] = None, include_groups: bool = True, include_start_page_routes: bool = True, limit_intent_to_initial: bool = False, is_initial: bool = False, include_meta: bool = False, verbose: bool = False) -> None:
        # TODO: Docstring
        target_page = route.target_page
        target_flow = route.target_flow
        if intent_route_limit is None or not hasattr(route, 'intent') or route.intent == '' or intent_route_count < intent_route_limit:
            if hasattr(page, 'form'):
                for parameter in page.form.parameters:
                    parameter_name = parameter.display_name
                    # Need to also account for parameters being set by intents (or by webhooks...)
                    if parameter_name not in presets.keys() or presets[parameter_name] == 'NULL':
                        # This page has an unfilled parameter
                        if limit_intent_to_initial and not is_initial:
                            return
            if hasattr(route, 'intent') and route.intent != '':
                if limit_intent_to_initial and not is_initial:
                    # Don't continue on this path
                    return
                intent_route_count += 1
            if target_page in self.pages:
                page_name = self.pages[target_page].display_name
                if verbose:
                      print(page.display_name,'->',page_name)
                # Move to this page (this is also the recursion limiting step to prevent infinite loops)
                if page_name not in reachable:
                    reachable.append(page_name)
                    min_intent_counts.append(intent_route_count)
                    conversation_path.append(page_name)
                    if verbose:
                        print(conversation_path, intent_route_count)

                    new_presets = presets.copy()
                    if hasattr(page, 'entry_fulfillment'):
                        if hasattr(page.entry_fulfillment, 'set_parameter_actions'):
                            for param_preset in page.entry_fulfillment.set_parameter_actions:
                                new_presets[param_preset.parameter] = param_preset.value
                    if hasattr(page, 'form'):
                        for parameter in page.form.parameters:
                            if hasattr(parameter, 'fill_behavior'):
                                if hasattr(parameter.fill_behavior, 'initial_prompt_fulfillment'):
                                    if hasattr(parameter.fill_behavior.initial_prompt_fulfillment, 'set_parameter_actions'):
                                        for param_preset in parameter.fill_behavior.initial_prompt_fulfillment.set_parameter_actions:
                                            new_presets[param_preset.parameter] = param_preset.value
                    if hasattr(route, 'trigger_fulfillment'):
                        if hasattr(route.trigger_fulfillment, 'set_parameter_actions'):
                            for param_preset in route.trigger_fulfillment.set_parameter_actions:
                                new_presets[param_preset.parameter] = param_preset.value

                    if hasattr(route, 'intent') and route.intent != '':
                        # Check the entities annotated on this intent
                        intent_name = self.intents_map[route.intent]
                        intent_params = self.get_intent_parameters(intent_name)
                        for param in intent_params:
                            new_presets[param.id] = f'(potentially set by {intent_name})'

                    self.find_reachable_pages_rec(self.pages[target_page], reachable, conversation_path, min_intent_counts, new_presets, intent_route_count=intent_route_count, intent_route_limit=intent_route_limit, include_groups=include_groups, include_start_page_routes=include_start_page_routes, limit_intent_to_initial=limit_intent_to_initial, is_initial=False, include_meta=include_meta, verbose=verbose)
                    conversation_path.pop(-1)
                elif page_name in reachable and intent_route_count < min_intent_counts[reachable.index(page_name)]:
                    # Better route found, traverse from here
                    min_intent_counts[reachable.index(page_name)] = intent_route_count
                    conversation_path.append(page_name)
                    if verbose:
                        print(conversation_path, intent_route_count)

                    new_presets = presets.copy()
                    if hasattr(page, 'entry_fulfillment'):
                        if hasattr(page.entry_fulfillment, 'set_parameter_actions'):
                            for param_preset in page.entry_fulfillment.set_parameter_actions:
                                new_presets[param_preset.parameter] = param_preset.value
                    if hasattr(page, 'form'):
                        for parameter in page.form.parameters:
                            if hasattr(parameter, 'fill_behavior'):
                                if hasattr(parameter.fill_behavior, 'initial_prompt_fulfillment'):
                                    if hasattr(parameter.fill_behavior.initial_prompt_fulfillment, 'set_parameter_actions'):
                                        for param_preset in parameter.fill_behavior.initial_prompt_fulfillment.set_parameter_actions:
                                            new_presets[param_preset.parameter] = param_preset.value
                    if hasattr(route, 'trigger_fulfillment'):
                        if hasattr(route.trigger_fulfillment, 'set_parameter_actions'):
                            for param_preset in route.trigger_fulfillment.set_parameter_actions:
                                new_presets[param_preset.parameter] = param_preset.value

                    if hasattr(route, 'intent') and route.intent != '':
                        # Check the entities annotated on this intent
                        intent_name = self.intents_map[route.intent]
                        intent_params = self.get_intent_parameters(intent_name)
                        for param in intent_params:
                            new_presets[param.id] = f'(potentially set by {intent_name})'

                    self.find_reachable_pages_rec(self.pages[target_page], reachable, conversation_path, min_intent_counts, new_presets, intent_route_count=intent_route_count, intent_route_limit=intent_route_limit, include_groups=include_groups, include_start_page_routes=include_start_page_routes, limit_intent_to_initial=limit_intent_to_initial, is_initial=False, include_meta=include_meta, verbose=verbose)
                    conversation_path.pop(-1)
            elif 'END_FLOW' in target_page:
                if verbose:
                    print(page.display_name,'-> END FLOW')
                if include_meta:
                    page_name = 'END FLOW'
                    if page_name not in reachable:
                        reachable.append(page_name)
                        min_intent_counts.append(intent_route_count)
                    elif page_name in reachable and intent_route_count < min_intent_counts[reachable.index(page_name)]:
                        min_intent_counts[reachable.index(page_name)] = intent_route_count
                #reachable.append('END FLOW')
            elif 'END_SESSION' in target_page:
                if verbose:
                    print(page.display_name,'-> END SESSION')
                if include_meta:
                    page_name = 'END SESSION'
                    if page_name not in reachable:
                        reachable.append(page_name)
                        min_intent_counts.append(intent_route_count)
                    elif page_name in reachable and intent_route_count < min_intent_counts[reachable.index(page_name)]:
                        min_intent_counts[reachable.index(page_name)] = intent_route_count
                #reachable.append('END SESSION')
            elif 'CURRENT_PAGE' in target_page:
                if verbose:
                    print(page.display_name,'-> CURRENT PAGE')
                page_name = page.display_name
                if page_name in reachable and intent_route_count < min_intent_counts[reachable.index(page_name)]:
                    min_intent_counts[reachable.index(page_name)] = intent_route_count
            elif 'PREVIOUS_PAGE' in target_page:
                if verbose:
                    print(page.display_name, '-> PREVIOUS PAGE')
                if include_meta:
                    page_name = 'PREVIOUS PAGE'
                    if page_name not in reachable:
                        reachable.append(page_name)
                        min_intent_counts.append(intent_route_count)
                    elif page_name in reachable and intent_route_count < min_intent_counts[reachable.index(page_name)]:
                        min_intent_counts[reachable.index(page_name)] = intent_route_count
                # TODO: This could cause huge problems...
            elif 'START_PAGE' in target_page:
                if verbose:
                    print(page.display_name, '-> START PAGE')
                page_name = 'Start'
                if page_name not in reachable:
                    reachable.append(page_name)
                    min_intent_counts.append(intent_route_count)
                    conversation_path.append(page_name)
                    if verbose:
                        print(conversation_path, intent_route_count)

                    new_presets = presets.copy()
                    if hasattr(page, 'entry_fulfillment'):
                        if hasattr(page.entry_fulfillment, 'set_parameter_actions'):
                            for param_preset in page.entry_fulfillment.set_parameter_actions:
                                new_presets[param_preset.parameter] = param_preset.value
                    if hasattr(page, 'form'):
                        for parameter in page.form.parameters:
                            if hasattr(parameter, 'fill_behavior'):
                                if hasattr(parameter.fill_behavior, 'initial_prompt_fulfillment'):
                                    if hasattr(parameter.fill_behavior.initial_prompt_fulfillment, 'set_parameter_actions'):
                                        for param_preset in parameter.fill_behavior.initial_prompt_fulfillment.set_parameter_actions:
                                            new_presets[param_preset.parameter] = param_preset.value
                    if hasattr(route, 'trigger_fulfillment'):
                        if hasattr(route.trigger_fulfillment, 'set_parameter_actions'):
                            for param_preset in route.trigger_fulfillment.set_parameter_actions:
                                new_presets[param_preset.parameter] = param_preset.value

                    if hasattr(route, 'intent') and route.intent != '':
                        # Check the entities annotated on this intent
                        intent_name = self.intents_map[route.intent]
                        intent_params = self.get_intent_parameters(intent_name)
                        for param in intent_params:
                            new_presets[param.id] = f'(potentially set by {intent_name})'

                    self.find_reachable_pages_rec(self.flow_data, reachable, conversation_path, min_intent_counts, new_presets, intent_route_count=intent_route_count, intent_route_limit=intent_route_limit, include_groups=include_groups, include_start_page_routes=include_start_page_routes, limit_intent_to_initial=limit_intent_to_initial, is_initial=False, include_meta=include_meta, verbose=verbose)
                    conversation_path.pop(-1)
                elif page_name in reachable and intent_route_count < min_intent_counts[reachable.index(page_name)]:
                  # Better route found, traverse from here
                    min_intent_counts[reachable.index(page_name)] = intent_route_count
                    conversation_path.append(page_name)
                    if verbose:
                        print(conversation_path, intent_route_count)

                    new_presets = presets.copy()
                    if hasattr(page, 'entry_fulfillment'):
                        if hasattr(page.entry_fulfillment, 'set_parameter_actions'):
                            for param_preset in page.entry_fulfillment.set_parameter_actions:
                                new_presets[param_preset.parameter] = param_preset.value
                    if hasattr(page, 'form'):
                        for parameter in page.form.parameters:
                            if hasattr(parameter, 'fill_behavior'):
                                if hasattr(parameter.fill_behavior, 'initial_prompt_fulfillment'):
                                    if hasattr(parameter.fill_behavior.initial_prompt_fulfillment, 'set_parameter_actions'):
                                        for param_preset in parameter.fill_behavior.initial_prompt_fulfillment.set_parameter_actions:
                                            new_presets[param_preset.parameter] = param_preset.value
                    if hasattr(route, 'trigger_fulfillment'):
                        if hasattr(route.trigger_fulfillment, 'set_parameter_actions'):
                            for param_preset in route.trigger_fulfillment.set_parameter_actions:
                                new_presets[param_preset.parameter] = param_preset.value

                    if hasattr(route, 'intent') and route.intent != '':
                        # Check the entities annotated on this intent
                        intent_name = self.intents_map[route.intent]
                        intent_params = self.get_intent_parameters(intent_name)
                        for param in intent_params:
                            new_presets[param.id] = f'(potentially set by {intent_name})'

                    self.find_reachable_pages_rec(self.flow_data, reachable, conversation_path, min_intent_counts, new_presets, intent_route_count=intent_route_count, intent_route_limit=intent_route_limit, include_groups=include_groups, include_start_page_routes=include_start_page_routes, limit_intent_to_initial=limit_intent_to_initial, is_initial=False, include_meta=include_meta, verbose=verbose)
                    conversation_path.pop(-1)
            elif len(target_page) > 0:
                print(page.display_name,'->',target_page)
                # This should not happen, and if it does it needs to be fixed
                input()
            elif len(target_flow) > 0:
                flow_name = self.flows_map[route.target_flow]
                if verbose:
                    print(page.display_name,'->',flow_name)
                if flow_name not in reachable:
                    reachable.append(flow_name)
                    min_intent_counts.append(intent_route_count)
                elif flow_name in reachable and intent_route_count < min_intent_counts[reachable.index(flow_name)]:
                    min_intent_counts[reachable.index(flow_name)] = intent_route_count
            else:
                if verbose:
                    print(page.display_name,'->',route.target_flow, '(empty)')
                page_name = page.display_name
                if page_name in reachable and intent_route_count < min_intent_counts[reachable.index(page_name)]:
                    min_intent_counts[reachable.index(page_name)] = intent_route_count
  
    def find_reachable_pages_rec(self, page: DFCXPage | DFCXFlow, reachable: List[str], conversation_path: List[str], min_intent_counts: List[int], presets: Dict[str,str], intent_route_count: int = 0, intent_route_limit: Optional[int] = None, include_groups: bool = True, include_start_page_routes: bool = True, limit_intent_to_initial: bool = False, is_initial: bool = False, include_meta: bool = False, verbose: bool = False) -> None:
        # TODO: Docstring
        if hasattr(page, 'form'):
            for parameter in page.form.parameters:
                for event_handler in parameter.fill_behavior.reprompt_event_handlers:
                    if limit_intent_to_initial and not is_initial:
                        continue
                    if hasattr(event_handler, 'target_page') or hasattr(event_handler, 'target_flow'):
                        self.find_reachable_pages_rec_helper(page, event_handler, reachable, conversation_path, min_intent_counts, presets, intent_route_count=intent_route_count, intent_route_limit=intent_route_limit, include_groups=include_groups, include_start_page_routes=include_start_page_routes, limit_intent_to_initial=limit_intent_to_initial, is_initial=is_initial, include_meta=include_meta, verbose=verbose)
        for event_handler in page.event_handlers:
            if limit_intent_to_initial and not is_initial:
                continue
            if hasattr(event_handler, 'target_page') or hasattr(event_handler, 'target_flow'):
                self.find_reachable_pages_rec_helper(page, event_handler, reachable, conversation_path, min_intent_counts, presets, intent_route_count=intent_route_count, intent_route_limit=intent_route_limit, include_groups=include_groups, include_start_page_routes=include_start_page_routes, limit_intent_to_initial=limit_intent_to_initial, is_initial=is_initial, include_meta=include_meta, verbose=verbose)
        for route in page.transition_routes:
            self.find_reachable_pages_rec_helper(page, route, reachable, conversation_path, min_intent_counts, presets, intent_route_count=intent_route_count, intent_route_limit=intent_route_limit, include_groups=include_groups, include_start_page_routes=include_start_page_routes, limit_intent_to_initial=limit_intent_to_initial, is_initial=is_initial, include_meta=include_meta, verbose=verbose)
        if include_groups:
            for route_group in page.transition_route_groups:
                for route in self.transition_route_groups[route_group].transition_routes:
                    self.find_reachable_pages_rec_helper(page, route, reachable, conversation_path, min_intent_counts, presets, intent_route_count=intent_route_count, intent_route_limit=intent_route_limit, include_groups=include_groups, include_start_page_routes=include_start_page_routes, limit_intent_to_initial=limit_intent_to_initial, is_initial=is_initial, include_meta=include_meta, verbose=verbose)
        # Start page routes and route groups are also accessible from this page
        if include_start_page_routes and page.display_name != self.flow_data.display_name and (not limit_intent_to_initial or is_initial):
            for event_handler in self.flow_data.event_handlers:
                if hasattr(event_handler, 'target_page') or hasattr(event_handler, 'target_flow'):
                    self.find_reachable_pages_rec_helper(self.flow_data, event_handler, reachable, conversation_path, min_intent_counts, presets, intent_route_count=intent_route_count, intent_route_limit=intent_route_limit, include_groups=include_groups, include_start_page_routes=include_start_page_routes, limit_intent_to_initial=limit_intent_to_initial, is_initial=is_initial, include_meta=include_meta, verbose=verbose)
            for route in self.flow_data.transition_routes:
                if hasattr(route, 'intent') and route.intent != '':
                    self.find_reachable_pages_rec_helper(self.flow_data, route, reachable, conversation_path, min_intent_counts, presets, intent_route_count=intent_route_count, intent_route_limit=intent_route_limit, include_groups=include_groups, include_start_page_routes=include_start_page_routes, limit_intent_to_initial=limit_intent_to_initial, is_initial=is_initial, include_meta=include_meta, verbose=verbose)
            if include_groups:
                for route_group in self.flow_data.transition_route_groups:
                    for route in self.transition_route_groups[route_group].transition_routes:
                        if hasattr(route, 'intent') and route.intent != '':
                            self.find_reachable_pages_rec_helper(self.flow_data, route, reachable, conversation_path, min_intent_counts, presets, intent_route_count=intent_route_count, intent_route_limit=intent_route_limit, include_groups=include_groups, include_start_page_routes=include_start_page_routes, limit_intent_to_initial=limit_intent_to_initial, is_initial=is_initial, include_meta=include_meta, verbose=verbose)    

    def find_reachable_pages(self, flow_id: str, flow_name: str, from_page: str = 'Start', intent_route_limit: Optional[int] = None, include_groups: bool = True, include_start_page_routes: bool = True, limit_intent_to_initial: bool = False, is_initial: bool = True, include_meta: bool = False, verbose: bool = False) -> List[str]:
        """Finds all pages which are reachable by transition routes,
        starting from a given page in a given flow. Either flow_id or
        flow_name must be used.

        Args:
          flow_id: The ID of the flow to find reachable pages for
          flow_name: The display name of the flow to find reachable pages for
          from_page: (Optional) The page to start from. If left blank, it will start on the Start Page
          intent_route_limit: (Optional) Default None
          include_groups: (Optional) If true, intents from transition route groups will be included, 
            but only if they are actually referenced on some page
          include_start_page_routes: (Optional) Default true
          limit_intent_to_initial: (Optional) Default False
          is_initial: (Optional) Default True
          include_meta: (Optional) Default False
          verbose: (Optional) If true, print debug information about route traversal

        Returns:
          The list of reachable pages in this flow
        """
        # Start at the start page...
        reachable = [from_page]
        conversation_path = [from_page]
        min_intent_counts = [25] # Technically this could be [0] or [1], or very rarely more than 1, depending on the routes that lead to current page...
        presets = {}
        page_data = self.get_page(flow_id=flow_id, flow_name=flow_name, page_id=None, page_name=from_page)
        self.find_reachable_pages_rec(page_data, reachable, conversation_path, min_intent_counts, presets, intent_route_count=0, intent_route_limit=intent_route_limit, include_groups=include_groups, include_start_page_routes=include_start_page_routes, limit_intent_to_initial=limit_intent_to_initial, is_initial=is_initial, include_meta=include_meta, verbose=verbose)
        return reachable
    
    def find_unreachable_pages(self, flow_id: str = None, flow_name: str = None, include_groups: bool = True, verbose: bool = False) -> List[str]:
        """Finds all pages which are unreachable by transition routes, 
        starting from the start page of a given flow. Either flow_id or
        flow_name must be used.

        Args:
          flow_id: The ID of the flow to find unreachable pages for
          flow_name: The display name of the flow to find unreachable pages for
          include_groups: (Optional) If true, intents from transition route groups will be included, 
            but only if they are actually referenced on some page
          verbose: (Optional) If true, print debug information about route traversal

        Returns:
          The list of unreachable pages in this flow
        """
        if not flow_id:
            if not flow_name:
                raise Exception("One of flow_id or flow_name must be set for find_unreachable_pages")
        reachable = self.find_reachable_pages(flow_id, flow_name, include_groups=include_groups, verbose=verbose)
        if flow_id:
            return list(set(self.pages_map[self.flows_map_rev[flow_name]].keys()) - set(reachable))
        else:
            return list(set(self.pages_map[self.flows_map[flow_id]].keys()) - set(reachable))

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
