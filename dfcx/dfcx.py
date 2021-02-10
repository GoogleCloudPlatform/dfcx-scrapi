import json
import logging
import os
import requests
import subprocess
import google.cloud.dialogflowcx_v3beta1.services as services
import google.cloud.dialogflowcx_v3beta1.types as types
from google.auth import credentials
from google.protobuf import field_mask_pb2
from typing import Dict, List

from typing import List

# logging config
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)-8s %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S')

class DialogflowCX:
    def __init__(self, creds_path, agent_id=None):          
        # with open(creds_path) as json_file:
        #     data = json.load(json_file)

        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = creds_path
        
        self.agents = services.agents.AgentsClient()
        self.intents = services.intents.IntentsClient()
        self.entities = services.entity_types.EntityTypesClient()
        self.pages = services.pages.PagesClient()
        self.flows = services.flows.FlowsClient()
        self.sessions = services.sessions.SessionsClient()
        self.route_groups = services.transition_route_groups.TransitionRouteGroupsClient()
        self.webhooks = services.webhooks.WebhooksClient()
            
        if agent_id:
            self.agent_id = agent_id

    @staticmethod
    def _set_region(id):
        location = id.split('/')[3]

        if location != 'global':
            api_endpoint = '{}-dialogflow.googleapis.com:443'.format(location)
            client_options = {'api_endpoint': api_endpoint}

            return client_options
        
            
### TODO (pmarlow@) break each set of Functions into its own Class so that we 
### can separate each Class into its own file to keep file line numbers within
### Google standard for Python classes as they grow.

