"""Flow extract methods and functions."""

# Copyright 2023 Google LLC
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

import json
import os

from typing import List

from dfcx_scrapi.agent_extract import graph
from dfcx_scrapi.agent_extract import common
from dfcx_scrapi.agent_extract import types
from dfcx_scrapi.agent_extract import pages
from dfcx_scrapi.agent_extract import routes
from dfcx_scrapi.agent_extract import route_groups


class Flows:
    """Flow processing methods and functions."""

    def __init__(self):
        self.common = common.Common()
        self.pages = pages.Pages()
        self.rgs = route_groups.RouteGroups()
        self.routes = routes.Fulfillments()
        self.special_pages = [
            "End Session",
            "End Flow",
            "Start Page",
            "Current Page",
            "Previous Page",
        ]

    @staticmethod
    def build_flow_path_list(agent_local_path: str):
        """Builds a list of dirs, each representing a Flow directory.

        Ex: /path/to/agent/flows/<flow_dir>

        This dir path can then be used to find the next level of information
        in the directory by appending the appropriate next dir structures like:
        - <flow_name>.json, for the Flow object
        - /transitionRouteGroups, for the Route Groups dir
        - /pages, for the Pages dir
        """
        root_dir = agent_local_path + "/flows"

        flow_paths = []

        for flow_dir in os.listdir(root_dir):
            flow_dir_path = f"{root_dir}/{flow_dir}"
            flow_paths.append(flow_dir_path)

        return flow_paths

    @staticmethod
    def remove_flow_pages_from_set(input_set: set) -> set:
        """Remove any transitions tagged with FLOW.

        Some route transitions go to Flow instead of Page. For these
        transitions, we tag them with `FLOW` for easier identification later.
        However, when reporting on Graph inconsistencies like Dangling or
        Unreachable pages, we want to remove these from any result sets as they
        are not relevant.
        """
        filtered_set = set()

        for page in input_set:
            if "FLOW" not in page:
                filtered_set.add(page)

        return filtered_set

    def find_unreachable_pages(self, flow: types.Flow):
        """Find Unreachable Pages in the graph.

        An Unreachable Page is defined as:
          - A Page which has no incoming edge when traversed from Start Page.
            That is, it is unreachable in the graph by any practical means.
          - A Page which is connected to a root unreachable page. That is, a
            page that could have both incoming or outgoing routes, but due to
            its connectedness to the root orphan page, is unreachable in the
            graph.

        Here we will compute the symmetric difference of 2 sets:
          - Active Pages (i.e. Pages that were reachable in the graph)
          - Used Pages (i.e. Pages that were used by some Route)

        If an Unreachable Page has children that it routes to, those children
        will appear in Used Pages, although they will ultimately be
        unreachable. It's possible for an Unreachable Page to route back to an
        Active Page in the graph. For these instances, we don't want to count
        those pages as unreachable, because they are reachable via other
        sections of the graph.
        """
        filtered_set = flow.active_pages.symmetric_difference(
            flow.graph.used_nodes
        )
        filtered_set = self.remove_flow_pages_from_set(filtered_set)
        flow.unreachable_pages.update(filtered_set)

        return flow

    def find_unused_pages(self, flow: types.Flow):
        """Find Unused Pages in the graph.

        An Unused Page is defined as:
          - A Page which has no incoming or outgoing edge AND
          - A Page which exists in the Agent design time, but which is not
            present anywhere in the graph, either visible or non-visible.

        Here we will compute the difference of 2 sets:
          - All Pages (i.e. Pages that exist in the Agent Design Time)
          - Used Pages (i.e. Pages that were used by some Route)

        The resulting set will consist of 2 types of Pages:
          - Truly Unused Pages
          - Unreachable Root Pages

        Unreachable Root Pages end up in the results due to the fact that no
        other Active Page is pointing to them. We remove these from the
        resulting set before presenting the Truly Unused Pages.
        """

        # Discard special pages as they are non-relevant for final outcome
        for page in self.special_pages:
            flow.all_pages.discard(page)

        prelim_unused = flow.all_pages.difference(flow.graph.used_nodes)

        # Filter out Unreachable Root Pages
        filtered_set = set()

        for page in prelim_unused:
            if page not in flow.graph.edges:
                filtered_set.add(page)
            else:
                flow.unreachable_pages.add(page)

        flow.unused_pages = filtered_set

        return flow

    def recurse_edges(
        self, edges: List, page: types.Page, dangling: set, visited: set
    ):
        """Recursive method searching graph edges for Active / Dangling Pages.

        A byproduct of searching for Dangling Pages in the graph is that we can
        produce a set of Active Pages in the graph. These are pages that are
        reachable when traversing from the Start Page. These can then be used
        to determine Unreachable Pages in another method.
        """
        # For Flow Start Pages, we prepend the Flow name for later
        # identification. For this section, we'll need to strip it off to
        # compare with the other sets.
        if page in edges:
            for inner_page in edges[page]:
                if inner_page not in visited:
                    visited.add(inner_page)
                    dangling, visited = self.recurse_edges(
                        edges, inner_page, dangling, visited
                    )

        else:
            dangling.add(page)

        return dangling, visited

    def find_dangling_pages(self, flow: types.Flow):
        """Find Dangling Pages in the graph.

        Dangling Page is defined as:
          - Any page that exists in the graph that has no outgoing edge
        Active Page is defined as:
          - Any page that is reachable via an active route in the graph and can
            be traced back to the Start Page.

        These pages can result in a conversational "dead end" which is
        potentially unrecoverable.
        A byproduct of searching for the dangling pages is locating all of the
        "active" pages. These are the pages that are "visited" as we traverse
        the graph. We'll also return Active Pages in this method since they
        will be used for downstream tasks.
        """

        flow.dangling_pages, flow.active_pages = self.recurse_edges(
            flow.graph.edges,
            f"{flow.display_name}: Start Page",
            flow.dangling_pages,
            flow.active_pages,
        )

        # Clean up Special Pages
        for page in self.special_pages:
            flow.dangling_pages.discard(page)

        flow.dangling_pages = self.remove_flow_pages_from_set(
            flow.dangling_pages
        )

        return flow

    def process_start_page(self, flow: types.Flow, stats: types.AgentData):
        """Process a single Flow Path file."""
        with open(flow.start_page_file, "r", encoding="UTF-8") as flow_file:
            page = types.Page(flow=flow)
            page.display_name = f"{flow.display_name}: Start Page"

            # We keep track of an instance specific Flow graph for the current
            # Flow, and then a main Graph for the entire agent.
            flow.graph.add_node(page.display_name)
            stats.graph.add_node(page.display_name)

            page.data = json.load(flow_file)
            page.events = page.data.get("eventHandlers", None)
            page.routes = page.data.get("transitionRoutes", None)
            page.route_groups = page.data.get("transitionRouteGroups", None)
            stats.flows.append(page.data)

            flow.resource_id = page.data.get("name", None)

            # Order of processing is important
            stats = self.routes.process_routes(page, stats)
            stats = self.routes.process_events(page, stats)

            if page.route_groups:
                page, stats = self.routes.set_route_group_targets(page, stats)

            flow_file.close()

        full_flow_id = f"{stats.agent_id}/flows/{flow.resource_id}"
        stats.flows_map[flow.display_name] = full_flow_id
        stats.flow_page_map[flow.display_name] = {
            "id": full_flow_id,
            "pages": {}
            }

        return stats

    def process_flow(self, flow: types.Flow, stats: types.AgentData):
        """Process a Single Flow dir and all subdirectories."""
        flow.file_name = self.common.parse_filepath(flow.dir_path, "flow")
        flow.display_name = self.common.clean_display_name(flow.file_name)

        flow.start_page_file = f"{flow.dir_path}/{flow.file_name}.json"

        stats.pages[flow.display_name] = []
        stats.active_intents[flow.display_name] = []
        stats = self.process_start_page(flow, stats)
        stats = self.pages.process_pages_directory(flow, stats)
        stats = self.rgs.process_route_groups_directory(flow, stats)

        # Order of Find Operations is important here!
        flow = self.find_unused_pages(flow)
        flow = self.find_dangling_pages(flow)
        flow = self.find_unreachable_pages(flow)

        stats.active_pages[flow.display_name] = flow.active_pages
        stats.unused_pages[flow.display_name] = flow.unused_pages
        stats.unreachable_pages[flow.display_name] = flow.unreachable_pages

        return stats

    def process_flows_directory(
            self, agent_local_path: str, stats: types.AgentData):
        """Process the top level Flows dir in the JSON Package structure.

        The following files/dirs exist under the `flows` dir:
        - Flow object (i.e. Flow START_PAGE)
        - transitionRouteGroups
        - pages

        In Dialogflow CX, the START_PAGE of each Flow is a special kind of Page
        that exists within the Flow object itself. In this method, we will lint
        the Flow object, all files in the transitionRouteGroups dir and all
        files in the pages dir.
        """
        # Create a list of all Flow paths to iter through
        flow_paths = self.build_flow_path_list(agent_local_path)
        stats.total_flows = len(flow_paths)

        for flow_path in flow_paths:
            flow = types.Flow()
            flow.graph = graph.Graph()
            flow.dir_path = flow_path
            stats = self.process_flow(flow, stats)

        return stats
