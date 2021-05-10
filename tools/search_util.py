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
import logging
import pandas as pd
import time
import google.cloud.dialogflowcx_v3beta1.types as types

from ..core import entity_types, flows, intents, pages

# logging config
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)-8s %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S')


class SearchUtil:
    def __init__(self, creds_path, agent_id=None):
        self.intents = intents.Intents(creds_path)
        self.entities = entity_types.EntityTypes(creds_path)
        self.flows = flows.Flows(creds_path)
        self.pages = pages.Pages(creds_path)

    def find_list_parameters(self, agent_id):
        """ This method extracts Parameters set at a page level that are
        designated as "lists".

        Page level parameters are tied to Entity Types and can be returned
        as String or List types. If the user selects "list" at the page
        level, the Entity Type will be returned with "is_list: True". This
        function will allow the user to provide an Agent ID and will return
        all instances of parameters being used as lists on pages.

        Args:
          - agent_id, the Agent ID string in the following format:
            projects/<project_id>/locations/<location_id>/agents/<agent_id>

        Returns:
          - params_map, a Dict of parameter names and Pages they belong to
        """

        # entities = self.dfcx.list_entity_types(agent_id)
        flows_map = self.flows.get_flows_map(agent_id)
        entities_map = self.entities.get_entities_map(agent_id)

        params_list = []

        for flow in flows_map:
            temp_pages = self.pages.list_pages(flows_map[flow])
            for page in temp_pages:
                for param in page.form.parameters:
                    if param.is_list:
                        params_list.append(param.display_name)
                        print('FLOW = {}'.format(flow))
                        print('PAGE = {}'.format(page.display_name))
                        print(param.display_name)
                        if 'sys' in param.entity_type.split('/')[-1]:
                            print(param.entity_type.split('/')[-1])
                        else:
                            print(param.entity_type)
                            print(
                                entities_map[param.entity_type.split('/')[-1]])
                        print('\n')

        return params_list

    def search_conditionals_page(self,page_id,search):
        """ search page for an exact string in conditional routes

        Args:
          - page_id, the formatted CX Page ID to use
          - search, string to search

        Returns:
          - locator, dataframe of the results of where this string was found
        """
        
        locator = pd.DataFrame()
        page = self.pages.get_page(page_id=page_id)
        i = 1
        for route in page.transition_routes:
            if search.lower() in route.condition.lower():
                iter_frame = pd.DataFrame(columns=['resource_id','condition', 'route_id'], data=[[page_id,route.condition,i]])
                locator = locator.append(iter_frame)
            i+=1

        return locator

    def search_conditionals_flow(self,flow_id, search):
            """ search flow for an exact string in conditional routes

            Args:
            - flow_id, the formatted CX Flow ID to use
            - search, string to search

            Returns:
            - locator, dataframe of the results of where this string was found
            """
            
            locator = pd.DataFrame()
            flow = self.flows.get_flow(flow_id=flow_id)
            i = 1
            for route in flow.transition_routes:
                if search.lower() in route.condition.lower():
                    iter_frame = pd.DataFrame(columns=['resource_id','condition', 'route_id'], data=[[flow_id,route.condition,i]])
                    locator = locator.append(iter_frame)
                i+=1

            return locator

    def search_conditionals(self,search, agent_id, flow_name=None, page_name=None, flag_search_all = False):
            """This is the master function where a user can search across all pages in a flow, 
            an entire agent etc. search conditionals for an exact string in conditional routes.

            Args:
                - search, string to search
                - agent_id, the formatted CX Agent ID to use
                - flow_name, (optional) the display name of the flow to search
                - page_name,  (optional) the display name of the page to search
                - flag_search_all, (optional)
                    When set to True:
                        -if just an agent_id is specified an entire agent is searched
                        -if just an agent_id and flow_name are specified an entire flow is searched
                        -if an agent_id, flow_name and page_name are specified a page is searched
                    When set to False:
                        -if just an agent_id and flow_name are specified only the start page of the flow is searched
                        -if an agent_id, flow_name and page_name are specified a page is searched
            Returns:
                - locator, dataframe of the results of where this string was found
            """
            
            if page_name:
                try:
                    flows_map = self.flows.get_flows_map(agent_id=agent_id,reverse=True)
                except:
                    logging.error('{0} is not a valid flow_name for agent {1}'.format(flow_name, agent_id))
                try:
                    pages_map = self.pages.get_pages_map(flow_id=flows_map[flow_name], reverse=True)
                    return  self.search_conditionals_page(page_id=pages_map[page_name], search = search)

                except:
                    logging.error('{0} is not a valid page_name for flow {1} in agent {2}'.format(page_name, flow_name,agent_id))


            if flow_name:
                locator = pd.DataFrame()
                try:
                    flows_map = self.flows.get_flows_map(agent_id=agent_id,reverse=True)
                    flow_search = self.search_conditionals_flow(flow_id=flows_map[flow_name], search=search)
                    flow_search.insert(0,'resource_name',flow_name)
                    flow_search.insert(0,'resource_type','flow')
                    locator = locator.append(flow_search)
                except:
                    logging.error('{0} is not a valid flow_name for agent {1}'.format(flow_name, agent_id))


                if flag_search_all:
                
                    pages_map = self.pages.get_pages_map(flow_id=flows_map[flow_name], reverse=True)
                    for page in pages_map:
                        page_search = self.search_conditionals_page(page_id=pages_map[page], search=search)
                        time.sleep(0.5)
                        page_search.insert(0,'resource_name',page)
                        page_search.insert(0,'resource_type','page')
                        locator = locator.append(page_search)
                    
                return locator


            if flow_name==None and page_name==None and flag_search_all==True:
                locator = pd.DataFrame()

                flows_map = self.flows.get_flows_map(agent_id=agent_id,reverse=True)
                for flow in flows_map:
                    flow_search = self.search_conditionals_flow(flow_id=flows_map[flow], search=search)
                    flow_search.insert(0,'resource_name',flow)
                    flow_search.insert(0,'resource_type','flow')
                    locator = locator.append(flow_search)
                    pages_map = self.pages.get_pages_map(flow_id=flows_map[flow], reverse=True)
                    for page in pages_map:
                        page_search = self.search_conditionals_page(page_id=pages_map[page], search=search)
                        time.sleep(0.5)
                        page_search.insert(0,'resource_name',page)
                        page_search.insert(0,'resource_type','page')
                        locator = locator.append(page_search)
                return locator