### AGENT FX

    def list_agents(self, location_id:str) -> List[types.Agent]:
        """Get list of all CX agents in a given GCP project
        
        Args:
          location_id: The GCP Project/Location ID in the following format
              `projects/<GCP PROJECT ID>/locations/<LOCATION ID>
        Returns:
          agents: List of Agent objects
        """
        request = types.agent.ListAgentsRequest()
        request.parent = location_id
        
        client_options = self._set_region(location_id)
        client = services.agents.AgentsClient(client_options=client_options)
        response = client.list_agents(request)
        
        agents = []
        for page in response.pages:
            for agent in page.agents:
                agents.append(agent)
        
        return agents
    
    
    def get_agent(self, agent_id):
        request = types.agent.GetAgentRequest()
        request.name = agent_id
        client_options = self._set_region(agent_id)
        client = services.agents.AgentsClient(client_options=client_options)
        response = client.get_agent(request)
        
        return response

    def create_agent(self, project_id:str, display_name:str, 
    gcp_region:str='global', obj:types.Agent=None, **kwargs):
        """Create a Dialogflow CX Agent with given display name.

        By default the CX Agent will be created in the project that the user
        is currently authenticated to
        If the user provides an existing Agent object, create a new CX agent
        based on this object.

        Args:
          project_id: GCP project id where the CX agent will be created
          display_name: Human readable display name for the CX agent
          gcp_region: GCP region to create CX agent. Defaults to 'global'
          obj: (Optional) Agent object to create new agent from

        Returns:
          response
        """

        if obj:
            agent = obj
            parent = 'projects/{}/location/{}'.format(
                agent.name.split('/')[1], 
                agent.name.split('/')[3])
            agent.display_name = display_name
        else:
            agent = types.agent.Agent()
            parent = 'projects/{}/locations/{}'.format(project_id, gcp_region)
            agent.display_name = display_name

        agent.default_language_code = 'en'
        agent.time_zone='America/Chicago'

        # set optional args as agent attributes
        for key, value in kwargs.items():
            setattr(agent, key, value)

        client_options = self._set_region(parent)
        client = services.agents.AgentsClient(client_options=client_options)
        response = client.create_agent(parent=parent, agent=agent)

        return response

    def validate(self, agent_id:str) -> Dict:
        """Initiates the Validation of the CX Agent or Flow.

        This function will start the Validation feature for the given Agent 
        and then return the results as a Dict.

        Args:
          agent_id: CX Agent ID string in the following format
            projects/<PROJECT ID>/locations/<LOCATION ID>/agents/<AGENT ID>

        Returns:
          results: Dictionary of Validation results for the entire Agent
            or for the specified Flow.
        """
        location = agent_id.split('/')[3]
        if location != 'global':
            base_url = 'https://{}-dialogflow.googleapis.com/v3beta1'.format(location)
        else:
            base_url = 'https://dialogflow.googleapis.com/v3beta1'

        url = '{0}/{1}/validationResult'.format(base_url, agent_id)
        
        token = subprocess.run(['gcloud', 'auth', 'application-default', 'print-access-token'], 
                              stdout=subprocess.PIPE,
                              text=True).stdout

        token = token.strip('\n') # remove newline appended as part of stdout
        headers = {"Authorization": "Bearer {}".format(token)}

        # Make REST call
        results = requests.get(url, headers=headers)
        results.raise_for_status()

        return results.json()


    def get_validation_result(self, agent_id:str, flow_id:str=None) -> Dict:
        """Extract Validation Results from CX Validation feature.

        This function will get the LATEST validation result run for the given
        CX Agent or CX Flow. If there has been no validation run on the Agent
        or Flow, no result will be returned. Use `dfcx.validate` function to
        run Validation on an Agent/Flow.

        Passing in the Agent ID will provide ALL validation results for
        ALL flows.
        Passing in the Flow ID will provide validation results for only
        that Flow ID.
        
        Args:
          agent_id: CX Agent ID string in the following format
            projects/<PROJECT ID>/locations/<LOCATION ID>/agents/<AGENT ID>
          flow_id: (Optional) CX Flow ID string in the following format
            projects/<PROJECT ID>/locations/<LOCATION ID>/agents/<AGENT ID>/flows/<FLOW ID>

        Returns:
          results: Dictionary of Validation results for the entire Agent
            or for the specified Flow.
        """

        if flow_id:
            location = flow_id.split('/')[3]
            if location != 'global':
                base_url = 'https://{}-dialogflow.googleapis.com/v3beta1'.format(location)
            else:
                base_url = 'https://dialogflow.googleapis.com/v3beta1'

            url = '{0}/{1}/validationResult'.format(base_url, flow_id)
        else:
            location = agent_id.split('/')[3]
            if location != 'global':
                base_url = 'https://{}-dialogflow.googleapis.com/v3beta1'.format(location)
            else:
                base_url = 'https://dialogflow.googleapis.com/v3beta1'

            url = '{0}/{1}/validationResult'.format(base_url, agent_id)
        
        token = subprocess.run(['gcloud', 'auth', 'application-default', 'print-access-token'], 
                              stdout=subprocess.PIPE,
                              text=True).stdout

        token = token.strip('\n') # remove newline appended as part of stdout
        headers = {"Authorization": "Bearer {}".format(token)}

        # Make REST call
        results = requests.get(url, headers=headers)
        results.raise_for_status()

        return results.json()


### INTENTS FX    
    
    def list_intents(self, agent_id):
        request = types.intent.ListIntentsRequest()
        request.parent = agent_id
        
        client_options = self._set_region(agent_id)
        client = services.intents.IntentsClient(client_options=client_options)
        response = client.list_intents(request)

        intents = []
        for page in response.pages:
            for intent in page.intents:
                intents.append(intent)

        return intents
    
    def get_intent(self, intent_id):
        client_options = self._set_region(intent_id)
        client = services.intents.IntentsClient(client_options=client_options)
        response = client.get_intent(name=intent_id)
        
        return response
    
    def create_intent(self, agent_id, obj=None, **kwargs):
        #If intent_obj is given, set intent variable to it
        if obj:
            intent = obj
            intent.name = ''
        else:
            intent = types.intent.Intent()

        #Set optional arguments as intent attributes
        for key, value in kwargs.items():
            if key == 'training_phrases':
                assert type(kwargs[key]) == list
                training_phrases = []
                for x in kwargs[key]:
                    if type(x) == dict:
                        tp = types.intent.Intent.TrainingPhrase()
                        parts = []
                        for y in x['parts']:
                            if type(y) == dict:
                                part = types.intent.Intent.TrainingPhrase.Part()
                                part.text = y['text']
                                part.parameter_id = y.get('parameter_id')
                                parts.append(part)
                            else:
                                print("Wrong object in parts list")
                                return
                        tp.parts = parts
                        tp.repeat_count = x.get("repeat_count")
                        training_phrases.append(tp)
                    else:
                        print("Wrong object in training phrases list")
                        return
                setattr(intent, key, training_phrases)
            setattr(intent, key, value)

        client_options = self._set_region(agent_id)
        client = services.intents.IntentsClient(client_options=client_options)
        response = client.create_intent(parent=agent_id, intent=intent)
        
        return response
    
    def update_intent(self, intent_id, obj=None, **kwargs):
        """ Updates a single Intent object based on provided args.
        
        Args:
          intent_id, the destination Intent ID. Must be formatted properly
              for Intent IDs in CX.
          obj, The CX Intent object in proper format. This can also
              be extracted by using the get_intent() method.     
        """
        
        if obj:
            intent = obj
            intent.name = intent_id
        else:
            intent = self.get_intent(intent_id)
        
        client_options = self._set_region(intent_id)
        client = services.intents.IntentsClient(client_options=client_options)
        response = client.update_intent(intent=intent)
        
        return response
    
    
