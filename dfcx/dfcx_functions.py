import logging
import json
import pandas as pd
import pathlib
from collections import defaultdict
from dfcx.dfcx import DialogflowCX

# logging config
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)-8s %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S')

class DialogflowFunctions:
    def __init__(self, creds, agent_id=None):
            
        with open(creds) as json_file:
            data = json.load(json_file)
        project_id = data['project_id']
        
        self.project_id = 'projects/{}/locations/global'.format(project_id)

        if agent_id:
            self.dfcx = DialogflowCX(creds, agent_id)
            self.agent_id = self.project_id + agent_id

        else:
            self.dfcx = DialogflowCX(creds)
    
    
    def get_flows_map(self, agent_id=None):
        """ Exports Agent Flow Names and UUIDs into a user friendly dict.
        
        Args:
          - agent_id (Optional), the formatted CX Agent ID to use
          
        Returns:
          - flows_map, Dictionary containing flow UUIDs as keys and 
              flow.display_name as values
          """
        
        flows_dict = {flow.display_name: flow.name 
                      for flow in self.dfcx.list_flows(agent_id)}
        
        return flows_dict
    
    
    def get_intents_map(self, agent_id=None, reverse=False):
        """ Exports Agent Intent Names and UUIDs into a user friendly dict.
        
        Args:
          - agent_id (Optional), the formatted CX Agent ID to use
          
        Returns:
          - intents_map, Dictionary containing Intent UUIDs as keys and 
              intent.display_name as values
          """
        
        if reverse:
            intents_dict = {intent.display_name:intent.name
                            for intent in self.dfcx.list_intents(agent_id)}
        
        else:
            intents_dict = {intent.name.split('/')[-1]:intent.display_name 
                       for intent in self.dfcx.list_intents(agent_id)}
        
        return intents_dict
    
    def get_entities_map(self, agent_id=None, reverse=False):
        """ Exports Agent Entityt Names and UUIDs into a user friendly dict.
        
        Args:
          - agent_id (Optional), the formatted CX Agent ID to use
          
        Returns:
          - intents_map, Dictionary containing Entity UUIDs as keys and 
              intent.display_name as values
          """
        
        if reverse:
            entities_dict = {entity.display_name:entity.name
                            for entity in self.dfcx.list_entity_types(agent_id)}
        
        else:
            entities_dict = {entity.name.split('/')[-1]:entity.display_name 
                       for entity in self.dfcx.list_entity_types(agent_id)}
        
        return entities_dict
    
    
    def get_webhooks_map(self, agent_id=None, reverse=False):
        """ Exports Agent Webhook Names and UUIDs into a user friendly dict.
        
        Args:
          - agent_id (Optional), the formatted CX Agent ID to use
          
        Returns:
          - webhooks_map, Dictionary containing Webhook UUIDs as keys and
              webhook.display_name as values
          """
        
        if reverse:
            webhooks_dict = {webhook.display_name:webhook.name 
                             for webhook in self.dfcx.list_webhooks(agent_id)}
            
        else:
            webhooks_dict = {webhook.name:webhook.display_name 
                             for webhook in self.dfcx.list_webhooks(agent_id)}
        
        return webhooks_dict
    
    def get_pages_map(self, flow_id, reverse=False):
        """ Exports Agent Page UUIDs and Names into a user friendly dict.
        
        Args:
          - agent_id, the formatted CX Agent ID to use
          - flow_id, the formatted CX Agent Flow ID to use
          - reverse (Optional), provides page_name:ID mapping instead of ID:page_name
          
        Returns:
          - webhooks_map, Dictionary containing Webhook UUIDs as keys and
              webhook.display_name as values. If Optional reverse=True, the 
              output will return page_name:ID mapping instead of ID:page_name
          """
        
        if reverse:
            pages_dict = {page.display_name:page.name 
                          for page in self.dfcx.list_pages(flow_id)}
            
        else:
            pages_dict = {page.name:page.display_name 
                          for page in self.dfcx.list_pages(flow_id)}
            
        return pages_dict
        
### TODO: (pmarlow@) build Agent export function for beginning of CICD pipeline

#    def export_agent_data(self, agent_id=None):
#         """ Exports Agent configuration info by resource type
        
#         Args:
#           - agent_id (Optional), the formatted CX Agent ID to export
          
#         Returns:
#           - No return other than files saved to local disk.
#         """
        
#         if not hasattr(self,'agent_id'):
#             raise Exception("No agent_id is set. Please set the agent_id using `agents.agent_id = <agent_id>`")
            
#         if not self.agent_id and not agent_id:
#             print("Agent Id has not been set. Please set with dfcx.agent_id = <agent_id>")
        
#         agent_data = self.dfcx.get_agent()
#         logging.info(agent_data)
#         intent_data = self.dfcx.list_intents()
#         logging.info(intent_data[0])
        
