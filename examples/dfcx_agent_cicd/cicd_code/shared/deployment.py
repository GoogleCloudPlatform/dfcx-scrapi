""" Shared module to do deployement acting as a wrapper for deployment"""

import datetime
import json
import logging
import sys
import time

from google.cloud.dialogflowcx_v3beta1 import types

from dfcx_scrapi.core.agents import Agents
from dfcx_scrapi.core.environments import Environments
from dfcx_scrapi.core.flows import Flows
from dfcx_scrapi.core.versions import Versions

from .en_vs_other_lang import en_vs_lang
from .test_case_run import RunTestCases
from .webhook_update import update_webhook

# logging config
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

class Deployment:
    """
    Manages the deployment and lifecycle of Dialogflow CX agents.

    This class provides methods for importing, testing, versioning, and
    deploying Dialogflow CX agents across different environments. It handles
    tasks such as:

    - Importing agents from GCS.
    - Updating webhook configurations.
    - Running test cases and validating results.
    - Collecting and managing flow IDs.
    - Versioning and deploying flows.
    - Syncing flows between environments (e.g., dev and prod).
    - Updating datastore settings.

    Attributes:
        (Initialized from an input dictionary)

    Methods:
        import_agent: Imports an agent from GCS to a target project.
        test_case_validation: Runs test cases and validates the results.
        collect_flow_id: Collects the IDs of flows to be deployed.
        version_count_delete: Manages version count and deletes old versions if
            necessary.
        version_cut: Creates new versions of the specified flows.
        deploy_versions: Deploys the new versions to the target environment.
        dev_prod_sync: Synchronizes flows between development and production
            environments.
        datastore_update: Updates datastore settings for the agent.
    """
    def __init__(self,input_dict):
        for key, value in input_dict.items():
            setattr(self, key, value)

    def import_agent(self,webhookenv):
        """Imports a Dialogflow CX agent to the target project.

        This method restores a Dialogflow CX agent from a GCS bucket to the
        specified target project and updates the webhook URI for the agent.

        Args:
            webhookenv: The webhook environment to use for the imported agent.
        """

        agent=Agents()
        target_agent_details=agent.get_agent_by_display_name(
            display_name=self.agent_name,
            project_id=self.target_project_id
        )

        self.target_agent_id=target_agent_details.name


        #restoring the agent from the SHA ID folder
        agent.restore_agent(
            agent_id=self.target_agent_id,
            gcs_bucket_uri=f"{self.sha_agent_gcs_location}/{self.agent_name}",
            restore_option=2
        )

        logging.info("import to destination project done")

        #[1.1] update webhooks uri
        update_webhook(self.target_agent_id,webhookenv)


    def test_case_validation(self):
        """Runs test cases and validates the results.

        This method executes test cases for the specified agent and environment,
        using tags to filter the test cases to run. If any test case fails,
        the script exits with an error code.

        Raises:
            SystemExit: If any test case fails.
        """

        tags=["#"+f for f in self.source_flow_names]
        obj=RunTestCases(
            project_id=self.target_project_id,
            agent_name=self.agent_name,
            environment_name=None)
        stats,result=obj.trigger_test_case(tags=tags)
        logging.info("test case result: %s", json.dumps(stats, indent=2))
        if not result:
            sys.exit(2)


    def collect_flow_id(self):
        """Collects the IDs of flows to be deployed.

        This method retrieves the IDs of the flows specified in
        `self.source_flow_names` from the target Dialogflow CX agent. It
        introduces a 50-second delay to allow for agent stabilization before
        fetching the flow IDs.
        """
        time.sleep(50)
        flow=Flows()
        logging.info(
            "flows to deployed in %s project: %s",
            self.target_project_id,
            self.source_flow_names
        )
        flow_ids=[]
        for flow_name in self.source_flow_names:
            flow_details=flow.get_flow_by_display_name(
                display_name=flow_name,
                agent_id=self.target_agent_id)
            flow_ids.append(flow_details.name
            )
        self.flow_ids=flow_ids

    def version_count_delete(self):
        """
        1. Check if the count of versions of a flow is not exceeding 20(limit)
        else delete the older version
        2. and make room for new version cut
        """
        versions=Versions()
        for flow_id in self.flow_ids:
            flowver=versions.list_versions(flow_id=flow_id)
        if len(flowver)==20:
            deletever=flowver[-1].name
            versions.delete_version(version_id=deletever)
            logging.info(
                "deleted version id %s in project %s",
                deletever,
                self.target_project_id
            )

    def version_cut(self):
        """
        1. Cut a version of those flows
        2. Storing new version ids created
        """
        versions=Versions()
        vers=[]
        for flow_id in self.flow_ids:
            v_display_name=f"version cut by CI/CD {datetime.datetime.now()}"
            ver=versions.create_version(
                flow_id=flow_id,
                description=self.updated_commit_message,
                display_name=v_display_name
            )
            vers.append(ver)

        #storing new version ids created
        new_versions=[]
        for ver in vers:
            verresult=ver.result()
            versionid=verresult.name
            new_versions.append(versionid)
        self.new_versions=new_versions
        logging.info("versions cut in %s project",self.target_project_id)

    def deploy_versions(self):
        """
        1.Deploy created versions to the env
        2.Deploy the version created to this env id
        """
        env=Environments()
        # get env id
        env_details=env.get_environment_by_display_name(
            display_name=self.target_environment_name,
            agent_id=self.target_agent_id
        )
        self.target_env_id=env_details.name

        # deploy the version created to this env id

        for new_version in self.new_versions:
            env.deploy_flow_to_environment(
                environment_id=self.target_env_id,
                flow_version=new_version)

        logging.info("versions deployed to deployed env %s project",
                     self.target_project_id
        )

    def dev_prod_sync(self):
        """
        sync the dev and prod project once deployment happens in prod
        1. Deploy created versions to the env
        2. Deploy the version created to this env id
        """
        agent=Agents()
        dev_agent_details=agent.get_agent_by_display_name(
            display_name=self.agent_name,
            project_id=self.dev_project
        )

        dev_agent_id=dev_agent_details.name
        env=Environments()
        # get env id
        env_details=env.get_environment_by_display_name(
            display_name=self.devprodsyncenv,
            agent_id=dev_agent_id
        )
        self.devprod_env_id=env_details.name

        # deploy the version created to this env id

        for new_version in self.impacted_version_ids:
            env.deploy_flow_to_environment(
                environment_id=self.devprod_env_id,
                flow_version=new_version)

        logging.info("flows deployed in prod is synced with dev environment")

    def datastore_update(self,projectlevel):
        """
        update the datastore id
        """
        if projectlevel=="uat":
            engine_id=self.uat_engine_id
        elif projectlevel=="uat":
            engine_id=self.prod_engine_id
        else:
            engine_id=""
        agents=Agents()
        app=types.Agent.GenAppBuilderSettings(engine=engine_id)
        kwargs={"gen_app_builder_settings":app}
        agents.update_agent(agent_id=self.target_agent_id,**kwargs)

        logging.info("datastore id updated")

    def fullfillment_lang_check(self,lang):
        """Checks fulfillment language coverage compared to English.

        This method compares the fulfillment coverage of the specified language
        (`lang`) with the English language ('en') for the given agent and flows.
        It returns dataframes containing statistics on fulfillment entries,
        parameters, and routes, along with a boolean result indicating whether
        all elements have agent responses in the specified language.

        Args:
            lang: The language code to compare against English (e.g., 'fr-ca').

        Returns:
            A tuple containing:
            - entry_df: DataFrame with statistics on entry fulfillment coverage.
            - param_df: DataFrame with statistics on parameter fulfillment
                coverage.
            - route_df: DataFrame with statistics on route fulfillment coverage.
            - result: A boolean indicating if all elements have agent responses
                in the specified language.
        """

        entry_df,param_df,route_df,result= en_vs_lang(
            self.target_agent_id,
            self.source_flow_names,
            lang
        )
        return entry_df,param_df,route_df,result