### ENTITIES FX

    def list_entity_types(self, agent_id):
        request = types.entity_type.ListEntityTypesRequest()
        request.parent = agent_id
            
        client = self.entities
        response = client.list_entity_types(request)
        
        entities = []
        for page in response.pages:
            for entity in page.entity_types:
                entities.append(entity)
        
        return entities
    
    def get_entity_type(self, entity_id):
        client = self.entities
        response = client.get_entity_type(name=entity_id)
        
        return response
        

    def create_entity_type(self, agent_id, obj=None, **kwargs):
        #If entity_type_obj is given set entity_type to it
        if obj:
            entity_type = obj
            entity_type.name = ''
        else:
            entity_type = types.entity_type.EntityType()
            
        #set optional arguments to entity type attributes
        for key, value in kwargs.items():
            setattr(entity_type, key, value)

        #Apply any optional functions argument to entity_type object
#         entity_type = set_entity_type_attr(entity_type, kwargs)

        client = self.entities
        response = client.create_entity_type(parent=agent_id, entity_type=entity_type)
        return response
    
    
### FLOWS FX
    
    def list_flows(self, agent_id):
        request = types.flow.ListFlowsRequest()
        request.parent = agent_id
            
        client = self.flows
        response = client.list_flows(request)
        
        flows = []
        for page in response.pages:
            for flow in page.flows:
                flows.append(flow)
        
        return flows
    
    def get_flow(self, flow_id):
        client = self.flows
        response = client.get_flow(name=flow_id)
        
        return response
    
    def update_flow(self, flow_id, obj=None, **kwargs):
        if obj:
            flow = obj
            flow.name = flow_id
        else:
            flow = self.get_flow(flow_id)
            
        # set flow attributes to args
        for key,value in kwargs.items():
            setattr(flow,key,value)
        paths = kwargs.keys()
        mask = field_mask_pb2.FieldMask(paths=paths)
        
        client = self.flows
        response = client.update_flow(flow=flow, update_mask=mask)
        
        return response
    
