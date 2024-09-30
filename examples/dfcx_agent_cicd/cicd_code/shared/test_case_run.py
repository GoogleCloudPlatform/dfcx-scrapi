""" Running test cases and produce results"""

from typing import Tuple, Dict
import logging

from dfcx_scrapi.core.test_cases import TestCases
from dfcx_scrapi.core.agents import Agents
from dfcx_scrapi.core.environments import Environments

# logging config
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

class RunTestCases:
    """
    Manages and executes test cases for Dialogflow CX agents.

    This class provides functionality to run test cases against a specified 
    Dialogflow CX agent and environment. It retrieves the necessary agent and 
    environment information and allows triggering test cases with optional tag filtering.

    Attributes:
        project_id: The ID of the Google Cloud project where the agent resides.
        agent_name: The display name of the agent.
        environment_name: The display name of the agent's environment (can be None).

    Methods:
        triggerTestcase: Executes test cases for the agent, optionally filtered by tags.
    """

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

        agent_details=agents.get_agent_by_display_name(
            display_name=self.agent_name,
            project_id=self.project_id)

        self.agent_id=agent_details.name

        #get environment id
        if self.environment_name:
            env_details=env.get_environment_by_display_name(
                display_name=self.environment_name,
                agent_id=self.agent_id)
            self.env_id=env_details.name
        else:
            self.env_id=None

    def trigger_test_case(
        self,
        tags,
        agent_id=None,
        env_id=None) -> Tuple[Dict[str, int], bool] :
        """
        Function to trigger the test case module in dfcx 
        Returns:
        Result: Dict of results
        boolean mentioning test case status
        """
        if not agent_id:
            agent_id=self.agent_id
        if not env_id:
            env_id=self.env_id
        tc=TestCases()
        tc_list=tc.list_test_cases(agent_id=agent_id)

        #get test cases
        try:
            filtered_tc = [
                testcase
                for testcase in tc_list
                if any(
                    tag in testcase
                    for tag in tags
                )
            ]

        except AttributeError as e:
            print(
                f"Test case not found to run due to error {e}. "
                "UAT deployment will be done without test case validation"
            )
            result={"Pass": 0, "Fail": 0}
            return result, True 
        filtered_tc_id=[filtestcase.name for filtestcase in filtered_tc]
        print(filtered_tc_id)

        #run the test cases
        tc_result=tc.batch_run_test_cases(test_cases=filtered_tc_id,
                        agent_id=agent_id,
                        environment=env_id)
        print(f"test case results {tc_result}")

        pass_count=0
        fail_count=0
        for result in tc_result.results:
            if result.test_result==1:
                pass_count+=1
            else:
                fail_count+=1

        print(f"Pass: {pass_count}, Fail: {fail_count}")
        result={"Pass": pass_count, "Fail": fail_count}

        if fail_count>0:
            return result,False
        return result,True
