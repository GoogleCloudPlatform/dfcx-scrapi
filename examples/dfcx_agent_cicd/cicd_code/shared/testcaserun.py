from dfcx_scrapi.core.test_cases import TestCases
from dfcx_scrapi.core.agents import Agents
from dfcx_scrapi.core.versions import Versions
from dfcx_scrapi.core.environments import Environments
from dfcx_scrapi.core.flows import Flows
from typing import Tuple, Dict
import logging

# logging config
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

class runtestcases:
    def __init__(
        self,project_id,
        agent_name,
        environment_name
    ):

        self.project_id=project_id
        self.agent_name=agent_name
        self.environment_name=environment_name

        agents=Agents()
        env=Environments()

        agent_details=agents.get_agent_by_display_name(display_name=self.agent_name,
                                                    project_id=self.project_id)

        self.agent_id=agent_details.name

        #get environment id
        if self.environment_name:
            env_details=env.get_environment_by_display_name(display_name=self.environment_name
                                                            ,agent_id=self.agent_id)
            self.env_id=env_details.name
        else:
            self.env_id=None

    def triggerTestcase(
        self,
        tags=["#flownametesttag"],
        agent_id=None,
        env_id=None) -> Tuple[Dict[str, int], bool] :

        if not agent_id:
            agent_id=self.agent_id
        if not env_id:
            env_id=self.env_id
        tc=TestCases()
        tclist=tc.list_test_cases(agent_id=agent_id)
        
        #get test cases
        try:
            filteredtc=[testcase for testcase in tclist if any(True for tag in tags if tag in testcase)]
        except AttributeError as e:
            print("Test case not found to run. UAT deployment will be done without test case validation")
            result={"Pass": 0, "Fail": 0}
            return result, True 
        print(filteredtc)
        filteredtcid=[filtestcase.name for filtestcase in filteredtc]
        print(filteredtcid)

        #run the test cases
        tcresult=tc.batch_run_test_cases(test_cases=filteredtcid,
                        agent_id=agent_id,
                        environment=env_id)
        

        print(tcresult)

        pass_count=0
        fail_count=0
        for result in tcresult.results:
            if result.test_result==1:
                pass_count+=1
            else:
                fail_count+=1

        print(f"Pass: {pass_count}, Fail: {fail_count}")
        result={"Pass": pass_count, "Fail": fail_count}

        if fail_count>0:
            return result,False
        return result,True


def main():
    project_id=sys.argv[1]
    agent_name=sys.argv[2]
    obj=runtestcases(project_id=project_id,agent_name=agent_name)
    stats,result=obj.triggerTestcase(tag="#flownametesttag")
    return result

# if used this script via cli as a file
if __name__=='__main__':
    main()
