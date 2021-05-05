import copy
import json
import logging
import pandas as pd
import time
import google.cloud.dialogflowcx_v3beta1.types as types

from collections import defaultdict
from typing import Dict, List
from ..core import intents, entity_types, flows, pages, webhooks, transition_route_groups

# logging config
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)-8s %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S')


class CopyUtil:
    def __init__(self, creds, agent_id=None):
        self.intents = intents.Intents(creds)
        self.entities = entity_types.EntityTypes(creds)
        self.flows = flows.Flows(creds)
        self.pages = pages.Pages(creds)
        self.webhooks = webhooks.Webhooks(creds)
        self.route_groups = transition_route_groups.TransitionRouteGroups(
            creds)


# COPY FUNCTIONS


    def copy_intent_to_agent(
            self,
            intent_display_name: str,
            source_agent: str,
            destination_agent: str,
            copy_option: str = 'create'):
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
            source_entities_map = self.entities.get_entities_map(source_agent)
            destination_entities_map = self.entities.get_entities_map(
                destination_agent, reverse=True)

            for param in intent_object.parameters:
                if 'sys.' in param.entity_type:
                    pass
                else:
                    source_name = source_entities_map[param.entity_type]
                    destination_name = destination_entities_map[source_name]
                    param.entity_type = destination_name

        # if copy_option = update, pull existing intent from destination agent
        if copy_option == 'update':
            destination_intents = self.intents.list_intents(destination_agent)
            for intent in destination_intents:
                if intent.display_name == intent_display_name:
                    destination_intent_obj = intent

        # push to destination agent
        try:
            if copy_option == 'create':
                self.intents.create_intent(destination_agent, intent_object)
                logging.info(
                    'Intent \'{}\' created successfully'.format(
                        intent_object.display_name))
            elif copy_option == 'update':
                self.intents.update_intent(destination_intent_obj.name,
                                           intent_object)
                logging.info(
                    'Intent \'{}\' updated successfully'.format(
                        intent_object.display_name))
            else:
                logging.info(
                    'Invalid copy option. Please use \'create\' or \'update\'')
        except Exception as e:
            print(e)
            print(
                'If you are trying to update an existing Intent, see method dfcx.update_intent()')

    def copy_entity_type_to_agent(
            self,
            entity_type_display_name,
            source_agent,
            destination_agent):
        # retrieve from source agent
        entity_map = self.entities.get_entities_map(source_agent, reverse=True)
        entity_id = entity_map[entity_type_display_name]
        entity_object = self.entities.get_entity_type(entity_id)

        # push to destination agent
        try:
            self.entities.create_entity_type(destination_agent, entity_object)
            logging.info(
                'Entity Type \'{}\' created successfully'.format(
                    entity_object.display_name))
        except BaseException:
            logging.info(
                'Entity Type \'{}\' already exists in agent'.format(
                    entity_object.display_name))
            logging.info(
                'If you are trying to update an existing Entity, see method dfcx.update_entity_type()')

    def create_page_shells(self,
                           pages_list: List[types.Page],
                           destination_agent: str,
                           destination_flow: str = 'Default Start Flow'):
        """ Create blank DFCX Page object(s) with given Display Name.

        This function aids in the copy/pasting of pages from one DFCX agent to
        another by first creating blank Page "shells" in the destination agent
        using the human-readable display names. These Pages will then be retrieved
        by Page ID to use in the final copy/paste of the Page object from source to
        destination.

        Args:
          pages_list, List of Page(s) object to extract page names from
          destination_agent, DFCX Agent ID of the Destination Agent
          destination_flow, DFCX Flow ID of the Destination Flow. If no Flow ID is
            provided, Default Start Flow will be used.

        Returns:
          Success!
        """

        destination_flows = self.flows.get_flows_map(
            destination_agent, reverse=True)

        for page in pages_list:
            try:
                self.pages.create_page(
                    destination_flows[destination_flow],
                    display_name=page.display_name)
                logging.info(
                    'Page \'{}\' created successfully'.format(
                        page.display_name))
            except Exception as e:
                logging.info(e)
                logging.info(
                    'Page \'{}\' already exists in agent'.format(
                        page.display_name))
                continue

    def copy_paste_agent_resources(self,
                                   resource_dict: Dict[str,
                                                       str],
                                   source_agent: str,
                                   destination_agent: str,
                                   destination_flow: str = 'Default Start Flow',
                                   skip_list: List[str] = []):
        """ Copy/Paste Agent level resources from one DFCX agent to another.

        Agent level resources in DFCX are resources like Entities, Intents, and
        Webhooks which are not Flow dependent. This method allows the user to
        provide a dictionary of Agent Resources and Resources IDs to be copied
        from a Source agent to a Destination agent. *NOTE* That this method
        will also copy all Route Groups from Default Start Flow only.

        To obtain the resource_dict in the proper format, you can use the
        get_page_dependencies() method included in the DFFX library.

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
        resource_obj_dict = defaultdict(list)
        resource_skip_list = defaultdict(list)

        # COPY
        if 'entities' not in skip_list:
            source_entities = self.entities.list_entity_types(source_agent)
            for entity in source_entities:
                if entity.name in resource_dict['entities']:
                    resource_obj_dict['entities'].append(entity)

        if 'intents' not in skip_list:
            source_intents = self.intents.list_intents(source_agent)
            for intent in source_intents:
                if intent.name in resource_dict['intents']:
                    resource_obj_dict['intents'].append(intent)

        if 'webhooks' not in skip_list:
            source_webhooks = self.webhooks.list_webhooks(source_agent)
            for webhook in source_webhooks:
                if webhook.name in resource_dict['webhooks']:
                    resource_obj_dict['webhooks'].append(webhook)

        if 'route_groups' not in skip_list:
            source_flows_map = self.flows.get_flows_map(
                source_agent, reverse=True)
            source_route_groups = self.route_groups.list_transition_route_groups(
                source_flows_map['Default Start Flow'])
            for rg in source_route_groups:
                if rg.name in resource_dict['route_groups']:
                    resource_obj_dict['route_groups'].append(rg)

        # TODO (pmarlow@): Add more descriptive Error Handling messages
        # TODO (pmarlow@): Need to identify strategy for dedupe logic / Design
        # Doc
        """ Notes
            - We don't have timestamp to determine when a resource was created so we can't use 'latest'
            - Need to allow user to determine merge strategy depending on type of resource
        """
        # PASTE
        if 'webhooks' in resource_obj_dict and 'webhooks' not in skip_list:
            # Attempt to Create the new Webhook Resource. If the Resource is
            # a duplicate, then we will skip it. Duplicate is determined by
            # display_name only at this time.
            for webhook in resource_obj_dict['webhooks']:
                logging.info(
                    'Creating Webhook \'{}\'...'.format(
                        webhook.display_name))
                try:
                    self.webhooks.create_webhook(destination_agent, webhook)
                    resource_skip_list['webhooks'].append(webhook.display_name)
                    logging.info(
                        'Webhook \'{}\' created successfully.'.format(
                            webhook.display_name))

                except Exception as e:
                    logging.info(e)
                    pass

        if 'entities' in resource_obj_dict and 'entities' not in skip_list:
            for entity in resource_obj_dict['entities']:
                logging.info(
                    'Creating Entity \'{}\'...'.format(
                        entity.display_name))
                # Attempt to Create the new Entity Resource. If the Resource is
                # a duplicate, then we will skip it. Duplicate is determined by
                # display_name only at this time.
                try:

                    self.entities.create_entity_type(destination_agent, entity)
                    resource_skip_list['entities'].append(entity.display_name)
                    logging.info(
                        'Entity \'{}\' created successfully.'.format(
                            entity.display_name))
                except Exception as e:
                    print(e)
                    pass

        if 'intents' in resource_obj_dict and 'intents' not in skip_list:
            source_entities_map = self.entities.get_entities_map(source_agent)
            destination_entities_map = self.entities.get_entities_map(
                destination_agent, reverse=True)
            for intent in resource_obj_dict['intents']:
                logging.info(
                    'Creating Intent \'{}\'...'.format(
                        intent.display_name))
                time.sleep(1)
                # If Intents contain Entity tags, we need to convert those to the new Agent ID string
                # Check to see if any Intents need Entity conversion before
                # creating
                if 'parameters' in intent:
                    for param in intent.parameters:
                        if 'sys.' in param.entity_type:
                            pass
                        else:
                            source_name = source_entities_map[param.entity_type]
                            destination_name = destination_entities_map[source_name]
                            param.entity_type = destination_name

                # Attempt to Create the new Intent Resource. If the Resource is
                # a duplicate, then we will skip it. Duplicate is determined by
                # display_name only at this time.
                try:
                    self.intents.create_intent(destination_agent, intent)
                    resource_skip_list['intents'].append(intent.display_name)
                    logging.info(
                        'Intent \'{}\' created successfully'.format(
                            intent.display_name))
                except Exception as e:
                    print(e)
                    pass

        if 'route_groups' in resource_obj_dict and 'route_groups' not in skip_list:
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
                destination_flows[destination_flow], reverse=True)

            for rg in resource_obj_dict['route_groups']:
                logging.info(
                    'Creating Route Group \'{}\'...'.format(
                        rg.display_name))
                for tr in rg.transition_routes:
                    source_name = source_intents_map[tr.intent]
                    destination_name = destination_intents_map[source_name]
                    tr.intent = destination_name

                    if 'trigger_fulfillment' in tr:
                        if 'webhook' in tr.trigger_fulfillment:
                            source_webhook = source_webhooks_map[tr.trigger_fulfillment.webhook]
                            destination_webhook = destination_webhooks_map[source_webhook]
                            tr.trigger_fulfillment.webhook = destination_webhook

                    if 'target_page' in tr:
                        if tr.target_page.split('/')[-1] == 'END_FLOW':
                            tr.target_page = destination_flows[destination_flow] + \
                                '/pages/END_FLOW'
                        else:
                            source_page = source_pages_map[tr.target_page]
                            destination_page = destination_pages_map[source_page]
                            tr.target_page = destination_page

                try:
                    self.route_groups.create_transition_route_group(
                        destination_flows[destination_flow], rg)
                    resource_skip_list['route_groups'].append(rg.display_name)
                    logging.info(
                        'Route Group \'{}\' created successfully'.format(
                            rg.display_name))
                except Exception as e:
                    print(e)
                    pass

        return resource_skip_list

    def convert_page_dependencies(self,
                                  agent_id: str,
                                  pages: List[types.Page],
                                  agent_type: str = 'source',
                                  flow: str = 'Default Start Flow') -> List[types.Page]:

        pages_mod = copy.deepcopy(pages)

        if agent_type == 'source':
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
                    if 'webhook' in page.entry_fulfillment:
                        page.entry_fulfillment.webhook = webhooks_map[page.entry_fulfillment.webhook]

                if 'transition_routes' in page:
                    for tr in page.transition_routes:
                        if 'target_page' in tr:
                            if tr.target_page.split('/')[-1] == 'END_FLOW':
                                tr.target_page = 'END_FLOW'

                            elif tr.target_page.split('/')[-1] == 'END_SESSION':
                                tr.target_page = 'END_SESSION'

                            elif tr.target_page.split('/')[-1] == 'CURRENT_PAGE':
                                tr.target_page = 'CURRENT_PAGE'

                            else:
                                tr.target_page = pages_map[tr.target_page]

                        if 'intent' in tr:
                            tr.intent = intents_map[tr.intent]
                            if 'webhook' in tr.trigger_fulfillment:
                                tr.trigger_fulfillment.webhook = webhooks_map[tr.trigger_fulfillment.webhook]
                        elif 'condition' in tr and 'webhook' in tr.trigger_fulfillment:
                            tr.trigger_fulfillment.webhook = webhooks_map[tr.trigger_fulfillment.webhook]

                if 'event_handlers' in page:
                    for handler in page.event_handlers:
                        if 'target_page' in handler:
                            if handler.target_page.split(
                                    '/')[-1] == 'END_FLOW':
                                handler.target_page = 'END_FLOW'

                            elif handler.target_page.split('/')[-1] == 'END_SESSION':
                                handler.target_page = 'END_SESSION'

                            elif handler.target_page.split('/')[-1] == 'CURRENT_PAGE':
                                handler.target_page = 'CURRENT_PAGE'

                            else:
                                handler.target_page = pages_map[handler.target_page]

                        if 'trigger_fulfillment' in handler:
                            if 'webhook' in handler.trigger_fulfillment:
                                handler.trigger_fulfillment.webhook = webhooks_map[
                                    handler.trigger_fulfillment.webhook]

                if 'form' in page:
                    if 'parameters' in page.form:
                        for param in page.form.parameters:
                            if 'fill_behavior' in param:
                                if 'initial_prompt_fulfillment' in param.fill_behavior:
                                    if 'webhook' in param.fill_behavior.initial_prompt_fulfillment:
                                        param.fill_behavior.initial_prompt_fulfillment.webhook = webhooks_map[
                                            param.fill_behavior.initial_prompt_fulfillment.webhook]

                                if 'reprompt_event_handlers' in param.fill_behavior:
                                    for handler in param.fill_behavior.reprompt_event_handlers:
                                        if 'trigger_fulfillment' in handler:
                                            if 'webhook' in handler.trigger_fulfillment:
                                                handler.trigger_fulfillment.webhook = webhooks_map[
                                                    handler.trigger_fulfillment.webhook]

                                        if 'target_page' in handler:
                                            print(handler.target_page)
                                            if handler.target_page.split(
                                                    '/')[-1] == 'END_FLOW':
                                                handler.target_page = 'END_FLOW'

                                            elif handler.target_page.split('/')[-1] == 'END_SESSION':
                                                handler.target_page = 'END_SESSION'

                                            elif handler.target_page.split('/')[-1] == 'CURRENT_PAGE':
                                                handler.target_page = 'CURRENT_PAGE'

                                            else:
                                                handler.target_page = pages_map[handler.target_page]

                            if 'sys.' in param.entity_type:
                                pass
                            else:
                                param.entity_type = entities_map[param.entity_type]

                if 'transition_route_groups' in page:
                    temp_list = []
                    for trg in page.transition_route_groups:
                        temp_list.append(rgs_map[trg])

                        page.transition_route_groups = temp_list

        if agent_type == 'destination':
            intents_map = self.intents.get_intents_map(agent_id, reverse=True)
            entities_map = self.entities.get_entities_map(
                agent_id, reverse=True)
            webhooks_map = self.webhooks.get_webhooks_map(
                agent_id, reverse=True)
            flows_map = self.flows.get_flows_map(agent_id, reverse=True)
            pages_map = self.pages.get_pages_map(flows_map[flow], reverse=True)
            rgs_map = self.route_groups.get_route_groups_map(
                flows_map[flow], reverse=True)

            # For each page, recurse through the resources and look for
            # specific resource types that have been replaced with literal
            # string display_name. Perform a lookup using the map resources
            # and replace the str display_name with the appropriate str UUID

            for page in pages_mod:
                page.name = pages_map[page.display_name]

                if 'entry_fulfillment' in page:
                    if 'webhook' in page.entry_fulfillment:
                        page.entry_fulfillment.webhook = webhooks_map[page.entry_fulfillment.webhook]

                if 'transition_routes' in page:
                    for tr in page.transition_routes:
                        if 'target_page' in tr:
                            if tr.target_page == 'END_FLOW':
                                tr.target_page = flows_map[flow] + \
                                    '/pages/END_FLOW'

                            elif tr.target_page == 'END_SESSION':
                                tr.target_page = flows_map[flow] + \
                                    '/pages/END_SESSION'

                            elif tr.target_page == 'CURRENT_PAGE':
                                tr.target_page = flows_map[flow] + \
                                    '/pages/CURRENT_PAGE'

                            else:
                                tr.target_page = pages_map[tr.target_page]

                        if 'intent' in tr:
                            tr.intent = intents_map[tr.intent]
                            if 'webhook' in tr.trigger_fulfillment:
                                tr.trigger_fulfillment.webhook = webhooks_map[tr.trigger_fulfillment.webhook]
                        elif 'condition' in tr and 'webhook' in tr.trigger_fulfillment:
                            tr.trigger_fulfillment.webhook = webhooks_map[tr.trigger_fulfillment.webhook]

                if 'event_handlers' in page:
                    for handler in page.event_handlers:
                        if 'target_page' in handler:
                            if handler.target_page == 'END_FLOW':
                                handler.target_page = flows_map[flow] + \
                                    '/pages/END_FLOW'

                            elif handler.target_page == 'END_SESSION':
                                handler.target_page = flows_map[flow] + \
                                    '/pages/END_SESSION'

                            elif handler.target_page == 'CURRENT_PAGE':
                                handler.target_page = flows_map[flow] + \
                                    '/pages/CURRENT_PAGE'

                            else:
                                handler.target_page = pages_map[handler.target_page]

                        if 'trigger_fulfillment' in handler:
                            if 'webhook' in handler.trigger_fulfillment:
                                handler.trigger_fulfillment.webhook = webhooks_map[
                                    handler.trigger_fulfillment.webhook]

                if 'form' in page:
                    if 'parameters' in page.form:
                        for param in page.form.parameters:
                            if 'fill_behavior' in param:
                                if 'initial_prompt_fulfillment' in param.fill_behavior:
                                    if 'webhook' in param.fill_behavior.initial_prompt_fulfillment:
                                        param.fill_behavior.initial_prompt_fulfillment.webhook = webhooks_map[
                                            param.fill_behavior.initial_prompt_fulfillment.webhook]
                                if 'reprompt_event_handlers' in param.fill_behavior:
                                    for handler in param.fill_behavior.reprompt_event_handlers:
                                        if 'trigger_fulfillment' in handler:
                                            if 'webhook' in handler.trigger_fulfillment:
                                                handler.trigger_fulfillment.webhook = webhooks_map[
                                                    handler.trigger_fulfillment.webhook]

                                        if 'target_page' in handler:
                                            if handler.target_page == 'END_FLOW':
                                                handler.target_page = flows_map[flow] + \
                                                    '/pages/END_FLOW'

                                            elif handler.target_page == 'END_SESSION':
                                                handler.target_page = flows_map[flow] + \
                                                    '/pages/END_SESSION'

                                            elif handler.target_page == 'CURRENT_PAGE':
                                                handler.target_page = flows_map[flow] + \
                                                    '/pages/CURRENT_PAGE'

                                            else:
                                                handler.target_page = pages_map[handler.target_page]

                            if 'sys.' in param.entity_type:
                                pass
                            else:
                                param.entity_type = entities_map[param.entity_type]

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
            flow='Default Start Flow'):
        page_mod = copy.deepcopy(start_page)

        if agent_type == 'source':
            print(page_mod.name)
            intents_map = self.intents.get_intents_map(agent_id)
            webhooks_map = self.webhooks.get_webhooks_map(agent_id)
            flows_map = self.flows.get_flows_map(agent_id, reverse=True)
            pages_map = self.pages.get_pages_map(flows_map[flow])

            for tr in page_mod.transition_routes:
                if 'target_page' in tr:
                    if tr.target_page.split('/')[-1] == 'END_FLOW':
                        tr.target_page = 'END_FLOW'
                    elif tr.target_page.split('/')[-1] == 'START_PAGE':
                        tr.target_page = 'START_PAGE'
                    else:
                        tr.target_page = pages_map[tr.target_page]

                if 'intent' in tr:
                    tr.intent = intents_map[tr.intent]
                    if 'webhook' in tr.trigger_fulfillment:
                        tr.trigger_fulfillment.webhook = webhooks_map[tr.trigger_fulfillment.webhook]
                elif 'condition' in tr and 'webhook' in tr.trigger_fulfillment:
                    tr.trigger_fulfillment.webhook = webhooks_map[tr.trigger_fulfillment.webhook]

            return page_mod

        elif agent_type == 'destination':
            final_trs = []
            intents_map = self.intents.get_intents_map(agent_id, reverse=True)
            webhooks_map = self.webhooks.get_webhooks_map(
                agent_id, reverse=True)
            flows_map = self.flows.get_flows_map(agent_id, reverse=True)
            pages_map = self.pages.get_pages_map(flows_map[flow], reverse=True)

            page_mod.name = flows_map[flow]
            print(page_mod.name)

            for tr in page_mod.transition_routes:
                if 'target_page' in tr:
                    if tr.target_page in ['END_FLOW', 'START_PAGE']:
                        if tr.target_page == 'END_FLOW':
                            tr.target_page = flows_map[flow] + \
                                '/pages/END_FLOW'
                        elif tr.target_page == 'START_PAGE':
                            tr.target_page = flows_map[flow] + \
                                '/pages/START_PAGE'

                    elif tr.target_page in pages_map:
                        tr.target_page = pages_map[tr.target_page]

                if 'intent' in tr:
                    if tr.intent not in intents_map:
                        print(
                            'Intent \'{}\' not in Intents Map. Skipping.'.format(
                                tr.intent))
                    elif tr.intent in intents_map:
                        tr.intent = intents_map[tr.intent]
                        if 'webhook' in tr.trigger_fulfillment:
                            tr.trigger_fulfillment.webhook = webhooks_map[tr.trigger_fulfillment.webhook]

                        final_trs.append(tr)

                elif 'condition' in tr and 'webhook' in tr.trigger_fulfillment:
                    tr.trigger_fulfillment.webhook = webhooks_map[tr.trigger_fulfillment.webhook]
                    final_trs.append(tr)

            page_mod.transition_routes = final_trs

            return page_mod


# PAGE FUNCTIONS


    def get_page_dependencies(self, obj_list):
        """ Pass in DFCX Page object(s) and retrieve all resource dependencies.

        Args:
            - obj_list, a List of one or more DFCX Page Objects

        Returns:
            - resources, Dictionary containing all of the resource objects
        """

        resources = defaultdict(list)

        flow_id = '/'.join(obj_list[0].name.split('/')[0:8])
        route_groups = self.route_groups.list_transition_route_groups(flow_id)

        # Loop through Pages and find all dependencies
        for page in obj_list:
            if 'entry_fulfillment' in page and 'webhook' in page.entry_fulfillment:
                resources['webhooks'].append(page.entry_fulfillment.webhook)
            if 'transition_routes' in page:
                for tr in page.transition_routes:
                    if 'intent' in tr:
                        resources['intents'].append(tr.intent)
                    elif 'condition' in tr and 'webhook' in tr.trigger_fulfillment:
                        resources['webhooks'].append(
                            tr.trigger_fulfillment.webhook)
            if 'form' in page:
                if 'parameters' in page.form:
                    for param in page.form.parameters:
                        if 'sys.' in param.entity_type:
                            continue
                        else:
                            resources['entities'].append(param.entity_type)

            if 'transition_route_groups' in page:
                for trg in page.transition_route_groups:
                    resources['route_groups'].append(trg)
                    for rg in route_groups:
                        if trg == rg.name:
                            for tr in rg.transition_routes:
                                resources['intents'].append(tr.intent)

        # Loop through Default Start Page and identify dependencies
        source_flow = self.flows.get_flow(flow_id)
        temp_page_name_list = [page.name for page in obj_list]
        for tr in source_flow.transition_routes:
            if 'intent' in tr:
                if tr.target_page in temp_page_name_list:
                    resources['intents'].append(tr.intent)

        # Loop through Intents to identify any additional Entity dependencies
        if 'intents' in resources:
            agent = '/'.join(resources['intents'][0].split('/')[0:6])
            intents = self.intents.list_intents(agent)

            for intent in intents:
                if intent.name in resources['intents']:
                    if len(intent.parameters) > 0:
                        for param in intent.parameters:
                            if 'sys.' in param.entity_type:
                                continue
                            else:
                                resources['entities'].append(param.entity_type)

        for key in resources:
            resources[key] = set(resources[key])

        return resources
