""" Getting impacted flow functions"""

from dfcx_scrapi.core.agents import Agents
from dfcx_scrapi.core.environments import Environments
from dfcx_scrapi.core.flows import Flows

from typing import Dict


class Impacted:
    """
    Analyzes and identifies changes in Dialogflow CX agent flows across environment versions.

    This class retrieves information about a specified Dialogflow CX agent and its environment,
    including version history and flow details. It then compares the latest two versions to
    identify any changes in the flows, providing a mapping of impacted flow IDs and names.

    Attributes:
        source_project_id: The ID of the Google Cloud project where the agent resides.
        source_agent_name: The display name of the agent.
        environment_name: The display name of the agent's environment (default: "ready to deploy").

    Methods:
        filter_flows: (Static method) Filters a flow map based on 
        differences between two environments.
        check_flow: Identifies and returns a dictionary of 
        changed flows between the latest two versions.
    """

    #Get agent id

    def __init__(
        self,source_project_id,
        source_agent_name,
        environment_name="ready to deploy"
    ):
        self.env=Environments()
        self.flows=Flows()

        self.source_project_id=source_project_id
        self.source_agent_name=source_agent_name
        self.environment_name=environment_name
        self.filtered_dict={}

        agents=Agents()
        agent_details=agents.get_agent_by_display_name(
            display_name=self.source_agent_name,
            project_id=self.source_project_id
        )

        self.agent_id=agent_details.name

        #get environment id
        env_details=self.env.get_environment_by_display_name(
            display_name=self.environment_name
            ,agent_id=self.agent_id
        )
        self.env_id=env_details.name

        #get history
        self.hist=self.env.lookup_environment_history(
            environment_id=self.env_id
        )

    @staticmethod
    def filter_flows(env1,env2,flowmap,versions):
        """ Returns filtered dict and impacted version ids"""
        impacted_flows=[]
        for k,v in env1.items():
            if v!=env2.get(k,0):
                impacted_flows.append(k)

        filtered_dict = {
            k: v for k, v in flowmap.items()
            if k.split("/")[-1] in impacted_flows
        }
        #getting version ids
        impacted_version_ids=[]
        for ver in versions:
            ver=ver.version
            flow=ver.split("/")[-3]
            if flow in impacted_flows:
                impacted_version_ids.append(ver)


        return filtered_dict,impacted_version_ids



    def check_flow(
        self
        ) -> Dict[str, str]:
        #compare latest 2 history
        """
        returns map of flow id:flow name which was found to be changed
        """
        env1={}
        for i in self.hist[0].version_configs:
            flow=i.version.split("/")[-3]
            version=i.version.split("/")[-1]
            env1[flow]=version

        env2={}
        if len(self.hist)>1:
            for i in self.hist[1].version_configs:
                flow=i.version.split("/")[-3]
                version=i.version.split("/")[-1]
                env2[flow]=version

        #get flow map for id name comparision
        flowmap=self.flows.get_flows_map(agent_id=self.agent_id)

        self.filtered_dict,self.impacted_version_ids = Impacted.filter_flows(
            env1,
            env2,
            flowmap,
            self.hist[0].version_configs
        )

        return self.filtered_dict,self.impacted_version_ids
