from dfcx_scrapi.core.agents import Agents
from dfcx_scrapi.core.versions import Versions
from dfcx_scrapi.core.environments import Environments
from dfcx_scrapi.core.flows import Flows

from typing import Dict, List

class impacted:
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
        agent_details=agents.get_agent_by_display_name(display_name=self.source_agent_name,
                                                    project_id=self.source_project_id)

        self.agent_id=agent_details.name

        #get environment id
        env_details=self.env.get_environment_by_display_name(display_name=self.environment_name
                                                        ,agent_id=self.agent_id)
        self.env_id=env_details.name

        #get history
        self.hist=self.env.lookup_environment_history(environment_id=self.env_id)

    @staticmethod
    def filterflows(env1,env2,flowmap,versions):
        impactedflows=[]
        for k,v in env1.items():
            if v!=env2.get(k,0):
                impactedflows.append(k)


        # filter flow map for impacted flow
        def flt(kv,t=impactedflows):
            k,v=kv
            if k.split("/")[-1] in t:
                return True
            else:
                False

        filtered_dict = dict(filter(flt, flowmap.items()))

        #getting version ids
        impactedVersionIds=[]
        for ver in versions:
            ver=ver.version
            flow=ver.split("/")[-3]
            if flow in impactedflows:
                impactedVersionIds.append(ver)


        return filtered_dict,impactedVersionIds



    def checkFlow(
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
        for i in self.hist[1].version_configs:
            flow=i.version.split("/")[-3]
            version=i.version.split("/")[-1]
            env2[flow]=version

        #get flow map for id name comparision
        
        flowmap=self.flows.get_flows_map(agent_id=self.agent_id)

        self.filtered_dict,self.impactedVersionIds=impacted.filterflows(env1,env2,flowmap,self.hist[0].version_configs)

        print("filtered flow name vs id map",self.filtered_dict)
        print("flow id vs version id map",self.impactedVersionIds)
        return self.filtered_dict,self.impactedVersionIds


def main():
    source_project_id=sys.argv[1]
    source_agent_name=sys.argv[2]
    obj=impacted(source_project_id=source_project_id,source_agent_name=source_agent_name)
    result=obj.checkFlow()
    return result

# if used this script via cli as a file
if __name__=='__main__':
    main()

