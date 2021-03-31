import json
import logging
import os
import requests
import subprocess
import google.cloud.dialogflowcx_v3beta1.services as services
import google.cloud.dialogflowcx_v3beta1.types as types
from google.oauth2 import service_account
from google.auth.transport.requests import Request
from google.protobuf import field_mask_pb2
from typing import Dict, List

from typing import List

# logging config
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)-8s %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S')

SCOPES = ['https://www.googleapis.com/auth/cloud-platform',
'https://www.googleapis.com/auth/dialogflow']

class DialogflowCX:
    def __init__(self, creds_path, agent_id=None):
        self.creds = service_account.Credentials.from_service_account_file(
            creds_path, scopes=SCOPES)
        self.creds.refresh(Request()) # used for REST API calls
        self.token = self.creds.token # used for REST API calls

        if agent_id:
            self.agent_id = agent_id
            self.client_options = self._set_region(agent_id)


    @staticmethod
    def _set_region(item_id):
        """different regions have different API endpoints

        Args:
            item_id: agent/flow/page - any type of long path id like 
                `projects/<GCP PROJECT ID>/locations/<LOCATION ID>

        Returns:
            client_options: use when instantiating other library client objects
        """
        try:
            location = item_id.split('/')[3]
        except IndexError as err:
            logging.error('IndexError - path too short? %s', item_id)
            raise err

        if location != 'global':
            api_endpoint = '{}-dialogflow.googleapis.com:443'.format(location)
            client_options = {'api_endpoint': api_endpoint}
            return client_options

        else:
            return None # explicit None return when not required


# TODO (pmarlow@) break each set of Functions into its own Class so that we
# can separate each Class into its own file to keep file line numbers within
# Google standard for Python classes as they grow.


# OPERATIONS FX

    def get_lro(self, lro: str):
        """Used to retrieve the status of LROs for Dialogflow CX.

        Args:
          lro: The Long Running Operation(LRO) ID

        Returns:
          response: Response status and payload from LRO
        """

        location = lro.split('/')[3]
        if location != 'global':
            base_url = 'https://{}-dialogflow.googleapis.com/v3beta1'.format(
                location)
        else:
            base_url = 'https://dialogflow.googleapis.com/v3beta1'

        url = '{0}/{1}'.format(base_url, lro)

        token = subprocess.run(['gcloud',
                                'auth',
                                'application-default',
                                'print-access-token'],
                               stdout=subprocess.PIPE,
                               text=True).stdout

        token = token.strip('\n')  # remove newline appended as part of stdout
        headers = {"Authorization": "Bearer {}".format(token)}

        # Make REST call
        results = requests.get(url, headers=headers)
        results.raise_for_status()

        return results.json()


# INTENTS FX


    def list_intents(self, agent_id):
        request = types.intent.ListIntentsRequest()
        request.parent = agent_id

        client_options = self._set_region(agent_id)
        client = services.intents.IntentsClient(
            credentials=self.creds, 
            client_options=client_options)
        response = client.list_intents(request)

        intents = []
        # pager through the response, not CX 'pages'
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
        # If intent_obj is given, set intent variable to it
        if obj:
            intent = obj
            intent.name = ''
        else:
            intent = types.intent.Intent()

        # Set optional arguments as intent attributes
        for key, value in kwargs.items():
            if key == 'training_phrases':
                assert isinstance(kwargs[key], list)
                training_phrases = []
                for x in kwargs[key]:
                    if isinstance(x, dict):
                        tp = types.intent.Intent.TrainingPhrase()
                        parts = []
                        for y in x['parts']:
                            if isinstance(y, dict):
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

    def delete_intent(self, intent_id, obj=None):
        if obj:
            intent_id = obj.name
        else:
            client_options = self._set_region(intent_id)
            client = services.intents.IntentsClient(
                client_options=client_options)
            client.delete_intent(name=intent_id)


