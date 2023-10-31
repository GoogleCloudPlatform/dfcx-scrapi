"""Example of building Dialogflow CX Agents using SCRAPI library."""
#!/usr/bin/env python
# coding: utf-8

# Copyright 2023 Google LLC
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
from dfcx_scrapi.tools.dataframe_functions import DataframeFunctions

# # Method 1 - Creating an Agent from Simple Text Inputs

# ## Create Your Agent
# Creating an agent requires a minimum of 2 pieces of information:
# - `project_id`, which is your GCP Project ID
# - `display_name`, (i.e. 'My Cool Agent!')
# - `gcp_region`, (Optional) This defaults to `global` region, but you can
# 	provide any GCP region that is currently available for Dialogflow CX.


def build_agent(creds_path, project_id, gcp_region, display_name):
    """Build out CX Agent."""

    # First we will instantiate our Agent object
    agent_instance = Agents(creds_path=creds_path)

    # Next, we will set some variables for our agent creation or retrieval args

    # Then we will call the `create_agent` and capture the result in a var call
	# `my_agent`
    my_agent = agent_instance.create_agent(project_id, display_name, gcp_region)

    # Option 2: If agent already exists
    # The agent ID must be entered as a string
    # "projects/<PROJECT_ID>/locations/<GCP_REGION>/agents/<AGENT_ID>"
    # my_agent = a.get_agent(
	#   "projects/<PROJECT_ID>/locations/<GCP_REGION>/agents/<AGENT_ID>")

    # ## Create Your First Intent
    # For this demo agent, we'll build a basic intent from list of Training
	# Phrases (TPs)

    # To simplify the Intent creation, we'll utilize the `DataframeFunctions`
    # class from the `tools` portion of the SCRAPI library.
    # This will allow us to build our intent into a simple Pandas DataFrame,
    # and then push this DataFrame directly into our bot that we just created.

    # A common method of building Intents and Training Phrases for Dialogflow
    # CX agents is to use Google Sheets or CSVs to store the Intent/TP data.
    # For this demo, we are working with annotated training phrases. To do so,
    # we've included
    # * `intent_sample_with_parts.csv` which contains all the training phrases
    # 	parts. It will be pulled into a dataframe
    # * `intent_sample_params`, that defines the parameters used for each
    # 	intent. It will also be pulled into a dataframe

    # First, we will instantiate our DataframeFunctions (dffx) object
    dffx = DataframeFunctions(creds_path=creds_path)

    # Next, we will read in our sample CSV with Intent training phrases data as
    # well as the entities used into 2 distinct Pandas DataFrames
    df = pd.read_csv("../../data/intent_sample_with_parts.csv")  # pylint: disable=C0103
    params_df = pd.read_csv("../../data/intent_sample_params.csv")

    # Finally, we will use `dffx` to push our Intents to our Agent
    # If intents do not exist, use bulk_create_intent_from_dataframe
    _ = dffx.bulk_create_intent_from_dataframe(
        my_agent.name, df, params_df, update_flag=True, mode="advanced"
    )


# If intent already exist, use bulk_update_intents_from_dataframe
# my_intents = dffx.bulk_update_intents_from_dataframe(
# my_agent.name, df, params_df, update_flag=True, mode="advanced")


# # Bot Building 101 End
# ## And there you have it!
# We've created a simple Dialogflow CX agent using only Python in a Jupyter
# notebook.
# You can see how this could be easily scaled up using .py files, git repos,
# and other scripts to speed up the bot building process.


# The agent ID must be entered as a string
# 	"projects/<PROJECT_ID>/locations/<GCP_REGION>/agents/<AGENT_ID>"
def update_agent(creds_path, agent_id):
    """Updating the agent."""
    # First we will instantiate our Agent object and retrieve the agent using
    # its id
    agent_instance = Agents(creds_path=creds_path)
    my_agent = agent_instance.get_agent(
        f"projects/<PROJECT_ID>/locations/<GCP_REGION>/agents/{agent_id}"
    )

    # ## Create Your First Intent
    # For this demo agent, we'll build a basic intent from list of Training
    # Phrases (TPs)

    # To simplify the Intent creation, we'll utilize the `DataframeFunctions`
    # class from the `tools` portion of the SCRAPI library. This will allow
    # us to build our intent into a simple Pandas DataFrame, and then push
    # this DataFrame directly into our bot that we just created.

    # A common method of building Intents and Training Phrases for Dialogflow
    # CX agents is to use Google Sheets or CSVs to store the Intent/TP data.
    # For this demo, we are working with annotated training phrases. To do so,
    # we've included:
    #   * `intent_sample_with_parts.csv` which contains all the training
    #     phrases parts. It will be pulled into a dataframe
    #   * `intent_sample_params`, that defines the parameters used for each
    #     intent. It will also be pulled into a dataframe

    # First, we will instantiate our DataframeFunctions (dffx) object
    dffx = DataframeFunctions(creds_path=creds_path)

    # Next, we will read in our sample CSV with Intent training phrases data as
    #  well as the entities used into 2 distinct Pandas DataFrames
    df = pd.read_csv("../../data/intent_sample_with_parts.csv")  # pylint: disable=C0103
    params_df = pd.read_csv("../../data/intent_sample_params.csv")

    # bulk update the existing intents
    _ = dffx.bulk_update_intents_from_dataframe(
        my_agent.name, df, params_df, update_flag=True, mode="advanced"
    )


# # Bot Building 102 End
# ## And there you have it!
# We've created a simple Dialogflow CX agent using only Python in a Jupyter
# notebook. You can see how this could be easily scaled up using .py files,
# git repos, and other scripts to speed up the bot building process.

if __name__ == "__main__":
    CREDS_PATH = str(sys.argv[1])
    PROJECT_ID = str(sys.argv[2])
    REGION = str(sys.argv[3])
    DISPLAY_NAME = str(sys.argv[4])

    build_agent(CREDS_PATH, PROJECT_ID, REGION, DISPLAY_NAME)
