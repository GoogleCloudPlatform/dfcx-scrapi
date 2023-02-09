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

import time
import logging
from typing import Dict, List, Optional, Union
import pandas as pd
from collections import defaultdict

import google.cloud.dialogflowcx_v3beta1.types as dfcx_types

from dfcx_scrapi.core.scrapi_base import ScrapiBase
from dfcx_scrapi.core.intents import Intents
from dfcx_scrapi.core.entity_types import EntityTypes
from dfcx_scrapi.core.flows import Flows
from dfcx_scrapi.core.pages import Pages
from dfcx_scrapi.core.webhooks import Webhooks
from dfcx_scrapi.core.transition_route_groups import TransitionRouteGroups

# Type aliases
DFCXFlow = dfcx_types.flow.Flow
DFCXPage = dfcx_types.page.Page
DFCXRoute = dfcx_types.page.TransitionRoute

# logging config
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

# TODO: Methods to implement:
#     - Run test cases and store results, and give a report
#         - Need to include a reference agent for this to give useful info
#           about new failing test cases
#     - Get condensed changelog compared to a reference
#         - Ideally include test case changes, to include info that the CX UI
#           can't provide
#     - Find unreachable/unused pages, intents, route groups, and maybe routes
#         - Finding unreachable routes is hard, but the other problems have
#           already been figured out
#     - Find invalid test cases
#         - Test cases referencing pages or intents that don't exist,
#           for example
#     - Check true routes
#         - Pages with only conditional routes, and no intents or parameter
#           filling, should have the last route be "true" to prevent getting
#           stuck on the page
#     - Check events
#         - Pages with user input should have a no-input-default and
#           no-match-default event handler.
#         - Not sure if this applies to all agents in the same way
#     - Check infinite loops
#         - Not possible to solve in general because of webhooks,
#           but can find likely candidates
#     - Probably other things

