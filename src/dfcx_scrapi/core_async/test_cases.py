"""Test Cases Resource Async functions."""

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
from  google.cloud.dialogflowcx_v3beta1 import types
from google.protobuf import field_mask_pb2

from dfcx_scrapi.core.scrapi_base import ScrapiBase

# logging config
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


class TestCasesAsync(ScrapiBase):
    """Core Class for CX Test Cases Async."""

    def __init__(
        self,
        creds_path: str = None,
        creds_dict: Dict = None,
        creds=None,
        scope=False,
        agent_id: str = None,
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

    @staticmethod
    def iterator(response, attribute):
        """Loops through pages of results to give all results"""
        iterated = []
        for instance in getattr(response, attribute):
            iterated.append(instance)
        return iterated

    def list_test_cases(self, agent_id: str = None):
        """Lists all Test Cases for a given Agent.

        Args:
          agent_id: The agent to list all pages for. Format:
             `projects/<Project ID>/locations/<Location ID>/agents/<Agent ID>`.

        Returns:
          response: List of test cases from an agent as a coroutine
        """

        if not agent_id:
            agent_id = self.agent_id

        request = types.test_case.ListTestCasesRequest()
        request.parent = agent_id

        client_options = self._set_region(agent_id)

        client = services.test_cases.TestCasesAsyncClient(
            credentials=self.creds, client_options=client_options
        )
        response = client.list_test_cases(request)

        return response

    def export_test_cases(
        self,
        gcs_uri: str,
        agent_id: str = None,
        data_format: str = None,
        data_filter: str = None,
    ):
        """Export test cases from an agent to cloud storage.

        Args:
          gcs_uri: The `Google Cloud Storage URI to export the test cases to.
            The format of this URI must be `gs://<bucket-name>/<object-name>`.
            If unspecified, the serialized test cases is returned inline.
          agent_id: Optional. The agent where to export test cases from.
            Format: `projects/<Project ID>/locations/<Location ID>/agents/
              <Agent ID>`
          data_format: The data format of the exported test cases. If not
            specified, ``BLOB`` is assumed.
          data_filter: The filter expression used to filter exported test
            cases, see `API Filtering <https://aip.dev/160>`__. The expression
            is case insensitive and supports the following syntax:
            name = [OR name = ] ...
            For example:
              -  "name = t1 OR name = t2" matches the test case with the
              exact resource name "t1" or "t2".

        Returns:
          response: Long running operation for export as a coroutine
        """

        if not agent_id:
            agent_id = self.agent_id

        request = types.test_case.ExportTestCasesRequest()
        request.parent = agent_id
        request.gcs_uri = gcs_uri
        request.data_format = data_format
        request.filter = data_filter

        client_options = self._set_region(agent_id)
        client = services.test_cases.TestCasesAsyncClient(
            credentials=self.creds, client_options=client_options
        )
        response = client.export_test_cases(request)
        return response

    def create_test_case(
        self,
        test_case: types.TestCase,
        agent_id: str = None):
        """Create a new Test Case.

        Args:
          test_case: The Test Case to create.
          agent_id: The agent to create the test case for. Format:
            `projects/<Project ID>/locations/<Location ID>/agents/<Agent ID>`.

        Returns:
          response: test case which was created as a coroutine
        """

        if not agent_id:
            agent_id = self.agent_id

        request = types.test_case.CreateTestCaseRequest()
        request.parent = agent_id
        request.test_case = test_case

        client_options = self._set_region(agent_id)
        client = services.test_cases.TestCasesAsyncClient(
            credentials=self.creds, client_options=client_options
        )
        response = client.create_test_case(request)
        return response

    def get_test_case(self, test_case_id: str):
        """Get the specified Test Case object.

        Args:
          test_case_id: The name of the testcase. Format:
            `projects/<Project ID>/locations/<Location ID>/agents/<Agent ID>/
              testCases/<TestCase ID>`.

        Returns:
          response: Test Case object as coroutine
        """

        request = types.test_case.GetTestCaseRequest()
        request.name = test_case_id

        client_options = self._set_region(test_case_id)
        client = services.test_cases.TestCasesAsyncClient(
            credentials=self.creds, client_options=client_options
        )
        response = client.get_test_case(request)
        return response

    def import_test_cases(self, gcs_uri: str, agent_id: str = None):
        """Import Test Cases from Google Cloud Storage.

        Args:
          gcs_uri: The Google Cloud Storage URI to import test cases from. The
            format of this URI must be `gs://<bucket-name>/<object-name>`.
          agent_id: The agent to import test cases to. Format:
            `projects/<Project ID>/locations/<Location ID>/agents/<Agent ID>`.

        Returns:
          response: long running operation for importing test cases as
            couroutine.
        """

        if not agent_id:
            agent_id = self.agent_id

        request = types.test_case.ImportTestCasesRequest()
        request.parent = agent_id
        request.gcs_uri = gcs_uri

        client_options = self._set_region(agent_id)
        client = services.test_cases.TestCasesAsyncClient(
            credentials=self.creds, client_options=client_options
        )
        response = client.import_test_cases(request)
        return response

    def batch_delete_test_cases(
        self,
        test_case_ids: List[str],
        agent_id: str = None):
        """Delete a set of Test Cases from an Agent.

        Args:
          test_case_ids: List of Test Case IDs to Delete. Format of Test Case
            IDs: `projects/<Project ID>/locations/ <Location ID>/agents/
              <AgentID>/testCases/<TestCase ID>`.
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
        client = services.test_cases.TestCasesAsyncClient(
            credentials=self.creds, client_options=client_options
        )
        response = client.batch_delete_test_cases(request)
        return response

    def list_test_case_results(self, test_case_id: str):
        """List a set of Test Case results for a given Test Case ID.

        Args:
          test_case_id: The test case to list results for. Format:
            `projects/<Project ID>/locations/<Location ID>/agents/<Agent ID>/
              testCases/<TestCase ID>`. Specify a ``-`` as a wildcard for
              TestCase ID to list results across multiple test cases.

        Returns:
          response: List of Test Case results
        """

        request = types.test_case.ListTestCaseResultsRequest()
        request.parent = test_case_id

        client_options = self._set_region(test_case_id)
        client = services.test_cases.TestCasesAsyncClient(
            credentials=self.creds, client_options=client_options
        )
        response = client.list_test_case_results(request)
        return response

    def batch_run_test_cases(
        self,
        test_cases: List[str],
        agent_id: str = None,
        environment: str = None):
        """Run a set of Test Cases to get their latest results.

        Args:
          test_cases: List of Test Case IDs to run.
          agent_id: Agent name. Format: `projects/<Project ID>/locations/
            <Location ID>/agents/<AgentID>`.
          environment: If not set, DRAFT environment is assumed. Format:
            `projects/<Project ID>/locations/<Location ID>/agents/<Agent ID>/
            environments/<Environment ID>`.

        Returns:
          response: Results for the set of Test Cases as a coroutine.
        """

        if not agent_id:
            agent_id = self.agent_id

        request = types.test_case.BatchRunTestCasesRequest()
        request.parent = agent_id
        request.environment = environment
        request.test_cases = test_cases
        client_options = self._set_region(agent_id)
        client = services.test_cases.TestCasesAsyncClient(
            credentials=self.creds, client_options=client_options
        )
        response = client.batch_run_test_cases(request)
        return response

    def update_test_case(
        self,
        obj: types.TestCase,
        test_case_id: str = None,
        **kwargs) -> types.TestCase:
        """Update Test Case attributes for a specified Test Case.

        Args:
          obj: The new Test Case object to use for update.
          test_case_id: (Optional) The Test Case ID to update.

        Returns:
          response: updated test case as coroutine.
        """
        test_case = obj
        if test_case_id:
            test_case.name = test_case_id

        for key, value in kwargs.items():
            setattr(test_case, key, value)
        paths = kwargs.keys()
        mask = field_mask_pb2.FieldMask(paths=paths)

        request = types.test_case.UpdateTestCaseRequest()
        request.test_case = test_case
        request.update_mask = mask

        client_options = self._set_region(test_case_id)
        client = services.test_cases.TestCasesAsyncClient(
            credentials=self.creds, client_options=client_options
        )
        response = client.update_test_case(request)
        return response

    def run_test_case(self, test_case_id: str, environment: str = None):
        """Run test case and get result for a specified test case.

        Args:
          test_case_id: Test Case ID to run with format:
            `projects/<Project ID>/locations/ <Location ID>/agents/<AgentID>/
              testCases/<TestCase ID>`.
          environment: (Optional) Environment name. If not set, DRAFT
            environment is assumed. Format: `projects/<Project ID>/locations/
              <Location ID>/agents/<Agent ID>/environments/<Environment ID>`.

        Returns:
          response: Test Case result as coroutine
        """

        request = types.test_case.RunTestCaseRequest()
        request.name = test_case_id
        request.environment = environment

        client_options = self._set_region(test_case_id)
        client = services.test_cases.TestCasesAsyncClient(
            credentials=self.creds, client_options=client_options
        )
        response = client.run_test_case(request)
        return response

    def get_test_case_result(self, test_case_result_id: str):
        """Get Test Case result for a specified run on a specified Test Case.

        Args:
          test_case_result_id: The ID of the Test Case Result. Format:
            projects/<Project ID>/locations/<Location ID>/agents/<Agent ID>/
              testCases/<TestCase ID>/results/<TestCaseResult ID>

        Returns:
          response: Test Case result as coroutine.
        """

        request = types.test_case.GetTestCaseResultRequest()
        request.name = test_case_result_id

        client_options = self._set_region(test_case_result_id)
        client = services.test_cases.TestCasesAsyncClient(
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
          agent_id: The agent to calculate coverage for. Format:
            `projects/<Project ID>/locations/<Location ID>/agents/<Agent ID>`.

        Returns:
          response: coroutine for returning the coverage of the test cases for
            the type_ specified.
        """

        if not agent_id:
            agent_id = self.agent_id

        if coverage_type not in [1, 2, 3]:
            raise ValueError(
                f"invalid coverage_type: {coverage_type}. coverage_type must "
                "be must be 1, 2 or 3"
            )

        request = types.test_case.CalculateCoverageRequest()
        request.agent = agent_id
        request.type_ = coverage_type

        client_options = self._set_region(agent_id)
        client = services.test_cases.TestCasesAsyncClient(
            credentials=self.creds, client_options=client_options
        )
        response = client.calculate_coverage(request)
        return response
