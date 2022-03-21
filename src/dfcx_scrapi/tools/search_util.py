"""util class for doing searches"""

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

import logging
import time
from typing import Dict, List
from google.cloud.dialogflowcx_v3beta1 import types
from google.oauth2 import service_account
import pandas as pd
from dfcx_scrapi.core import (
    scrapi_base, 
    intents, 
    flows, 
    pages, 
    entity_types,
    transition_route_groups
)

# logging config
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


class SearchUtil(scrapi_base.ScrapiBase):
    """class for searching items"""

    def __init__(
        self,
        creds_path: str = None,
        creds_dict: Dict[str,str] = None,
        creds: service_account.Credentials = None,
        scope=False, #TODO type hint
        agent_id: str = None,
    ):
        super().__init__(
            creds_path=creds_path,
            creds_dict=creds_dict,
            creds=creds,
            scope=scope,
        )

        logging.info("create dfcx creds %s", creds_path)
        self.intents = intents.Intents(creds_path=creds_path, creds_dict=creds_dict)
        self.entities = entity_types.EntityTypes(
            creds_path=creds_path, creds_dict=creds_dict
        )
        self.flows = flows.Flows(creds_path=creds_path, creds_dict=creds_dict)
        self.pages = pages.Pages(creds_path=creds_path, creds_dict=creds_dict)
        self.route_groups = transition_route_groups.TransitionRouteGroups(
            creds_path, creds_dict
        )
        self.creds_path = creds_path
        self.intents_map = None
        if agent_id:
            self.agent_id = agent_id
            self.flow_map = self.flows.get_flows_map(
                agent_id=agent_id, reverse=True
            )
            self.intents_map = self.intents.get_intents_map(agent_id)
            self.client_options = self._set_region(agent_id)

    def _find_true_routes_flow_level(self, flow_display_name, flow_map):
        flow_id = flow_map[flow_display_name]
        start_page = self.flows.get_flow(flow_id) # pylint: disable=W0612
        other_pages = self.pages.list_pages(flow_id)

        # Start page - no entry fulfillment
        pages_dataframe = pd.DataFrame()
        for page in other_pages:
            display_name = page.display_name

            webhook = False
            if page.entry_fulfillment.webhook:
                webhook = True

            has_parameters = False
            if page.form.parameters:
                has_parameters = True

            has_true_route = False
            has_true_final_route = False
            for route in page.transition_routes:
                if route.condition == "true":
                    has_true_route = True

                if route.condition == '$page.params.status = "FINAL" AND true':
                    has_true_final_route = True

            page_dataframe = pd.DataFrame(
                columns=[
                    "flow_display_name",
                    "page_display_name",
                    "webhook_entry_fullfillment",
                    "has_parameters",
                    "has_true_route",
                    "has_true_and_final_route",
                ],
                data=[
                    [
                        flow_display_name,
                        display_name,
                        webhook,
                        has_parameters,
                        has_true_route,
                        has_true_final_route,
                    ]
                ],
            )
            pages_dataframe = pages_dataframe.append(page_dataframe)

        return pages_dataframe

    # Flows - event handlers
    def _flow_level_handlers(self):
        flows_in_agent = self.flows.list_flows(self.agent_id)

        flow_event_handler_data = pd.DataFrame()
        for flow in flows_in_agent:
            flow_level_event_handlers = flow.event_handlers
            flow_level_event_handlers_dataframe = pd.DataFrame()

            for handler in flow_level_event_handlers:
                flow_level_event_handlers_dataframe = (
                    flow_level_event_handlers_dataframe.append(
                        pd.DataFrame(
                            columns=[
                                "flow",
                                "event",
                                "messages",
                                "transition_flow",
                                "transition_page",
                            ],
                            data=[
                                [
                                    flow.display_name,
                                    handler.event,
                                    handler.trigger_fulfillment.messages,
                                    handler.target_flow,
                                    handler.target_page,
                                ]
                            ],
                        )
                    )
                )
                flow_event_handler_data = flow_event_handler_data.append(
                    flow_level_event_handlers_dataframe
                )

        return flow_event_handler_data

    # Pages - event handlers
    def _page_level_handlers(self):
        page_level_event_handlers_all_dataframe = pd.DataFrame()
        flow_map = self.flows.get_flows_map(self.agent_id)
        for flow_ in flow_map.keys():
            pages_in_flow = self.pages.list_pages(flow_)

            for page in pages_in_flow:
                page_level_event_handlers = page.event_handlers
                page_level_event_handlers_dataframe = pd.DataFrame()
                for handler in page_level_event_handlers:
                    page_level_event_handlers_dataframe = (
                        page_level_event_handlers_dataframe.append(
                            pd.DataFrame(
                                columns=[
                                    "flow",
                                    "page",
                                    "event",
                                    "messages",
                                    "transition_flow",
                                    "transition_page",
                                ],
                                data=[
                                    [
                                        flow_map[flow_],
                                        page.display_name,
                                        handler.event,
                                        handler.trigger_fulfillment.messages,
                                        handler.target_flow,
                                        handler.target_page,
                                    ]
                                ],
                            )
                        )
                    )

                page_level_event_handlers_all_dataframe = (
                    page_level_event_handlers_all_dataframe.append(
                        page_level_event_handlers_dataframe
                    )
                )
        return page_level_event_handlers_all_dataframe

    # Parameters - event handlers
    def _parameter_level_handlers(self):
        parameter_level_event_handlers_all_dataframe = pd.DataFrame()
        flow_map = self.flows.get_flows_map(self.agent_id)
        for flow_ in flow_map.keys():
            pages_in_flow = self.pages.list_pages(flow_)
            for page in pages_in_flow:
                parameters = page.form.parameters
                for parameter in parameters:
                    parameter_event_handlers = (
                        parameter.fill_behavior.reprompt_event_handlers
                    )
                    param_lvl_event_df = pd.DataFrame()
                    for handler in parameter_event_handlers:
                        param_lvl_event_df = param_lvl_event_df.append(
                            pd.DataFrame(
                                columns=[
                                    "flow",
                                    "page",
                                    "parameter",
                                    "event",
                                    "messages",
                                    "transition_flow",
                                    "transition_page",
                                ],
                                data=[
                                    [
                                        flow_map[flow_],
                                        page.display_name,
                                        parameter.display_name,
                                        handler.event,
                                        handler.trigger_fulfillment.messages,
                                        handler.target_flow,
                                        handler.target_page,
                                    ]
                                ],
                            )
                        )
                    parameter_level_event_handlers_all_dataframe = (
                        parameter_level_event_handlers_all_dataframe.append(
                            param_lvl_event_df
                        )
                    )
        return parameter_level_event_handlers_all_dataframe


    def find_list_parameters(self, agent_id):
        """This method extracts Parameters set at a page level that are
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

        params_list = []

        for flow in flows_map.keys():
            temp_pages = self.pages.list_pages(flow)
            for page in temp_pages:
                for param in page.form.parameters:
                    if param.is_list:
                        params_list.append(param.display_name)

        return params_list

    def search_conditionals_page(self, page_id, search):
        """search page for an exact string in conditional routes

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
                iter_frame = pd.DataFrame(
                    columns=["resource_id", "condition", "route_id"],
                    data=[[page_id, route.condition, i]],
                )
                locator = locator.append(iter_frame)
            i += 1

        return locator

    def search_conditionals_flow(self, flow_id, search):
        """search flow for an exact string in conditional routes

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
                iter_frame = pd.DataFrame(
                    columns=["resource_id", "condition", "route_id"],
                    data=[[flow_id, route.condition, i]],
                )
                locator = locator.append(iter_frame)
            i += 1

        return locator

    def search_conditionals(
        self,
        search,
        agent_id,
        flow_name=None,
        page_name=None,
        flag_search_all=False,
    ):
        """This is the master function where a user can search across
        all pages in a flow, an entire agent etc.
        Search conditionals for an exact string in conditional routes.

        Args:
            - search, string to search
            - agent_id, the formatted CX Agent ID to use
            - flow_name, (optional) the display name of the flow to search
            - page_name,  (optional) the display name of the page to search
            - flag_search_all, (optional)
                When set to True:
                    -if just an agent_id then entire agent is searched
                    -if just an agent_id and flow_name are specified
                        an entire flow is searched
                    -if an agent_id, flow_name and page_name are specified
                        a page is searched
                When set to False:
                    -if just an agent_id and flow_name are specified
                        only the start page of the flow is searched
                    -if an agent_id, flow_name and page_name are specified
                        a page is searched
        Returns:
            - locator, dataframe of the results of where this string was found
        """

        if page_name:
            try:
                flows_map = self.flows.get_flows_map(
                    agent_id=agent_id, reverse=True
                )
            # check - maybe other error types here
            except ValueError:
                logging.error(
                    "%s is not a valid flow_name for agent %s",
                    flow_name,
                    agent_id,
                )
            try:
                pages_map = self.pages.get_pages_map(
                    flow_id=flows_map[flow_name], reverse=True
                )
                return self.search_conditionals_page(
                    page_id=pages_map[page_name], search=search
                )

            except ValueError:
                logging.error(
                    "%s is not a valid page_name for flow %s in agent %s",
                    page_name,
                    flow_name,
                    agent_id,
                )

        if flow_name:
            locator = pd.DataFrame()
            try:
                flows_map = self.flows.get_flows_map(
                    agent_id=agent_id, reverse=True
                )
                flow_search = self.search_conditionals_flow(
                    flow_id=flows_map[flow_name], search=search
                )
                flow_search.insert(0, "resource_name", flow_name)
                flow_search.insert(0, "resource_type", "flow")
                locator = locator.append(flow_search)
            except ValueError:
                logging.error(
                    "%s is not a valid flow_name for agent %s",
                    flow_name,
                    agent_id,
                )

            if flag_search_all:

                pages_map = self.pages.get_pages_map(
                    flow_id=flows_map[flow_name], reverse=True
                )
                for page in pages_map:
                    page_search = self.search_conditionals_page(
                        page_id=pages_map[page], search=search
                    )
                    time.sleep(0.5)
                    page_search.insert(0, "resource_name", page)
                    page_search.insert(0, "resource_type", "page")
                    locator = locator.append(page_search)

            return locator

        if flow_name is None and page_name is None and flag_search_all is True:
            locator = pd.DataFrame()

            flows_map = self.flows.get_flows_map(
                agent_id=agent_id, reverse=True
            )
            for flow in flows_map:
                flow_search = self.search_conditionals_flow(
                    flow_id=flows_map[flow], search=search
                )
                flow_search.insert(0, "resource_name", flow)
                flow_search.insert(0, "resource_type", "flow")
                locator = locator.append(flow_search)
                pages_map = self.pages.get_pages_map(
                    flow_id=flows_map[flow], reverse=True
                )
                for page in pages_map:
                    page_search = self.search_conditionals_page(
                        page_id=pages_map[page], search=search
                    )
                    time.sleep(0.5)
                    page_search.insert(0, "resource_name", page)
                    page_search.insert(0, "resource_type", "page")
                    locator = locator.append(page_search)
            return locator

        # not found
        return None


    def find_true_routes(self, agent_id: str = None):
        """This method extracts data to see if routes with no parameters have a
        true route or pages with parameters have a true route +
        page.params.status = "Final" route. Having these routes ensure a user
        can escape this page no matter what.

        Args:
          - agent_id: The properly formatted CX Agent ID

        Returns:
          - agent_results: dataframe with:
              flow_display_name: display name of the associated page
              page_display_name: display name of the page with the associated
                data
              webhook_entry_fulfillments: True if a page has a webhook on entry
                else False
              has_parameters: True if a page has parameters else False
              has_true_route: True if a page has a true route else False
              has_true_and_final_route: True if a page has a route with true
                + page.params.status=Final else False
        """

        if not agent_id:
            agent_id = self.agent_id

        agent_results = pd.DataFrame()
        flow_map = self.flows.get_flows_map(
                agent_id=agent_id, reverse=True
            )

        for flow_display_name in flow_map.keys():
            flow_scan = self._find_true_routes_flow_level(
                flow_display_name, flow_map
            )
            agent_results = agent_results.append(flow_scan)
        return agent_results


    # Event handlers Main Function
    def find_event_handlers(self):
        """This method extracts event handlers at the flow, page and parameter
        level and displays data about their associated event. A user can use
        this data to spot patterns in event types and look for detrimental
        patterns.

        Args:
          - agent_id must specify agent id when instantiating the class

        Returns:
          - dictionary with flow, page and parameter events
        """
        event_handler_scan = {
            "flow": self._flow_level_handlers(),
            "page": self._page_level_handlers(),
            "parameter": self._parameter_level_handlers(),
        }

        return event_handler_scan
    
    def get_agent_fulfillments(self, agent_id: str):
        """Gets all fulfillments, conditional responses from an agent.

        Args:
          agent_id: if of agent to pull fulfillments from.

        Returns:
          dataframe of agent fulfillments as well as identifiers which help
          users locate the position of fulfillments in an agent. Has columns:
            flow
            resource_type
            resource_name
            fulfillment_type
            identifier_type
            identifier
            response_type
            condition
        """
        flow_list = self.flows.list_flows(agent_id)
        if not self.intents_map:
            self.intents_map = self.intents.get_intents_map(agent_id)

        agent_fulfillments = pd.DataFrame()
        for flow_obj in flow_list:
            flow_data = self.get_flow_fufillments(flow_obj=flow_obj)
            agent_fulfillments = pd.concat(
                [agent_fulfillments, flow_data]
            )
            page_list = self.pages.list_pages(flow_obj.name)
            for page in page_list:
                page_data = self._get_page_fulfillments(
                    flow_obj.display_name, page_obj=page
                )
                agent_fulfillments = pd.concat([agent_fulfillments, page_data])

        column_order = [
            "flow",
            "resource_type",
            "resource_name",
            "fulfillment_type",
            "identifier_type",
            "identifier",
            "response_type",
            "condition",
            "fulfillment",
        ]
        agent_fulfillments = agent_fulfillments[column_order]
        return agent_fulfillments
    
    def get_flow_fufillments(self, flow_obj: types.Flow):
        """Get all fulfillments from a flow object.

        Args:
            flow_obj: flow object to get fulfillments from.
        Returns:
            Dataframe with columns:
                flow
                resource_type
                resource_name
                fulfillment_type
                identifier_type
                identifier
                response_type
                condition
        """
        flow_fufillments = pd.DataFrame()
        flow_dictionary = types.Flow.to_dict(flow_obj)
        transition_routes = flow_dictionary["transition_routes"]
        event_handlers = flow_dictionary["event_handlers"]
        route_fulfillments = self._get_transition_route_fulfillments(
            flow_obj.display_name,
            resource_type="page",
            resource_name="START_PAGE",
            routes=transition_routes,
        )
        event_fulfillments = self._get_event_handler_fulfillments(
            flow_obj.display_name, "START_PAGE", event_handlers
        )
        route_group_fulfillments = self._get_route_group_fulfillments(flow_dictionary)

        flow_fufillments = pd.concat(
            [
                flow_fufillments, 
                route_fulfillments, 
                event_fulfillments, 
                route_group_fulfillments
            ]
        )
        return flow_fufillments
    
    @staticmethod
    def _get_message_fulfillments(messages: List[types.ResponseMessage]):
        """
        Gets fulfillments from messages dictionary.

        Args:
            messages: object to extract fulfillments from.
        Returns:
            a simple list of fulfillment strings.
        """
        text_fulfillments_list = list()
        for message in messages:
            text_fulfillments = message.get("text", dict()).get("text")
            if text_fulfillments:
                for text_fulfillment in text_fulfillments:
                    text_fulfillments_list.append(text_fulfillment)
        return text_fulfillments_list

    
    @staticmethod
    def _get_conditional_case_fulfillments(
        case_content: 
            List[types.Fulfillment.ConditionalCases.Case.CaseContent]
    ):
        """
        Gets conditinal fulfillments from case content dictionary.

        Args:
            case_content: object to extract fulfillments from 
        Returns:
            a simple list of fulfillment strings.
        """
        text_fulfillments_list = list()
        for content in case_content:
            message = content.get("message", False)
            if message:
                text_fulfillments = message.get("text", dict()).get("text")
                if text_fulfillments:
                    for text_fulfillment in text_fulfillments:
                        text_fulfillments_list.append(text_fulfillment)
        return text_fulfillments_list

    def _get_transition_route_fulfillments(
        self,
        flow_display_name: str,
        resource_type: str,
        resource_name: str,
        routes: List[types.TransitionRouteGroup]
    ):
        """
        Gets fulfillments from routes list.

        Args: 
            flow_display_name: origin of routes list
            resource_type: 'page' or 'route group'.
            resource_name: name corresponding to the resource type.
            routes: routes to pull fulfillments from.
        Returns:
            Dataframe with columns:
                fulfillment
                identifier
                response_type
                consition
                flow
                resource_type
                resource_name
                fulfillment_type
                identifier_type
        """

        routes_fulfillments = pd.DataFrame()
        for route in routes:
            # non-conditional cases
            route_dataframe = pd.DataFrame()

            intent_triggered = self.intents_map.get(route["intent"], "")
            if route.get("trigger_fulfillment", False):
                messages = route["trigger_fulfillment"]["messages"]
                text_fulfillments = self._get_message_fulfillments(messages)
                route_dataframe["fulfillment"] = text_fulfillments
                route_dataframe["identifier"] = intent_triggered
                route_dataframe["response_type"] = "text"
                route_dataframe["condition"] = None

                routes_fulfillments = pd.concat([routes_fulfillments, route_dataframe])

            # conditional cases
            conditional_cases = route.get("trigger_fulfillment", {}).get(
                "conditional_cases", False
            )
            if conditional_cases:
                for cases in conditional_cases:
                    for case in cases["cases"]:
                        condition = case["condition"]
                        if not condition or condition == "":
                            condition = "else"
                        case_content = case.get("case_content", False)
                        if case_content:
                            text_fulfillments = self._get_conditional_case_fulfillments(
                                case_content
                            )
                            route_dataframe = pd.DataFrame()
                            route_dataframe["fulfillment"] = text_fulfillments
                            route_dataframe["identifier"] = intent_triggered
                            route_dataframe["response_type"] = "conditional"
                            route_dataframe["condition"] = condition

                            routes_fulfillments = pd.concat(
                                [routes_fulfillments, route_dataframe]
                            )

        routes_fulfillments["flow"] = flow_display_name
        routes_fulfillments["resource_type"] = resource_type
        routes_fulfillments["resource_name"] = resource_name
        routes_fulfillments["fulfillment_type"] = "transition route"
        routes_fulfillments["identifier_type"] = "intent triggered"

        return routes_fulfillments

    def _get_event_handler_fulfillments(
        self,
        flow_display_name: str,
        page_display_name: str,
        event_handlers: List[types.EventHandler]
    ):
        """
        Gets fulfillments from event handlers.

        Args:
            flow_display_name: origin flow of the event handler fulfillments.
            page_display_name: origin page of the event handler fulfillments.
            event_handlers: list of event handlers.
        Returns:
            Dataframe with columns:
                fulfillment
                identifier
                response_type
                condition
                flow
                resource_type
                resource_name
                fulfillment_type
                identifier_type
        """
        event_handler_fulfillments = pd.DataFrame()
        for event_handler in event_handlers:
            # non-conditional cases
            event_handler_dataframe = pd.DataFrame()
            event_handler_name = event_handler.get("event", "")
            if event_handler.get("trigger_fulfillment", False):
                messages = event_handler["trigger_fulfillment"]["messages"]
                text_fulfillments = self._get_message_fulfillments(messages)

                event_handler_dataframe["fulfillment"] = text_fulfillments
                event_handler_dataframe["identifier"] = event_handler_name
                event_handler_dataframe["response_type"] = "text"
                event_handler_dataframe["condition"] = None

                event_handler_fulfillments = pd.concat(
                    [event_handler_fulfillments, event_handler_dataframe]
                )

            # conditional cases
            conditional_cases = event_handler.get("trigger_fulfillment", {}).get(
                "conditional_cases", False
            )
            if conditional_cases:
                for cases in conditional_cases:
                    for case in cases["cases"]:
                        condition = case["condition"]
                        if not condition or condition == "":
                            condition = "else"
                        case_content = case.get("case_content", False)
                        if case_content:
                            text_fulfillments = self._get_conditional_case_fulfillments(
                                case_content
                            )
                            event_handler_dataframe = pd.DataFrame()
                            event_handler_dataframe["fulfillment"] = text_fulfillments
                            event_handler_dataframe["identifier"] = event_handler_name
                            event_handler_dataframe["response_type"] = "conditional"
                            event_handler_dataframe["condition"] = condition

                            event_handler_fulfillments = pd.concat(
                                [event_handler_fulfillments, event_handler_dataframe]
                            )

        event_handler_fulfillments["flow"] = flow_display_name
        event_handler_fulfillments["resource_type"] = "page"
        event_handler_fulfillments["resource_name"] = page_display_name
        event_handler_fulfillments["fulfillment_type"] = "event handler"
        event_handler_fulfillments["identifier_type"] = "event name"

        return event_handler_fulfillments

    def _get_entry_fulfillments(
        self,
        flow_display_name: str,
        object_display_name: str,
        entry_fulfillment: types.Fulfillment,
    ):
        """
        Gets fulfillments from entry fulfillments dictionary on a page.

        Args:
            flow_display_name: origin flow of entry_fulfillment.
            object_display_name: origin object of entry_fulfillment.
            entry_fulfillment: object to pull fulfillments from.
        Returns:
            Dataframe with columns:
                fulfillment
                identifier
                response_type
                condition
                flow
                resource_type
                resource_name
                fulfillment_type
                identifier_type
        """
        entry_fulfillments = pd.DataFrame()

        # non-conditionals
        entry_fulfillments_dataframe = pd.DataFrame()
        if entry_fulfillment.get("trigger_fulfillment", False):
            messages = entry_fulfillment["trigger_fulfillment"]["messages"]
            text_fulfillments = self._get_message_fulfillments(messages)

            entry_fulfillments_dataframe["fulfillment"] = text_fulfillments
            entry_fulfillments_dataframe["identifier"] = object_display_name
            entry_fulfillments_dataframe["response_type"] = "text"
            entry_fulfillments_dataframe["condition"] = None

            entry_fulfillments = pd.concat(
                [entry_fulfillments, entry_fulfillments_dataframe]
            )

        # conditionals
        conditional_cases = entry_fulfillment.get("conditional_cases", False)
        if conditional_cases:
            for cases in conditional_cases:
                for case in cases["cases"]:
                    condition = case["condition"]
                    if not condition or condition == "":
                        condition = "else"
                    case_content = case.get("case_content", False)
                    if case_content:
                        text_fulfillments = self._get_conditional_case_fulfillments(
                            case_content
                        )
                        entry_fulfillments_dataframe = pd.DataFrame()
                        entry_fulfillments_dataframe["fulfillment"] = text_fulfillments
                        entry_fulfillments_dataframe["identifier"] = object_display_name
                        entry_fulfillments_dataframe["response_type"] = "conditional"
                        entry_fulfillments_dataframe["condition"] = condition

                        entry_fulfillments = pd.concat(
                            [entry_fulfillments, entry_fulfillments_dataframe]
                        )

        entry_fulfillments["flow"] = flow_display_name
        entry_fulfillments["resource_type"] = "page"
        entry_fulfillments["resource_name"] = object_display_name
        entry_fulfillments["fulfillment_type"] = "entry fulfillment"
        entry_fulfillments["identifier_type"] = "page name"
        return entry_fulfillments

    def _get_route_group_fulfillments(self, flow_dictionary: Dict):
        """
        Gets fulfillments from route groups in a flow.

        Args:
            flow_dictionary: from calling types.Flow.to_dict on a types.Flow 
                object.
        Returns:
            Dataframe with columns:
                flow
                resource_type
                resource_name
                fulfillment_type
                identifier_type
                identifier
                response_type
                condition
        """
        route_group_fulfillments_df = pd.DataFrame()
        route_groups_flow = self.route_groups.list_transition_route_groups(
            flow_id=flow_dictionary["name"]
        )
        for route_group_flow in route_groups_flow:
            route_group_flow = types.TransitionRouteGroup.to_dict(route_group_flow)
            route_group_name = route_group_flow["display_name"]
            routes = route_group_flow["transition_routes"]
            route_group_fulfillment_df = self._get_transition_route_fulfillments(
                flow_dictionary["display_name"],
                resource_type="route group",
                resource_name=route_group_name,
                routes=routes,
            )
            route_group_fulfillments_df = pd.concat(
                [route_group_fulfillments_df, route_group_fulfillment_df]
            )
        return route_group_fulfillments_df


    def _get_page_fulfillments(
        self, flow_display_name: str, page_obj: types.Page
    ):
        """
        Gets all fulfillments from a page object.

        Args:
            flow_display_name: origin flow of the page_obj.
            page_obj: page object to extract fulfillments from
        Returns:
            Dataframe with columns:
                flow
                resource_type
                resource_name
                fulfillment_type
                identifier_type
                identifier
                response_type
                condition
        """
        page_fulfillments = pd.DataFrame()
        page_dictionary = types.Page.to_dict(page_obj)

        entry_fulfillment = page_dictionary.get("entry_fulfillment", False)
        transition_routes = page_dictionary["transition_routes"]
        event_handlers = page_dictionary["event_handlers"]

        if entry_fulfillment:
            entry_fulfillments = self._get_entry_fulfillments(
                flow_display_name,
                page_dictionary["display_name"],
                entry_fulfillment,
            )
            page_fulfillments = pd.concat(
                [page_fulfillments, entry_fulfillments]
            )

        route_fulfillments = self._get_transition_route_fulfillments(
            flow_display_name,
            resource_type="page",
            resource_name=page_obj.display_name,
            routes=transition_routes,
        )
        event_fulfillments = self._get_event_handler_fulfillments(
            flow_display_name, page_obj.display_name, event_handlers
        )

        fulfillments = pd.concat(
            [page_fulfillments, route_fulfillments, event_fulfillments]
        )
        return fulfillments

