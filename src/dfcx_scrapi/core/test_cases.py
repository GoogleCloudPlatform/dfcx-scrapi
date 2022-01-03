"""Test Cases Resource functions."""

# Copyright 2021 Google LLC
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


import logging
from typing import Dict, List

from google.cloud.dialogflowcx_v3beta1 import services
from google.cloud.dialogflowcx_v3beta1 import types
from google.protobuf import field_mask_pb2

from dfcx_scrapi.core.scrapi_base import ScrapiBase

# logging config
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


class TestCases(ScrapiBase):
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

    def list_test_cases(self, agent_id: str = None):
        """List test cases from an agent.

        Args:
          agent_id: The agent to list all pages for.
            `projects/<Project ID>/locations/<Location ID>/agents/<Agent ID>`

        Returns:
          response: list of test cases from an agent.
        """

        if not agent_id:
            agent_id = self.agent_id

        request = types.test_case.ListTestCasesRequest()
        request.parent = agent_id

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

    def export_test_cases(
        self,
        gcs_uri: str,
        agent_id: str = None,
        data_format: str = None,
        data_filter: str = None,
    ):
        """Export test cases from an agent to cloud storage

        Args:
          gcs_uri:
            The GCS URI to export the test cases to. The format of this URI
              must be `gs://<bucket-name>/<object-name>`. If unspecified,
              the serialized test cases is returned inline.
          agent_id: The agent to export test cases from.
            `projects/<Project ID>/locations/<Location ID>/agents/<Agent ID>`
          data_format:
            The data format of the exported test cases. If not specified,
            `BLOB` is assumed.
          data_filter:
            The filter expression used to filter exported test cases, see
            `API Filtering <https://aip.dev/160>`__. The expression is case
            insensitive and supports the following syntax:
              name = [OR name = ] ...
              For example:
                -  "name = t1 OR name = t2" matches the test case with the
                exact resource name "t1" or "t2".

        Returns:
          response: long running operation for export
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

    def create_test_case(self, test_case: types.TestCase, agent_id: str = None):
        """Create a new Test Case in the specified CX Agent.

        Args:
            test_case: The test case to create.
            agent_id: The agent to create the test case for. Format:
              `projects/<Project ID>/locations/<Location ID>/agents/<Agent ID>`

        Returns:
          response: test case which was created
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

    def get_test_case(self, test_case_id: str):
        """Get test case object from CX Agent.

        Args:
          test_case_id: The name of the test case. Format:
            `projects/<Project ID>/locations/<Location ID>/agents/<Agent ID>/
              testCases/<TestCase ID>`

        Returns:
          response: test case
        """

        request = types.test_case.GetTestCaseRequest()
        request.name = test_case_id

        client_options = self._set_region(test_case_id)
        client = services.test_cases.TestCasesClient(
            credentials=self.creds, client_options=client_options
        )
        response = client.get_test_case(request)
        return response

    def import_test_cases(self, gcs_uri: str, agent_id: str = None):
        """Import test cases from cloud storage.

        Args:
          gcs_uri: The GCS URI to import test cases from. The format of this
            URI must be `gs://<bucket-name>/<object-name>`
          agent_id: The agent to import test cases to. Format:
            `projects/<Project ID>/locations/<Location ID>/agents/<Agent ID>`

        Returns:
          response: long running operation for importing test cases.
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
          response: deleted test cases
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

    def list_test_case_results(self, test_case_id: str):
        """List the results from a specific Test Case.

        Args:
          test_case_id: The test case to list results for. Format:
            `projects/<Project ID>/locations/<Location ID>/agents/<Agent ID>/
              testCases/<TestCase ID>`
              NOTE: Specify a ``-`` as a wildcard for TestCase ID to list
                results across multiple test cases.

        Returns:
          response: List of test case results
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
          response: results for the set of run test cases.
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
          response: updated Test Case.
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
          response: test case result.
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

    def get_test_case_result(self, test_case_result_id: str):
        """Get test case result for a specified run on a specified test case.

        Args:
          test_case_result_id: The Test Case Result ID to retrieve.
            projects/<Project ID>/locations/<Location ID>/agents/<Agent ID>/
              testCases/<TestCase ID>/results/<TestCaseResult ID>

        Returns:
          response: test case result.
        """
        request = types.test_case.GetTestCaseResultRequest()
        request.name = test_case_result_id

        client_options = self._set_region(test_case_result_id)
        client = services.test_cases.TestCasesClient(
            credentials=self.creds, client_options=client_options
        )
        response = client.get_test_case_result(request)
        return response

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
          response: Coverage of the test cases for the type specified.
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
