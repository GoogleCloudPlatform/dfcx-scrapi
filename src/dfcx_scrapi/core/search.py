"""Search methods for Vertex Search and Conversation."""

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

import re
from typing import Any, Dict, List, Optional, Union

from google.cloud.discoveryengine import (
    Document,
    DocumentServiceClient,
    Interval,
    ListDocumentsRequest,
    SearchRequest,
    SearchServiceClient,
    UserInfo,
)

from dfcx_scrapi.core import scrapi_base


class Search(scrapi_base.ScrapiBase):
    """Core Class for Search Client functions."""

    def __init__(
        self,
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

    @staticmethod
    def build_image_query(
        search_request: Dict[str, Any]
    ) -> Union[SearchRequest.ImageQuery, None]:
        image_query = search_request.get("image_query", None)
        if image_query:
            image_bytes = image_query.get("image_bytes", None)
            return SearchRequest.ImageQuery(image_bytes=image_bytes)

        else:
            return None

    @staticmethod
    def build_user_info(
        search_request: Dict[str, Any]
    ) -> Union[UserInfo, None]:

        user_info = search_request.get("user_info", None)
        if user_info:
            user_id = user_info.get("user_id", None)
            user_agent = user_info.get("user_agent", None)
            return UserInfo(user_id=user_id, user_agent=user_agent)

        else:
            return None

    @staticmethod
    def build_interval(interval_dict: Dict[str, Any]) -> Interval:
        for k, v in interval_dict.items():
            if k == "minimum":
                return Interval(minimum=v)
            elif k == "exclusive_minimum":
                return Interval(exclusive_minimum=v)
            elif k == "maximum":
                return Interval(maximum=v)
            elif k == "exclusive_maximum":
                return Interval(exclusive_maximum=v)
            else:
                return None

    @staticmethod
    def search_url(urls: List[str], url: str, regex: bool = False) -> List[str]:
        """Searches a url in a list of urls."""
        matched_urls: List[str] = []

        if regex:
            pattern = re.compile(url)
            for item in urls:
                if pattern.search(item):
                    matched_urls.append(item)
                    print(item)

        else:
            for item in urls:
                if url in item:
                    matched_urls.append(item)
                    print(item)

        return matched_urls

    def build_facet_key(
        self, facet_key_dict: Dict[str, Any]
    ) -> SearchRequest.FacetSpec.FacetKey:
        intervals_list = facet_key_dict.get("intervals", None)
        if intervals_list:
            all_intervals = []
            for interval in intervals_list:
                all_intervals.append(self.build_interval(interval))

        return SearchRequest.FacetSpec.FacetKey(
            key=facet_key_dict.get("key", None),
            intervals=all_intervals,
            restricted_values=facet_key_dict.get("restricted_values", None),
            prefixes=facet_key_dict.get("prefixes", None),
            contains=facet_key_dict.get("contains", None),
            case_insensitive=facet_key_dict.get("case_insensitive", False),
            order_by=facet_key_dict.get("order_by", None),
        )

    def build_single_facet_spec(
        self, spec: Dict[str, Any]
    ) -> SearchRequest.FacetSpec:
        facet_key_dict = spec.get("facet_key", None)
        if not facet_key_dict:
            raise ValueError(
                "`facet_key` is required when providing FacetSpec."
            )
        facet_key = self.build_facet_key(facet_key_dict)

        return SearchRequest.FacetSpec(
            facet_key=facet_key,
            limit=spec.get("limit", None),
            excluded_filter_keys=spec.get("excluded_filter_keys", None),
            enable_dynamic_position=spec.get("enable_dynamic_position", None),
        )

    def build_facet_specs(
        self, search_request: Dict[str, Any]
    ) -> Union[List[SearchRequest.FacetSpec], None]:
        facet_specs = search_request.get("facet_specs", None)
        if facet_specs:
            all_specs = []
            for spec in facet_specs:
                all_specs.append(self.build_single_facet_spec(spec))

            return all_specs

        else:
            return None

    def build_condition_boost_spec(
        self, spec: Dict[str, Any]
    ) -> SearchRequest.BoostSpec.ConditionBoostSpec:
        return SearchRequest.BoostSpec.ConditionBoostSpec(
            condition=spec.get("condition", None), boost=spec.get("boost", None)
        )

    def build_boost_spec(
        self, search_request: Dict[str, Any]
    ) -> Union[SearchRequest.BoostSpec, None]:
        boost_spec_dict = search_request.get("boost_spec", None)
        if boost_spec_dict:
            condition_boost_specs = boost_spec_dict.get(
                "condition_boost_specs", None
            )
            all_boost_specs = []
            for spec in condition_boost_specs:
                all_boost_specs.append(self.build_condition_boost_spec(spec))
            return SearchRequest.BoostSpec(
                condition_boost_specs=all_boost_specs
            )

        else:
            return None

    def get_condition_from_map(
            self, exp_spec_dict: Dict[str, Any]
            ) -> SearchRequest.QueryExpansionSpec.Condition:
        condition_map = {
            "DISABLED": SearchRequest.QueryExpansionSpec.Condition.DISABLED, # pylint: disable=C0301
            "AUTO": SearchRequest.QueryExpansionSpec.Condition.AUTO,
        }

        condition_value = exp_spec_dict.get("condition", "DISABLED")

        return condition_map[condition_value]

    def build_query_expansion_spec(
        self, search_request: Dict[str, Any]
    ) -> Union[SearchRequest.QueryExpansionSpec, None]:
        exp_spec_dict = search_request.get("query_expansion_spec", None)
        if exp_spec_dict:
            condition = self.get_condition_from_map(exp_spec_dict)
            pin_unexpanded_results = exp_spec_dict.get(
                "pin_unexpanded_results", False
            )

            return SearchRequest.QueryExpansionSpec(
                condition=condition,
                pin_unexpanded_results=pin_unexpanded_results,
            )

        else:
            return None

    def get_spell_correct_mode_from_map(
        self, spell_spec_dict: Dict[str, Any]
    ) -> SearchRequest.SpellCorrectionSpec.Mode:
        mode_map = {
            "SUGGESTION_ONLY": SearchRequest.SpellCorrectionSpec.Mode.SUGGESTION_ONLY, # noqa: E501
            "AUTO": SearchRequest.SpellCorrectionSpec.Mode.AUTO,
        }

        mode_value = spell_spec_dict.get("mode", "AUTO")

        return mode_map[mode_value]

    def build_spell_correction_spec(
        self, search_request: Dict[str, Any]
    ) -> Union[SearchRequest.SpellCorrectionSpec, None]:
        spell_spec_dict = search_request.get("spell_correction_spec", None)
        if spell_spec_dict:
            mode = self.get_spell_correct_mode_from_map(spell_spec_dict)
            return SearchRequest.SpellCorrectionSpec(mode=mode)

        else:
            return None

    def build_model_prompt_spec(
        self, content_spec_dict: Dict[str, Any]
    ) -> SearchRequest.ContentSearchSpec.SummarySpec.ModelPromptSpec:
        model_prompt_spec_dict = content_spec_dict.get(
            "model_prompt_spec", None
        )
        if model_prompt_spec_dict:
            return SearchRequest.ContentSearchSpec.SummarySpec.ModelPromptSpec(
                preamble=model_prompt_spec_dict.get("preamble", None)
            )

        else:
            return None

    def build_model_spec(
        self, content_spec_dict: Dict[str, Any]
    ) -> SearchRequest.ContentSearchSpec.SummarySpec.ModelSpec:
        model_spec_dict = content_spec_dict.get("model_spec", None)
        if model_spec_dict:
            return SearchRequest.ContentSearchSpec.SummarySpec.ModelSpec(
                version=model_spec_dict.get("version", "stable")
            )

        else:
            return None

    def build_snippet_spec(
            self) -> SearchRequest.ContentSearchSpec.SnippetSpec:
        return SearchRequest.ContentSearchSpec.SnippetSpec(
            return_snippet=True
        )

    def build_summary_spec(
        self, content_spec_dict: Dict[str, Any]
    ) -> SearchRequest.ContentSearchSpec.SummarySpec:

        model_prompt_spec = self.build_model_prompt_spec(content_spec_dict)
        model_spec = self.build_model_spec(content_spec_dict)

        return SearchRequest.ContentSearchSpec.SummarySpec(
            summary_result_count=content_spec_dict.get(
                "summary_result_count", 10
            ),
            include_citations=content_spec_dict.get("include_citations", False),
            ignore_adversarial_query=content_spec_dict.get(
                "ignore_adversarial_query", False
            ),
            ignore_non_summary_seeking_query=content_spec_dict.get(
                "ignore_non_summary_seeking_query", False
            ),
            model_prompt_spec=model_prompt_spec,
            language_code=content_spec_dict.get("language_code", "en"),
            model_spec=model_spec,
        )

    def build_extractive_content_spec(
        self, content_spec_dict: Dict[str, Any]
    ) -> Union[
        SearchRequest.ContentSearchSpec.ExtractiveContentSpec, None
    ]:

        ext_spec_dict = content_spec_dict.get("extractive_content_spec", None)
        if ext_spec_dict:
            return SearchRequest.ContentSearchSpec.ExtractiveContentSpec(
                max_extractive_answer_count=ext_spec_dict.get(
                    "max_extractive_answer_count", 5
                ),
                max_extractive_segment_count=ext_spec_dict.get(
                    "max_extractive_segment_count", 5
                ),
                return_extractive_segment_score=ext_spec_dict.get(
                    "return_extractive_segment_score", False
                ),
                num_previous_segments=ext_spec_dict.get(
                    "num_previous_segments", 5
                ),
                num_next_segments=ext_spec_dict.get("num_next_segments", 5),
            )
        else:
            return None

    def build_content_search_spec(
        self, search_request: Dict[str, Any]
    ) -> Union[SearchRequest.ContentSearchSpec, None]:
        content_spec_dict = search_request.get("content_search_spec", None)
        if content_spec_dict:
            snippet_spec = self.build_snippet_spec()
            summary_spec = self.build_summary_spec(content_spec_dict)
            extractive_content_spec = self.build_extractive_content_spec(
                content_spec_dict
            )

            return SearchRequest.ContentSearchSpec(
                snippet_spec=snippet_spec,
                summary_spect=summary_spec,
                extractive_content_spec=extractive_content_spec,
            )

        else:
            return None

    def build_embedding_vector(
        self, vector_dict: Dict[str, Any]
    ) -> SearchRequest.EmbeddingSpec.EmbeddingVector:
        return SearchRequest.EmbeddingSpec.EmbeddingVector(
            field_path=vector_dict.get("field_path", None),
            vector=vector_dict.get("vector", None),
        )

    def build_embedding_spec(
        self, search_request: Dict[str, Any]
    ) -> Union[SearchRequest.EmbeddingSpec, None]:
        embedding_vectors_dict = search_request.get("embedding_vectors", None)
        if embedding_vectors_dict:
            vector_list = embedding_vectors_dict.get("embedding_vectors", None)
            all_vectors = []
            for vector_dict in vector_list:
                all_vectors.append(self.build_embedding_vector(vector_dict))
            return SearchRequest.EmbeddingSpec(
                embedding_vectors=all_vectors
            )

        else:
            return None

    def list_documents(
            self, datastore_id: str, page_size: int = 1000) -> List[Document]:
        """List all documents in the provided datastore."""
        client_options = self._client_options_discovery_engine(datastore_id)
        client = DocumentServiceClient(
            credentials=self.creds,
            client_options=client_options
        )

        request = ListDocumentsRequest(
            parent=f"{datastore_id}/branches/default_branch",
            page_size=page_size
        )

        response = client.list_documents(request)

        all_docs: List[Document] = []
        for page in response.pages:
            for doc in page.documents:
                all_docs.append(doc)

        return all_docs

    def list_indexed_urls(
            self, datastore_id: str, docs: Optional[List[Document]] = None
            ) -> List[str]:
        """List all indexed URLs from the provided datastore."""
        if not docs:
            docs = self.list_documents(datastore_id)

        urls: List[str] = [doc.content.uri for doc in docs]

        return urls

    def search_doc_id(
            self,
            document_id: str,
            datastore_id: str = None,
            docs: Optional[List[Document]] = None
            ) -> List[str]:
        if not docs and not datastore_id:
            raise ValueError("Must provide either `docs` or `datastore_id`")

        elif not docs and datastore_id:
            docs = self.list_documents(datastore_id)

        doc_found = False
        for doc in docs:
            if doc.parent_document_id == document_id:
                doc_found = True
                print(doc)
                break

        if not doc_found:
            print(f"Document not found for Doc ID: `{document_id}`")

    def check_datastore_index_status(self, datastore_id: str):
        """Checks the current indexing status of your datastore."""

        PENDING_MESSAGE = "No docs found.\n" \
            "It\'s likely one of two issues:\n" \
            "\t[1] Your data store is not finished indexing.\n" \
            "\t[2] Your data store failed indexing.\n\n" \
            "If you just added your data store, it can take up to 4 hours" \
                " before it will become available."

        SUCCESS_MESSAGE = "Success! 🎉\n" \
            "Your indexing is complete.\n" \
            "Your index contains {DOCS} documents."

        docs = self.list_documents(datastore_id)

        if len(docs) == 0:
            print(PENDING_MESSAGE)
        else:
            print(SUCCESS_MESSAGE.replace("{DOCS}", str(len(docs))))


    def search(self, search_config: Dict[str, Any], total_results: int = 10):
        """Performs a search against an indexed Vertex Data Store.

        Args:
            search_config: A dictionary containing keys that correspond to the
                SearchRequest attributes as defined in: https://cloud.google.com/python/docs/reference/discoveryengine/latest/google.cloud.discoveryengine.SearchRequest

                For complex attributes that require nested fields, you can pass
                in another Dictionary as the value.

                Example: To represent the complex facet_specs config with some
                other simple parameters, you would do the following.

				```py
                search_config = {
                    "facet_specs": [
                        {
                        "facet_key": {
                            "key": "my_key",
                            "intervals": [
                                {
                                "minimum": .5
                                },
                                {
                                "maximum": .95
                                }
                            ],
                        "case_insensitive": True
                        },
                        "limit": 10
                        }
                    ],
                    "page_size": 10,
                    "offset": 2
                    }
			total_results: Total number of results to return for the search. If
				not specified, will default to 10 results. Increasing this to a
				high number can result in long search times.

        Returns:
                A List of SearchResponse objects.
        """
        serving_config = (
            f"{search_config.get('data_store_id', None)}"
            "/servingConfigs/default_serving_config"
        )

        branch_stub = "/".join(serving_config.split("/")[0:8])
        branch = branch_stub + "/branches/0"

        request = SearchRequest(
            serving_config=serving_config,
            branch=branch,
            query=search_config.get("query", None),
            image_query=self.build_image_query(search_config),
            page_size=search_config.get("page_size", 10),
            page_token=search_config.get("page_token", None),
            offset=search_config.get("offset", 0),
            filter=search_config.get("filter", None),
            canonical_filter=search_config.get("canonical_filter", None),
            order_by=search_config.get("order_by", None),
            user_info=self.build_user_info(search_config),
            facet_specs=self.build_facet_specs(search_config),
            boost_spec=self.build_boost_spec(search_config),
            params=search_config.get("params", None),
            query_expansion_spec=self.build_query_expansion_spec(search_config),
            spell_correction_spec=self.build_spell_correction_spec(
                search_config
            ),
            user_pseudo_id=search_config.get("user_pseudo_id", None),
            content_search_spec=self.build_content_search_spec(search_config),
            embedding_spec=self.build_embedding_spec(search_config),
            ranking_expression=search_config.get("ranking_expression", None),
            safe_search=search_config.get("safe_search", False),
            user_labels=search_config.get("user_labels", None),
        )

        client_options = self._client_options_discovery_engine(serving_config)
        client = SearchServiceClient(
            credentials=self.creds, client_options=client_options
        )
        response = client.search(request)

        all_results = []
        for search_result in response:
            if len(all_results) < total_results:
                all_results.append(search_result)
            else:
                break

        return all_results
