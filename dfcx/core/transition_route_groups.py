import logging
import requests
import google.cloud.dialogflowcx_v3beta1.services as services
import google.cloud.dialogflowcx_v3beta1.types as types
from google.oauth2 import service_account
from google.auth.transport.requests import Request
from google.protobuf import field_mask_pb2

from typing import Dict, List
# from dfcx.dfcx import DialogflowCX

# logging config
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)-8s %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S')

SCOPES = ['https://www.googleapis.com/auth/cloud-platform',
          'https://www.googleapis.com/auth/dialogflow']


class TransitionRouteGroups:
    def __init__(self, creds_path: str, route_group_id: str = None):
        self.creds = service_account.Credentials.from_service_account_file(
            creds_path, scopes=SCOPES)
        self.creds.refresh(Request())  # used for REST API calls
        self.token = self.creds.token  # used for REST API calls

        if route_group_id:
            self.route_group_id = route_group_id
            self.client_options = self._set_region(route_group_id)

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
            return None  # explicit None return when not required

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
