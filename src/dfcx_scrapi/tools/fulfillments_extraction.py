"""Utility file for working with fulfillments from Dialogflow CX."""

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

import logging
import google.cloud.dialogflowcx_v3beta1.types as types
import pandas as pd


from dfcx_scrapi.core import scrapi_base, intents, flows, pages, transition_route_groups


# logging config
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


class Fulfillments(scrapi_base.ScrapiBase):
    """Class that supports fulfillment-pulling functions in DFCX."""

    def __init__(
        self,
        creds_path: str = None,
        creds_dict: dict = None,
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

        logging.info("create dfcx creds %s", creds_path)
        self.intents = intents.Intents(creds_path, creds_dict)
        self.flows = flows.Flows(creds_path, creds_dict)
        self.pages = pages.Pages(creds_path, creds_dict)
        self.route_groups = transition_route_groups.TransitionRouteGroups(
            creds_path, creds_dict
        )
        self.creds_path = creds_path

        if agent_id:
            self.agent_id = agent_id
            self.intents_map = self.intents.get_intents_map(agent_id)

    @staticmethod
    # TODO (greenford) list of what? possibly protobuff type
    def get_message_fulfillments(messages: List):
        """
        Gets fulfillments from messages dictionary.

        Args:
            messages: #TODO.
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
    def get_conditional_case_fulfillments(case_content: List):
        """
        Gets conditinal fulfillments from case content dictionary.

        Args:
            case_contents: #TODO also above in type hint
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

    # TODO (greenford) test function - has dubious dateframe inserts
    def get_transition_route_fulfillments(
        self,
        flow_display_name: str,
        resource_type: str,
        resource_name: str,
        routes: List,
    ):
        """
        Gets fulfillments from routes list.

        Args: #TODO confirm arg types
            flow_display_name: origin of routes list
            resource_type: #TODO
            resource_name: #TODO
            routes: #TODO
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
                text_fulfillments = self.get_message_fulfillments(messages)
                route_dataframe["fulfillment"] = text_fulfillments
                route_dataframe["identifier"] = intent_triggered
                route_dataframe["response_type"] = "text"
                route_dataframe["condition"] = "N/A"

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
                            text_fulfillments = self.get_conditional_case_fulfillments(
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

    def get_event_handler_fulfillments(
        self,
        flow_display_name: str,
        page_display_name: str,
        event_handlers: List,  # TODO
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
                text_fulfillments = self.get_message_fulfillments(messages)

                event_handler_dataframe["fulfillment"] = text_fulfillments
                event_handler_dataframe["identifier"] = event_handler_name
                event_handler_dataframe["response_type"] = "text"
                event_handler_dataframe["condition"] = "N/A"

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
                            text_fulfillments = self.get_conditional_case_fulfillments(
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

    # entry fulfillments
    def get_entry_fulfillments(
        self,
        flow_display_name: str,
        object_display_name: str,
        entry_fulfillment: Dict,  # TODO
    ):
        """
        Gets fulfillments from entry fulfillments dictionary on a page.

        Args:
            flow_display_name: origin flow of entry_fulfillment
            object_display_name: origin object of entry_fulfillment
            entry_fulfillment: #TODO
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
            text_fulfillments = self.get_message_fulfillments(messages)

            entry_fulfillments_dataframe["fulfillment"] = text_fulfillments
            entry_fulfillments_dataframe["identifier"] = object_display_name
            entry_fulfillments_dataframe["response_type"] = "text"
            entry_fulfillments_dataframe["condition"] = "N/A"

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
                        text_fulfillments = self.get_conditional_case_fulfillments(
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

        # route groups

    def get_route_group_fulfillments(self, flow_dictionary: Dict):
        """
        Gets fulfillments from route groups in a flow.

        Args:
            flow_dictionary: #TODO
        Returns:
            Dataframe with columns: #TODO
        """
        route_group_fulfillments_df = pd.DataFrame()
        route_groups_flow = self.route_groups.list_transition_route_groups(
            flow_id=flow_dictionary["name"]
        )
        for route_group_flow in route_groups_flow:
            route_group_flow = types.TransitionRouteGroup.to_dict(route_group_flow)
            route_group_name = route_group_flow["display_name"]
            routes = route_group_flow["transition_routes"]
            route_group_fulfillment_df = self.get_transition_route_fulfillments(
                flow_dictionary["display_name"],
                resource_type="route group",
                resource_name=route_group_name,
                routes=routes,
            )
            route_group_fulfillments_df = pd.concat(
                [route_group_fulfillments_df, route_group_fulfillment_df]
            )
        return route_group_fulfillments_df

    # TODO type
    def get_flow_fufillments(self, flow_obj):
        """Get all fulfillments from a flow object.

        Args:
            flow_obj: #TODO
        Returns:
            Dataframe with columns: #TODO
        """
        flow_fufillments = pd.DataFrame()
        flow_dictionary = types.Flow.to_dict(flow_obj)
        transition_routes = flow_dictionary["transition_routes"]
        event_handlers = flow_dictionary["event_handlers"]
        route_fulfillments = self.get_transition_route_fulfillments(
            flow_obj.display_name,
            resource_type="page",
            resource_name="START_PAGE",
            routes=transition_routes,
        )
        event_fulfillments = self.get_event_handler_fulfillments(
            flow_obj.display_name, "START_PAGE", event_handlers
        )
        route_group_fulfillments = self.get_route_group_fulfillments(flow_dictionary)

        flow_fufillments = pd.concat(
            [
                flow_fufillments, 
                route_fulfillments, 
                event_fulfillments, 
                route_group_fulfillments
            ]
        )
        return flow_fufillments

    # TODO type hints
    def get_page_fulfillments(self, flow_display_name: str, page_obj):
        """
        Gets all fulfillments from a page object.

        Args:
            flow_display_name: origin flow of the page_obj.
            page_obj: #TODO
        Returns:
            Dataframe with columns: #TODO
        """
        page_fulfillments = pd.DataFrame()
        page_dictionary = types.Page.to_dict(page_obj)

        entry_fulfillment = page_dictionary.get("entry_fulfillment", False)
        transition_routes = page_dictionary["transition_routes"]
        event_handlers = page_dictionary["event_handlers"]

        if entry_fulfillment:
            entry_fulfillments = self.get_entry_fulfillments(
                flow_display_name,
                page_dictionary["display_name"],
                entry_fulfillment,
            )
            page_fulfillments = pd.concat(
                [page_fulfillments, entry_fulfillments]
            )

        route_fulfillments = self.get_transition_route_fulfillments(
            flow_display_name,
            resource_type="page",
            resource_name=page_obj.display_name,
            routes=transition_routes,
        )
        event_fulfillments = self.get_event_handler_fulfillments(
            flow_display_name, page_obj.display_name, event_handlers
        )

        fulfillments = pd.concat(
            [page_fulfillments, route_fulfillments, event_fulfillments]
        )
        return fulfillments

    # Agent Level
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
                page_data = self.get_page_fulfillments(
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
