""" UAT Deployment functions"""

import json
import logging
import sys

from shared.deployment import Deployment

#from .shared.deployments import Deployment
# logging config
logging.basicConfig(
    level=logging.INFO,
    format="UAT: %(asctime)s %(levelname)-8s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


def main(data):
    """
    Deploys and tests a Dialogflow CX agent in a UAT environment.

    This function performs the following steps:

    1. Initializes a Deployment object with the provided data.
    2. Imports the agent to the specified UAT webhook environment.
    3. Validates test cases.
    4. Collects flow IDs.
    5. Deletes versions based on count.
    6. Cuts a new version.
    7. Deploys the new version.
    8. Updates the datastore with UAT information.

    Args:
        data: A dictionary containing configuration data, including the
            'uat_webhook_env' key.
    """

    dep=Deployment(data)
    # call the steps sequentially
    dep.import_agent(webhookenv=data["uat_webhook_env"])
    dep.test_case_validation()
    dep.collect_flow_id()
    dep.version_count_delete()
    dep.version_cut()
    dep.deploy_versions()
    dep.datastore_update("uat")



if __name__=="__main__":
    # read env variables
    with open("config.json" , encoding='utf-8') as config_file:
        config = json.load(config_file)
    SHA_ID=sys.argv[1]
    obj=f"UAT/{config['agent_name']}/{SHA_ID}"
    sha_gs_loc=(
        f"gs://{config['bucket']}/UAT/{config['agent_name']}/{SHA_ID}"
    )
    logging.info("Agent location: %s" ,sha_gs_loc)
    #adding additional variables to dict
    config["sha_agent_gcs_location"]=sha_gs_loc
    config["target_project_id"] = config["uat_project"]
    config["target_environment_name"]=config["uat_env_deploy"]
    with open("agent_artifacts/metadata.json",
              encoding='utf-8') as metadata_file:
        metadata = json.load(metadata_file)

    config["source_flow_names"]=metadata["source_flow_names"]
    config["updated_commit_message"]=metadata["updated_commit_message"]

    # To execute steps in order
    main(config)