### PAGES FX

    def list_pages(self, flow_id):
        request = types.page.ListPagesRequest()
        request.parent = flow_id
        
        client = self.pages
        response = client.list_pages(request)
        
        cx_pages = []
        for page in response.pages:
            for cx_page in page.pages:
                cx_pages.append(cx_page)
        
        return cx_pages
    
    def get_page(self, page_id):
        client = self.pages
        response = client.get_page(name=page_id)
        
        return response
    
    def create_page(self, flow_id, obj=None, **kwargs):
        #Intialize client library for pages
        client = services.pages.PagesClient()

        #if page object is given, set page to it
        if obj:
            page = obj
            page.name = ''
        else:
            page = types.page.Page()

        #set optional arguments to page attributes
        for key, value in kwargs.items():  
            setattr(page, key, value)

        response = client.create_page(parent=flow_id, page=page)
        return response
    
    def update_page(self, page_id, obj=None, **kwargs):
        #Initialize client library for pages
        client = services.pages.PagesClient()

        #If page object is given set page to it
        if obj:
            #Set page variable to page object
            page = obj
            #Set name attribute to the name of the updated page
            page.name = page_id
        else:
            page = self.get_page(page_id)

        #Set page attributes to arguments
        for key, value in kwargs.items():
            setattr(page, key, value)
        paths = kwargs.keys()
        mask = field_mask_pb2.FieldMask(paths=paths)

        #Call client function with page and mask as arguments
        response = client.update_page(page=page, update_mask=mask)
        return response
    
    def create_transition_route_old(self, intent=None, condition=None, 
                                target_page=None, target_flow=None, 
                               trigger_fulfillment=None):
        route = types.page.TransitionRoute()
        
        if intent:
            route.intent = intent
            
        if condition:
            route.condition = condition
            
        if target_page:
            route.target_page = target_page
            
        if target_flow:
            route.target_flow = target_flow
            
        if trigger_fulfillment:
            fulfillment = types.fulfillment.Fulfillment()
            
            if 'messages' in trigger_fulfillment:
                response_message = types.response_message.ResponseMessage()
                
                message_text = response_message.Text()
                message_text.text = trigger_fulfillment['messages']
                response_message.text = message_text
                fulfillment.messages = [response_message]
            
            if 'webhook' in trigger_fulfillment:
                fulfillment.webhook = trigger_fulfillment['webhook']
                
            if 'webhook_tag' in trigger_fulfillment:
                fulfillment.tag = trigger_fulfillment['webhook_tag']
                
            route.trigger_fulfillment = fulfillment
            
        return route
    
### ROUTE GROUPS FX
    
    def list_transition_route_groups(self, flow_id):
        request = types.transition_route_group.ListTransitionRouteGroupsRequest()
        request.parent = flow_id
            
        client = self.route_groups
        response = client.list_transition_route_groups(request)
        
        cx_route_groups = []
        for page in response.pages:
            for cx_route_group in page.transition_route_groups:
                cx_route_groups.append(cx_route_group)

        return cx_route_groups
    
    
    def get_transition_route_group(self, name):
        request = types.transition_route_group.GetTransitionRouteGroupRequest()
        request.name = name
        client = self.route_groups
        response = client.get_transition_route_group(request)
        
        return response
    
    
    def create_transition_route_group(self, flow_id, obj, **kwargs):
#         request = types.transition_route_group.CreateTransitionRouteGroupRequest()
        
        #if rg object is given, set rg to it
        if obj:
            trg = obj
            trg.name = ''
        else:
            trg =  types.transition_route_group.TransitionRouteGroup()
        
        # set optional args to rg attributes
        for key, value in kwargs.items():
            setattr(trg,key,value)
                        
#         if obj['display_name']:
#             trg.display_name = route_group['display_name']
            
#         if obj['transition_routes']:
#             trg.transition_routes = route_group['transition_routes']

            
#         request.transition_route_group = trg        
        client = self.route_groups
        response = client.create_transition_route_group(parent=flow_id, transition_route_group=trg)
        
        return response
    
    def update_transition_route_group(self, rg_id, obj=None, **kwargs):
        # If route group object is given set route group to it
        if obj:
            #Set rg variable to rg object
            rg = obj
            #Set name attribute to the name of the updated page
            rg.name = rg_id
        else:
            rg = self.get_transition_route_group(rg_id)

        # Set rg attributes to arguments
        for key, value in kwargs.items():
            setattr(rg, key, value)
        paths = kwargs.keys()
        mask = field_mask_pb2.FieldMask(paths=paths)
                  
        client = self.route_groups
        response = client.update_transition_route_group(transition_route_group=rg, update_mask=mask)
        
        return response

    
### WEBHOOK FX
    
    def list_webhooks(self, agent_id):
        request = types.webhook.ListWebhooksRequest()
        request.parent = agent_id
            
        client = self.webhooks
        response = client.list_webhooks(request)
        
        cx_webhooks = []
        for page in response.pages:
            for cx_webhook in page.webhooks:
                cx_webhooks.append(cx_webhook)
        
        return cx_webhooks
    
    def create_webhook(self, agent_id, obj=None, **kwargs):
        # if webhook object is given, set webhook to it
        if obj:
            webhook = obj
            webhook.name = ''
        else:
            webhook = types.webhook.Webhook()
            
        # set optional kwargs to webhook attributes
        for key, value in kwargs.items():
            setattr(webhook, key, value)
        
        client = self.webhooks
        response = client.create_webhook(parent=agent_id, webhook=webhook)
        
        return response
        
    