# ENTITIES FX

    def list_entity_types(self, agent_id):
        request = types.entity_type.ListEntityTypesRequest()
        request.parent = agent_id

        client_options = self._set_region(agent_id)
        client = services.entity_types.EntityTypesClient(
            credentials=self.creds,
            client_options=client_options)

        response = client.list_entity_types(request)

        entities = []
        for page in response.pages:
            for entity in page.entity_types:
                entities.append(entity)

        return entities

    def get_entity_type(self, entity_id):
        client_options = self._set_region(entity_id)
        client = services.entity_types.EntityTypesClient(
            client_options=client_options)
        response = client.get_entity_type(name=entity_id)

        return response

    def create_entity_type(self, agent_id, obj=None, **kwargs):
        # If entity_type_obj is given set entity_type to it
        if obj:
            entity_type = obj
            entity_type.name = ''
        else:
            entity_type = types.entity_type.EntityType()

        # set optional arguments to entity type attributes
        for key, value in kwargs.items():
            setattr(entity_type, key, value)

        # Apply any optional functions argument to entity_type object
#         entity_type = set_entity_type_attr(entity_type, kwargs)

        client_options = self._set_region(agent_id)
        client = services.entity_types.EntityTypesClient(
            client_options=client_options)
        response = client.create_entity_type(
            parent=agent_id, entity_type=entity_type)
        return response


    def delete_entity_type(self, entity_id, obj=None) -> None:
        if obj:
            entity_id = obj.name
        else:
            client_options = self._set_region(entity_id)
            client = services.entity_types.EntityTypesClient(
                client_options=client_options)
            client.delete_entity_type(name=entity_id)


