"""A sample script for building a DFCX bot from scratch using simple inputs."""
# Copyright 2021 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import sys
import pandas as pd

from dfcx_scrapi.core.agents import Agents
from dfcx_scrapi.core.intents import Intents
from dfcx_scrapi.core.flows import Flows
from dfcx_scrapi.core.pages import Pages
from dfcx_scrapi.tools.dataframe_functions import DataframeFunctions
from dfcx_scrapi.tools.maker_util import MakerUtil

def build_agent(creds_path, project_id):
    """Build a simple agent."""

    # First we will instansiate our Agent object
    a = Agents(creds_path=creds_path)

    # Next, we will set some variables for our agent creation args
    display_name = 'My Cool Agent!'
    gcp_region = 'us-central1'

    # Then we will call the `create_agent` method and capture the result in a
    # var called `my_agent`
    my_agent = a.create_agent(project_id, display_name, gcp_region)

    # First, we will instantiate our DataframeFunctions (dffx) object
    dffx = DataframeFunctions(creds_path=creds_path)

    # Next, we will read in our sample CSV with Intent/TP data into a Pandas
    # DataFrame
    df = pd.read_csv('../data/sample_intent_tp.csv')

    # Finally, we will use `dffx` to push our Intents to our Agent
    dffx.bulk_create_intent_from_dataframe(
        my_agent.name, df, update_flag=True)

    # First, we will instantiate our Flows and Pages objects.
    f = Flows(creds_path=creds_path)
    p = Pages(creds_path=creds_path)

    # The `get_flows_map` method provides an easy to use map of your Flows,
    # their IDs, and their human readable Display Names
    # Using the `reverse=True` arg allows you to call the dictionary by your
    # flow Display Names which can be easier for exploratory building.
    flows_map = f.get_flows_map(my_agent.name, reverse=True)

    # Now that we know our Flow ID, we'll create a Page using the Flow ID as
    # the Page parent
    my_page = p.create_page(
        flows_map['Default Start Flow'],
        display_name='My First Page!')

    # We'll first get the Default Start Flow (dsf for short)
    dsf = f.get_flow(flows_map['Default Start Flow'])

    # We'll also fetch our Intent directly from the bot by Display Name to make
    # this next part easier
    i = Intents(creds_path=creds_path)
    intent_list = i.list_intents(my_agent.name)
    my_intent = [
        x for x in intent_list if \
            x.display_name == 'head_intent.order_pizza'][0]

    # Next, we'll use the MakerUtil to build our Transition Route (tr) object
    mu = MakerUtil()
    my_tr = mu.make_transition_route(
        intent=my_intent.name, target_page=my_page.name)

    # Now, we'll add the newly created Transition Route object to our DSF
    # object
    dsf.transition_routes.append(my_tr)

    # Finally, we'll update the DSF object in our agent
    f.update_flow(
        flows_map['Default Start Flow'],
        obj=dsf,
        transition_routes=dsf.transition_routes)

if __name__ == '__main__':
    CREDS_PATH = str(sys.argv[1])
    PROJECT_ID = str(sys.argv[2])
    build_agent(CREDS_PATH, PROJECT_ID)
