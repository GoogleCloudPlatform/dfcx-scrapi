"""A set of Utility methods to copy DFCX Resources."""

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

import copy
import logging
import time
from typing import Dict, List
from collections import defaultdict

import google.cloud.dialogflowcx_v3beta1.types as types
from google.api_core import exceptions as core_exceptions

from dfcx_scrapi.core import (scrapi_base, intents, entity_types, flows, pages,
  webhooks, transition_route_groups)

# logging config
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)-8s %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)

class CopyUtil(scrapi_base.ScrapiBase):
    """Tools Utility class for copying DFCX Resources between Agents."""
    def __init__( #pylint: disable=too-many-arguments
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


        self.intents = intents.Intents(
            creds=self.creds, agent_id=self.agent_id)
        self.entities = entity_types.EntityTypes(
            creds=self.creds, agent_id=self.agent_id)
        self.flows = flows.Flows(
            creds=self.creds, agent_id=self.agent_id)
        self.pages = pages.Pages(creds=self.creds)
        self.webhooks = webhooks.Webhooks(
            creds=self.creds, agent_id=self.agent_id)
        self.route_groups = transition_route_groups.TransitionRouteGroups(
            creds=self.creds, agent_id=self.agent_id)

    @staticmethod
    def _get_entry_webhooks(page_object, resources):
        """Check the Entry Fulfillment for webhooks and return them."""
        if 'entry_fulfillment' in page_object:
            if 'webhook' in page_object.entry_fulfillment:
                resources['webhooks'].append(
                    page_object.entry_fulfillment.webhook)

        return resources


    @staticmethod
    def _get_condition_route_webhooks(page_object, resources):
        """Extract Webhooks from Condition for a given Page."""
        if 'transition_routes' in page_object:
            for transition_route in page_object.transition_routes:
                if ('condition' in transition_route
                and 'webhook' in transition_route.trigger_fulfillment):
                    resources['webhooks'].append(
                        transition_route.trigger_fulfillment.webhook
                    )

        return resources

    @staticmethod
    def _get_form_entity_types(page_object, resources):
        """Extract Entity Types from Parameters for a given Page."""
        if 'form' in page_object:
            if 'parameters' in page_object.form:
                for param in page_object.form.parameters:
                    if 'sys.' in param.entity_type:
                        continue
                    resources['entities'].append(
                            param.entity_type
                        )

        return resources

    @staticmethod
    def _get_intent_route_intents(page_object, resources):
        """Extract any Intents from Transition Routes in a given Page."""

        if 'transition_routes' in page_object:
            for transition_route in page_object.transition_routes:
                if 'intent' in transition_route:
                    resources['intents'].append(
                        transition_route.intent
                    )

        return resources

    @staticmethod
    def _convert_entry_webhooks(page_object, webhooks_map):
        """Convert webhooks in the entry fulfillment of the Page Object.

        Internal method to convert webhooks in the entry fulfillment of
        a given page from the Resource ID to their Display Name or vice versa.
        """
        if 'webhook' in page_object.entry_fulfillment:
            page_object.entry_fulfillment.webhook = webhooks_map[
                page_object.entry_fulfillment.webhook
            ]

        return page_object

    @staticmethod
    def __convert_tr_target_page(
        trans_route,
        pages_map,
        convert_type = None,
        flows_map = None,
        flow = None):

        if convert_type == 'source':
            if trans_route.target_page.split('/')[-1] == 'END_FLOW':
                trans_route.target_page = 'END_FLOW'

            elif trans_route.target_page.split('/')[-1] == 'END_SESSION':
                trans_route.target_page = 'END_SESSION'

            elif (
                trans_route.target_page.split('/')[-1] == 'CURRENT_PAGE'
            ):
                trans_route.target_page = 'CURRENT_PAGE'

            else:
                trans_route.target_page = pages_map[trans_route.target_page]

        elif convert_type == 'destination':
            if trans_route.target_page == 'END_FLOW':
                trans_route.target_page = (
                    flows_map[flow] + '/pages/END_FLOW')

            elif trans_route.target_page == 'END_SESSION':
                trans_route.target_page = (
                    flows_map[flow] + '/pages/END_SESSION')

            elif trans_route.target_page == 'CURRENT_PAGE':
                trans_route.target_page = (
                    flows_map[flow] + '/pages/CURRENT_PAGE')

            else:
                trans_route.target_page = pages_map[trans_route.target_page]

        return trans_route.target_page

    @staticmethod
    def __convert_trigger_fulfillment_webhook(handler, webhooks_map):
        if 'webhook' in handler.trigger_fulfillment:
            handler.trigger_fulfillment.webhook = webhooks_map[
                handler.trigger_fulfillment.webhook]

        return handler.trigger_fulfillment.webhook

    def _convert_form_parameters( #pylint: disable=too-many-arguments
        self,
        page_object,
        pages_map,
        webhooks_map,
        entities_map,
        convert_type = None):

        for param in page_object.form.parameters:
            if 'fill_behavior' in param:
                if 'initial_prompt_fulfillment' in param.fill_behavior:
                    if 'webhook' in (
                        param.fill_behavior.initial_prompt_fulfillment):
                        param.fill_behavior.initial_prompt_fulfillment.webhook = webhooks_map[ #pylint: disable=line-too-long
                            param.fill_behavior.initial_prompt_fulfillment.webhook #pylint: disable=line-too-long
                        ]

                if 'reprompt_event_handlers' in param.fill_behavior:
                    for handler in param.fill_behavior.reprompt_event_handlers:
                        if 'trigger_fulfillment' in handler:
                            handler.trigger_fulfillment.webhook = (
                                self.__convert_trigger_fulfillment_webhook(
                                    handler, webhooks_map)
                            )

                        if 'target_page' in handler:
                            handler.target_page = (
                                self.__convert_tr_target_page(
                                    handler, pages_map,
                                    convert_type=convert_type)
                            )

            if 'sys.' in param.entity_type:
                pass
            else:
                param.entity_type = entities_map[param.entity_type]

        return page_object

    def _convert_event_handlers(
        self, page_object, pages_map, webhooks_map, convert_type = None):

        for handler in page_object.event_handlers:
            if 'target_page' in handler:
                handler.target_page = self.__convert_tr_target_page(
                    handler, pages_map, convert_type=convert_type)

            if 'trigger_fulfillment' in handler:
                handler.trigger_fulfillment.webhook = (
                    self.__convert_trigger_fulfillment_webhook(
                        handler, webhooks_map
                    )
                )

        return page_object

    def _convert_trans_routes( #pylint: disable=too-many-arguments
        self,
        page_object,
        pages_map,
        intents_map,
        webhooks_map,
        convert_type = None):

        for trans_route in page_object.transition_routes:
            if 'target_page' in trans_route:
                trans_route.target_page = self.__convert_tr_target_page(
                    trans_route, pages_map, convert_type=convert_type)

            if 'intent' in trans_route:
                trans_route.intent = intents_map[trans_route.intent]
                if 'webhook' in trans_route.trigger_fulfillment:
                    trans_route.trigger_fulfillment.webhook = webhooks_map[
                        trans_route.trigger_fulfillment.webhook
                    ]
            elif (
                'condition' in trans_route
                and 'webhook' in trans_route.trigger_fulfillment
            ):
                trans_route.trigger_fulfillment.webhook = webhooks_map[
                    trans_route.trigger_fulfillment.webhook
                ]

        return page_object

    def _get_intent_entity_dependencies(self, resources):
        """Loop through Intents and find any additional Entity dependencies"""
        agent = '/'.join(resources['intents'][0].split('/')[0:6])
        temp_intents = self.intents.list_intents(agent)

        for intent in temp_intents:
            if intent.name in resources['intents']:
                if len(intent.parameters) > 0:
                    for param in intent.parameters:
                        if 'sys.' in param.entity_type:
                            continue
                        resources['entities'].append(param.entity_type)

        return resources

    def _get_flow_intent_route_intents(self, flow_id, obj_list, resources):
        """Extract Intents from Transition Routes on the Flow Start Page.

        The Start Page of every Flow is a special Page-like object that
        actually exists as part of the Flow object. Because it is different
        enough from a standard Page object, we have to extract the resources
        from it differently.
        """
        source_flow = self.flows.get_flow(flow_id)
        temp_page_name_list = [page.name for page in obj_list]

        for transition_route in source_flow.transition_routes:
            if 'intent' in transition_route:
                if transition_route.target_page in temp_page_name_list:
                    resources['intents'].append(transition_route.intent)

        return resources

    def _get_route_groups_and_intents(self, page_object, flow_id, resources):
        """Extract Intent resources from Transition Route Groups on a Page."""
        route_groups = self.route_groups.list_transition_route_groups(flow_id)

        if 'transition_route_groups' in page_object:
            for trg in page_object.transition_route_groups:
                resources['route_groups'].append(trg)
                for route_group in route_groups:
                    if trg == route_group.name:
                        for transition_route in route_group.transition_routes:
                            resources['intents'].append(
                                transition_route.intent)

        return resources

    def _remap_parameters_in_intent(
        self,
        source_agent,
        destination_agent,
        intent_object):
        """Remap the Entity Type Resource ID from the Source to Destination.

        Internal function to find the Source Entity Type Resource ID, convert
        it to the Display Name, perform a lookup in the Destination Agent, and
        convert that final Resource ID to the Desitnation Agent Entity Type
        Resource ID
        """

        source_entities_map = self.entities.get_entities_map(source_agent)
        destination_entities_map = self.entities.get_entities_map(
            destination_agent, reverse=True
            )

        for param in intent_object.parameters:
            if 'sys.' in param.entity_type:
                pass
            else:
                source_name = source_entities_map[param.entity_type]
                destination_name = destination_entities_map[source_name]
                param.entity_type = destination_name

        return intent_object

    def _update_intent_via_copy(
        self,
        intent_display_name,
        intent_object,
        destination_agent):
        """Update the Source Intent Display Name in the Destination Agent.

        Internal method to update the Destination Intent based on the defined
        Source Intent Display Name. This is specifically used when the
        Destination Agent already contains the Intent Display Name specified.
        This performs a lookup based on Intent Display Name, retrieves the
        Destination Intent object, and then updates it appropriately."""

        destination_intents = self.intents.list_intents(destination_agent)
        for intent in destination_intents:
            if intent.display_name == intent_display_name:
                destination_intent_obj = intent

        self.intents.update_intent(destination_intent_obj.name, intent_object)
        logging.info('Intent %s updated successfully',
          intent_object.display_name)

    def _create_intent_via_copy(
        self,
        destination_agent,
        intent_object):
        """Create the Source Intent in the Destination Agent."""
        try:
            self.intents.create_intent(destination_agent, intent_object)
            logging.info(
                'Intent %s created successfully', intent_object.display_name)

        except core_exceptions.AlreadyExists as error:
            print(error)
            print(
                'If you are trying to update an existing Intent, use the'
                + ' \'update\' option instead'
            )

    def _get_resource_objects(
        self,
        source_agent,
        resources,
        resources_objects,
        skip_list):

        if 'entities' not in skip_list:
            source_entities = self.entities.list_entity_types(source_agent)
            for entity in source_entities:
                if entity.name in resources['entities']:
                    resources_objects['entities'].append(entity)

        if 'intents' not in skip_list:
            source_intents = self.intents.list_intents(source_agent)
            for intent in source_intents:
                if intent.name in resources['intents']:
                    resources_objects['intents'].append(intent)

        if 'webhooks' not in skip_list:
            source_webhooks = self.webhooks.list_webhooks(source_agent)
            for webhook in source_webhooks:
                if webhook.name in resources['webhooks']:
                    resources_objects['webhooks'].append(webhook)

        if 'route_groups' not in skip_list:
            source_flows_map = self.flows.get_flows_map(
                source_agent, reverse=True
            )
            source_route_groups = (
                self.route_groups.list_transition_route_groups(
                    source_flows_map['Default Start Flow']
                )
            )
            for route_group in source_route_groups:
                if route_group.name in resources['route_groups']:
                    resources_objects['route_groups'].append(route_group)

        return resources_objects

    def _create_webhook_resources(
        self,
        destination_agent,
        resources_objects,
        resources_skip_list):
        for webhook in resources_objects['webhooks']:
            logging.info('Creating Webhook %s...', webhook.display_name)
            try:
                self.webhooks.create_webhook(destination_agent, webhook)
                resources_skip_list['webhooks'].append(webhook.display_name)
                logging.info(
                    'Webhook %s created successfully.', webhook.display_name)

            except core_exceptions.AlreadyExists as error:
                logging.info(error)

        return resources_skip_list

    def _create_entity_resources(
        self,
        destination_agent,
        resources_objects,
        resources_skip_list):

        for entity in resources_objects['entities']:
            logging.info('Creating Entity %s...', entity.display_name)
            try:
                self.entities.create_entity_type(destination_agent, entity)
                resources_skip_list['entities'].append(entity.display_name)
                logging.info(
                    'Entity %s created successfully.', entity.display_name)

            except core_exceptions.AlreadyExists as error:
                print(error)

        return resources_skip_list

    def _create_intent_resources(
        self,
        source_agent,
        destination_agent,
        resources_objects,
        resources_skip_list):

        for intent in resources_objects['intents']:
            logging.info('Creating Intent %s...', intent.display_name)
            time.sleep(1) # sleep to not overrun API rate limiter

            if 'parameters' in intent:
                intent = self._remap_parameters_in_intent(
                    source_agent, destination_agent, intent)
            try:
                self.intents.create_intent(destination_agent, intent)
                resources_skip_list['intents'].append(intent.display_name)
                logging.info('Intent %s created successfully',
                  intent.display_name)
            except core_exceptions.AlreadyExists as error:
                print(error)

        return resources_skip_list

    def _create_route_group_resources( #pylint: disable=too-many-arguments
        self,
        source_agent,
        destination_agent,
        destination_flow,
        resources_objects,
        resources_skip_list):

        source_flows_map = self.flows.get_flows_map(source_agent)
        source_intents_map = self.intents.get_intents_map(source_agent)
        source_webhooks_map = self.webhooks.get_webhooks_map(source_agent)
        source_pages_map = self.pages.get_pages_map(
            source_flows_map['Default Start Flow'])

        destination_flows = self.flows.get_flows_map(
            destination_agent, reverse=True)
        destination_intents_map = self.intents.get_intents_map(
                destination_agent, reverse=True)
        destination_webhooks_map = self.webhooks.get_webhooks_map(
                destination_agent, reverse=True)
        destination_pages_map = self.pages.get_pages_map(
                destination_flows[destination_flow], reverse=True
            )

        for route_group in resources_objects['route_groups']:
            logging.info(
                'Creating Route Group %s...', route_group.display_name)
            for trans_route in route_group.transition_routes:
                source_name = source_intents_map[trans_route.intent]
                destination_name = destination_intents_map[source_name]
                trans_route.intent = destination_name

                if 'trigger_fulfillment' in trans_route:
                    if 'webhook' in trans_route.trigger_fulfillment:
                        source_webhook = source_webhooks_map[
                            trans_route.trigger_fulfillment.webhook
                        ]
                        destination_webhook = destination_webhooks_map[
                            source_webhook
                        ]
                        trans_route.trigger_fulfillment.webhook = (
                            destination_webhook)

                if 'target_page' in trans_route:
                    if trans_route.target_page.split('/')[-1] == 'END_FLOW':
                        trans_route.target_page = (
                            destination_flows[destination_flow]
                            + '/pages/END_FLOW'
                        )
                    else:
                        source_page = source_pages_map[trans_route.target_page]
                        destination_page = destination_pages_map[
                            source_page
                        ]
                        trans_route.target_page = destination_page

            try:
                self.route_groups.create_transition_route_group(
                    destination_flows[destination_flow], route_group
                )
                resources_skip_list['route_groups'].append(
                    route_group.display_name)
                logging.info('Route Group %s created successfully',
                  route_group.display_name)
            except core_exceptions.AlreadyExists as error:
                print(error)

        return resources_skip_list

    def copy_intent_to_agent(
        self,
        intent_display_name: str,
        source_agent: str,
        destination_agent: str,
        copy_option: str = 'create',
    ):
        """Copy an Intent object from one CX agent to another.

        Args:
          intent_display_name: The human readable display name of the intent.
          source_agent: the Agent ID string in the following format:
            projects/<project_id>/locations/<location_id>/agents/<agent_id>
          destination_agent: the Agent ID string in the following format:
            projects/<project_id>/locations/<location_id>/agents/<agent_id>
          copy_optoion: The update method of the copy to the new agent.
            One of 'create' or 'update'. Defaults to 'create'
        """
        # retrieve from source agent
        intents_map = self.intents.get_intents_map(source_agent, reverse=True)
        intent_id = intents_map[intent_display_name]
        intent_object = self.intents.get_intent(intent_id)

        if 'parameters' in intent_object:
            intent_object = self._remap_parameters_in_intent(
                source_agent, destination_agent, intent_object
            )

        if copy_option == 'update':
            self._update_intent_via_copy(
                intent_display_name, intent_object,destination_agent)

        elif copy_option == 'create':
            self._create_intent_via_copy(
                destination_agent, intent_object
            )

        else:
            logging.info('Invalid option. Please use \'create\' or \'update\'')


    def copy_entity_type_to_agent(
        self,
        entity_type_display_name,
        source_agent,
        destination_agent
    ):
        """Copy an Entity Type object from one CX agent to another.

        Args:
          entity_type_display_name: The human readable display name of the
            entity.
          source_agent: the Agent ID string in the following format:
            projects/<project_id>/locations/<location_id>/agents/<agent_id>
          destination_agent: the Agent ID string in the following format:
            projects/<project_id>/locations/<location_id>/agents/<agent_id>
        """
        # retrieve from source agent
        entity_map = self.entities.get_entities_map(source_agent, reverse=True)
        entity_id = entity_map[entity_type_display_name]
        entity_object = self.entities.get_entity_type(entity_id)

        # push to destination agent
        try:
            self.entities.create_entity_type(destination_agent, entity_object)
            logging.info('Entity Type %s created successfully',
              entity_object.display_name)

        except core_exceptions.AlreadyExists as error:
            print(error)

    def create_page_shells(
        self,
        pages_list: List[types.Page],
        destination_agent: str,
        destination_flow: str = 'Default Start Flow',
    ):
        """Create blank DFCX Page object(s) with given Display Name.

        This function aids in the copy/pasting of pages from one DFCX agent to
        another by first creating blank Page "shells" in the destination agent
        using the human-readable display names. These Pages will then be
        retrieved by Page ID to use in the final copy/paste of the Page object
        from source to destination.

        Args:
          pages_list, List of Page(s) object to extract page names from
          destination_agent, DFCX Agent ID of the Destination Agent
          destination_flow, DFCX Flow ID of the Destination Flow. If no Flow ID
            is provided, Default Start Flow will be used.

        Return:
          Success!
        """
        destination_flows = self.flows.get_flows_map(
            destination_agent, reverse=True
        )

        for page in pages_list:
            try:
                self.pages.create_page(
                    destination_flows[destination_flow],
                    display_name=page.display_name,
                )
                logging.info(
                    'Page %s created successfully', page.display_name
                )
            except core_exceptions.AlreadyExists as error:
                logging.info(error)
                continue

    def copy_paste_agent_resources( #pylint: disable=too-many-arguments
        self,
        resources: Dict[str, str],
        source_agent: str,
        destination_agent: str,
        destination_flow: str = 'Default Start Flow',
        skip_list: List[str] = None
    ):
        """Copy/Paste Agent level resources from one DFCX agent to another.

        Agent level resources in DFCX are resources like Entities, Intents, and
        Webhooks which are not Flow dependent. This method allows the user to
        provide a dictionary of Agent Resources and Resources IDs to be copied
        from a Source agent to a Destination agent. *NOTE* That this method
        will also copy all Route Groups from Default Start Flow only.

        To obtain the resource_dict in the proper format, you can use the
        get_page_dependencies() method included in the CopyUtil Class.

        Args:
          resource_dict: Dictionary of Lists of DFCX Resource IDs with keys
            corresponding to the Resource type (i.e. intents, entities, etc.)
            and values corresponding to the Resource ID itself.
          source_agent: DFCX Source Agent ID (Name)
          destination_agent: DFCX Destination Agent ID (Name)
          destination_flow: (Optional) Defaults to 'Default Start Flow'
          skip_list: (Optional) List of resources to exclude. Use the following
              strings: 'intents', 'entities', 'webhooks', 'route_groups'

        Returns:
          Success!
        """
        resources_objects = defaultdict(list)
        resources_skip_list = defaultdict(list)

        resources_objects = self._get_resource_objects(
            source_agent, resources, resources_objects, skip_list)

        # Create Objects in Destination Agent
        # For all objects, we will attempt to create them in the destination
        # Agent. If the Resource is a duplicate, then we will skip it and add
        # it to the resources_skip_list. Duplicates are determined by
        # display_name only at this time.

        if 'webhooks' in resources_objects and 'webhooks' not in skip_list:
            resources_skip_list = self._create_webhook_resources(
                destination_agent, resources_objects, resources_skip_list)

        if 'entities' in resources_objects and 'entities' not in skip_list:
            resources_skip_list = self._create_entity_resources(
                destination_agent, resources_objects, resources_skip_list)

        if 'intents' in resources_objects and 'intents' not in skip_list:
            resources_skip_list = self._create_intent_resources(
                source_agent, destination_agent, resources_objects,
                resources_skip_list)

        if (
            'route_groups' in resources_objects and
            'route_groups' not in skip_list):
            resources_skip_list = self._create_route_group_resources(
                source_agent, destination_agent, destination_flow,
                resources_objects,resources_skip_list)

        return resources_skip_list

    def convert_from_source_page_dependencies(
        self,
        agent_id: str,
        pages_list: List[types.Page],
        flow: str = 'Default Start Flow',
    ) -> List[types.Page]:
        """Convert all Source Agent dependencies to Display Names.

        In order to copy resources over to a Destination Agent, we need to
        first convert all of the Resource IDs to their respective Display
        Names. We will then use the Display Names to convert back to the
        Destination Agent resource IDs using another method.
        """

        pages_mod = copy.deepcopy(pages_list)

        intents_map = self.intents.get_intents_map(agent_id)
        entities_map = self.entities.get_entities_map(agent_id)
        webhooks_map = self.webhooks.get_webhooks_map(agent_id)
        flows_map = self.flows.get_flows_map(agent_id, reverse=True)
        pages_map = self.pages.get_pages_map(flows_map[flow])
        rgs_map = self.route_groups.get_route_groups_map(flows_map[flow])

        # For each page, recurse through the resources and look for
        # specific resource types that will have local agent
        # dependencies, then replace that UUID with a literal
        # str display_name. We will use this display_name to map back
        # to the appropriate destination UUID later.
        for page in pages_mod:

            if 'entry_fulfillment' in page:
                page = self._convert_entry_webhooks(page, webhooks_map)

            if 'transition_routes' in page:
                page = self._convert_trans_routes(
                    page, pages_map, intents_map, webhooks_map,
                    convert_type='source')

            if 'event_handlers' in page:
                page = self._convert_event_handlers(
                    page, pages_map, webhooks_map, convert_type='source')

            if 'form' in page:
                if 'parameters' in page.form:
                    page = self._convert_form_parameters(
                        page, pages_map, webhooks_map, entities_map,
                        convert_type='source')

            if 'transition_route_groups' in page:
                temp_list = []
                for trg in page.transition_route_groups:
                    temp_list.append(rgs_map[trg])

                    page.transition_route_groups = temp_list

        return pages_mod

    def convert_to_destination_page_dependencies(
        self,
        agent_id: str,
        pages_list: List[types.Page],
        flow: str = 'Default Start Flow'
    ) -> List[types.Page]:
        """Convert from Display Names to Destination Agent Resource IDs.

        In order to copy resources over to a Destination Agent, we need to
        look up all the Display Names we previously converted and remap them
        to their respective Destination Agent Resource IDs. We will do this
        by extracting maps of the Destination Agent Resources and then
        performing a lookup with the Page objects in our pages_list.
        """

        pages_mod = copy.deepcopy(pages_list)

        intents_map = self.intents.get_intents_map(agent_id, reverse=True)
        entities_map = self.entities.get_entities_map(agent_id, reverse=True)
        webhooks_map = self.webhooks.get_webhooks_map(agent_id, reverse=True)
        flows_map = self.flows.get_flows_map(agent_id, reverse=True)
        pages_map = self.pages.get_pages_map(flows_map[flow], reverse=True)
        rgs_map = self.route_groups.get_route_groups_map(
            flows_map[flow], reverse=True
        )

        # For each page, recurse through the resources and look for
        # specific resource types that have been replaced with literal
        # string display_name. Perform a lookup using the map resources
        # and replace the str display_name with the appropriate str UUID

        for page in pages_mod:
            page.name = pages_map[page.display_name]

            if 'entry_fulfillment' in page:
                page = self._convert_entry_webhooks(page, webhooks_map)

            if 'transition_routes' in page:
                page = self._convert_trans_routes(
                    page, pages_map, intents_map, webhooks_map,
                    convert_type='destination'
                )

            if 'event_handlers' in page:
                page = self._convert_event_handlers(
                    page, pages_map, webhooks_map, convert_type='destination')


            if 'form' in page:
                if 'parameters' in page.form:
                    page = self._convert_form_parameters(
                        page, pages_map, webhooks_map, entities_map,
                        convert_type='destination')

            if 'transition_route_groups' in page:
                temp_list = []
                for trg in page.transition_route_groups:
                    temp_list.append(rgs_map[trg])

                page.transition_route_groups = temp_list

        return pages_mod

    def convert_start_page_dependencies(
        self,
        agent_id,
        start_page,
        agent_type='source',
        flow='Default Start Flow',
    ):
        """Convert all Source Agent Start page dependencies to Display Names.

        In order to copy resources over to a Destination Agent, we need to
        first convert all of the Resource IDs to their respective Display
        Names. We will then use the Display Names to convert back to the
        Destination Agent resource IDs using another method. Start Pages are a
        special type of Page that exists inside of the Flow object, so they
        have to be handled differently.
        """
        page_mod = copy.deepcopy(start_page)

        if agent_type == 'source':
            intents_map = self.intents.get_intents_map(agent_id)
            webhooks_map = self.webhooks.get_webhooks_map(agent_id)
            flows_map = self.flows.get_flows_map(agent_id, reverse=True)
            pages_map = self.pages.get_pages_map(flows_map[flow])

            for trans_route in page_mod.transition_routes:
                if 'target_page' in trans_route:
                    if trans_route.target_page.split('/')[-1] == 'END_FLOW':
                        trans_route.target_page = 'END_FLOW'
                    elif trans_route.target_page.split('/')[-1] == 'START_PAGE':
                        trans_route.target_page = 'START_PAGE'
                    else:
                        trans_route.target_page = pages_map[
                            trans_route.target_page]

                if 'intent' in trans_route:
                    trans_route.intent = intents_map[trans_route.intent]
                    if 'webhook' in trans_route.trigger_fulfillment:
                        trans_route.trigger_fulfillment.webhook = webhooks_map[
                            trans_route.trigger_fulfillment.webhook
                        ]
                elif ('condition' in trans_route and
                'webhook' in trans_route.trigger_fulfillment):
                    trans_route.trigger_fulfillment.webhook = webhooks_map[
                        trans_route.trigger_fulfillment.webhook
                    ]

        elif agent_type == 'destination':
            final_trs = []
            intents_map = self.intents.get_intents_map(agent_id, reverse=True)
            webhooks_map = self.webhooks.get_webhooks_map(
                agent_id, reverse=True
            )
            flows_map = self.flows.get_flows_map(agent_id, reverse=True)
            pages_map = self.pages.get_pages_map(flows_map[flow], reverse=True)

            page_mod.name = flows_map[flow]
            print(page_mod.name)

            for trans_route in page_mod.transition_routes:
                if 'target_page' in trans_route:
                    if trans_route.target_page in ['END_FLOW', 'START_PAGE']:
                        if trans_route.target_page == 'END_FLOW':
                            trans_route.target_page = (
                                flows_map[flow] + '/pages/END_FLOW')
                        elif trans_route.target_page == 'START_PAGE':
                            trans_route.target_page = (
                                flows_map[flow] + '/pages/START_PAGE'
                            )

                    elif trans_route.target_page in pages_map:
                        trans_route.target_page = pages_map[
                            trans_route.target_page]

                if 'intent' in trans_route:
                    if trans_route.intent not in intents_map:
                        logging.info(
                            'Intent %s not in Intents Map. Skipping.',
                            trans_route.intent)
                    elif trans_route.intent in intents_map:
                        trans_route.intent = intents_map[trans_route.intent]
                        if 'webhook' in trans_route.trigger_fulfillment:
                            trans_route.trigger_fulfillment.webhook = (
                                webhooks_map[
                                    trans_route.trigger_fulfillment.webhook
                                    ]
                            )

                        final_trs.append(trans_route)

                elif ('condition' in trans_route and
                'webhook' in trans_route.trigger_fulfillment):
                    trans_route.trigger_fulfillment.webhook = webhooks_map[
                        trans_route.trigger_fulfillment.webhook
                    ]
                    final_trs.append(trans_route)

            page_mod.transition_routes = final_trs

        return page_mod


    def get_page_dependencies(self, obj_list):
        """Pass in DFCX Page object(s) and retrieve all resource dependencies.

        Args:
            - obj_list, a List of one or more DFCX Page Objects

        Returns:
            - resources, Dictionary containing all of the resource objects
        """
        resources = defaultdict(list)
        flow_id = '/'.join(obj_list[0].name.split('/')[0:8])

        # Loop through Pages and find all dependencies
        for page in obj_list:
            resources = self._get_entry_webhooks(page, resources)
            resources = self._get_condition_route_webhooks(page, resources)
            resources = self._get_intent_route_intents(page, resources)
            resources = self._get_form_entity_types(page, resources)
            resources = self._get_route_groups_and_intents(page, flow_id,
              resources)

        # Start Pages of Flows are special Page-like objects and have different
        # structure, so we need to extract the resources from them differently.
        resources = self._get_flow_intent_route_intents(
            flow_id, obj_list, resources)

        # Final check to look for additional Entity dependencies
        if 'intents' in resources:
            resources = self._get_intent_entity_dependencies(resources)

        for key in resources:
            resources[key] = set(resources[key])

        return resources
