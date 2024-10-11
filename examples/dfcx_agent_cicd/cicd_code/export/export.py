""" export functions"""

import json
import sys
import logging

from dfcx_scrapi.core.agents import Agents

from .flow_impacted import Impacted
from google.cloud import storage

# logging config
logging.basicConfig(
    level=logging.INFO,
    format="dev: %(asctime)s %(levelname)-8s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

def agent_to_gcs(
    agent_name,
    project_id,
    environment_name,
    gsloc):
    """Exports a Dialogflow CX agent to Google Cloud Storage (GCS).

    This function exports a specified Dialogflow CX agent and its environment 
    to a designated location in Google Cloud Storage.

    Args:
        agent_name: The display name of the agent to export.
        project_id: The ID of the Google Cloud project where the agent resides.
        environment_name: The display name of the environment to export.
        gsloc: The GCS bucket URI where the agent will be exported.

    Returns:
        None
    """
    agents=Agents()

    agent_details=agents.get_agent_by_display_name(
        display_name=agent_name,
        project_id=project_id
    )

    agent_id=agent_details.name
    agent_gcs_location=f"{gsloc}/{agent_name}"

    #export will replace exisitng agent in bucket
    agents.export_agent(agent_id=agent_id,
                        gcs_bucket_uri=agent_gcs_location,
                        environment_display_name=environment_name)
    logging.info("Agent export from dev done")

def meta_to_gcs(
    config_data,
    flow_names,
    commit_message,
    gsloc,
    agent_name,
    gcs_bucket,
    version_ids
    ):
    """Exports metadata to a JSON file in Google Cloud Storage (GCS).

    This function takes configuration data, flow names, a commit message, 
    GCS location information, agent name, and version IDs, and creates a JSON 
    file containing this metadata in the specified GCS bucket.

    Args:
        config_data: A dictionary containing configuration data.
        flow_names: A list of flow names.
        commit_message: The commit message to include in the metadata.
        gsloc: The full GCS URI where the metadata file will be stored.
        agent_name: The name of the agent.
        gcs_bucket: The name of the GCS bucket.
        version_ids: A list of version IDs.

    Returns:
        None
    """

    config_data["source_flow_names"]=flow_names
    config_data["impacted_version_ids"]= version_ids
    config_data["updated_commit_message"]=commit_message
    gcslist=gsloc.split("/")
    obj="/".join(gcslist[3:])

    bucket_obj = storage.Client().get_bucket(gcs_bucket)

    blob = bucket_obj.blob(f"{obj}/{agent_name}_metadata.json")
    blob.upload_from_string(data=json.dumps(config_data),
                            content_type='application/json')


if __name__=='__main__':
    # read env variables
    with open("config.json", encoding='utf-8') as config_file:
        config = json.load(config_file)

    source_project_id=config["dev_project"]
    source_agent_name=config["agent_name"]
    source_environment_name=config["dev_env_pull"]
    bucket=config["bucket"]
    user_commit_message=sys.argv[1]
    userid=sys.argv[2]
    #updated_commit_message=f"{user_commit_message} by {userid} for {source_agent_name}"
    updated_commit_message = (
    f"{user_commit_message} by {userid} "
    f"for {source_agent_name}"
    )
    impflows=Impacted(source_project_id=source_project_id,
                      source_agent_name=source_agent_name,
                      environment_name=source_environment_name)
    imp_flow_map,impacted_version_ids=impflows.check_flow()
    source_flow_names=list(imp_flow_map.values())
    source_flow_ids=list(imp_flow_map.keys())
    gs_loc=f"gs://{bucket}/exports/dev"

    logging.info("impacted flow is %(imp_flow_map)s"
                 , {'imp_flow_map': imp_flow_map})


    #Execute in steps
    agent_to_gcs(source_agent_name,
                 source_project_id,
                 source_environment_name,
                 gs_loc)
    meta_to_gcs(config,source_flow_names,
                updated_commit_message,gs_loc,
                source_agent_name,bucket,impacted_version_ids)
    