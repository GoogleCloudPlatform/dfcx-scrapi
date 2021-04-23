import logging
import pandas as pd
import google.cloud.dialogflowcx_v3beta1.types as types

from core import entity_types, flows, intents, pages

# logging config
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)-8s %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S')

class SearchUtil:
    def __init__(self, creds_path, agent_id=None):
        self.intents = intents.Intents(creds_path)
        self.entities = entity_types.EntityTypes(creds_path)
        self.flows = flows.Flows(creds_path)
        self.pages = pages.Pages(creds_path)

    def find_list_parameters(self, agent_id):
        """ This method extracts Parameters set at a page level that are
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
        entities_map = self.entities.get_entities_map(agent_id)

        params_list = []

        for flow in flows_map:
            temp_pages = self.pages.list_pages(flows_map[flow])
            for page in temp_pages:
                for param in page.form.parameters:
                    if param.is_list:
                        params_list.append(param.display_name)
                        print('FLOW = {}'.format(flow))
                        print('PAGE = {}'.format(page.display_name))
                        print(param.display_name)
                        if 'sys' in param.entity_type.split('/')[-1]:
                            print(param.entity_type.split('/')[-1])
                        else:
                            print(param.entity_type)
                            print(
                                entities_map[param.entity_type.split('/')[-1]])
                        print('\n')

        return params_list