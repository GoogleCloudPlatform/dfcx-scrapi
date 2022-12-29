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
            creds=self.creds, agent_id=self.agent_id
        )
        self.test_cases = TestCases(creds=self.creds, agent_id=self.agent_id)

        # Generate maps
        self.intents_map = self.intents.get_intents_map(agent_id=self.agent_id)
        self.flows_map = self.flows.get_flows_map(agent_id=self.agent_id)
        self.flows_map_rev = self.flows.get_flows_map(
            agent_id=self.agent_id, reverse=True
        )
        self.pages_map = {}
        for flow_id in self.flows_map.keys():
            self.pages_map[flow_id] = self.pages.get_pages_map(flow_id=flow_id)
        self.pages_map_rev = {}
        for flow_id in self.flows_map.keys():
            self.pages_map_rev[flow_id] = self.pages.get_pages_map(
                flow_id=flow_id, reverse=True
            )
        self.route_groups_map = {}
        for fid in self.flows_map.keys():
            self.route_groups_map[fid] = self.route_groups.get_route_groups_map(
                flow_id=fid
            )

        # Get intent, flow, and page data
        self.intent_data = self.intents.list_intents(agent_id=self.agent_id)
        self.flow_data = self.get_all_flow_data()
        self.page_data = self.get_all_page_data()
        self.route_group_data = self.get_all_route_group_data()

    def get_all_flow_data(self):
        flow_data = {}
        flow_list = self.flows.list_flows(self.agent_id)
        for flow in flow_list:
            flow_data[flow.name] = flow
        return flow_data

    def get_all_page_data(self):
        page_data = {}
        for flow_id in self.flows_map.keys():
            page_list = self.pages.list_pages(flow_id=flow_id)
            page_data[flow_id] = {page.name: page for page in page_list}
        return page_data

    def get_all_route_group_data(self):
        route_group_data = {}
        for flow_id in self.flows_map.keys():
            group_list = self.route_groups.list_transition_route_groups(
                flow_id=flow_id
            )
            route_group_data[flow_id] = {rg.name: rg for rg in group_list}
        return route_group_data

    # Conversion utilities

    def _convert_intent(self, intent_id):
        """Gets an intent display name from an intent ID"""
        intent_id_converted = str(self.agent_id) + "/intents/" + str(intent_id)
        if intent_id_converted in self.intents_map:
            return self.intents_map[intent_id_converted]
        return ""

    def _convert_flow(self, flow_id):
        """Gets a flow display name from a flow ID"""
        if flow_id.split("/")[-1] == "-":
            return ""
        # flow_id_converted = str(agent_id) + '/flows/' + str(flow_id)
        if flow_id in self.flows_map:
            return self.flows_map[flow_id]
        # TODO: Should throw error instead of returning default
        return "Default Start Flow"

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
        if flow_id in self.pages_map:
            if page_id_converted in self.pages_map[flow_id]:
                return self.pages_map[flow_id][page_id_converted]
            else:
                # TODO: Should throw error instead of returning default
                return "Start"
        print("Flow not found")
        # TODO: Should throw error, but returning this probably will anyway
        return "Invalid"

    def _get_intent_parameters(self, intent_name):
        """Gets the parameters for a particular intent, by display name"""
        for intent in self.intent_data:
            if intent.display_name == intent_name:
                return intent.parameters
        return None

    def _get_page(
        self,
        flow_id: str = None,
        flow_name: str = None,
        page_id: str = None,
        page_name: str = None,
    ) -> DFCXPage | DFCXFlow:
        """Gets the page data for a specified page within
        a specified flow. The flow and page can be specified
        by ID or by display name.

        Args:
          flow_id OR flow_name: The ID or display name of the flow
          page_id OR page_name: The ID or display name of the page

        Returns:
          A DFCX Page object for this page,
          or DFCX Flow object if it's the start page

        Raises:
          KeyError, if the page is not found
        """
        if flow_id is None and flow_name is None:
            raise Exception("Please specify a flow")
        elif flow_name is not None:
            if flow_name in self.flows_map_rev:
                flow_id = self.flows_map_rev[flow_name]
            else:
                raise Exception(f"Flow not found: {flow_name}")
        # Now that flow_id is set, look up the page
        if page_id is None and page_name is None:
            raise Exception("Please specify a page")
        elif page_name is not None:
            if page_name == "Start":
                return self.flow_data[flow_id]
            if page_name in self.pages_map_rev[flow_id]:
                page_id = self.pages_map_rev[flow_id][page_name]
                return self.page_data[flow_id][page_id]
            else:
                raise KeyError('Page not found. Did you forget "page_name="?')
        else:
            if "START_PAGE" in page_id:
                return self.flow_data[flow_id]
            elif page_id not in self.pages_map[flow_id]:
                raise KeyError("Page not found.")
            else:
                return self.page_data[flow_id][page_id]

    # Changelogs

    # Reachable and unreachable pages

    def _find_reachable_pages_rec_helper(
        self,
        flow_id: str,
        flow_name: str,
        page: DFCXPage | DFCXFlow,
        route: DFCXRoute,
        reachable: List[str],
        conversation_path: List[str],
        min_intent_counts: List[int],
        presets: Dict[str, str],
        intent_route_count: int = 0,
        intent_route_limit: Optional[int] = None,
        include_groups: bool = True,
        include_start_page_routes: bool = True,
        limit_intent_to_initial: bool = False,
        is_initial: bool = False,
        include_meta: bool = False,
        verbose: bool = False,
    ) -> None:
        """Helper function for the recursion involved in
        finding reachable pages
        """
        if not flow_name:
            flow_name = self.flows_map[flow_id]
        target_page = route.target_page
        target_flow = route.target_flow
        if (
            hasattr(route, "intent") and route.intent != ""
            and intent_route_limit and intent_route_count >= intent_route_limit
        ):
            return
        if hasattr(page, "form") and page.form:
            for parameter in page.form.parameters:
                parameter_name = parameter.display_name
                # Need to also account for parameters being
                # set by intents (or by webhooks...)
                if (
                    parameter_name not in presets
                    or presets[parameter_name] == "NULL"
                ):
                    # This page has an unfilled parameter
                    if limit_intent_to_initial and not is_initial:
                        return
        if hasattr(route, "intent") and route.intent != "":
            if limit_intent_to_initial and not is_initial:
                # Don't continue on this path
                return
            intent_route_count += 1
        if target_page in self.page_data[flow_id]:
            page_name = self.page_data[flow_id][target_page].display_name
            if verbose:
                print(page.display_name, "->", page_name)
            # Move to this page (this is also the recursion limiting step
            # to prevent infinite loops)
            if page_name not in reachable:
                reachable.append(page_name)
                min_intent_counts.append(intent_route_count)
                conversation_path.append(page_name)
                if verbose:
                    print(conversation_path, intent_route_count)

                new_presets = self._get_new_presets(presets, page, route)

                self._find_reachable_pages_rec(
                    flow_id,
                    flow_name,
                    self.page_data[flow_id][target_page],
                    reachable,
                    conversation_path,
                    min_intent_counts,
                    new_presets,
                    intent_route_count=intent_route_count,
                    intent_route_limit=intent_route_limit,
                    include_groups=include_groups,
                    include_start_page_routes=include_start_page_routes,
                    limit_intent_to_initial=limit_intent_to_initial,
                    is_initial=False,
                    include_meta=include_meta,
                    verbose=verbose,
                )
                conversation_path.pop(-1)
            elif (
                page_name in reachable
                and intent_route_count
                < min_intent_counts[reachable.index(page_name)]
            ):
                # Better route found, traverse from here
                min_intent_counts[reachable.index(page_name)]=intent_route_count
                conversation_path.append(page_name)
                if verbose:
                    print(conversation_path, intent_route_count)

                new_presets = self._get_new_presets(presets, page, route)

                self._find_reachable_pages_rec(
                    flow_id,
                    flow_name,
                    self.page_data[flow_id][target_page],
                    reachable,
                    conversation_path,
                    min_intent_counts,
                    new_presets,
                    intent_route_count=intent_route_count,
                    intent_route_limit=intent_route_limit,
                    include_groups=include_groups,
                    include_start_page_routes=include_start_page_routes,
                    limit_intent_to_initial=limit_intent_to_initial,
                    is_initial=False,
                    include_meta=include_meta,
                    verbose=verbose,
                )
                conversation_path.pop(-1)
        elif "END_FLOW" in target_page:
            if verbose:
                print(page.display_name, "-> END FLOW")
            if include_meta:
                page_name = "END FLOW"
                if page_name not in reachable:
                    reachable.append(page_name)
                    min_intent_counts.append(intent_route_count)
                elif (
                    page_name in reachable
                    and intent_route_count
                    < min_intent_counts[reachable.index(page_name)]
                ):
                    min_intent_counts[
                        reachable.index(page_name)
                    ] = intent_route_count
            # reachable.append('END FLOW')
        elif "END_SESSION" in target_page:
            if verbose:
                print(page.display_name, "-> END SESSION")
            if include_meta:
                page_name = "END SESSION"
                if page_name not in reachable:
                    reachable.append(page_name)
                    min_intent_counts.append(intent_route_count)
                elif (
                    page_name in reachable
                    and intent_route_count
                    < min_intent_counts[reachable.index(page_name)]
                ):
                    min_intent_counts[
                        reachable.index(page_name)
                    ] = intent_route_count
            # reachable.append('END SESSION')
        elif "CURRENT_PAGE" in target_page:
            if verbose:
                print(page.display_name, "-> CURRENT PAGE")
            page_name = page.display_name
            if (
                page_name in reachable
                and intent_route_count
                < min_intent_counts[reachable.index(page_name)]
            ):
                min_intent_counts[reachable.index(page_name)]=intent_route_count
        elif "PREVIOUS_PAGE" in target_page:
            if verbose:
                print(page.display_name, "-> PREVIOUS PAGE")
            if include_meta:
                page_name = "PREVIOUS PAGE"
                if page_name not in reachable:
                    reachable.append(page_name)
                    min_intent_counts.append(intent_route_count)
                elif (
                    page_name in reachable
                    and intent_route_count
                    < min_intent_counts[reachable.index(page_name)]
                ):
                    min_intent_counts[
                        reachable.index(page_name)
                    ] = intent_route_count
            # TODO: This could cause huge problems...
        elif "START_PAGE" in target_page:
            if verbose:
                print(page.display_name, "-> START PAGE")
            page_name = "Start"
            if page_name not in reachable:
                reachable.append(page_name)
                min_intent_counts.append(intent_route_count)
                conversation_path.append(page_name)
                if verbose:
                    print(conversation_path, intent_route_count)

                new_presets = self._get_new_presets(presets, page, route)

                self._find_reachable_pages_rec(
                    flow_id,
                    flow_name,
                    self.flow_data[flow_id],
                    reachable,
                    conversation_path,
                    min_intent_counts,
                    new_presets,
                    intent_route_count=intent_route_count,
                    intent_route_limit=intent_route_limit,
                    include_groups=include_groups,
                    include_start_page_routes=include_start_page_routes,
                    limit_intent_to_initial=limit_intent_to_initial,
                    is_initial=False,
                    include_meta=include_meta,
                    verbose=verbose,
                )
                conversation_path.pop(-1)
            elif (
                page_name in reachable
                and intent_route_count
                < min_intent_counts[reachable.index(page_name)]
            ):
                # Better route found, traverse from here
                min_intent_counts[reachable.index(page_name)]=intent_route_count
                conversation_path.append(page_name)
                if verbose:
                    print(conversation_path, intent_route_count)

                new_presets = self._get_new_presets(presets, page, route)

                self._find_reachable_pages_rec(
                    flow_id,
                    flow_name,
                    self.flow_data[flow_id],
                    reachable,
                    conversation_path,
                    min_intent_counts,
                    new_presets,
                    intent_route_count=intent_route_count,
                    intent_route_limit=intent_route_limit,
                    include_groups=include_groups,
                    include_start_page_routes=include_start_page_routes,
                    limit_intent_to_initial=limit_intent_to_initial,
                    is_initial=False,
                    include_meta=include_meta,
                    verbose=verbose,
                )
                conversation_path.pop(-1)
        elif len(target_page) > 0:
            print(page.display_name, "->", target_page)
            # This should not happen, and if it does it needs to be fixed
            input()
        elif len(target_flow) > 0:
            flow_name = self.flows_map[route.target_flow]
            if verbose:
                print(page.display_name, "->", flow_name)
            if flow_name not in reachable:
                reachable.append(flow_name)
                min_intent_counts.append(intent_route_count)
            elif (
                flow_name in reachable
                and intent_route_count
                < min_intent_counts[reachable.index(flow_name)]
            ):
                min_intent_counts[reachable.index(flow_name)]=intent_route_count
        else:
            if verbose:
                print(page.display_name, "->", route.target_flow, "(empty)")
            page_name = page.display_name
            if (
                page_name in reachable
                and intent_route_count
                < min_intent_counts[reachable.index(page_name)]
            ):
                min_intent_counts[reachable.index(page_name)]=intent_route_count

    def _get_new_presets(self, presets, page, route):
        new_presets = presets.copy()
        if hasattr(page, "entry_fulfillment"):
            if hasattr(page.entry_fulfillment, "set_parameter_actions"):
                for (
                    param_preset
                ) in page.entry_fulfillment.set_parameter_actions:
                    new_presets[param_preset.parameter] = param_preset.value
        if hasattr(page, "form"):
            for parameter in page.form.parameters:
                if (hasattr(parameter, "fill_behavior")
                    and hasattr(
                        parameter.fill_behavior,
                        "initial_prompt_fulfillment",
                    )
                    and hasattr(
                        parameter.fill_behavior.initial_prompt_fulfillment,
                        "set_parameter_actions",
                    )
                ):
                    ipf = parameter.fill_behavior.initial_prompt_fulfillment
                    for param_preset in ipf.set_parameter_actions:
                        new_presets[
                            param_preset.parameter
                        ] = param_preset.value
        if hasattr(route, "trigger_fulfillment"):
            if hasattr(route.trigger_fulfillment, "set_parameter_actions"):
                for (
                    param_preset
                ) in route.trigger_fulfillment.set_parameter_actions:
                    new_presets[param_preset.parameter] = param_preset.value
        if hasattr(route, "intent") and route.intent != "":
            # Check the entities annotated on this intent
            intent_name = self.intents_map[route.intent]
            intent_params = self._get_intent_parameters(intent_name)
            for param in intent_params:
                new_presets[
                    param.id
                ] = f"(potentially set by {intent_name})"
        return new_presets

    def _find_reachable_pages_rec(
        self,
        flow_id: str,
        flow_name: str,
        page: DFCXPage | DFCXFlow,
        reachable: List[str],
        conversation_path: List[str],
        min_intent_counts: List[int],
        presets: Dict[str, str],
        intent_route_count: int = 0,
        intent_route_limit: Optional[int] = None,
        include_groups: bool = True,
        include_start_page_routes: bool = True,
        limit_intent_to_initial: bool = False,
        is_initial: bool = False,
        include_meta: bool = False,
        verbose: bool = False,
    ) -> None:
        """Recursive function to find reachable pages within a given flow,
        starting at a particular page. Other parameters here are used for
        more general traversal, but not currently used."""
        if not flow_name:
            flow_name = self.flows_map[flow_id]
        if hasattr(page, "form") and page.form:
            for parameter in page.form.parameters:
                self._process_form_parameter_for_reachable_pages(
                    flow_id,
                    flow_name,
                    page,
                    parameter,
                    reachable,
                    conversation_path,
                    min_intent_counts,
                    presets,
                    intent_route_count=intent_route_count,
                    intent_route_limit=intent_route_limit,
                    include_groups=include_groups,
                    include_start_page_routes=include_start_page_routes,
                    limit_intent_to_initial=limit_intent_to_initial,
                    is_initial=is_initial,
                    include_meta=include_meta,
                    verbose=verbose,
                )
        for event_handler in page.event_handlers:
            if limit_intent_to_initial and not is_initial:
                continue
            if hasattr(event_handler, "target_page") or hasattr(
                event_handler, "target_flow"
            ):
                self._find_reachable_pages_rec_helper(
                    flow_id,
                    flow_name,
                    page,
                    event_handler,
                    reachable,
                    conversation_path,
                    min_intent_counts,
                    presets,
                    intent_route_count=intent_route_count,
                    intent_route_limit=intent_route_limit,
                    include_groups=include_groups,
                    include_start_page_routes=include_start_page_routes,
                    limit_intent_to_initial=limit_intent_to_initial,
                    is_initial=is_initial,
                    include_meta=include_meta,
                    verbose=verbose,
                )
        for route in page.transition_routes:
            self._find_reachable_pages_rec_helper(
                flow_id,
                flow_name,
                page,
                route,
                reachable,
                conversation_path,
                min_intent_counts,
                presets,
                intent_route_count=intent_route_count,
                intent_route_limit=intent_route_limit,
                include_groups=include_groups,
                include_start_page_routes=include_start_page_routes,
                limit_intent_to_initial=limit_intent_to_initial,
                is_initial=is_initial,
                include_meta=include_meta,
                verbose=verbose,
            )
        if include_groups:
            for route_group in page.transition_route_groups:
                # TODO: Need to map by flow
                for route in self.route_group_data[flow_id][
                    route_group
                ].transition_routes:
                    self._find_reachable_pages_rec_helper(
                        flow_id,
                        flow_name,
                        page,
                        route,
                        reachable,
                        conversation_path,
                        min_intent_counts,
                        presets,
                        intent_route_count=intent_route_count,
                        intent_route_limit=intent_route_limit,
                        include_groups=include_groups,
                        include_start_page_routes=include_start_page_routes,
                        limit_intent_to_initial=limit_intent_to_initial,
                        is_initial=is_initial,
                        include_meta=include_meta,
                        verbose=verbose,
                    )
        # Start page routes and route groups are also accessible from this page
        if (
            include_start_page_routes
            and page.display_name != flow_name
            and (not limit_intent_to_initial or is_initial)
        ):
            self._process_start_page_routes_for_reachable_pages(
                flow_id,
                flow_name,
                reachable,
                conversation_path,
                min_intent_counts,
                presets,
                intent_route_count=intent_route_count,
                intent_route_limit=intent_route_limit,
                include_groups=include_groups,
                include_start_page_routes=include_start_page_routes,
                limit_intent_to_initial=limit_intent_to_initial,
                is_initial=is_initial,
                include_meta=include_meta,
                verbose=verbose,
            )

    def _process_form_parameter_for_reachable_pages(
        self,
        flow_id: str,
        flow_name: str,
        page: DFCXPage | DFCXFlow,
        parameter, # TODO: Data type for DFCX Parameter
        reachable: List[str],
        conversation_path: List[str],
        min_intent_counts: List[int],
        presets: Dict[str, str],
        intent_route_count: int = 0,
        intent_route_limit: Optional[int] = None,
        include_groups: bool = True,
        include_start_page_routes: bool = True,
        limit_intent_to_initial: bool = False,
        is_initial: bool = False,
        include_meta: bool = False,
        verbose: bool = False,
    ) -> None:
        for event_handler in parameter.fill_behavior.reprompt_event_handlers:
            if limit_intent_to_initial and not is_initial:
                continue
            if hasattr(event_handler, "target_page") or hasattr(
                event_handler, "target_flow"
            ):
                self._find_reachable_pages_rec_helper(
                    flow_id,
                    flow_name,
                    page,
                    event_handler,
                    reachable,
                    conversation_path,
                    min_intent_counts,
                    presets,
                    intent_route_count=intent_route_count,
                    intent_route_limit=intent_route_limit,
                    include_groups=include_groups,
                    include_start_page_routes=include_start_page_routes,
                    limit_intent_to_initial=limit_intent_to_initial,
                    is_initial=is_initial,
                    include_meta=include_meta,
                    verbose=verbose,
                )

    def _process_start_page_routes_for_reachable_pages(
        self,
        flow_id: str,
        flow_name: str,
        reachable: List[str],
        conversation_path: List[str],
        min_intent_counts: List[int],
        presets: Dict[str, str],
        intent_route_count: int = 0,
        intent_route_limit: Optional[int] = None,
        include_groups: bool = True,
        include_start_page_routes: bool = True,
        limit_intent_to_initial: bool = False,
        is_initial: bool = False,
        include_meta: bool = False,
        verbose: bool = False,
    ):
        for event_handler in self.flow_data[flow_id].event_handlers:
            if hasattr(event_handler, "target_page") or hasattr(
                event_handler, "target_flow"
            ):
                self._find_reachable_pages_rec_helper(
                    flow_id,
                    flow_name,
                    self.flow_data[flow_id],
                    event_handler,
                    reachable,
                    conversation_path,
                    min_intent_counts,
                    presets,
                    intent_route_count=intent_route_count,
                    intent_route_limit=intent_route_limit,
                    include_groups=include_groups,
                    include_start_page_routes=include_start_page_routes,
                    limit_intent_to_initial=limit_intent_to_initial,
                    is_initial=is_initial,
                    include_meta=include_meta,
                    verbose=verbose,
                )
        for route in self.flow_data[flow_id].transition_routes:
            if hasattr(route, "intent") and route.intent != "":
                self._find_reachable_pages_rec_helper(
                    flow_id,
                    flow_name,
                    self.flow_data[flow_id],
                    route,
                    reachable,
                    conversation_path,
                    min_intent_counts,
                    presets,
                    intent_route_count=intent_route_count,
                    intent_route_limit=intent_route_limit,
                    include_groups=include_groups,
                    include_start_page_routes=include_start_page_routes,
                    limit_intent_to_initial=limit_intent_to_initial,
                    is_initial=is_initial,
                    include_meta=include_meta,
                    verbose=verbose,
                )
        if include_groups:
            for route_group in self.flow_data[flow_id].transition_route_groups:
                for route in self.route_group_data[flow_id][
                    route_group
                ].transition_routes:
                    if hasattr(route, "intent") and route.intent != "":
                        self._find_reachable_pages_rec_helper(
                            flow_id,
                            flow_name,
                            self.flow_data[flow_id],
                            route,
                            reachable,
                            conversation_path,
                            min_intent_counts,
                            presets,
                            intent_route_count=intent_route_count,
                            intent_route_limit=intent_route_limit,
                            include_groups=include_groups,
                            include_start_page_routes=include_start_page_routes,
                            limit_intent_to_initial=limit_intent_to_initial,
                            is_initial=is_initial,
                            include_meta=include_meta,
                            verbose=verbose,
                        )

    def find_reachable_pages(
        self,
        flow_id: str = None,
        flow_name: str = None,
        from_page: str = "Start",
        intent_route_limit: Optional[int] = None,
        include_groups: bool = True,
        include_start_page_routes: bool = True,
        limit_intent_to_initial: bool = False,
        is_initial: bool = True,
        include_meta: bool = False,
        verbose: bool = False,
    ) -> List[str]:
        """Finds all pages which are reachable by transition routes,
        starting from a given page in a given flow. Either flow_id or
        flow_name must be used.

        Args:
          flow_id OR flow_name: The ID or name of the flow
          from_page: (Optional) The page to start from. If left blank, it will
            start on the Start Page
          intent_route_limit: (Optional) Default None
          include_groups: (Optional) If true, intents from transition route
            groups will be included, but only if they are actually referenced
            on some page
          include_start_page_routes: (Optional) Default true
          limit_intent_to_initial: (Optional) Default False
          is_initial: (Optional) Default True
          include_meta: (Optional) Default False
          verbose: (Optional) If true, print debug information about
            route traversal

        Returns:
          The list of reachable pages in this flow
        """
        if not flow_id:
            if not flow_name:
                raise Exception("One of flow_id or flow_name must be set")
            if flow_name in self.flows_map_rev:
                flow_id = self.flows_map_rev[flow_name]
            else:
                raise Exception(f"Flow not found: {flow_name}")
        if flow_id in self.flows_map:
            flow_name = self.flows_map[flow_id]
        else:
            raise Exception(f"Flow not found: {flow_id}")

        # Start at the start page...
        reachable = [from_page]
        conversation_path = [from_page]
        # Technically this could be [0] or [1], or very rarely more than 1,
        # depending on the routes that lead to current page...
        min_intent_counts = [25]
        presets = {}
        page_data = self._get_page(
            flow_id=flow_id, flow_name=flow_name,
            page_id=None, page_name=from_page
        )
        self._find_reachable_pages_rec(
            flow_id,
            flow_name,
            page_data,
            reachable,
            conversation_path,
            min_intent_counts,
            presets,
            intent_route_count=0,
            intent_route_limit=intent_route_limit,
            include_groups=include_groups,
            include_start_page_routes=include_start_page_routes,
            limit_intent_to_initial=limit_intent_to_initial,
            is_initial=is_initial,
            include_meta=include_meta,
            verbose=verbose,
        )
        return reachable

    def find_unreachable_pages(
        self,
        flow_id: str = None,
        flow_name: str = None,
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
        if not flow_id:
            if not flow_name:
                raise Exception("One of flow_id or flow_name must be set")
            if flow_name in self.flows_map_rev:
                flow_id = self.flows_map_rev[flow_name]
            else:
                raise Exception(f"Flow not found: {flow_name}")
        if flow_id in self.flows_map:
            flow_name = self.flows_map[flow_id]
        else:
            raise Exception(f"Flow not found: {flow_id}")

        reachable = self.find_reachable_pages(
            flow_id, flow_name, include_groups=include_groups, verbose=verbose
        )
        return list(set(self.pages_map[flow_id].values()) - set(reachable))

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
        for flow_id, flow_name in self.flows_map.items():
            reachable = self.find_reachable_pages(
                flow_id=flow_id,
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
        for flow_id, flow_name in self.flows_map.items():
            unreachable = self.find_unreachable_pages(
                flow_id=flow_id,
                include_groups=include_groups,
                verbose=verbose
            )
            flow_names.extend([flow_name for _ in unreachable])
            page_names.extend(unreachable)
        return pd.DataFrame({"flow_name": flow_names, "page_name": page_names})

    def add_intents_from_routes(self,
                                transition_list: List[DFCXRoute],
                                intents: List[str],
                                routegroups: List[str],
                                route_group
    ) -> None:
        """Helper function which adds intents from routes to a list of intents

        Args:
          transition_list, The list of transition routes
          intents, The list of intent names

        Returns:
          Nothing (appends to the intent list)
        """
        for route in transition_list:
            # Ignore empty intents (such as the true condition)
            if len(route.intent) == 0:
                continue
            intent = self.intents_map[route.intent]
            if intent not in intents:
                intents.append(intent)
                if route_group is not None:
                    routegroups.append(route_group.display_name)
                else:
                    routegroups.append("")

    def _get_page_intents(self,
                         flow_id: Optional[str] = None,
                         flow_name: Optional[str] = None,
                         page_id: Optional[str] = None,
                         page_name: Optional[str] = None,
                         include_groups: bool = True
    ) -> List[str]:
        """Get the list of intents for a given page of this flow.

        Args:
          flow_id OR flow_name: The ID or name of the flow
          page_id OR page_name: The ID or name of the page
          include_groups (Optional): If true, intents from transition route
            groups on the given page will be included

        Returns:
          List of intent names
        """
        page = self._get_page(flow_id=flow_id, flow_name=flow_name,
                             page_id=page_id, page_name=page_name)

        page_routegroups = []
        page_intents = []
        transition_list = page.transition_routes
        self.add_intents_from_routes(transition_list,
                                     page_intents,
                                     page_routegroups,
                                     None)

        if not flow_id:
            flow_id = self.flows_map_rev[flow_name]

        # Get intents in transition route groups
        if include_groups:
            for route_group_id in page.transition_route_groups:
                route_group = self.route_group_data[flow_id][route_group_id]
                self.add_intents_from_routes(route_group.transition_routes,
                                         page_intents,
                                         page_routegroups,
                                         route_group)

        return pd.DataFrame({
            "route group": page_routegroups,
            "intent": page_intents
        })

    def find_reachable_intents(self,
                               flow_name,
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
            if page_name not in self.flows_map_rev:
                page_intents = set(self._get_page_intents(
                    flow_name=flow_name,
                    page_name=page_name,
                    include_groups=include_groups
                )["intent"])
            intents |= page_intents
        return list(intents)

    def find_all_reachable_intents(self) -> pd.DataFrame:
        """Finds all intents referenced in the agent, across all flows,
        and produces a dataframe listing which flows reference each intent.

        Returns:
            A dataframe with columns
            intent - the intent display name
            flows - a list of flow display names that use this intent
        """
        intents = {}
        for flow_name in self.flows_map_rev:
            flow_intents = self.find_reachable_intents(flow_name=flow_name,
                                                       include_groups=True)
            for intent in flow_intents:
                if intent in intents:
                    intents[intent].append(flow_name)
                else:
                    intents[intent] = [flow_name]
        # Also return the unreachable ones, because why not
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
        for flow_name in self.flows_map_rev:
            flow_intents = self.find_reachable_intents(flow_name=flow_name,
                                                       include_groups=True)
            all_reachable_intents |= set(flow_intents)
        unreachable_intents = []
        for intent in self.intent_data:
            if intent.display_name in all_reachable_intents:
                continue
            unreachable_intents.append(intent.display_name)
        return unreachable_intents