class AgentCheckerUtil(ScrapiBase):
    """Utility class for checking DFCX Agents."""

    def __init__(
        self,
        creds_path: str = None,
        creds_dict: Dict = None,
        creds=None,
        scope=False,
        agent_id: str = None,
        delay: float = 1.0
    ):
        """
        Args:
          agent_id (required): The agent ID
          delay (optional): The time in seconds to wait between CX API calls,
            if you need to limit the rate. The number of API calls used in this
            initialization is 2*(number of flows) + 2.
        """
        super().__init__(
            creds_path=creds_path,
            creds_dict=creds_dict,
            creds=creds,
            scope=scope,
        )

        self.agent_id = agent_id
        if not self.agent_id:
            raise Exception("agent_id parameter is required")

        self._intents = Intents(creds=self.creds, agent_id=self.agent_id)
        self._entities = EntityTypes(creds=self.creds, agent_id=self.agent_id)
        self._flows = Flows(creds=self.creds, agent_id=self.agent_id)
        self._pages = Pages(creds=self.creds)
        self._webhooks = Webhooks(creds=self.creds, agent_id=self.agent_id)
        self._route_groups = TransitionRouteGroups(
            creds=self.creds, agent_id=self.agent_id
        )

        # Intent data (1 API call)
        self._intent_data = self._intents.list_intents(agent_id=self.agent_id)
        # Intents map (0 API calls)
        self._intents_map = {
            intent.name: intent.display_name for intent in self._intent_data
        }

        # Flow data (1 API call)
        self._flow_data = self._get_all_flow_data(delay)
        # Flows maps (0 API calls)
        self._flows_map = {
            flow.name: flow.display_name for flow in self._flow_data.values()
        }
        self._flows_map_rev = {
            flow.display_name: flow.name for flow in self._flow_data.values()
        }

        # Page data (len(flows) API calls)
        self._page_data = self._get_all_page_data(delay)

        # Route group data (len(flows) API calls)
        self._route_group_data = self._get_all_route_group_data(delay)

        # Pages and route groups maps (0 API calls)
        self._pages_map = {}
        self._pages_map_rev = {}
        self._route_groups_map = {}
        for fid in self._flows_map.keys():
            self._pages_map[fid] = {
                page.name: page.display_name
                for page in self._page_data[fid].values()
            }
            self._pages_map_rev[fid] = {
                page.display_name: page.name
                for page in self._page_data[fid].values()
            }
            self._route_groups_map[fid] = {
                rg.name: rg.display_name
                for rg in self._route_group_data[fid].values()
            }
        # Total API calls: 2*len(flows) + 2

    def _get_all_flow_data(self, delay):
        flow_list = self._flows.list_flows(self.agent_id)
        time.sleep(delay)
        return {flow.name: flow for flow in flow_list}

    def _get_all_page_data(self, delay):
        page_data = {}
        for flow_id in self._flows_map.keys():
            page_list = self._pages.list_pages(flow_id=flow_id)
            page_data[flow_id] = {page.name: page for page in page_list}
            time.sleep(delay)
        return page_data

    def _get_all_route_group_data(self, delay):
        route_group_data = {}
        for flow_id in self._flows_map.keys():
            group_list = self._route_groups.list_transition_route_groups(
                flow_id=flow_id
            )
            route_group_data[flow_id] = {rg.name: rg for rg in group_list}
            time.sleep(delay)
        return route_group_data

    # Conversion utilities
    # (Not currently used)

    def _convert_intent(self, intent_id):
        """Gets an intent display name from an intent ID"""
        intent_id_converted = str(self.agent_id) + "/intents/" + str(intent_id)
        return self._intents_map.get(intent_id_converted, "")

    def _convert_flow(self, flow_id):
        """Gets a flow display name from a flow ID"""
        if flow_id.split("/")[-1] == "-":
            return ""
        # flow_id_converted = str(agent_id) + '/flows/' + str(flow_id)
        return self._flows_map.get(flow_id, "Default Start Flow")
        # TODO: Should throw error instead of returning default

    # Note that flow id includes agent, normally...
    def _convert_page(self, page_id, flow_id):
        """Gets a page display name from a page and flow ID"""
        if page_id == "END_SESSION":
            return "End Session"
        elif page_id == "END_FLOW":
            return "End Flow"
        elif page_id == "START_PAGE":
            return "Start"
        page_id_converted = str(flow_id) + "/pages/" + str(page_id)
        if flow_id in self._pages_map:
            return self._pages_map[flow_id].get(page_id_converted, "Start")
        logging.info("Flow not found")
        # TODO: Should throw error, but returning this probably will anyway
        return "Invalid"

    def _get_intent_parameters(self, intent_name):
        """Gets the parameters for a particular intent, by display name"""
        for intent in self._intent_data:
            if intent.display_name == intent_name:
                return intent.parameters
        return None

    def _get_page(
        self,
        flow_name: str,
        page_name: str
    ) -> Union[DFCXPage, DFCXFlow]:
        """Gets the page data for a specified page within
        a specified flow. The flow and page can be specified
        by ID or by display name.

        Args:
          flow_name: The display name of the flow
          page_name: The display name of the page

        Returns:
          A DFCX Page object for this page,
          or DFCX Flow object if it's the start page

        Raises:
          KeyError, if the page is not found
        """
        # Look up flow ID
        flow_id = self._flows_map_rev.get(flow_name, None)
        if not flow_id:
            raise Exception(f"Flow not found: {flow_name}")
        # Now that flow_id is set, look up the page
        # Special case for the start page
        if page_name == "Start":
            return self._flow_data[flow_id]
        # Look up page ID
        page_id = self._pages_map_rev[flow_id].get(page_name, None)
        if not page_id:
            raise KeyError(f"Page not found: {page_name}")
        return self._page_data[flow_id][page_id]

    # Changelogs

    # Reachable and unreachable pages

    def _continue_page_recursion(
        self,
        page: Union[DFCXPage, DFCXFlow],
        page_name: str,
        route: DFCXRoute,
        target_page: str,
        params: Dict
    ) -> None:
        if page_name not in params["reachable"]:
            params["reachable"].append(page_name)
            params["min_intent_counts"].append(params["intent_route_count"])
        else:
            # Better route found, traverse from here
            params["min_intent_counts"][
                params["reachable"].index(page_name)
            ] = params["intent_route_count"]

        params["conversation_path"].append(page_name)
        if params["verbose"]:
            logging.info(params["conversation_path"],
                         params["intent_route_count"])

        old_presets = params["presets"].copy()
        new_presets = self._get_new_presets(params["presets"], page, route)
        if "START_PAGE" in target_page:
            next_page = self._flow_data[params["flow_id"]]
        else:
            next_page = self._page_data[params["flow_id"]][target_page]
        params["presets"] = new_presets

        self._find_reachable_pages_rec(next_page, params) # is_initial=False

        params["conversation_path"].pop(-1)
        # pop presets since we can't if we're passing a params dict like this
        params["presets"] = old_presets

    def _handle_meta_page(
        self,
        page: Union[DFCXPage, DFCXFlow],
        target_page: str,
        params: Dict
    ) -> None:
        page_name = page.display_name
        if "END_SESSION" in target_page:
            page_name = "END SESSION"
        elif "END_FLOW" in target_page:
            page_name = "END FLOW"
        elif "PREVIOUS_PAGE" in target_page:
            page_name = "PREVIOUS PAGE"
        #elif "CURRENT_PAGE" in target_page:
        #    page_name = page.display_name

        if params["verbose"]:
            logging.info(page.display_name, "->", page_name)
        # Only include the special "pages" like END SESSION
        # if the include_meta parameter is set.
        if page_name == page.display_name or params["include_meta"]:
            if page_name not in params["reachable"]:
                params["reachable"].append(page_name)
                params["min_intent_counts"].append(
                    params["intent_route_count"]
                )
            elif (
                page_name in params["reachable"]
                and params["intent_route_count"]
                < params["min_intent_counts"][
                    params["reachable"].index(page_name)
                ]
            ):
                params["min_intent_counts"][
                    params["reachable"].index(page_name)
                ] = params["intent_route_count"]

    def _find_reachable_pages_rec_helper(
        self,
        page: Union[DFCXPage, DFCXFlow],
        route: DFCXRoute,
        params: Dict,
        # Having a default of False is absolutely critical
        is_initial: bool = False
    ) -> None:
        """Helper function for the recursion involved in
        finding reachable pages
        """
        target_page = route.target_page
        target_flow = route.target_flow
        if (
            getattr(route, "intent", "") != ""
            and params["intent_route_limit"]
            and params["intent_route_count"] >= params["intent_route_limit"]
        ):
            return
        if isinstance(page, DFCXPage):
            for parameter in page.form.parameters:
                parameter_name = parameter.display_name
                # Need to also account for parameters being
                # set by intents (or by webhooks...)
                if (
                    parameter_name not in params["presets"]
                    or params["presets"][parameter_name] == "NULL"
                ):
                    # This page has an unfilled parameter
                    if (params["limit_intent_to_initial"]
                        and not is_initial
                    ):
                        return
        if getattr(route, "intent", "") != "":
            if params["limit_intent_to_initial"] and not is_initial:
                # Don't continue on this path
                return
            params["intent_route_count"] += 1
        if target_page in self._page_data[params["flow_id"]]:
            page_name = self._page_data[params["flow_id"]][
                target_page
            ].display_name
            if params["verbose"]:
                logging.info(page.display_name, "->", page_name)
            # Move to this page (this is also the recursion limiting step
            # to prevent infinite loops)
            if (
                page_name not in params["reachable"]
                or (page_name in params["reachable"]
                and params["intent_route_count"]
                < params["min_intent_counts"][
                    params["reachable"].index(page_name)
                ])
            ):
                self._continue_page_recursion(page, page_name, route,
                                              target_page, params)
        elif ("END_FLOW" in target_page
            or "END_SESSION" in target_page
            or "PREVIOUS_PAGE" in target_page
            or "CURRENT_PAGE" in target_page
        ):
            self._handle_meta_page(page, target_page, params)
        elif "START_PAGE" in target_page:
            if params["verbose"]:
                logging.info(page.display_name, "-> START PAGE")
            page_name = "Start"
            if (page_name not in params["reachable"]
                or (page_name in params["reachable"]
                and params["intent_route_count"]
                < params["min_intent_counts"][
                    params["reachable"].index(page_name)
                ])
            ):
                self._continue_page_recursion(page, page_name, route,
                                              target_page, params)
        elif len(target_page) > 0:
            logging.info(page.display_name, "->", target_page)
            # This should not happen, and if it does it needs to be fixed
            logging.error(f"Page target not in list of pages: {target_page}")
        elif len(target_flow) > 0:
            flow_name = self._flows_map[route.target_flow]
            if params["verbose"]:
                logging.info(page.display_name, "->", flow_name)
            if flow_name not in params["reachable"]:
                params["reachable"].append(flow_name)
                params["min_intent_counts"].append(
                    params["intent_route_count"]
                )
            elif (
                flow_name in params["reachable"]
                and params["intent_route_count"]
                < params["min_intent_counts"][
                    params["reachable"].index(flow_name)
                ]
            ):
                params["min_intent_counts"][
                    params["reachable"].index(flow_name)
                ] = params["intent_route_count"]
        else:
            if params["verbose"]:
                logging.info(page.display_name, "->",
                    route.target_flow, "(empty)")
            page_name = page.display_name
            if (
                page_name in params["reachable"]
                and params["intent_route_count"]
                < params["min_intent_counts"][
                    params["reachable"].index(page_name)
                ]
            ):
                params["min_intent_counts"][
                    params["reachable"].index(page_name)
                ] = params["intent_route_count"]

    def _get_new_presets(self, presets, page, route):
        """Gets parameter presets that have been added on a given route.
        """
        new_presets = presets.copy()
        if isinstance(page, DFCXPage):
            for preset in page.entry_fulfillment.set_parameter_actions:
                new_presets[preset.parameter] = preset.value
            for parameter in page.form.parameters:
                ipf = parameter.fill_behavior.initial_prompt_fulfillment
                for preset in ipf.set_parameter_actions:
                    new_presets[preset.parameter] = preset.value
        for preset in route.trigger_fulfillment.set_parameter_actions:
            new_presets[preset.parameter] = preset.value
        if getattr(route, "intent", "") != "":
            # Check the entities annotated on this intent
            intent_name = self._intents_map[route.intent]
            intent_params = self._get_intent_parameters(intent_name)
            for param in intent_params:
                new_presets[param.id] = f"(potentially set by {intent_name})"
        return new_presets

    def _find_reachable_pages_rec(
        self,
        page: Union[DFCXPage, DFCXFlow],
        params: Dict,
        # Having a default of False is absolutely critical
        is_initial: bool = False
    ) -> None:
        """Recursive function to find reachable pages within a given flow,
        starting at a particular page. Other parameters here are used for
        more general traversal options."""
        if isinstance(page, DFCXPage):
            for parameter in page.form.parameters:
                self._process_form_parameter_for_reachable_pages(
                    page,
                    parameter,
                    params,
                    is_initial=is_initial)
        for event_handler in page.event_handlers:
            if params["limit_intent_to_initial"] and not is_initial:
                continue
            if (event_handler.target_page != ""
                or event_handler.target_flow != ""):
                self._find_reachable_pages_rec_helper(page,
                                                      event_handler,
                                                      params,
                                                      is_initial=is_initial)
        for route in page.transition_routes:
            self._find_reachable_pages_rec_helper(page,
                                                  route,
                                                  params,
                                                  is_initial=is_initial)
        if params["include_groups"]:
            for route_group in page.transition_route_groups:
                for route in self._route_group_data[params["flow_id"]][
                    route_group
                ].transition_routes:
                    self._find_reachable_pages_rec_helper(page,
                                                          route,
                                                          params,
                                                          is_initial=is_initial
                    )
        # Start page routes and route groups are also accessible from this page
        if (
            params["include_start_page_routes"]
            and page.display_name != params["flow_name"]
            and (not params["limit_intent_to_initial"] or is_initial)
        ):
            self._process_start_page_routes_for_reachable_pages(params,
                is_initial=is_initial)

    def _process_form_parameter_for_reachable_pages(
        self,
        page: Union[DFCXPage, DFCXFlow],
        parameter, # TODO: Data type for DFCX Parameter
        params: Dict,
        is_initial: bool = False
    ) -> None:
        for event_handler in parameter.fill_behavior.reprompt_event_handlers:
            if params["limit_intent_to_initial"] and not is_initial:
                continue
            if (event_handler.target_page != ""
                or event_handler.target_flow != ""):
                self._find_reachable_pages_rec_helper(page,
                                                      event_handler,
                                                      params,
                                                      is_initial=is_initial)

    def _process_start_page_routes_for_reachable_pages(
        self,
        params: Dict,
        is_initial: bool = False
    ):
        page = self._flow_data[params["flow_id"]]
        for event_handler in page.event_handlers:
            if (event_handler.target_page != ""
                or event_handler.target_flow != ""):
                self._find_reachable_pages_rec_helper(page,
                                                      event_handler,
                                                      params,
                                                      is_initial=is_initial)
        for route in page.transition_routes:
            if route.intent:
                self._find_reachable_pages_rec_helper(
                    page, route, params, is_initial=is_initial)
        if params["include_groups"]:
            for route_group in page.transition_route_groups:
                for route in self._route_group_data[params["flow_id"]][
                    route_group
                ].transition_routes:
                    if route.intent:
                        self._find_reachable_pages_rec_helper(
                            page, route, params, is_initial=is_initial)

    def find_reachable_pages(
        self,
        flow_name: str,
        from_page: str = "Start",
        intent_route_limit: Optional[int] = None,
        include_groups: bool = True,
        include_start_page_routes: bool = True,
        include_meta: bool = False,
        verbose: bool = False,
    ) -> List[str]:
        """Finds all pages which are reachable by transition routes,
        starting from a given page in a given flow. Either flow_id or
        flow_name must be used.

        Args:
          flow_name: The display name of the flow.
          from_page: (Optional) The page to start from. If left blank, it will
            start on the Start Page of the given flow.
          intent_route_limit: (Optional) Default None. The maximum number of
            intent routes to take. This can be used to answer questions like
            "which pages can I reach within N turns, starting at this page?"
          include_groups: (Optional) If true, intents from transition route
            groups will be included, but only if they are actually referenced
            on each given page in the traversal.
          include_start_page_routes: (Optional) Default true. If true, intent
            routes on the start page are always considered in scope. This is
            how DFCX normally behaves.
          include_meta: (Optional) Default False. If true, includes special
            transition targets like End Session, End Flow, etc. as if they
            are actual pages.
          verbose: (Optional) If true, prints debug information about
            route traversal.

        Returns:
          The list of reachable pages in this flow
        """
        flow_id = self._flows_map_rev.get(flow_name, None)
        if not flow_id:
            raise Exception(f"Flow not found: {flow_name}")

        # Start at the start page...
        reachable = [from_page]
        conversation_path = [from_page]
        # Technically this could be [0] or [1], or very rarely more than 1,
        # depending on the routes that lead to current page...
        min_intent_counts = [25]
        presets = {}
        page_data = self._get_page(
            flow_name=flow_name,
            page_name=from_page
        )
        params = {
            "flow_id": flow_id,
            "flow_name": flow_name,
            "reachable": reachable,
            "conversation_path": conversation_path,
            "min_intent_counts": min_intent_counts,
            "presets": presets,
            "intent_route_limit": intent_route_limit,
            "intent_route_count": 0,
            "include_groups": include_groups,
            "include_start_page_routes": include_start_page_routes,
            "limit_intent_to_initial": False,
            # This can't be stored here unless I want to add a lot of complex
            # conditions to change it to False and back depending on the level
            # of recursion
            #"is_initial": True,
            "include_meta": include_meta,
            "verbose": verbose
        }
        self._find_reachable_pages_rec(page_data, params, is_initial=True)
        return reachable

    def find_unreachable_pages(
        self,
        flow_name: str,
        include_groups: bool = True,
        verbose: bool = False,
    ) -> List[str]:
        """Finds all pages which are unreachable by transition routes,
        starting from the start page of a given flow. Either flow_id or
        flow_name must be used.

        Args:
          flow_id: The ID of the flow to find unreachable pages for
          flow_name: The display name of the flow to find unreachable pages for
          include_groups: (Optional) If true, intents from transition route
            groups will be included, but only if they are actually referenced
            on some page
          verbose: (Optional) If true, print debug information about
            route traversal

        Returns:
          The list of unreachable pages in this flow
        """
        flow_id = self._flows_map_rev.get(flow_name, None)
        if not flow_id:
            raise Exception(f"Flow not found: {flow_name}")

        reachable = self.find_reachable_pages(
            flow_name, include_groups=include_groups, verbose=verbose
        )
        return list(set(self._pages_map[flow_id].values()) - set(reachable))

    def find_all_reachable_pages(
        self,
        include_groups: bool = True,
        verbose: bool = False,
    ):
        """Gets a dataframe of all reachable pages in this agent

        Args:
          include_groups: whether or not to consider route group routes
            as being reachable. Defaults to True.
          verbose: whether to display debug info in the agent structure
            traversal. Defaults to False.

        Returns:
          A dataframe with columns flow_name and page_name
        """
        flow_names = []
        page_names = []
        for flow_name in self._flows_map_rev:
            reachable = self.find_reachable_pages(
                flow_name=flow_name,
                include_groups=include_groups,
                verbose=verbose
            )
            flow_names.extend([flow_name for _ in reachable])
            page_names.extend(reachable)
        return pd.DataFrame({"flow_name": flow_names, "page_name": page_names})

    def find_all_unreachable_pages(
        self,
        include_groups: bool = True,
        verbose: bool = False,
    ):
        """Gets a dataframe of all unreachable pages in this agent

        Args:
          include_groups: whether or not to consider route group routes
            as being reachable. Defaults to True.
          verbose: whether to display debug info in the agent structure
            traversal. Defaults to False.

        Returns:
          A dataframe with columns flow_name and page_name
        """
        flow_names = []
        page_names = []
        for flow_name in self._flows_map_rev:
            unreachable = self.find_unreachable_pages(
                flow_name=flow_name,
                include_groups=include_groups,
                verbose=verbose
            )
            flow_names.extend([flow_name for _ in unreachable])
            page_names.extend(unreachable)
        return pd.DataFrame({"flow_name": flow_names, "page_name": page_names})

    def _get_intents_from_routes(
        self,
        transition_list: List[DFCXRoute],
        route_group
    ) -> Dict[str, List[str]]:
        """Helper function which adds intents from routes to a list of intents

        Args:
          transition_list: The list of transition routes
          route_group (Optional): The route group where the route is
            located.

        Returns:
          A dictionary with keys 'intents' and 'routegroups' which each contain
          a list of intent/route group names to be added
        """
        intents = []
        routegroups = []
        for route in transition_list:
            # Ignore empty intents (such as the true condition)
            if len(route.intent) == 0:
                continue
            intent = self._intents_map[route.intent]
            if intent not in intents:
                intents.append(intent)
                if route_group is not None:
                    routegroups.append(route_group.display_name)
                else:
                    routegroups.append("")
        return {
            "intents": intents,
            "routegroups": routegroups
        }

    def _get_page_intents(
        self,
        flow_name: str,
        page_name: str,
        include_groups: bool = True
    ) -> List[str]:
        """Get the list of intents for a given page of this flow.

        Args:
          flow_name: The display name of the flow
          page_name: The display name of the page
          include_groups (Optional): If true, intents from transition route
            groups on the given page will be included

        Returns:
          List of intent names
        """
        page = self._get_page(flow_name=flow_name,
                              page_name=page_name)

        page_intents = []
        page_routegroups = []
        transition_list = page.transition_routes
        route_intent_dict = self._get_intents_from_routes(transition_list,None)
        page_intents.extend(route_intent_dict["intents"])
        page_routegroups.extend(route_intent_dict["routegroups"])

        flow_id = self._flows_map_rev.get(flow_name, None)
        if not flow_id:
            raise Exception(f"Flow not found: {flow_name}")

        # Get intents in transition route groups
        if include_groups:
            for route_group_id in page.transition_route_groups:
                route_group = self._route_group_data[flow_id][route_group_id]
                route_intent_dict = self._get_intents_from_routes(
                    route_group.transition_routes,
                    route_group
                )
                page_intents.extend(route_intent_dict["intents"])
                page_routegroups.extend(route_intent_dict["routegroups"])

        return pd.DataFrame({
            "route group": page_routegroups,
            "intent": page_intents
        })

    def find_reachable_intents(
        self,
        flow_name: str,
        include_groups: bool = True
    ) -> List[str]:
        """Finds all intents which are on reachable pages, starting from the
        start page of the given flow.

        Args:
          flow_name: The name of the flow to check for reachable intents.
          include_groups (Optional): If true, intents from transition route
            groups will be included, but only if they are actually referenced
            on some page.

        Returns:
          The list of intents on reachable pages in this flow
        """
        intents = set()
        reachable_pages = self.find_reachable_pages(
            flow_name=flow_name,
            include_groups=include_groups)
        for page_name in reachable_pages:
            if page_name not in self._flows_map_rev:
                page_intents = set(self._get_page_intents(
                    flow_name=flow_name,
                    page_name=page_name,
                    include_groups=include_groups
                )["intent"])
            intents.update(page_intents)
        return list(intents)

    def find_all_reachable_intents(self) -> pd.DataFrame:
        """Finds all intents referenced in the agent, across all flows,
        and produces a dataframe listing which flows reference each intent.

        Returns:
            A dataframe with columns
            intent - the intent display name
            flows - a list of flow display names that use this intent
        """
        intents = defaultdict(lambda: [])
        for flow_name in self._flows_map_rev:
            flow_intents = self.find_reachable_intents(flow_name=flow_name,
                                                       include_groups=True)
            for intent in flow_intents:
                intents[intent].append(flow_name)

        return pd.DataFrame({
            "intent": intents.keys(),
            "flows": intents.values()
        })

    def find_all_unreachable_intents(self) -> List[str]:
        """Finds all unreachable intents, either because they are on
        unreachable pages or they are unused in the agent. Note that
        Default Negative Intent will always show up here.

        Returns:
            A list of unreachable intent display names
        """
        all_reachable_intents = set()
        for flow_name in self._flows_map_rev:
            flow_intents = self.find_reachable_intents(flow_name=flow_name,
                                                       include_groups=True)
            all_reachable_intents.update(set(flow_intents))
        all_intents = {intent.display_name for intent in self._intent_data}
        return all_intents - all_reachable_intents