# FLOWS FX


    def list_flows(self, agent_id=None):
        agent_id = agent_id or self.agent_id # default value
        request = types.flow.ListFlowsRequest()
        request.parent = agent_id

        client_options = self._set_region(agent_id)
        client = services.flows.FlowsClient(
            credentials=self.creds,
            client_options=client_options)
        response = client.list_flows(request)

        flows = []
        for page in response.pages:
            for flow in page.flows:
                flows.append(flow)

        return flows

    def get_flow(self, flow_id):
        client_options = self._set_region(flow_id)
        client = services.flows.FlowsClient(client_options=client_options)
        response = client.get_flow(name=flow_id)

        return response

    def update_flow(self, flow_id, obj=None, **kwargs):
        if obj:
            flow = obj
            flow.name = flow_id
        else:
            flow = self.get_flow(flow_id)

        # set flow attributes to args
        for key, value in kwargs.items():
            setattr(flow, key, value)
        paths = kwargs.keys()
        mask = field_mask_pb2.FieldMask(paths=paths)

        client_options = self._set_region(flow_id)
        client = services.flows.FlowsClient(client_options=client_options)
        response = client.update_flow(flow=flow, update_mask=mask)

        return response
    
    
    def nlu_settings(self,flow_id, **kwargs):
        """updates flow to new NLU setting.
        Args:
            flow_id: flow id to update nlu settings for.
            model_type: (Optional) [0:unspecified, 1:MODEL_TYPE_STANDARD, 2:Custom, 3:Advanced]
            classification_threshold: (Optional) threshold for the flow
            model_training_mode: (Optional) [0:unspecified, 1:automatic, 2:'manual]
        """
        
        flow = self.get_flow(flow_id)
        currentSettings = flow.nlu_settings
        for key, value in kwargs.items():
            setattr(currentSettings, key, value)
        self.update_flow(flow_id=flow_id, 
                         nlu_settings=currentSettings)
 


    def export_flow(self,
                    flow_id: str,
                    gcs_path: str,
                    data_format: str = 'BLOB',
                    ref_flows: bool = True) -> Dict[str,
                                                    str]:
        """ Exports DFCX Flow(s) into GCS bucket.

        Args:
          flow_id, the formatted CX Flow ID to export
          gcs_path, the full GCS Bucket and File name path
          data_format, (Optional) One of 'BLOB' or 'JSON'. Defaults to 'BLOB'.
          ref_flows, (Optional) Bool to include referenced flows connected to primary flow

        Returns:
          lro, Dict with value containing a Long Running Operation UUID that can be
              used to retrieve status of LRO from dfcx.get_lro
        """

        location = flow_id.split('/')[3]
        if location != 'global':
            base_url = 'https://{}-dialogflow.googleapis.com/v3beta1'.format(
                location)
        else:
            base_url = 'https://dialogflow.googleapis.com/v3beta1'
        url = '{0}/{1}:export'.format(base_url, flow_id)

        body = {
            'flow_uri': '{}'.format(gcs_path),
            'data_format': data_format,
            'include_referenced_flows': ref_flows}
        token = subprocess.run(['gcloud',
                                'auth',
                                'application-default',
                                'print-access-token'],
                               stdout=subprocess.PIPE,
                               text=True).stdout

        token = token.strip('\n')  # remove newline appended as part of stdout
        headers = {
            'Authorization': 'Bearer {}'.format(token),
            'Content-Type': 'application/json; charset=utf-8'}

        # Make REST call
        r = requests.post(url, json=body, headers=headers)
        r.raise_for_status()

        lro = r.json()

        return lro

    def import_flow(self, destination_agent_id: str, gcs_path: str,
                    import_option: str = 'FALLBACK') -> Dict[str, str]:
        """ Imports a DFCX Flow from GCS bucket to CX Agent.

        Args:
          agent_id, the DFCX formatted Agent ID
          gcs_path, the full GCS Bucket and File name path
          import_option, one of 'FALLBACK' or 'KEEP'. Defaults to 'FALLBACK'

        Returns:
          lro, Dict with value containing a Long Running Operation UUID that can be
              used to retrieve status of LRO from dfcx.get_lro
        """

        location = destination_agent_id.split('/')[3]
        if location != 'global':
            base_url = 'https://{}-dialogflow.googleapis.com/v3beta1'.format(
                location)
        else:
            base_url = 'https://dialogflow.googleapis.com/v3beta1'
        url = '{0}/{1}/flows:import'.format(base_url, destination_agent_id)

        body = {
            'flow_uri': '{}'.format(gcs_path),
            'import_option': '{}'.format(import_option)}
        token = subprocess.run(['gcloud',
                                'auth',
                                'application-default',
                                'print-access-token'],
                               stdout=subprocess.PIPE,
                               text=True).stdout

        token = token.strip('\n')  # remove newline appended as part of stdout

        headers = {
            'Authorization': 'Bearer {}'.format(token),
            'Content-Type': 'application/json; charset=utf-8'}

        # Make REST call
        r = requests.post(url, json=body, headers=headers)
        r.raise_for_status()

        lro = r.json()

        return lro


    def delete_flow(self, flow_id: str, force: bool=False):
        """
        Args:
          flow_id: flow to delete
          force: False means a flow will not be deleted if a route to the flow exists, True means the flow will be deleted and all
        """
        request = types.DeleteFlowRequest()
        request.name = flow_id
        request.force = force
        client = services.flows.FlowsClient()
        client.delete_flow(request)


# PAGES FX

    def list_pages(self, flow_id):
        request = types.page.ListPagesRequest()
        request.parent = flow_id

        client_options = self._set_region(flow_id)
        client = services.pages.PagesClient(
            credentials=self.creds,
            client_options=client_options)
        response = client.list_pages(request)

        cx_pages = []
        for page in response.pages:
            for cx_page in page.pages:
                cx_pages.append(cx_page)

        return cx_pages

    def get_page(self, page_id):
        client_options = self._set_region(page_id)
        client = services.pages.PagesClient(client_options=client_options)
        response = client.get_page(name=page_id)

        return response

    def create_page(self, flow_id, obj=None, **kwargs):
        # if page object is given, set page to it
        if obj:
            page = obj
            page.name = ''
        else:
            page = types.page.Page()

        # set optional arguments to page attributes
        for key, value in kwargs.items():
            setattr(page, key, value)

        client_options = self._set_region(flow_id)
        client = services.pages.PagesClient(
            credentials=self.creds,
            client_options=client_options)

        response = client.create_page(parent=flow_id, page=page)
        return response

    def update_page(self, page_id, obj=None, **kwargs):
        # If page object is given set page to it
        if obj:
            # Set page variable to page object
            page = obj
            # Set name attribute to the name of the updated page
            page.name = page_id
        else:
            page = self.get_page(page_id)

        # Set page attributes to arguments
        for key, value in kwargs.items():
            setattr(page, key, value)
        paths = kwargs.keys()
        mask = field_mask_pb2.FieldMask(paths=paths)

        client_options = self._set_region(page_id)
        client = services.pages.PagesClient(
            credentials=self.creds,
            client_options=client_options)

        # Call client function with page and mask as arguments
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

