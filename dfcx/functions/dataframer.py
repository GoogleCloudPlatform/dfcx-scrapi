import logging
import pandas as pd
import google.cloud.dialogflowcx_v3beta1.types as types

from collections import defaultdict
from typing import Dict, List
from dfcx.dfcx import DialogflowCX

# logging config
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)-8s %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S')

class Dataframer:
    def __init__(self, creds, agent_id=None):

        if agent_id:
            self.dfcx = DialogflowCX(creds, agent_id)
            self.agent_id = agent_id

        else:
            self.dfcx = DialogflowCX(creds)