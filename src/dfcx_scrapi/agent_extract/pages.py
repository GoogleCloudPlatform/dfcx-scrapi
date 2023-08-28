"""Pages processing methods and functions."""

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

from typing import Dict, Any

from dfcx_scrapi.agent_extract import common
from dfcx_scrapi.agent_extract import types
from dfcx_scrapi.agent_extract import routes


class Pages:
    """Pages processing methods and functions."""

    def __init__(self):
        self.common = common.Common()
        self.routes = routes.Fulfillments()

    @staticmethod
    def build_page_path_list(flow_path: str):
        """Builds a list of files, each representing a Page.

        Ex: /path/to/agent/flows/<flow_dir>/pages/<page_name>.json
        """
        pages_path = f"{flow_path}/pages"

        page_paths = []

        for page in os.listdir(pages_path):
            page_file_path = f"{pages_path}/{page}"
            page_paths.append(page_file_path)

        return page_paths

    @staticmethod
    def get_form_parameter_data(param: Dict[str, Any], page: types.Page):
        fp = types.FormParameter(page=page)
        fp.display_name = param.get("displayName", None)
        fp.entity_type = param.get("entityType", None)
        fp.required = param.get("required", None)

        fp.fill_behavior = param.get("fillBehavior", None)

        if fp.fill_behavior:
            fp.init_fulfillment = fp.fill_behavior.get(
                "initialPromptFulfillment", None)
            fp.reprompt_handlers = fp.fill_behavior.get(
                "repromptEventHandlers", None)

        fp.advanced_settings = page.form.get("advancedSettings", None)

        if fp.advanced_settings:
            fp.dtmf_settings = fp.advanced_settings.get("dtmfSettings", None)

        return fp

    def process_form(self, page: types.Page, stats: types.AgentData):
        """Process the Form and sub-resources within it for the Page."""
        parameters = page.form.get("parameters", None)

        if parameters:
            for param in parameters:
                fp = self.get_form_parameter_data(param, page)
                stats = self.routes.process_reprompt_handlers(fp, stats)

        return stats


    def process_page(self, page: types.Page, stats: types.AgentData):
        """Process a Single Page file."""
        page.display_name = self.common.parse_filepath(page.page_file, "page")
        page.display_name = self.common.clean_display_name(page.display_name)

        stats.graph.add_node(page.display_name)
        page.flow.graph.add_node(page.display_name)

        page.flow.all_pages.add(page.display_name)

        with open(page.page_file, "r", encoding="UTF-8") as page_file:
            page.data = json.load(page_file)
            page.entry = page.data.get("entryFulfillment", None)
            page.events = page.data.get("eventHandlers", None)
            page.form = page.data.get("form", None)
            page.routes = page.data.get("transitionRoutes", None)
            page.route_groups = page.data.get("transitionRouteGroups", None)
            page.resource_id = page.data.get("name", None)

            # Order of linting is important here
            stats = self.routes.process_entry(page, stats)
            stats = self.routes.process_routes(page, stats)
            stats = self.routes.process_events(page, stats)
            stats = self.process_form(page, stats)

            if page.route_groups:
                page, stats = self.routes.set_route_group_targets(page, stats)

            page_file.close()

        full_flow_id = f"{stats.agent_id}/flows/{page.flow.resource_id}"
        full_page_id = f"{full_flow_id}/pages/{page.resource_id}"
        stats.pages[page.flow.display_name].append(page.data)
        stats.flow_page_map[
            page.flow.display_name]["pages"][page.display_name] = full_page_id

        return stats

    def process_pages_directory(self, flow: types.Flow, stats: types.AgentData):
        """Process the Pages dir inside a specific Flow dir.

        Some Flows may not contain Pages, so we check for the existence
        of the directory before traversing
        """
        if "pages" in os.listdir(flow.dir_path):
            page_paths = self.build_page_path_list(flow.dir_path)

            for page_path in page_paths:
                page = types.Page(flow=flow)
                page.agent_id = flow.agent_id
                page.page_file = page_path
                stats.total_pages += 1
                stats = self.process_page(page, stats)

        return stats