# ROUTE GROUPS FX

    def list_transition_route_groups(self, flow_id):
        request = types.transition_route_group.ListTransitionRouteGroupsRequest()
        request.parent = flow_id

        client_options = self._set_region(flow_id)
        client = services.transition_route_groups.TransitionRouteGroupsClient(
            credentials=self.creds,
            client_options=client_options)
        response = client.list_transition_route_groups(request)

        cx_route_groups = []
        for page in response.pages:
            for cx_route_group in page.transition_route_groups:
                cx_route_groups.append(cx_route_group)

        return cx_route_groups

    def get_transition_route_group(self, name):
        request = types.transition_route_group.GetTransitionRouteGroupRequest()
        request.name = name
        client_options = self._set_region(name)
        client = services.transition_route_groups.TransitionRouteGroupsClient(
            client_options=client_options)
        response = client.get_transition_route_group(request)

        return response

    def create_transition_route_group(self, flow_id, obj, **kwargs):
        #         request = types.transition_route_group.CreateTransitionRouteGroupRequest()

        # if rg object is given, set rg to it
        if obj:
            trg = obj
            trg.name = ''
        else:
            trg = types.transition_route_group.TransitionRouteGroup()

        # set optional args to rg attributes
        for key, value in kwargs.items():
            setattr(trg, key, value)

        client_options = self._set_region(flow_id)
        client = services.transition_route_groups.TransitionRouteGroupsClient(
            client_options=client_options)
        response = client.create_transition_route_group(
            parent=flow_id, transition_route_group=trg)

        return response

    def update_transition_route_group(self, rg_id, obj=None, **kwargs):
        # If route group object is given set route group to it
        if obj:
            # Set rg variable to rg object
            rg = obj
            # Set name attribute to the name of the updated page
            rg.name = rg_id
        else:
            rg = self.get_transition_route_group(rg_id)

        # Set rg attributes to arguments
        for key, value in kwargs.items():
            setattr(rg, key, value)
        paths = kwargs.keys()
        mask = field_mask_pb2.FieldMask(paths=paths)

        client_options = self._set_region(rg_id)
        client = services.transition_route_groups.TransitionRouteGroupsClient(
            client_options=client_options)
        response = client.update_transition_route_group(
            transition_route_group=rg, update_mask=mask)

        return response


# WEBHOOK FX


    def list_webhooks(self, agent_id):
        request = types.webhook.ListWebhooksRequest()
        request.parent = agent_id

        client_options = self._set_region(agent_id)
        client = services.webhooks.WebhooksClient(
            credentials=self.creds,
            client_options=client_options)
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

        client_options = self._set_region(agent_id)
        client = services.webhooks.WebhooksClient(
            client_options=client_options)
        response = client.create_webhook(parent=agent_id, webhook=webhook)

        return response


