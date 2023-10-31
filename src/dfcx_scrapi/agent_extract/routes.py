"""Fulfillment routes processing methods and functions."""

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

from typing import Dict, Any

from dfcx_scrapi.agent_extract import common
from dfcx_scrapi.agent_extract import types


class Fulfillments:
    """Fulfillment routes processing methods and functions."""

    def __init__(self):
        self.common = common.Common()
        self.route_parameters = {}

    @staticmethod
    def check_for_webhook(page: types.Page, path: Dict[str, Any]):
        """Check the current route for existence of webhook."""
        if "webhook" in path:
            page.has_webhook = True

    @staticmethod
    def check_for_webhook_event_handlers(route: types.Fulfillment):
        """Check for Webhook Error Event Handler on Page.

        In this method, we're interested in the following conditions:
         - Page is currently flagged w/webhook = True
         - Page HAS NOT been flagged w/having a webhook error handler
         - The trigger MATCHES the pattern 'webhook.error'

        If a Page and its Route meet all the criteria, we'll flip the bit.
        Otherwise, the webhook handler bit will remain False, causing a rule
        flag."""

        if all(
            [
                route.page.has_webhook,
                not route.page.has_webhook_event_handler,
                "webhook.error" in route.trigger,
            ]
        ):
            route.page.has_webhook_event_handler = True

    @staticmethod
    def check_for_intent(route: types.Fulfillment):
        """Check route data to see if Intent is present."""
        intent = None
        if "intent" in route.data:
            intent = route.data["intent"]

        return intent

    def process_intents_in_routes(
            self, route: types.Fulfillment, stats: types.AgentData):
        intent = self.check_for_intent(route)
        if intent:
            pair = (intent, route.page.display_name)
            stats.active_intents[
                route.page.flow.display_name].append(pair)

        return stats

    def collect_transition_route_trigger(self, route):
        """Inspect route and return all Intent/Condition info."""

        trigger = []

        if "intent" in route.data:
            trigger.append("intent")

        if "condition" in route.data:
            trigger.append("condition")

        if len(trigger) > 0:
            trigger = "+".join(trigger)

        return trigger

    def get_trigger_info(self, route):
        """Extract trigger info from route based on primary key."""

        if route.fulfillment_type == "event":
            trigger = f"event : {route.data.get('event', None)}"

        if route.fulfillment_type == "reprompt_handler":
            trigger = f"{route.parameter} : event : "\
                f"{route.data.get('event', None)}"

        if route.fulfillment_type == "transition_route":
            intent_condition = self.collect_transition_route_trigger(route)
            trigger = f"route : {intent_condition}"

        return trigger

    def set_route_group_targets(self, page: types.Page, stats: types.AgentData):
        """Determine Route Targets for Route Group routes."""
        current_page = page.display_name

        for route_group in page.route_groups:
            page.flow.graph.add_edge(current_page, route_group)
            page.flow.graph.add_used_node(route_group)

            stats.graph.add_edge(current_page, route_group)
            stats.graph.add_used_node(route_group)

        return page, stats

    def set_route_targets(
            self, route: types.Fulfillment, stats: types.AgentData):
        """Determine the Route Targets for the specified route.

        Primary function is to build out the graph structure for the
        Flow based on the current page and where the routes are pointing to.
        The graph structure can then be traversed later to determine any errors
        or inconsistencies in design.
        """
        current_page = route.page.display_name

        route.target_flow = route.data.get("targetFlow", None)
        route.target_page = route.data.get("targetPage", None)

        if route.target_page:
            route.page.flow.graph.add_edge(current_page, route.target_page)
            route.page.flow.graph.add_used_node(route.target_page)

            stats.graph.add_edge(current_page, route.target_page)
            stats.graph.add_used_node(route.target_page)

        if route.target_flow:
            route.page.flow.graph.add_edge(
                current_page, f"FLOW: {route.target_flow}")
            route.page.flow.graph.add_used_node(f"FLOW: {route.target_flow}")

            stats.graph.add_edge(
                current_page, f"FLOW: {route.target_flow}"
            )
            stats.graph.add_used_node(f"FLOW: {route.target_flow}")

        return route, stats

    def update_route_parameters(
            self, route: types.Fulfillment, item: Dict[str, str]):
        """Update the Route Parameters map based on new info."""
        flow_name = route.page.flow.display_name
        page_name = route.page.display_name

        flow_data = self.route_parameters.get(flow_name, None)
        page_data = None

        if flow_data:
            page_data = flow_data.get(page_name, None)

        # Flow and Page already exists, append to existing list.
        if page_data:
            self.route_parameters[flow_name][page_name].append(item)

        # Flow data exists, but not Page, so only create the Page list.
        elif flow_data and not page_data:
            self.route_parameters[flow_name][page_name] = [item]

        # Neither the Flow or Page data exists, so create it all.
        else:
            self.route_parameters[flow_name] = {page_name: [item]}


    def process_fulfillment_type(
        self, stats: types.AgentData, route: types.Fulfillment, path: object,
        key: str):
        """Parse through specific fulfillment types."""
        fulfillment_data = path.get(key, None)

        if fulfillment_data:
            for item in fulfillment_data:
                # This is where each message type will exist
                # text, custom payload, etc.

                if "text" in item:
                    for text in item["text"]["text"]:
                        route.text = text

                if "parameter" in item:
                    self.update_route_parameters(route, item)

        return stats

    def process_reprompt_handlers(
            self, fp: types.FormParameter, stats: types.AgentData):
        """Processing for Reprompt Event Handlers inside Form parameters.

        While Reprompt Event Handlers are technically Events, they differ from
        standard Page level Events because they act on the FormParameter data
        structure, not Fulfillment Route data structure as standard Events do.
        """
        if not fp.reprompt_handlers:
            return stats

        for handler in fp.reprompt_handlers:
            route = types.Fulfillment(page=fp.page)
            route.data = handler
            route.agent_id = fp.page.agent_id
            route.fulfillment_type = "reprompt_handler"
            route.parameter = fp.display_name
            route.trigger = self.get_trigger_info(route)
            route, stats = self.set_route_targets(route, stats)
            path = route.data.get("triggerFulfillment", None)
            event = route.data.get("event", None)

            stats = self.process_intents_in_routes(route, stats)

            if not path and not event:
                continue

            # Flag for Webhook Handler
            self.check_for_webhook(fp.page, path)

            stats = self.process_fulfillment_type(
                stats, route, path, "messages")

        return stats

    def process_events(self, page: types.Page, stats: types.AgentData):
        """Parse through all Page Event Handlers."""
        if not page.events:
            return stats

        for route_data in page.events:
            route = types.Fulfillment(page=page)
            route.data = route_data
            route.agent_id = page.agent_id
            route.fulfillment_type = "event"
            route.trigger = self.get_trigger_info(route)
            route, stats = self.set_route_targets(route, stats)
            path = route.data.get("triggerFulfillment", None)
            event = route.data.get("event", None)

            stats = self.process_intents_in_routes(route, stats)

            if not path and not event:
                continue

            # Flag for Webhook Handler
            self.check_for_webhook_event_handlers(route)

            stats = self.process_fulfillment_type(
                stats, route, path, "messages")

        return stats

    def process_routes(self, page: types.Page, stats: types.AgentData):
        """Parse through all Transition Routes."""
        tf_key = "triggerFulfillment"

        if not page.routes:
            return stats

        for route_data in page.routes:
            route = types.Fulfillment(page=page)
            route.data = route_data
            route.agent_id = page.agent_id
            route.fulfillment_type = "transition_route"
            route.trigger = self.get_trigger_info(route)
            route, stats = self.set_route_targets(route, stats)

            stats = self.process_intents_in_routes(route, stats)

            path = route.data.get(tf_key, None)

            if not path:
                continue

            # Flag for Webhook Handler
            self.check_for_webhook(page, path)

            stats = self.process_fulfillment_type(
                stats, route, path, "messages")

            # Preset Params processed here
            stats = self.process_fulfillment_type(
                stats, route, path, "setParameterActions"
            )

        return stats

    def process_entry(self, page: types.Page, stats: types.AgentData):
        """Process Entry Fulfillment on a single page file.

        The Entry Fulfillment to a Page only has 1 "route" (i.e. itself) so
        there is no need to loop through multiple routes, as they don't
        exist for Entry Fulfillment.
        """

        if not page.entry:
            return stats

        route = types.Fulfillment(page=page)
        route.data = page.entry
        route.agent_id = page.agent_id
        route.fulfillment_type = "entry"
        route.trigger = "entry"
        path = route.data

        self.check_for_webhook(page, path)

        stats = self.process_fulfillment_type(stats, route, path, "messages")

        return stats