### SESSION FX
    def run_conversation(self, agent, session_id, conversation, parameters=None, response_text=False):
        """Tests a full conversation with the bot.

        Using the same `session_id` between requests allows continuation
        of the conversation."""
        session_client = self.sessions
        session_path = "{}/sessions/{}".format(agent, session_id)
        
        if parameters:
            query_params = types.session.QueryParameters(parameters=parameters)
            text_input = types.session.TextInput(text='')
            query_input = types.session.QueryInput(text=text_input, language_code='en')
            request = types.session.DetectIntentRequest(session=session_path,
                                                       query_params=query_params,
                                                       query_input=query_input)
            
            response = session_client.detect_intent(request=request)
            
        for text in conversation:
            text_input = types.session.TextInput(text=text)
            query_input = types.session.QueryInput(text=text_input, language_code='en')
            request = types.session.DetectIntentRequest(
                session=session_path, query_input=query_input
            )
            response = session_client.detect_intent(request=request)
            qr = response.query_result

            print("=" * 20)
            print("Query text: {}".format(qr.text))
            if "intent" in qr:
                print("Triggered Intent: {}".format(qr.intent.display_name))
                
            if "intent_detection_confidence" in qr:
                print("Intent Confidence {}".format(qr.intent_detection_confidence))
                
            print("Response Page: {}".format(qr.current_page.display_name))
            
            for param in qr.parameters: 
                if param == "statusMessage":
                    print("Status Message: {}".format(qr.parameters[param]))
            
            if response_text:
                print(
                    "Response Text: {}\n".format(
                        " ".join(
                            [
                                " ".join(response_message.text.text)
                                for response_message in qr.response_messages
                            ]
                        )
                    )
                )
                
    
    def detect_intent(self, agent, session_id, text, parameters=None, response_text=False):
        """Returns the result of detect intent with texts as inputs.

        Using the same `session_id` between requests allows continuation
        of the conversation."""
        session_client = self.sessions
        session_path = "{}/sessions/{}".format(agent, session_id)
        
        if parameters:
            query_params = types.session.QueryParameters(parameters=parameters)
            text_input = types.session.TextInput(text='')
            query_input = types.session.QueryInput(text=text_input, language_code='en')
            request = types.session.DetectIntentRequest(session=session_path,
                                                       query_params=query_params,
                                                       query_input=query_input)
            
            response = session_client.detect_intent(request=request)
            
        text_input = types.session.TextInput(text=text)
        query_input = types.session.QueryInput(text=text_input, language_code='en')
        request = types.session.DetectIntentRequest(
            session=session_path, query_input=query_input
        )
        response = session_client.detect_intent(request=request)
        qr = response.query_result

        return qr
    
    def preset_parameters(self, agent, session_id, parameters):
        session_client = self.sessions
        session_path = "{}/sessions/{}".format(agent, session_id)
        
        query_params = types.session.QueryParameters(parameters=parameters)
        text_input = types.session.TextInput(text=None)
        query_input = types.session.QueryInput(text=text_input, language_code='en')
        request = types.session.DetectIntentRequest(session=session_path,
                                                   query_params=query_params,
                                                   query_input=query_input)

        response = session_client.detect_intent(request=request)
        
        return response
                
### Make Component Functions

