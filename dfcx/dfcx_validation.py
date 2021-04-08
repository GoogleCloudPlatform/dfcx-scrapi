import os, sys,re, time
import pandas as pd
import numpy as np
import requests
from typing import Dict, List


import google.cloud.dialogflowcx_v3beta1.types as types
import google.cloud.dialogflowcx_v3beta1.services as services
from google.oauth2 import service_account
from google.auth.transport.requests import Request

from .dfcx import DialogflowCX
from .dfcx_functions import DialogflowFunctions
from .dataframe_fxns import Dataframe_fxns
from .core.agents import Agents

SCOPES = ['https://www.googleapis.com/auth/cloud-platform',
'https://www.googleapis.com/auth/dialogflow']

class ValidationKit:
    
    def __init__(self, creds, agent_id):
        self.creds = service_account.Credentials.from_service_account_file(
            creds, scopes=SCOPES)
        self.creds.refresh(Request()) # used for REST API calls
        self.token = self.creds.token # used for REST API calls
        
        self.agent_id= agent_id
        self.dfcx = DialogflowCX(creds)
        self.dffx = DialogflowFunctions(creds)
        self.agents = Agents(creds_path=creds)
        
       
        
    def run_validation_result(self, agent_id: str) -> Dict:
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
            base_url = 'https://{}-dialogflow.googleapis.com/v3beta1'.format(
                location)
        else:
            base_url = 'https://dialogflow.googleapis.com/v3beta1'

        url = '{0}/{1}/validationResult'.format(base_url, agent_id)
        headers = {"Authorization": "Bearer {}".format(self.token)}

        # Make REST call
        results = requests.get(url, headers=headers)
        results.raise_for_status()

        return results.json()

    
    def get_validation_result(
            self,
            agent_id: str,
            flow_id: str = None) -> Dict:
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
                base_url = 'https://{}-dialogflow.googleapis.com/v3beta1'.format(
                    location)
            else:
                base_url = 'https://dialogflow.googleapis.com/v3beta1'

            url = '{0}/{1}/validationResult'.format(base_url, flow_id)
        else:
            location = agent_id.split('/')[3]
            if location != 'global':
                base_url = 'https://{}-dialogflow.googleapis.com/v3beta1'.format(
                    location)
            else:
                base_url = 'https://dialogflow.googleapis.com/v3beta1'

            url = '{0}/{1}/validationResult'.format(base_url, agent_id)

        headers = {"Authorization": "Bearer {}".format(self.token)}

        # Make REST call
        results = requests.get(url, headers=headers)
        results.raise_for_status()

        return results.json()

                
    def validation_results_to_dataframe(self, validation_results: Dict):
        """"Transform the Validation results into a dataframe. Note will not work if you call get_validation_result with a flow_id specified. For calling validate ensure lro is complete
        Args:
            validation_results: dictionary of validation results passed back from get_validation_result or validate functions
        
        Return:
            df: dataframe containing the validation results
        """
        

        agent_id = '/'.join(validation_results['name'].split('/')[0:6])

        flows_map = self.dffx.get_flows_map(agent_id)
        max_cols_old = 0
        df = pd.DataFrame()

        for flow in validation_results['flowValidationResults']:
            temp = '/'.join(flow['name'].split('/')[:-1])
            temp_df = pd.DataFrame(flow['validationMessages'])
            temp_df.insert(0, 'flow', flows_map[temp])

            max_cols_new = max([len(x) for x in temp_df.resourceNames])

            if max_cols_new > max_cols_old:
                for i in range(1, max_cols_new + 1):
                    temp_df['resource{}'.format(i)] = None
                max_cols_old = max_cols_new

            for index in temp_df.index:
                i = 1
                for d in temp_df['resourceNames'][index]:
                    temp_df['resource{}'.format(i)][index] = d['displayName']
                    i += 1

            df = df.append(temp_df)
            max_cols_old = 0

        return df

        
    def intent_disambg(self, refresh = False, flow = None):
        '''Obtains the intent disambiguation tasks from the validation tool
            Args:
                refresh: (optional) False means validation results are pulled as is. True means the validation tool is refreshed then results are pulled
                flow: (optional) If specified results are returned for the indicated flow display name
                
            
        Returns:
          Dictionary of intent disambiguation Validation results in two dataframes.
              extended: All intent disambiguation validtion results as seperate instances. If 5 training phrases conflict in 5 intents they will be shown as 5 rows. 
              compact: Only showing the first instance of a conflict for each grouping. If 5 trainig phrases conflic in 5 intents only the first training phrase will show.
        '''
        
        if refresh:
            validation = self.run_validation_result(self.agent_id)
        else:
            validation = self.get_validation_result(agent_id=self.agent_id)
            
        validation_df = self.validation_results_to_dataframe(validation)
        if flow:
            validation_df = validation_df[validation_df['flow']==flow]
       
        
        
        #Parse df
        validation_df = validation_df[['flow','detail','resource1','resource2','resource3','resource4']]
        disambig_id,intents_list, tp_list,id_  = [], [], [], 0
        flows = []
        for index, row in validation_df.iterrows():
            deets, flow = row['detail'], row['flow']
            if bool(re.search('Multiple intents share training phrases which are too similar:',deets)):
                intents = re.findall('Intent \'(.*)\': training phrase ', deets)
                training_phrases = re.findall('training phrase \'(.*)\'',deets)
                intents_list = intents_list + intents
                tp_list = tp_list + training_phrases
                disambig_id = disambig_id + ([id_]*len(training_phrases))
                flows = flows + ([flow]*len(training_phrases))
                id_ += 1

        extraction = pd.DataFrame()
        extraction['disambig_id'] = disambig_id
        extraction.insert(0,'flow',flows)
        extraction['intent'] = intents_list
        extraction['training_phrase'] = tp_list
        intent_options = extraction.groupby(['disambig_id'])['intent'].apply(list).reset_index().rename(columns={'intent':'intents'})
        intent_options['intents'] = intent_options.apply(lambda x: list(set(x['intents'])),axis=1)
        extraction = pd.merge(extraction, intent_options, on=['disambig_id'],how='left')
        internal = extraction.copy()
        internal['intent_count'] = internal.apply(lambda x: len(x['intents']),axis=1)
        external = extraction.groupby(['flow','disambig_id'])[['training_phrase','intents']].first().reset_index()
        external['intent_count'] = external.apply(lambda x: len(x['intents']),axis=1)
        
       
        return {'extended':internal , 'compact': external}
    