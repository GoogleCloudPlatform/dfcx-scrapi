""" Deploy to prod functions """
import json
import logging
import sys

from shared.deployment import Deployment

# logging config
logging.basicConfig(
    level=logging.INFO,
    format="PROD: %(asctime)s %(levelname)-8s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

def main(data):
    """
    Deploys and validates a Dialogflow CX agent in a production environment.
    This function orchestrates the deployment and validation of a Dialogflow CX agent
    in a production environment. It performs the following key steps:

    1. Imports the agent to the specified production webhook environment.
    2. Performs a language check on fulfillment entries, parameters, and routes, 
        specifically for French Canadian ('fr-ca').
    3. Collects flow IDs.
    4. Manages version count and deletion.
    5. Cuts a new version of the agent.
    6. Deploys the new version to production.
    7. Synchronizes the agent between development and production environments.
    8. Updates the datastore with production information.

    Args:
        data: A dictionary containing configuration data, including the 'prod_webhook_env' key.

    Raises:
        SystemExit: If the language check fails, indicating missing agent responses.
    """
    dep=Deployment(data)
    # call the steps sequentially
    dep.import_agent(webhookenv=data["prod_webhook_env"])

    entry,param,route,result=dep.fullfillment_lang_check(lang='fr-ca')

    logging.info("Entry fulfilment is %s",entry)
    logging.info("Param fulfilment is %s",param)
    logging.info("Route fulfilment is %s",route)
    if not result:
        print("some pages,parameters, routes does not have agent response")
        sys.exit(2)

    dep.collect_flow_id()
    dep.version_count_delete()
    dep.version_cut()
    dep.deploy_versions()
    dep.dev_prod_sync()
    dep.datastore_update("prod")



if __name__=='__main__':
    # read env variables
    with open("config.json" , encoding='utf-8') as config_file:
        config = json.load(config_file)

    SHA_ID=sys.argv[1]
    obj=f"UAT/{config['agent_name']}/{SHA_ID}"
    sha_agent_gcs_location=(
        f"gs://{config['bucket']}/UAT/{config['agent_name']}/{SHA_ID}"
    )
    logging.info("agent location %s", sha_agent_gcs_location)
    #adding additional variables to dict
    config["sha_agent_gcs_location"]=sha_agent_gcs_location
    config["target_project_id"] = config["prod_project"]
    config['target_environment_name']=config["prod_env_deploy"]
    with open("agent_artifacts/metadata.json" , encoding='utf-8') as metadata_file:
        metadata = json.load(metadata_file)

    config["source_flow_names"]=metadata["source_flow_names"]
    config["updated_commit_message"]=metadata["updated_commit_message"]
    config["impacted_version_ids"]=metadata["impacted_version_ids"]

    # To execute steps in order
    main(config)