# SESSION FX

    def run_conversation(
            self,
            agent,
            session_id,
            conversation,
            parameters=None,
            response_text=False):
        """Tests a full conversation with the bot.

        Using the same `session_id` between requests allows continuation
        of the conversation."""
        client_options = self._set_region(agent)
        session_client = services.sessions.SessionsClient(
            client_options=client_options)
        session_path = "{}/sessions/{}".format(agent, session_id)

        if parameters:
            query_params = types.session.QueryParameters(parameters=parameters)
            text_input = types.session.TextInput(text='')
            query_input = types.session.QueryInput(
                text=text_input, language_code='en')
            request = types.session.DetectIntentRequest(
                session=session_path, query_params=query_params, query_input=query_input)

            response = session_client.detect_intent(request=request)

        for text in conversation:
            text_input = types.session.TextInput(text=text)
            query_input = types.session.QueryInput(
                text=text_input, language_code='en')
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
                print(
                    "Intent Confidence {}".format(
                        qr.intent_detection_confidence))

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

    def detect_intent(
            self,
            agent,
            session_id,
            text,
            parameters=None,
            response_text=False):
        """Returns the result of detect intent with texts as inputs.

        Using the same `session_id` between requests allows continuation
        of the conversation."""
        client_options = self._set_region(agent)
        session_client = services.sessions.SessionsClient(
            client_options=client_options)
        session_path = "{}/sessions/{}".format(agent, session_id)

        if parameters:
            query_params = types.session.QueryParameters(parameters=parameters)
            text_input = types.session.TextInput(text='')
            query_input = types.session.QueryInput(
                text=text_input, language_code='en')
            request = types.session.DetectIntentRequest(
                session=session_path, query_params=query_params, query_input=query_input)

            response = session_client.detect_intent(request=request)

        text_input = types.session.TextInput(text=text)
        query_input = types.session.QueryInput(
            text=text_input, language_code='en')
        request = types.session.DetectIntentRequest(
            session=session_path, query_input=query_input
        )
        response = session_client.detect_intent(request=request)
        qr = response.query_result

        return qr

    def preset_parameters(self, agent, session_id, parameters):
        client_options = self._set_region(agent)
        session_client = services.sessions.SessionsClient(
            client_options=client_options)
        session_path = "{}/sessions/{}".format(agent, session_id)

        query_params = types.session.QueryParameters(parameters=parameters)
        text_input = types.session.TextInput(text=None)
        query_input = types.session.QueryInput(
            text=text_input, language_code='en')
        request = types.session.DetectIntentRequest(session=session_path,
                                                    query_params=query_params,
                                                    query_input=query_input)

        response = session_client.detect_intent(request=request)

        return response

# Make Component Functions

# TODO (pmarlow@): Turn these into @staticmethods since we are not
# doing any authentication with these

    def make_generic(self, obj, obj_type, default, conditionals=dict()):
        if isinstance(obj, obj_type):
            return obj

        elif isinstance(obj, dict):
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

        elif isinstance(obj, str):
            dic = {
                'unspecified': 0,
                'map': 1,
                'list': 2,
                'regexp': 3,
                'default': 1}
            t = dic.get(obj.lower())
            if t:
                return obj_type(t)
            else:
                return default
        else:
            return default

    def make_seq(self, obj, obj_type, default, conditionals=dict()):
        assert isinstance(obj, list)
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

    def make_trigger_fulfillment(
            self,
            messages=None,
            webhook_id=None,
            webhook_tag=None):
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
        # For the auto expansion mode case create helper object to set at
        # entity_type attribute
        elif key == "auto_expansion_mode":
            aem = types.entity_type.EntityType.AutoExpansionMode
            obj = self.make_generic(value, aem, aem(1))
            setattr(entity_type, key, obj)

        # For the entities case iterate over dictionary and assign key value
        # pairs to entity type elements of entities list
        elif key == "entities":
            entity = types.entity_type.EntityType.Entity
            obj = self.make_seq(value, entity, entity())
            setattr(entity_type, key, obj)

        # For the excluded phrases case assign value to the excluded phrase
        # object then set as the entity_type attribute
        elif key == "excluded_phrases":
            ep = types.entity_type.EntityType.ExcludedPhrase
            obj = self.make_seq(value, ep, ep())
            setattr(entity_type, key, obj)

        else:
            setattr(entity_type, key, value)
