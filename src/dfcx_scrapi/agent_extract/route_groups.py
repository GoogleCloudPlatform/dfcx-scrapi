"""Route Groups processing methods and functions."""

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

import os
import json

from dfcx_scrapi.agent_extract import common
from dfcx_scrapi.agent_extract import types
from dfcx_scrapi.agent_extract import routes


class RouteGroups:
    """Route Groups processing methods and functions."""

    def __init__(self):
        self.special_pages = [
            "End Session",
            "End Flow",
            "Start Page",
            "Current Page",
            "Previous Page",
        ]

        self.common = common.Common()
        self.routes = routes.Fulfillments()

    @staticmethod
    def build_route_group_path_list(flow_local_path: str):
        """Builds a list of files, each representing a Route Group.

        Ex: /path/to/agent/flows/<flow_dir>/transitionRouteGroups/<rg.json>
        """
        root_dir = flow_local_path + "/transitionRouteGroups"

        if "transitionRouteGroups" in os.listdir(flow_local_path):
            rg_paths = []

            for rg_file in os.listdir(root_dir):
                rg_file_path = f"{root_dir}/{rg_file}"
                rg_paths.append(rg_file_path)

        return rg_paths

    def process_route_group(self, rg: types.RouteGroup, stats: types.AgentData):
        """Process a single Route Group."""
        rg.display_name = self.common.parse_filepath(rg.rg_file, "route_group")
        rg.display_name = self.common.clean_display_name(rg.display_name)

        with open(rg.rg_file, "r", encoding="UTF-8") as route_group_file:
            rg.data = json.load(route_group_file)
            rg.resource_id = rg.data.get("name", None)
            rg.display_name = rg.data.get("displayName", None)
            rg.routes = rg.data.get("transitionRoutes", None)

            stats = self.routes.process_routes(rg, stats)

            route_group_file.close()

        full_flow_id = f"{stats.agent_id}/flows/{rg.flow.resource_id}"
        full_rg_id = f"{full_flow_id}/transitionRouteGroups/{rg.resource_id}"
        stats.route_groups_map[
            rg.flow.display_name]["route_groups"][rg.display_name] = full_rg_id
        stats.route_groups[rg.flow.display_name].append(rg.data)

        return stats

    def process_route_groups_directory(
            self, flow: types.Flow, stats: types.AgentData):
        """Process Route Groups dir in the JSON Package structure."""
        if "transitionRouteGroups" in os.listdir(flow.dir_path):
            # Create a list of all Route Group paths to iter through
            rg_paths = self.build_route_group_path_list(flow.dir_path)
            stats.total_route_groups += len(rg_paths)

            full_flow_id = f"{stats.agent_id}/flows/{flow.resource_id}"
            stats.route_groups_map[flow.display_name] = {
                "id": full_flow_id,
                "route_groups": {}
            }
            stats.route_groups[flow.display_name] = []

            for rg_path in rg_paths:
                rg = types.RouteGroup(flow=flow)
                rg.rg_file = rg_path
                stats = self.process_route_group(rg, stats)

        return stats
