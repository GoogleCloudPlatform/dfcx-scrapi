"""A set of Utility methods to check resources stats on DFCX Agents."""

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

import logging
import time
from typing import Dict, List
import pandas as pd

from dfcx_scrapi.core import scrapi_base
from dfcx_scrapi.agent_extract import agents

# logging config
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

class AgentCheckerUtil(scrapi_base.ScrapiBase):
    """Utility class for checking DFCX Agents."""

    def __init__(
        self,
        agent_id: str,
        gcs_bucket_uri: str,
        creds_path: str = None,
        creds_dict: Dict = None,
        creds=None,
        scope=False,
    ):
        super().__init__(
            creds_path=creds_path,
            creds_dict=creds_dict,
            creds=creds,
            scope=scope,
        )
        self.agent_id = agent_id
        self.special_pages = [
            "End Session",
            "End Flow",
            "Start Page",
            "Current Page",
            "Previous Page",
        ]

        startup_time = time.time()
        self.extract = agents.Agents(agent_id)
        processing_time = time.time()
        logging.debug(f"STARTUP: {processing_time - startup_time}")

        self.data = self.extract.process_agent(agent_id, gcs_bucket_uri)
        logging.debug(f"TOTAL PROCESSING: {time.time() - processing_time}")

        self.active_intents_df = self.active_intents_to_dataframe()

    def _filter_special_pages(self, page: str, filter_special_pages: bool):
        """Recursion helper to check for special page match."""
        if filter_special_pages and page in self.special_pages:
            return True

        return False

    def _recurse_edges(self, edges: Dict[str, List[str]], page: str,
                      visited: set, depth: int, max_depth: int,
                      filter_special_pages: bool):
        """Recursion method used to traverse the agent graph for page data.

        Args:
          edges: The set of graph edges collected from the agent.
          page: The current Page Display Name
          visited: A set of visited Page nodes
          depth: The current recursion depth
          max_depth: The max recursion depth
          filter_special_pages: Will discard all self.special_pages from output
            if set to False.
        """
        if depth == max_depth:
            return visited

        if page in edges:
            for inner_page in edges[page]:
                if self._filter_special_pages(inner_page, filter_special_pages):
                    return visited

                if inner_page not in visited:
                    visited.add(inner_page)
                    visited = self._recurse_edges(
                        edges, inner_page, visited, depth+1, max_depth,
                        filter_special_pages)

        return visited

    def _mark_unreachable_pages(self, df: pd.DataFrame) -> pd.DataFrame:
        """Mark dataframe rows True if the page is unreachable in graph."""
        for idx, row in df.iterrows():
            for page in self.data.unreachable_pages[row["flow"]]:
                if row["page"] == page:
                    df.loc[idx, "unreachable"] = True

        return df

    def get_reachable_pages(
            self,
            flow_display_name: str,
            page_display_name: str = "Start Page",
            max_depth: int = 1,
            filter_special_pages = True) -> List[str]:
        """Get all pages in the graph that are reachable via transition routes,
        starting from a given Flow and Page.

        Args:
          flow_display_name: The display name of the flow
          page_display_name: The display name of the page. Defaults to
            "Start Page"
          max_depth: The max recursion depth to search the graph from the
            provided starting point. For example, a max_depth of 2 would produce
            all reachable Pages that are 2 transition routes away from the
            starting Flow/Page. Defaults to 1.
          filter_special_pages: Will filter out all self.special_pages. Defaults
            to True.
          """
        if page_display_name in ["START", "START_PAGE", "Start", "Start Page"]:
            page_display_name = "Start Page"
            page_display_name = f"{flow_display_name}: {page_display_name}"

        visited = self._recurse_edges(
            self.data.graph.edges, page_display_name, set(), 0, max_depth,
            filter_special_pages)

        return list(visited)

    def active_intents_to_dataframe(self) -> pd.DataFrame:
        """Gets all intents referenced in the agent, across all flows and pages,
        and produces a dataframe listing which flows/pages reference each
        intent.

        Returns:
            A dataframe with columns
            intent - the intent display name
            flow - the Flow Display Name where the intent resides
            page - the Page Display Name where the intent resides
            unreachable - Denotes whether the Flow/Page/Intent combination is
              unreachable in the graph.
        """
        df = pd.DataFrame({
            "intent": pd.Series(dtype="str"),
            "flow": pd.Series(dtype="str"),
            "page": pd.Series(dtype="str"),
            "unreachable": pd.Series(dtype="bool")
            })

        # Loop over active_intents, create temp dataframe, then concat with the
        # main dataframe to build out the complete Flow/Page/Intent dataset.
        for flow in self.data.active_intents:
            for pair in self.data.active_intents[flow]:
                intent = pair[0]
                page = pair[1]
                temp = pd.DataFrame({
                    "intent": [intent],
                    "flow": [flow],
                    "page": [page],
                    "unreachable": [False]})
                df = pd.concat([df, temp])

        df = df.reset_index(drop=True)

        # Finally, determine what rows are unreachable.
        self.active_intents_df = self._mark_unreachable_pages(df)

        return self.active_intents_df

    def get_unused_intents(self) -> List:
        """Get all unused Intents across the agent."""
        if self.active_intents_df.empty:
            self.active_intents_df = self.active_intents_to_dataframe()
        active_intents_set = set(self.active_intents_df.intent.to_list())
        all_intents_set = set(self.data.intents_map.keys())

        return list(all_intents_set.difference(active_intents_set))

    def get_unreachable_intents(self) -> pd.DataFrame:
        """Get all unreachable Intents across the agent.

        An Intent is unreachable if it resides on a page that is also
        unreachable.
        """
        if self.active_intents_df.empty:
            self.active_intents_df = self.active_intents_to_dataframe()

        return self.active_intents_df[self.active_intents_df["unreachable"]]