#         # agent level data
#         # entity_type data
#         # environments data
#         # flows data
#         # intents data
#         # pages data
#         # versions data
#         # webhooks data
#         # transition route groups data
        

    def route_groups_to_dataframe(self, agent_id=None):
        """ This method extracts the Transition Route Groups from a given DFCX Agent 
        and returns key information about the Route Groups in a Pandas Dataframe
        
        DFCX Route Groups exist as an Agent level resource, however they are 
        categorized by the Flow they are associated with. This method will
        extract all Flows for the given agent, then use the Flow IDs to 
        extract all Route Groups per Flow. Once all Route Groups have been
        extracted, the method will convert the DFCX object to a Pandas
        Dataframe and return this to the user.
        
        Args:
          - agent_id, the Agent ID string in the following format:
            projects/<project_id>/locations/<location_id>/agents/<agent_id>
          
        Returns:
          - df, a Pandas Dataframe
        """
        
        if not agent_id:
            agent_id = self.agent_id            
        
        # The following dicts and lists are setup to use to map "user friendly"
        # data labels before writing the Route Group object to a dataframe.
        flows_dict = {flow.display_name: flow.name for flow in self.dfcx.list_flows(agent_id)}
                
        intent_dict = {intent.name.split('/')[-1]:intent.display_name 
                       for intent in self.dfcx.list_intents(agent_id)}
        
        webhooks_dict = {webhook.name.split('/')[-1]:webhook.display_name 
                         for webhook in self.dfcx.list_webhooks(agent_id)}
                
        route_groups_dict = {flow:self.dfcx.list_transition_route_groups(flows_dict[flow]) for flow in flows_dict}

        rows_list = []
        for flow in route_groups_dict:
            for route_group in route_groups_dict[flow]:
                for route in route_group.transition_routes:
                    temp_dict = {}

                    temp_dict.update({'flow':flow})
                    temp_dict.update({'route_group_name':route_group.display_name})
                    temp_dict.update({'intent':intent_dict[route.intent.split('/')[-1]]})
                    
                    if route.trigger_fulfillment.webhook:temp_dict.update({'webhook':webhooks_dict[route.trigger_fulfillment.webhook.split('/')[-1]]})
                        
                    temp_dict.update({'webhook_tag':route.trigger_fulfillment.tag})
                    
                    if len(route.trigger_fulfillment.messages) > 0:
                        if len(route.trigger_fulfillment.messages[0].text.text) > 0:
                            temp_dict.update({'fulfillment_message':route.trigger_fulfillment.messages[0].text.text[0]})

                    rows_list.append(temp_dict)
                    
            
        df = pd.DataFrame(rows_list)
            
        return df

    def intents_to_dataframe(self,intents):
        """
        This functions takes an Intents object from the DFCX API and returns
        a Pandas Dataframe
        """
        intent_dict = defaultdict(list)

        for element in intents:
            if 'training_phrases' in element:
                for tp in element.training_phrases:
                    s = []
                    if len(tp.parts) > 1:
                        for item in tp.parts:
                            s.append(item.text)
                        intent_dict[element.display_name].append(''.join(s))
                    else:
                        intent_dict[element.display_name].append(tp.parts[0].text)
            else:
                intent_dict[element.display_name].append('')
                    
        df = pd.DataFrame.from_dict(intent_dict, orient='index').transpose()
        df = df.stack().to_frame().reset_index(level=1)
        df = df.rename(columns={'level_1':'intent',0:'tp'}).reset_index(drop=True)
        df = df.sort_values(['intent','tp'])

        return df

    def agent_intents_to_csv(self,agents):
        """
        This function takes an Agent object in JSON format from the DFCX API, extracts all of the
        Intents and TPs to a dataframe, and then writes them to a CSV files.
        """
        intent_file_list = []
        for agent in agents['agents']:
            # Get agent_id, agent_name from Agent object
            project_id = agent['name'].split('/')[1]
            agent_id = agent['name'].split('/')[-1]
            agent_name = agent['displayName'].replace(" ","_").replace("/","_")

            # Define path and filename to write
#             path = 'agents/{}'.format(agent_name)
            path = 'agents/{}'.format(agent_id)
            filename = 'intents_and_tps.csv'

            logging.info('Getting Intents for Agent: {}'.format(agent_name))
            intents = self.intents.get_intents(agent_id)

            logging.info('Writing Intents to dataframe...')
            df = self.intents_to_dataframe(intents)

            logging.info('Saving dataframe to CSV...')
            pathlib.Path(path).mkdir(parents=True, exist_ok=True) 
            df.to_csv(path+'/'+filename, index=False)

            intent_file_list.append(path+'/'+filename)
            logging.info('CSV write complete.')

        return intent_file_list
