import json
import logging
import google.cloud.dialogflowcx_v3beta1.services as services
import google.cloud.dialogflowcx_v3beta1.types as types

# logging config
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)-8s %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S')

class DialogflowCX:
    def __init__(self, creds_path, agent_id=None):          
        with open(creds_path) as json_file:
            data = json.load(json_file)
        project_id = data['project_id']

        self.project_id = 'projects/{}/locations/global'.format(project_id)
        
        self.agents = services.agents.AgentsClient()
        self.intents = services.intents.IntentsClient()
        self.entities = services.entity_types.EntityTypesClient()
        self.pages = services.pages.PagesClient()
        self.flows = services.flows.FlowsClient()
        self.sessions = services.sessions.SessionsClient()
        self.route_groups = \
          services.transition_route_groups.TransitionRouteGroupsClient()
        self.webhooks = services.webhooks.WebhooksClient()
            
        if agent_id:
            self.agent_id = agent_id 
            
### TODO (pmarlow@) break each set of Functions into its own Class so that we 
### can separate each Class into its own file to keep file line numbers within
### Google standard for Python classes as they grow.

### AGENT FX

    def list_agents(self, project_id):
        request = types.agent.ListAgentsRequest()
        request.parent = self.project_id
        
        client = self.agents
        response = client.list_agents(request)
        
        agents = []
        for page in response.pages:
            for agent in page.agents:
                agents.append(agent)
        
        return agents
    
    
    def get_agent(self, project_id):
        request = types.agent.GetAgentRequest()
        request.name = self.agent_id
        client = self.agents
        response = client.get_agent(request)
        
        return response

### INTENTS FX    
    
    def list_intents(self, agent_id):
        request = types.intent.ListIntentsRequest()
        request.parent = agent_id
            
        client = self.intents
        response = client.list_intents(request)

        intents = []
        for page in response.pages:
            for intent in page.intents:
                intents.append(intent)

        return intents
    
    def get_intent(self, intent_id):
        client = self.intents
        response = client.get_intent(name=intent_id)
        
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
        
        client = self.intents
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
    
    def create_transition_route(self, intent=None, condition=None, 
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
    
    
    def create_transition_route_group(self, route_group, flow_id=None):
        request = types.transition_route_group.CreateTransitionRouteGroupRequest()
        
        if flow_id:
            request.parent = flow_id
            
        trg = types.transition_route_group.TransitionRouteGroup()
            
        if route_group['display_name']:
            trg.display_name = route_group['display_name']
            
        if route_group['transition_routes']:
            trg.transition_routes = route_group['transition_routes']

            
        request.transition_route_group = trg        
        client = self.route_groups
        response = client.create_transition_route_group(request)
        
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
        
    
### SESSION FX
    def detect_intent_texts(self, agent, session_id, texts, language_code):
        """Returns the result of detect intent with texts as inputs.

        Using the same `session_id` between requests allows continuation
        of the conversation."""
        session_client = SessionsClient()
        session_path = "{}/sessions/{}".format(agent, session_id)
        print("Session path: {}\n".format(session_path))

        for text in texts:
            text_input = session.TextInput(text=text)
            query_input = session.QueryInput(text=text_input, language_code=language_code)
            request = session.DetectIntentRequest(
                session=session_path, query_input=query_input
            )
            print(request)
            response = session_client.detect_intent(request=request)

            print("=" * 20)
            print("Query text: {}".format(response.query_result.text))
            print(
                "Response text: {}\n".format(
                    " ".join(
                        [
                            " ".join(response_message.text.text)
                            for response_message in response.query_result.response_messages
                        ]
                    )
                )
            )