### TODO (pmarlow@): Turn these into @staticmethods since we are not
### doing any authentication with these

    def make_generic(self, obj, obj_type, default, conditionals=dict()):
        if type(obj) == obj_type:
            return obj
        
        elif type(obj) == dict:
            obj_ins = obj_type()
            for key, value in obj.items():
                if key in conditionals.keys():
                    func = conditionals[key]
                    out = func(value)
                    setattr(obj_ins, key, out)
                else:
                    print(value)
                    setattr(obj_ins, key, value)
            return obj_ins
        
        elif type(obj) == str:
            dic = {'unspecified': 0, 'map': 1, 'list': 2, 'regexp': 3, 'default': 1}
            t = dic.get(obj.lower())
            if t:
                return obj_type(t)
            else:
                return default
        else:
            return default
        
    def make_seq(self, obj, obj_type, default, conditionals=dict()):
        assert type(obj) == list
        l = []
        for x in obj:
            l.append(self.make_generic(x, obj_type, default, conditionals))
        return l

    def make_transition_route(self, obj=None, **kwargs):
        """ Creates a single Transition Route object for Dialogflow CX.
        
        Transition routes are used to navigate a user from page to page, or
        page to flow in Dialogflow CX. Routes can be part of a Page object or
        they can also be associated with Route Groups. In either case, the 
        structure of the Route is the same. This method allows the user to 
        create a single Route object that can be used interchangeably with 
        Pages or Route Groups as needed.
        
        Note: if no args are provided, a blank Route object will be created.
        
        Args:
          obj, (Optional) an existing Route object can be provided if the
              user wants to modify or duplicate the object.
              
        Keyword Args:
          intent, (str): The UUID of the Intent to route to
          condition, (str): The condition to evaluate on the route
          target_page, (str): The UUID of the target page to transition to
          target_flow, (str): The UUID of the target flow to transition to
          trigger_fulfillment, (obj): Requires an object in the format of
              type <google.cloud.dialogflowcx_v3beta1.types.fulfillment.Fulfillment>
          
        Returns:
          Route object of type <google.cloud.dialogflowcx_v3beta1.types.page.TransitionRoute>
          """
        
        if obj:
            route = obj
            
            # make sure the route name is cleared if this is a copy of 
            # another existing route object
            route.name = ""
            
        else:
            route = types.page.TransitionRoute()
            
        # Set route attributes to args
        for key, value in kwargs.items():
            if key == 'trigger_fulfillment':
                tf = self.make_trigger_fulfillment(value)
                setattr(route, key, tf)
            else:
                setattr(route, key, value)
                
        return route

    def make_trigger_fulfillment(self, messages=None, webhook_id=None, webhook_tag=None):
        """ Creates a single Fulfillment object for Dialogflow CX.
        
        Fulfillments are used as part of Transition Routes to add Dialogue
        messages back to the user, trigger webhooks, set parameter presets, 
        and enable IVR options where applicable.
        
        Note: if no args are provided, a blank Fulfillment object will be returned.
        
        Args:
          messages, (list): (Optional) The list of Dialogue messages to send back to the user
          webhook_id, (str): (Optional) The UUID of the Dialogflow CX webhook to trigger 
            when the Fulfillment is triggered by the conversation.
          webhook_tag, (str): (Required if webhook_id is provided) User defined tag 
            associated with
            
        Returns:
          Fulfillment object of type <google.cloud.dialogflowcx_v3beta1.types.fulfillment.Fulfillment>
        """
        fulfillment = types.fulfillment.Fulfillment()
        
        if messages:
            response_message = types.response_message.ResponseMessage()
            message_text = response_message.Text()
            
            message_text.text = messages
            response_message.text = message_text
            fulfillment.messages = [response_message]

        if webhook_id:
            fulfillment.webhook = webhook_id
            
            if not webhook_tag:
                print("webhook_tag is required when specifying webhook_id")
                return
            
            else:
                fulfillment.tag = webhook_tag

        print(fulfillment)
        return fulfillment
    
def set_entity_type_attr(self, entity_type, kwargs):
    for key, value in kwargs.items():
        if key == 'kind':
            kind = types.entity_type.EntityType.Kind
            obj = self.make_generic(value, kind, kind(0))
            setattr(entity_type, key, obj)
        #For the auto expansion mode case create helper object to set at entity_type attribute
        elif key == "auto_expansion_mode":
            aem = types.entity_type.EntityType.AutoExpansionMode
            obj = self.make_generic(value, aem, aem(1))
            setattr(entity_type, key, obj)
            
        #For the entities case iterate over dictionary and assign key value pairs to entity type elements of entities list
        elif key == "entities":
            entity = types.entity_type.EntityType.Entity
            obj = self.make_seq(value, entity, entity())
            setattr(entity_type, key, obj)
            
        #For the excluded phrases case assign value to the excluded phrase object then set as the entity_type attribute
        elif key == "excluded_phrases":
            ep = types.entity_type.EntityType.ExcludedPhrase
            obj = self.make_seq(value, ep, ep())
            setattr(entity_type, key, obj)
            
        else:
            setattr(entity_type, key, value)

