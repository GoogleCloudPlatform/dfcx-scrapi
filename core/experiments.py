"""
Copyright 2021 Google LLC

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""
'''wrapper for Experiments'''

import json
import logging

from google.cloud.dialogflowcx_v3beta1.services.experiments import ExperimentsClient

from .sapi_base import SapiBase

import google.cloud.dialogflowcx_v3beta1.services as services
import google.cloud.dialogflowcx_v3beta1.types as types

# logging config
# logging.basicConfig(
#     level=logging.INFO,
#     format='%(asctime)s %(levelname)-8s %(message)s',
#     datefmt='%Y-%m-%d %H:%M:%S')

log = logging.info

SCOPES = ['https://www.googleapis.com/auth/cloud-platform',
          'https://www.googleapis.com/auth/dialogflow']


class SapiExperiments(SapiBase):
    '''Wrapper for working with Experiments'''

    def __init__(self, creds_path, agent_path=None):
        '''constructor'''
        super().__init__(creds_path, agent_path)
        logging.info('created %s', self.agent_path)

    # def list_environments(self):

    def list_experiments(self, environment_id=None):
        '''list out experiments'''
        # projects/verizon-custom-ccai-external/locations/global/agents/f727a856-bbba-45ce-9d91-4e437cd448ba/environments/ec44091d-0171-4729-9c8b-5eca321dc8bc
        environment_path = f'{self.agent_path}/environments/{environment_id}'
        logging.info('environment_path %s', environment_path)
        # request = types.experiment.ListExperimentsRequest(
        #     parent=environment_path
        # )
        # result = ex_client.list_experiments(request=request)
        # logging.log('list %s', result)
        # ex
        request = types.experiment.ListExperimentsRequest()
        request.parent = environment_path
        client = services.experiments.ExperimentsClient(
            client_options=self.client_options,
            credentials=self.creds)
        response = client.list_experiments(request)
        blob = SapiBase.response_to_dict(response)

        if len(blob) < 1:
            logging.warning('no experiments found for environment: %s', environment_id)
            return None

        experiments: list = blob['experiments']

        results = [
            {
                'environment_id': environment_id,
                'experiment_id': ex['name'].split('/').pop(),
                'displayName': ex['displayName'],
                'name': ex['name'],
            } for ex in experiments
        ]

        # ex_names = [exid['name'] for exid in experiments]
        # ex_ids = [
        #     elem.split('/').pop() for elem in ex_names
        # ]
        # logging.info('name: \n%s', ex['name'])

        # log('first %s', experiments[0])
        # log('len %s', len(experiments))

        # for ex in blob['experiments']:
        # logging.info('experiments %s', experiments)
        # logging.info('ex_names %s', ex_names)
        logging.info('results %s', json.dumps(results, indent=2))
        return experiments
