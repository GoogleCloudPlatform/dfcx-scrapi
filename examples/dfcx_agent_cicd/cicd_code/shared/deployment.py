from dfcx_scrapi.core.agents import Agents
from dfcx_scrapi.core.versions import Versions 
from dfcx_scrapi.core.environments import Environments 
from dfcx_scrapi.core.flows import Flows
from google.cloud import dialogflowcx_v3beta1
from google.cloud.dialogflowcx_v3beta1 import types
from google.api_core.client_options import ClientOptions


from testcaserun import runtestcases
from webhookupdate import updatewebhook
from google.cloud import storage
import sys
import datetime
import time
import json
import logging

# logging config
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

"""
[1] import to destination project
[1.1] update the webhooks uri
[2] run test cases. If passed proceed else exit.
[3] Collect Flow id to version them
[4] Check if the count of versions of a flow is not exceeding 20(limit) else delete the older version
    and make room for new version cut
[5] cut a version of those flows
[5.1] storing new version ids created
[6] deploy created versions to the env
[7] sync the deployed version back deployed env in dev
"""

class Deployment:
    def __init__(self,input_dict):
        for key, value in input_dict.items():
            setattr(self, key, value)     

    #[1] import to destination project
    def importAgent(self,webhookenv):
        
        agent=Agents()
        target_agent_details=agent.get_agent_by_display_name(display_name=self.agent_name,
                                                            project_id=self.target_project_id)

        self.target_agent_id=target_agent_details.name


        #restoring the agent from the SHA ID folder 
        agent.restore_agent(agent_id=self.target_agent_id,
                            gcs_bucket_uri=self.sha_agent_gcs_location)

        logging.info("import to destination project done")

        #[1.1] update webhooks uri
        updatewebhook(self.target_agent_id,webhookenv)
        

    #[2] Run the the test cases and only cut a version if it is passed.
    def testCaseValidation(self):
        tags=['#'+f for f in self.source_flow_names]
        obj=runtestcases(
            project_id=self.target_project_id,
            agent_name=self.agent_name,
            environment_name=None)
        stats,result=obj.triggerTestcase(tags=tags)
        logging.info(f"test case result {stats}")
        if not result:
            sys.exit(2)

    #[3] Collect Flow id to version them
    def collectFlowid(self):
        time.sleep(50)
        flow=Flows()
        logging.info(f"flows to deployed in {self.target_project_id} project: {self.source_flow_names}")
        flow_ids=[]
        for flow_name in self.source_flow_names:
            flow_details=flow.get_flow_by_display_name(display_name=flow_name,
                                                    agent_id=self.target_agent_id)
            flow_ids.append(flow_details.name)
        self.flow_ids=flow_ids

    #[4] Check if the count of versions of a flow is not exceeding 20(limit) else delete the older version
    # and make room for new version cut
    def versionCountDelete(self):
        versions=Versions()
        for flow_id in self.flow_ids:
            flowver=versions.list_versions(flow_id=flow_id)
        if len(flowver)==20:
            deletever=res[-1].name
            versions.delete_version(version_id=deletever)
            logging.info(f"deleted version id {deletever} in project {self.target_project_id}")

    #[5] cut a version of those flows
    def versionCut(self):
        versions=Versions()
        vers=[]
        for flow_id in self.flow_ids:
            v_display_name=f"version cut by CI/CD {datetime.datetime.now()}"
            ver=versions.create_version(flow_id=flow_id,
                                        description=self.updatedcommitmessage,
                                        display_name=v_display_name)
            vers.append(ver)

        #[5.1] storing new version ids created
        new_versions=[]
        for ver in vers:
            verresult=ver.result()
            versionid=verresult.name
            new_versions.append(versionid)
        self.new_versions=new_versions
        logging.info(f"versions cut in {self.target_project_id} project")


    # [6] deploy created versions to the env
    def deployVersions(self):
        env=Environments()
        # get env id
        env_details=env.get_environment_by_display_name(display_name=self.target_environment_name
                                                        ,agent_id=self.target_agent_id)
        self.target_env_id=env_details.name

        # deploy the version created to this env id

        for new_version in self.new_versions:
            env.deploy_flow_to_environment(
                environment_id=self.target_env_id,
                flow_version=new_version)

        logging.info(f"versions deployed to deployed env {self.target_project_id} project")

    # [6] deploy created versions to the env
    def devprodsync(self):
        agent=Agents()
        dev_agent_details=agent.get_agent_by_display_name(display_name=self.agent_name,
                                                            project_id=self.dev_project)

        dev_agent_id=dev_agent_details.name
        env=Environments()
        # get env id
        env_details=env.get_environment_by_display_name(display_name=self.devprodsyncenv
                                                        ,agent_id=dev_agent_id)
        self.devprod_env_id=env_details.name

        # deploy the version created to this env id

        for new_version in self.impactedVersionIds:
            env.deploy_flow_to_environment(
                environment_id=self.devprod_env_id,
                flow_version=new_version)

        logging.info(f"flows deployed in prod is synced with {self.dev_project} project to {self.devprodsyncenv} environment ")

    def datastoreUpdate(self,projectlevel):
        if projectlevel=='uat':
            engine_id=self.uat_engine_id
        elif projectlevel=='uat':
            engine_id=self.prod_engine_id
        else:
             engine_id=""
        
        agents=Agents()
        agentupdate=agents.get_agent(self.target_agent_id)
        app=types.Agent.GenAppBuilderSettings(engine=engine_id)
        kwargs={'gen_app_builder_settings':app}
        resp=agents.update_agent(agent_id=self.target_agent_id,**kwargs)

        logging.info("datastore id updated")