from dfcx_scrapi.core.agents import Agents
from dfcx_scrapi.core.versions import Versions 
from dfcx_scrapi.core.environments import Environments 
from dfcx_scrapi.core.flows import Flows

import sys
import datetime
import json
import os
import logging
sys.path.append('./shared')
from deployment import Deployment
#from .shared.deployments import Deployment
# logging config
logging.basicConfig(
    level=logging.INFO,
    format="UAT: %(asctime)s %(levelname)-8s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


def main(data):
    dep=Deployment(data)
    # call the steps sequentially
    dep.importAgent(webhookenv=data["uat_webhook_env"])
    dep.testCaseValidation()
    dep.collectFlowid()
    dep.versionCountDelete()
    dep.versionCut()
    dep.deployVersions()
    dep.datastoreUpdate("uat")



if __name__=='__main__':
    # read env variables
    with open('config.json') as config_file:
        config = json.load(config_file)
    logging.info(f"config file: {json.dumps(config, indent=4)}")
    SHA_ID=sys.argv[1]
    obj=f"UAT/{config['agent_name']}/{SHA_ID}"
    sha_agent_gcs_location=gs_loc=f"gs://{config['bucket']}/UAT/{config['agent_name']}/{SHA_ID}"
    logging.info(f"agent location {sha_agent_gcs_location}")
    #adding additional variables to dict
    config["sha_agent_gcs_location"]=sha_agent_gcs_location
    config['target_project_id'] = config['uat_project']
    config['target_environment_name']=config['uat_env_deploy']
    f = open('agent_artifacts/metadata.json')
    metadata = json.load(f)
    print(metadata)

    config["source_flow_names"]=metadata["source_flow_names"]
    config["updatedcommitmessage"]=metadata["updatedcommitmessage"]

    # To execute steps in order
    main(config)