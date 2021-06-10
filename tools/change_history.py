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

import logging
import numpy as np
import pandas as pd
import requests

from dfcx_sapi.core.sapi_base import SapiBase
from typing import Dict, List

# logging config
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)-8s %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S')


class ChangeHistory(SapiBase):
    def __init__(self, creds_path: str = None,
                creds_dict: Dict = None,
                scope=False,
                webhook_id: str = None):
        super().__init__(creds_path=creds_path,
                         creds_dict=creds_dict,
                         scope=scope)


    def get_change_history(self, agent_id):
        location = agent_id.split('/')[3]
        if location != 'global':
            base_url = 'https://{}-dialogflow.googleapis.com/v3alpha1'.format(
                location)
        else:
            base_url = 'https://dialogflow.googleapis.com/v3alpha1'

        url = '{0}/{1}/changelogs'.format(base_url, agent_id)

        headers = {"Authorization": "Bearer {}".format(self.token)}

        # Make REST call
        results = requests.get(url, headers=headers)
        results.raise_for_status()

        res = results.json()

        logs = []
        for log in res['changelogs']:
            logs.append(log)

        next_token = res['nextPageToken'] 

        while next_token is not None:
            results = requests.get(url, headers=headers, params={'page_token': next_token})
            res = results.json()
            for log in res['changelogs']:
                logs.append(log)

            if 'nextPageToken' in res:
                next_token = res['nextPageToken']
            else:
                next_token = None
                print('All done!')

        return logs


    def change_history_to_dataframe(self, agent_id):
        change_logs = self.get_change_history(agent_id)
        df = pd.DataFrame.from_records(data=change_logs)

        df['createTime'] = pd.to_datetime(df['createTime'], infer_datetime_format=True) # coerce datetime from CX
        df['userType'] = np.where(df.userEmail.str.contains('@google.com'), 'Internal', 'External') # determine int/ext user

        # functions to determine which Flow this resource belongs to

        return df