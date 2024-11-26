"""Helper classes for parsing Agent Responses."""

# Copyright 2024 Google LLC
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

import dataclasses
import json
from typing import Any, Union

from google.cloud.dialogflowcx_v3beta1 import types
from google.protobuf.json_format import MessageToDict

DataStoreConnectionSignals = (
    types.data_store_connection.DataStoreConnectionSignals
)

_EXECUTION_SEQUENCE_KEY = "DataStore Execution Sequence"

@dataclasses.dataclass
class Snippet:
   uri: Union[str, None]
   title: Union[str, None]
   text: Union[str, None]

   def to_prompt_snippet(self) -> str:
    result = []
    if self.title:
       result.append(self.title)
    if self.text:
        result.append(self.text)

    return "\n".join(result) if result else ""

@dataclasses.dataclass
class AgentResponse:
    """Dataclass for storing relevant fields of detect intent response."""
    # ResponseMessages
    answer_text: str = None

    # MatchType
    match_type: str = None

    # DataStoreConnectionSignals
    rewriter_llm_rendered_prompt: str = None
    rewriter_llm_output: str = None
    rewritten_query: str = None
    search_results: list[Snippet] = dataclasses.field(default_factory=list)
    answer_generator_llm_rendered_prompt: str = None
    answer_generator_llm_output: str = None
    generated_answer: str = None
    cited_snippet_indices: list[int] = dataclasses.field(default_factory=list)
    grounding_decision: str = None
    grounding_score: str = None
    safety_decision: str = None
    safety_banned_phrase_match: str = None

    # DiagnosticInfo ExecutionResult
    response_type: str = None
    response_reason: str = None
    latency: float = None
    faq_citation: bool = None
    search_fallback: bool = None
    unstructured_citation: bool = None
    website_citation: bool = None
    language: str = None

    def from_query_result(self, query_result: types.session.QueryResult):
        """Extracts the relevant fields from a QueryResult proto message."""
        answer_text = self._extract_text(query_result)
        match_type = self._extract_match_type(query_result)
        execution_result = self._extract_execution_result(query_result)

        self.answer_text=answer_text
        self.match_type=match_type
        self.response_type = execution_result.get("response_type")
        self.response_reason = execution_result.get("response_reason")
        self.latency = execution_result.get("latency")
        self.faq_citation = execution_result.get("faq_citation")
        self.search_fallback = execution_result.get("ucs_fallback")
        self.unstructured_citation = execution_result.get(
            "unstructured_citation")
        self.website_citation = execution_result.get("website_citation")
        self.language = execution_result.get("language")

        if query_result.data_store_connection_signals:
            self._extract_data_store_connection_signals(
                query_result.data_store_connection_signals
                )

    @classmethod
    def from_row(cls, row: dict[str, Any]):
        """Extracts the relevant fields from a dictionary."""
        row = row.copy()
        search_results = []
        for search_result in json.loads(row["search_results"]):
            search_results.append(Snippet(**search_result))

        row["search_results"] = search_results
        row["cited_snippet_indices"] = json.loads(row["cited_snippet_indices"])

        return cls(**row)

    def to_row(self):
        """Dumps the query result fields to a dictionary."""
        result = dataclasses.asdict(self)
        result["search_results"] = json.dumps(
            result.pop("search_results", []), indent=4
        )
        result["cited_snippet_indices"] = json.dumps(
            result["cited_snippet_indices"])

        return result

    @staticmethod
    def _extract_match_type(query_result: types.session.QueryResult) -> str:
        """Extracts the name of the match type from query result."""
        try:
            return types.session.Match.MatchType(
                query_result.match.match_type).name

        except ValueError:
            # if an enum type is returned which is not visible externally then
            # fallback to default value
            return types.session.Match.MatchType(0).name

    @staticmethod
    def _extract_text(res: types.session.QueryResult) -> str:
        all_text: list[str] = []
        if res.response_messages:
            for rm in res.response_messages:
                if rm.text and len(rm.text.text) > 0:
                    all_text.append(rm.text.text[0])

        final_text = "\n".join(all_text)

        return final_text

    @staticmethod
    def _extract_execution_result(
            query_result: types.session.QueryResult) -> dict[str, Any]:
        """Extracts the execution result from diagnostic info."""
        if _EXECUTION_SEQUENCE_KEY in query_result.diagnostic_info:
            execution_sequence = query_result.diagnostic_info[
                _EXECUTION_SEQUENCE_KEY
                ]
            if "executionResult" in execution_sequence:
                return MessageToDict(execution_sequence["executionResult"])
        return {}

    def _extract_search_results(
        self,
        data_store_connection_signals: DataStoreConnectionSignals
        ):
        """Extracts search results as a list of strings."""
        self.search_results = []
        for search_snippet in data_store_connection_signals.search_snippets:
            self.search_results.append(
                Snippet(
                    uri=search_snippet.document_uri,
                    title=search_snippet.document_title,
                    text=search_snippet.text,
                )
            )

    def _extract_citation_indices(
            self,
            data_store_connection_signals: DataStoreConnectionSignals
            ):
        """Extracts the links and snippets used to generate answer."""
        self.cited_snippet_indices = []
        for cited_snippet in data_store_connection_signals.cited_snippets:
            self.cited_snippet_indices.append(cited_snippet.snippet_index)

    @staticmethod
    def _extract_grounding_decision(
            grounding_signals: DataStoreConnectionSignals.GroundingSignals
            ) -> str:
        return DataStoreConnectionSignals.GroundingSignals.GroundingDecision(
            grounding_signals.decision
            ).name

    @staticmethod
    def _extract_grounding_score(
            grounding_signals: DataStoreConnectionSignals.GroundingSignals
            ):
        return DataStoreConnectionSignals.GroundingSignals.GroundingScoreBucket(
            grounding_signals.score
            ).name

    def _extract_grounding_signals(
            self, data_store_connection_signals: DataStoreConnectionSignals
            ) -> dict[str, str]:
        grounding_signals = data_store_connection_signals.grounding_signals
        if not grounding_signals:
            self.grounding_decision = None
            self.grounding_score = None
        else:
            self.grounding_decision = self._extract_grounding_decision(
                grounding_signals)
            self.grounding_score = self._extract_grounding_score(
                grounding_signals)

    def _extract_rewriter_llm_signals(
            self,
            data_store_connection_signals: DataStoreConnectionSignals
            ):
        rewriter_model_call_signals = (
            data_store_connection_signals.rewriter_model_call_signals
            )
        if not rewriter_model_call_signals:
            self.rewriter_llm_rendered_prompt = None
            self.rewriter_llm_output = None

        else:
            self.rewriter_llm_rendered_prompt = (
                rewriter_model_call_signals.rendered_prompt
            )
            self.rewriter_llm_output = rewriter_model_call_signals.model_output

    def _extract_answer_generator_llm_signals(
            self,
            data_store_connection_signals: DataStoreConnectionSignals
            ) -> dict[str, str]:
        answer_generation_model_call_signals = (
            data_store_connection_signals.answer_generation_model_call_signals
            )
        if not answer_generation_model_call_signals:
            self.answer_generator_llm_rendered_prompt = None
            self.answer_generator_llm_output = None

        else:
            self.answer_generator_llm_rendered_prompt = (
                answer_generation_model_call_signals.rendered_prompt
            )
            self.answer_generator_llm_output = (
                answer_generation_model_call_signals.model_output
            )

    @staticmethod
    def _extract_safety_decision(
            safety_signals: DataStoreConnectionSignals.SafetySignals) -> str:
        return DataStoreConnectionSignals.SafetySignals.SafetyDecision(
            safety_signals.decision
            ).name

    @staticmethod
    def _extract_safety_banned_phrase(
            safety_signals: DataStoreConnectionSignals.SafetySignals
            ) -> str:
        return DataStoreConnectionSignals.SafetySignals.BannedPhraseMatch(
            safety_signals.banned_phrase_match
            ).name

    def _extract_safety_signals(
            self, data_store_connection_signals: DataStoreConnectionSignals
            ) -> dict[str, str]:
        safety_signals = data_store_connection_signals.safety_signals
        if not safety_signals:
            self.safety_decision = None
            self.safety_banned_phrase_match = None
        else:
            self.safety_decision = self._extract_safety_decision(safety_signals)
            self.safety_banned_phrase_match = (
                self._extract_safety_banned_phrase(safety_signals)
            )

    def _extract_data_store_connection_signals(
            self,
            data_store_connection_signals: DataStoreConnectionSignals
            ) -> dict[str, Any]:
            self._extract_rewriter_llm_signals(data_store_connection_signals
                                               )
            self.rewritten_query = (
                data_store_connection_signals.rewritten_query
                if data_store_connection_signals.rewritten_query
                else None
            )

            self._extract_grounding_signals(data_store_connection_signals)
            self._extract_search_results(data_store_connection_signals)
            self._extract_answer_generator_llm_signals(
                data_store_connection_signals
                )
            self.generated_answer = (
                data_store_connection_signals.answer
                if data_store_connection_signals.answer
                else None
            )
            self._extract_citation_indices(data_store_connection_signals)
            self._extract_safety_signals(data_store_connection_signals)

    @property
    def search_result_links(self):
        return [search_result.uri for search_result in self.search_results]

    @property
    def cited_search_results(self):
        return [self.search_results[idx] for idx in self.cited_snippet_indices]

    @property
    def cited_search_result_links(self):
        return [
            search_result.uri for search_result in self.cited_search_results]

    @property
    def prompt_snippets(self):
        return [
            search_result.to_prompt_snippet()
            for search_result in self.search_results
        ]
