"""Test Cases Resource functions."""

# Copyright 2023 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import pandas as pd
import logging
from typing import Dict, List

from google.cloud.dialogflowcx_v3beta1 import services
from google.cloud.dialogflowcx_v3beta1 import types
from google.protobuf import field_mask_pb2

from dfcx_scrapi.core import scrapi_base
from dfcx_scrapi.core import flows
from dfcx_scrapi.core import pages

# logging config
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


class TestCases(scrapi_base.ScrapiBase):
    """Core Class for CX Test Cases."""

    def __init__(
        self,
        creds_path: str = None,
        creds_dict: Dict = None,
        creds=None,
        scope=False,
        agent_id: str = None,
        test_case_id: str = None,
    ):
        super().__init__(
            creds_path=creds_path,
            creds_dict=creds_dict,
            creds=creds,
            scope=scope,
        )

        if agent_id:
            self.agent_id = agent_id
            self.client_options = self._set_region(self.agent_id)

        if test_case_id:
            self.test_case_id = test_case_id
            self.client_options = self._set_region(self.test_case_id)

    def _convert_test_result_to_string(self, test_case: types.TestCase) -> str:
        """Converts the Enum result to a string."""
        if test_case.last_test_result.test_result == 0:
            return "TEST_RESULT_UNSPECIFIED"
        elif test_case.last_test_result.test_result == 1:
            return "PASSED"
        elif test_case.last_test_result.test_result == 2:
            return "FAILED"
        else:
            return ""

    def _convert_test_result_to_bool(self, test_case: types.TestCase) -> bool:
        """Converts the String result to a boolean."""
        test_result = self._convert_test_result_to_string(test_case)

        if test_result == "PASSED":
            return True
        elif test_result == "FAILED":
            return False
        else:
            return None

    def _get_flow_id_from_test_config(
            self, test_case: types.TestCase) -> str:
        """Attempt to get the Flow ID from the Test Case Test Config."""
        if "flow" in test_case.test_config:
            return test_case.test_config.flow
        elif "page" in test_case.test_config:
            return "/".join(test_case.test_config.page.split("/")[:8])
        else:
            agent_id = "/".join(test_case.name.split("/")[:6])
            return f"{agent_id}/flows/00000000-0000-0000-0000-000000000000"

    def _get_page_id_from_test_config(
            self, test_case: types.TestCase, flow_id: str) -> str:
        """Attempt to get the Page ID from the Test Case Test Config."""
        if "page" in test_case.test_config:
            return test_case.test_config.page
        else:
            return f"{flow_id}/pages/START_PAGE"

    def _get_page_display_name(
            self, flow_id: str, page_id: str,
            pages_map: Dict[str, Dict[str, str]]) -> str:
        """Get the Page Display Name from the Pages Map based on the Page ID."""
        page_map = pages_map.get(flow_id, None)
        page = "START_PAGE"
        if page_map:
            page = page_map.get(page_id, None)

        return page

    def _process_test_case(self, test_case, flows_map, pages_map):
        """Takes a response from list_test_cases and returns a single row
        dataframe of the test case result.

        Args:
          test_case: The test case response
          flows_map: A dictionary mapping flow IDs to flow display names
          pages_map: A dictionary with keys as flow IDs and values as
            dictionaries mapping page IDs to page display names for that flow

        Returns: A dataframe with columns:
          display_name, id, short_id, tags, creation_time, start_flow,
          start_page, test_result, passed, test_time
        """
        flow_id = self._get_flow_id_from_test_config(test_case)
        page_id = self._get_page_id_from_test_config(test_case, flow_id)
        page = self._get_page_display_name(flow_id, page_id, pages_map)
        test_result = self._convert_test_result_to_bool(test_case)

        return pd.DataFrame(
            {
                "display_name": [test_case.display_name],
                "id": [test_case.name],
                "short_id": [test_case.name.split("/")[-1]],
                "tags": [",".join(test_case.tags)],
                "creation_time": [test_case.creation_time],
                "start_flow": [flows_map.get(flow_id, None)],
                "start_page": [page],
                # "test_result": [test_result],
                "passed": [test_result],
                "test_time": [test_case.last_test_result.test_time]
            }
        )

    def _retest_cases(
            self, test_case_df: pd.DataFrame, retest_ids: List[str]
            ) -> pd.DataFrame:
        print("To retest:", len(retest_ids))
        response = self.batch_run_test_cases(retest_ids, self.agent_id)
        for result in response.results:
            # Results may not be in the same order as they went in
            # Process the name a bit to remove the /results/id part
            tc_id_full = "/".join(result.name.split("/")[:-2])
            tc_id = tc_id_full.rsplit("/", maxsplit=1)[-1]

            # Update dataframe where id = tc_id_full
            # row = test_case_df.loc[test_case_df['id']==tc_id_full]
            test_case_df.loc[
                test_case_df["id"] == tc_id_full, "short_id"
            ] = tc_id
            # test_case_df.loc[
            #     test_case_df["id"] == tc_id_full, "test_result"
            # ] = str(result.test_result)
            test_case_df.loc[
                test_case_df["id"] == tc_id_full, "test_time"
            ] = result.test_time
            test_case_df.loc[test_case_df["id"] == tc_id_full,"passed"] = (
                str(result.test_result) == "TestResult.PASSED"
            )

        return test_case_df

    @scrapi_base.api_call_counter_decorator
    def list_test_cases(
        self, agent_id: str = None, include_conversation_turns: bool = False
    ):
        """List test cases from an agent.

        Args:
          agent_id: The agent to list all test cases for.
            `projects/<Project ID>/locations/<Location ID>/agents/<Agent ID>`
          include_conversation_turns: Either to include the conversation turns
            in the test cases or not. Default is False
            which shows only the basic metadata about the test cases.

        Returns:
          List of test cases from an agent.
        """

        if not agent_id:
            agent_id = self.agent_id

        if include_conversation_turns:
            test_case_view = types.ListTestCasesRequest.TestCaseView.FULL
        else:
            test_case_view = types.ListTestCasesRequest.TestCaseView.BASIC

        request = types.test_case.ListTestCasesRequest(
            parent=agent_id, view=test_case_view
        )

        client_options = self._set_region(agent_id)

        client = services.test_cases.TestCasesClient(
            credentials=self.creds, client_options=client_options
        )

        response = client.list_test_cases(request)

        test_cases = []
        for page in response.pages:
            for test_case in page.test_cases:
                test_cases.append(test_case)

        return test_cases

    @scrapi_base.api_call_counter_decorator
    def export_test_cases(
        self,
        gcs_uri: str,
        agent_id: str = None,
        data_format: str = None,
        data_filter: str = None,
    ):
        """Export test cases from an agent to cloud storage

        Args:
          gcs_uri: The GCS URI to export the test cases to. The format of this
            URI must be `gs://<bucket-name>/<object-name>`. If unspecified,
            the serialized test cases are returned inline.
          agent_id: The agent to export test cases from.
            `projects/<Project ID>/locations/<Location ID>/agents/<Agent ID>`
          data_format: The data format of the exported test cases. If not
            specified, `BLOB` is assumed.
          data_filter: The filter expression used to filter exported test
            cases, see `API Filtering <https://aip.dev/160>`__. The expression
            is case insensitive and supports the following syntax:
              name = [OR name = ] ...
              For example:
                -  "name = t1 OR name = t2" matches the test case with the
                exact resource name "t1" or "t2".

        Returns:
          Long running operation for export
        """

        if not agent_id:
            agent_id = self.agent_id

        request = types.test_case.ExportTestCasesRequest()
        request.parent = agent_id
        request.gcs_uri = gcs_uri
        request.data_format = data_format
        request.filter = data_filter

        client_options = self._set_region(agent_id)
        client = services.test_cases.TestCasesClient(
            credentials=self.creds, client_options=client_options
        )
        response = client.export_test_cases(request)

        return response

    @scrapi_base.api_call_counter_decorator
    def create_test_case(self, test_case: types.TestCase, agent_id: str = None):
        """Create a new Test Case in the specified CX Agent.

        Args:
          test_case: The test case to create.
          agent_id: The agent to create the test case for. Format:
              `projects/<Project ID>/locations/<Location ID>/agents/<Agent ID>`

        Returns:
          The test case which was created
        """
        if not agent_id:
            agent_id = self.agent_id

        request = types.test_case.CreateTestCaseRequest()
        request.parent = agent_id
        request.test_case = test_case

        client_options = self._set_region(agent_id)
        client = services.test_cases.TestCasesClient(
            credentials=self.creds, client_options=client_options
        )
        response = client.create_test_case(request)
        return response

    @scrapi_base.api_call_counter_decorator
    def get_test_case(self, test_case_id: str):
        """Get test case object from CX Agent.

        Args:
          test_case_id: The name of the test case. Format:
            `projects/<Project ID>/locations/<Location ID>/agents/<Agent ID>/
              testCases/<TestCase ID>`

        Returns:
          The test case object
        """

        request = types.test_case.GetTestCaseRequest()
        request.name = test_case_id

        client_options = self._set_region(test_case_id)
        client = services.test_cases.TestCasesClient(
            credentials=self.creds, client_options=client_options
        )
        response = client.get_test_case(request)
        return response

    @scrapi_base.api_call_counter_decorator
    def import_test_cases(self, gcs_uri: str, agent_id: str = None):
        """Import test cases from cloud storage.

        Args:
          gcs_uri: The GCS URI to import test cases from. The format of this
            URI must be `gs://<bucket-name>/<object-name>`
          agent_id: The agent to import test cases to. Format:
            `projects/<Project ID>/locations/<Location ID>/agents/<Agent ID>`

        Returns:
          Long running operation for importing test cases.
        """

        if not agent_id:
            agent_id = self.agent_id

        request = types.test_case.ImportTestCasesRequest()
        request.parent = agent_id
        request.gcs_uri = gcs_uri

        client_options = self._set_region(agent_id)
        client = services.test_cases.TestCasesClient(
            credentials=self.creds, client_options=client_options
        )
        response = client.import_test_cases(request)
        result = response.result()
        return result

    @scrapi_base.api_call_counter_decorator
    def batch_delete_test_cases(
        self,
        test_case_ids: List[str],
        agent_id: str = None):
        """Delete a set of test cases from an agent.

        Args:
          test_case_id: List of test case names in the following format:
            `projects/<Project ID>/locations/ <Location ID>/agents/<AgentID>/
              testCases/<TestCase ID>`
          agent_id: The agent to delete test cases from. Format:
            `projects/<Project ID>/locations/<Location ID>/agents/<Agent ID>`.

        Returns:
          None
        """

        if not agent_id:
            agent_id = self.agent_id

        request = types.test_case.BatchDeleteTestCasesRequest()
        request.parent = agent_id
        request.names = test_case_ids

        client_options = self._set_region(agent_id)
        client = services.test_cases.TestCasesClient(
            credentials=self.creds, client_options=client_options
        )
        client.batch_delete_test_cases(request)

    @scrapi_base.api_call_counter_decorator
    def list_test_case_results(self, test_case_id: str):
        """List the results from a specific Test Case.

        Args:
          test_case_id: The test case to list results for. Format:
            `projects/<Project ID>/locations/<Location ID>/agents/<Agent ID>/
              testCases/<TestCase ID>`
            NOTE: Specify a ``-`` as a wildcard for TestCase ID to list
            results across multiple test cases.

        Returns:
          List of test case results
        """

        request = types.test_case.ListTestCaseResultsRequest()
        request.parent = test_case_id

        client_options = self._set_region(test_case_id)
        client = services.test_cases.TestCasesClient(
            credentials=self.creds, client_options=client_options
        )
        response = client.list_test_case_results(request)

        test_case_results = []
        for page in response.pages:
            for result in page.test_case_results:
                test_case_results.append(result)

        return test_case_results

    @scrapi_base.api_call_counter_decorator
    def batch_run_test_cases(
        self,
        test_cases: List[str],
        agent_id: str = None,
        environment: str = None):
        """Run a set of test cases to get their latest results.

        Args:
          test_cases: List of Test Case IDs in the following format:
            `projects/<Project ID>/locations/<Location ID>/agents/<Agent ID>/
              testCases/<TestCase ID>`
          agent_id: The CX Agent ID to run the Test Cases on.
            `projects/<Project ID>/locations/<Location ID>/agents/<AgentID>`
          environment: If not set, draft environment is assumed. Format:
            `projects/<Project ID>/locations/<Location ID>/agents/<Agent ID>/
            environments/<Environment ID>`

        Returns:
          Results for the set of run test cases.
        """

        if not agent_id:
            agent_id = self.agent_id

        request = types.test_case.BatchRunTestCasesRequest()
        request.parent = agent_id
        request.environment = environment
        request.test_cases = test_cases

        client_options = self._set_region(agent_id)
        client = services.test_cases.TestCasesClient(
            credentials=self.creds, client_options=client_options
        )
        response = client.batch_run_test_cases(request)
        results = response.result()
        return results

    @scrapi_base.api_call_counter_decorator
    def update_test_case(
        self,
        test_case_id: str = None,
        obj: types.TestCase = None,
        **kwargs) -> types.TestCase:
        """Update Test Case attributes for a specified Test Case.

        Args:
          test_case_id: The Test Case ID to update.
          obj: The Test Case obj of types.TestCase to use for the update.

        Returns:
          The updated Test Case.
        """

        if obj:
            test_case = obj
            test_case.name = test_case_id
        else:
            if not test_case_id:
                test_case_id = self.test_case_id
            test_case = self.get_test_case(test_case_id)

        for key, value in kwargs.items():
            setattr(test_case, key, value)
        paths = kwargs.keys()
        mask = field_mask_pb2.FieldMask(paths=paths)

        request = types.test_case.UpdateTestCaseRequest()
        request.test_case = test_case
        request.update_mask = mask

        client_options = self._set_region(test_case_id)
        client = services.test_cases.TestCasesClient(
            credentials=self.creds, client_options=client_options
        )
        response = client.update_test_case(request)
        return response

    @scrapi_base.api_call_counter_decorator
    def run_test_case(self, test_case_id: str, environment: str = None):
        """Run test case and get result for a specified test case.

        Args:
          test_case_id: Test Case ID in the following format:
            `projects/<Project ID>/locations/ <Location ID>/agents/<AgentID>/
              testCases/<TestCase ID>`
          environment: The CX Environment name. If not set, DRAFT environment
            is assumed. Format: `projects/<Project ID>/locations/<Location ID>/
              agents/<Agent ID>/environments/<Environment ID>`

        Returns:
          The test case result.
        """

        request = types.test_case.RunTestCaseRequest()
        request.name = test_case_id
        request.environment = environment

        client_options = self._set_region(test_case_id)
        client = services.test_cases.TestCasesClient(
            credentials=self.creds, client_options=client_options
        )
        response = client.run_test_case(request)
        results = response.result()
        return results

    @scrapi_base.api_call_counter_decorator
    def get_test_case_result(self, test_case_result_id: str):
        """Get test case result for a specified run on a specified test case.

        Args:
          test_case_result_id: The Test Case Result ID to retrieve.
            projects/<Project ID>/locations/<Location ID>/agents/<Agent ID>/
              testCases/<TestCase ID>/results/<TestCaseResult ID>

        Returns:
          The test case result.
        """
        request = types.test_case.GetTestCaseResultRequest()
        request.name = test_case_result_id

        client_options = self._set_region(test_case_result_id)
        client = services.test_cases.TestCasesClient(
            credentials=self.creds, client_options=client_options
        )
        response = client.get_test_case_result(request)
        return response

    @scrapi_base.api_call_counter_decorator
    def calculate_coverage(self, coverage_type: int, agent_id: str = None):
        """Calculate coverage of different resources in the test case set.

        Args:
          coverage_type: The type of coverage requested.
            INTENT = 1
            PAGE_TRANSITION = 2
            TRANSITION_ROUTE_GROUP = 3
          agent: The CX agent to calculate coverage for.
            `projects/<Project ID>/locations/<Location ID>/agents/<Agent ID>`

        Returns:
          The Coverage response of the test cases for the type specified.
        """

        if not agent_id:
            agent_id = self.agent_id

        if coverage_type not in [1, 2, 3]:
            raise ValueError(
                f"Invalid coverage_type: {coverage_type}. coverage_type must "
                "be must be 1, 2 or 3"
            )

        request = types.test_case.CalculateCoverageRequest()
        request.agent = agent_id
        request.type_ = coverage_type

        client_options = self._set_region(agent_id)
        client = services.test_cases.TestCasesClient(
            credentials=self.creds, client_options=client_options
        )
        response = client.calculate_coverage(request)
        return response

    def get_test_case_results_df(self, agent_id=None, retest_all=False):
        """Convert Test Cases to Dataframe.

        Gets the test case results for this agent, and generates a dataframe
        with their details. Any tests without a result will be run in a batch.

        Args:
          agent_id: The agent to create the test case for. Format:
              `projects/<Project ID>/locations/<Location ID>/agents/<Agent ID>`
          retest_all: if true, all test cases are re-run,
            regardless of whether or not they had a result

        Returns:
          DataFrame of test case results for this agent, with columns:
            display_name, id, short_id, tags, creation_time, start_flow,
            start_page, passed, test_time
        """
        if agent_id:
            self.agent_id = agent_id

        dfcx_flows = flows.Flows(creds=self.creds, agent_id=self.agent_id)
        dfcx_pages = pages.Pages(creds=self.creds)
        flows_map = dfcx_flows.get_flows_map(agent_id=self.agent_id)
        pages_map = {}
        for flow_id in flows_map.keys():
            pages_map[flow_id] = dfcx_pages.get_pages_map(flow_id=flow_id)

        test_case_results = self.list_test_cases(self.agent_id)
        retest_ids = []
        test_case_rows = []

        for test_case in test_case_results:
            row = self._process_test_case(test_case, flows_map, pages_map)
            test_case_rows.append(row)
            test_result = self._convert_test_result_to_string(test_case)
            if retest_all or test_result == "TEST_RESULT_UNSPECIFIED":
                retest_ids.append(test_case.name)

        # Create dataframe
        test_case_df = pd.concat(test_case_rows)

        # Retest any that haven't been run yet
        if len(retest_ids) > 0:
            test_case_df = self._retest_cases(test_case_df,retest_ids)

        return test_case_df
