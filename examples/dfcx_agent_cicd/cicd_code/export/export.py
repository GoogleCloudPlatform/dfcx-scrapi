from dfcx_scrapi.core.agents import Agents
from dfcx_scrapi.core.versions import Versions 
from dfcx_scrapi.core.environments import Environments
from flowimpacted import impacted
from google.cloud import storage
import json
import sys
import logging

# logging config
logging.basicConfig(
    level=logging.INFO,
    format="dev: %(asctime)s %(levelname)-8s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

"""
Pre requisites
[1] make your Flow changes in dev (in dfcx)
[2] Create a Flow version (in dfcx)
[3] Add Version to ready to deploy Environment (in dfcx)

Handled by the pipline
[4] Run the pipeline to Export ready to deploy Environment / Agent
[5] Export metadata file to gcs in path same as agent
"""



def agentToGcs(
    source_agent_name,
    source_project_id,
    source_environment_name,
    gs_loc):
    #[4] Export ready to deploy Environment / Agent

    agents=Agents()

    agent_details=agents.get_agent_by_display_name(display_name=source_agent_name,
                                                project_id=source_project_id)

    agent_id=agent_details.name
    agent_gcs_location=f"{gs_loc}/{source_agent_name}"

    #export will replace exisitng agent in bucket
    export_result=agents.export_agent(agent_id=agent_id,
                                    gcs_bucket_uri=agent_gcs_location,
                                    environment_display_name=source_environment_name)
    logging.info("Agent export from dev done")

def metaToGcs(
    config,
    source_flow_names,
    updatedcommitmessage,
    gs_loc,
    source_agent_name,
    bucket,
    impactedVersionIds):
    #[5] Export metadata file to gcs in path same as agent

    config["source_flow_names"]=source_flow_names
    config["impactedVersionIds"]= impactedVersionIds
    config["updatedcommitmessage"]=updatedcommitmessage
    gcslist=gs_loc.split("/")
    bucket_name = gcslist[2]
    obj="/".join(gcslist[3:])

    bucket = storage.Client().get_bucket(bucket)

    blob = bucket.blob(f'{obj}/{source_agent_name}_metadata.json')
    blob.upload_from_string(data=json.dumps(config),content_type='application/json')
    


if __name__=='__main__':
    # read env variables
    with open('config.json') as config_file:
        config = json.load(config_file)
    logging.info(f"config file: {json.dumps(config, indent=4)}")

    source_project_id=config['dev_project']
    source_agent_name=config['agent_name']
    source_environment_name=config['dev_env_pull']
    bucket=config['bucket']
    usercommitmessage=sys.argv[1]
    userid=sys.argv[2]
    updatedcommitmessage=f"{usercommitmessage} by {userid} for {source_agent_name}"
    impflows=impacted(source_project_id=source_project_id,source_agent_name=source_agent_name,environment_name=source_environment_name)
    impflowmap,impactedVersionIds=impflows.checkFlow()
    source_flow_names=list(impflowmap.values())
    source_flow_ids=list(impflowmap.keys())
    gs_loc=f"gs://[{bucket}/exports/dev"

    logging.info(f"impacted flow is {impflowmap}")

    #Execute in steps
    agentToGcs(source_agent_name,source_project_id,source_environment_name,gs_loc)
    metaToGcs(config,source_flow_names,updatedcommitmessage,gs_loc,source_agent_name,bucket,impactedVersionIds)

