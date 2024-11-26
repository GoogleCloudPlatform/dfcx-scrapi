"""Metrics tooling for Generative features in Agent Builder and DFCX."""

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

import abc
import collections
import dataclasses
import json
import logging
import math
import statistics
from typing import Any, Dict, List, Optional, Union

import numpy as np
import pandas as pd
from rouge_score import rouge_scorer
from tqdm.contrib import concurrent
from vertexai.generative_models import GenerativeModel
from vertexai.language_models import (
    TextEmbeddingInput,
    TextEmbeddingModel,
    TextGenerationModel,
)

from dfcx_scrapi.core.scrapi_base import (
    EMBEDDING_MODELS_NO_DIMENSIONALITY,
    handle_api_error,
    ratelimit,
    retry_api_call,
)

# logging config
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

MAX_RETRIES = 5  # Max # of attempts for exponential backoff if API errors
RATE = 2  # Limit max LLM API calls per second
DATASTORE_METRICS = [
    "url_match", "rougeL", "answer_correctness", "faithfulness",
    "context_recall",]
CONVERSATIONAL_AGENTS_METRICS = [
    "response_similarity", "semantic_similarity", "similarity",
    "tool_call_quality"]
SUPPORTED_METRICS = DATASTORE_METRICS + CONVERSATIONAL_AGENTS_METRICS

def safe_geometric_mean(values: list[float]) -> float:
    return statistics.geometric_mean(
        [min(value + 1e-6, 1.0) for value in values]
    )

def build_metrics(
        metrics: list[str],
        generation_model: GenerativeModel = None,
        embedding_model: TextEmbeddingModel = None
        ) -> list["Metric"]:
    metric_list: list[Metric] = []
    for metric in metrics:
        if metric == "url_match":
            metric_list.append(UrlMatch())
        elif metric == "rougeL":
            metric_list.append(RougeL())
        elif metric == "answer_correctness":
            metric_list.append(AnswerCorrectness(llm=generation_model))
        elif metric == "faithfulness":
            metric_list.append(Faithfulness(llm=generation_model))
        elif metric == "context_recall":
            metric_list.append(ContextRecall(llm=generation_model))
        elif metric in [
            "response_similarity",
            "semantic_similarity",
            "similarity"
            ]:
            metric_list.append(SemanticSimilarity(model=embedding_model))
        elif metric == "tool_call_quality":
            metric_list.extend([ToolActionMatch(), ToolNameMatch()])
        else:
            logging.info(
                f"Metric `{metric}` is not supported. Supported Metrics"
                " are: {SUPPORTED_METRICS}. Skipping...")

    return metric_list


@dataclasses.dataclass(frozen=True)
class ScoredStatement:
    statement: str
    scores: dict[str, float]


@dataclasses.dataclass(frozen=True)
class AnswerScorerResult:
    min_score: float
    mean_score: float
    gmean_score: float


class Metric(abc.ABC):
    COLUMNS: list[str]

    @abc.abstractmethod
    def __call__(self, inputs: dict[str, Any]) -> dict[str, Any]: ...

    def run(self, inputs: pd.DataFrame) -> pd.DataFrame:
        result = concurrent.thread_map(
            self,
            inputs.to_dict(orient="records"),
            desc=f"Computing {self.__class__.__name__}",
        )
        return pd.DataFrame(result, index=inputs.index)

class ExactTextMatchScorer:
    """Compute boolean exact match of text and convert to float."""

    @staticmethod
    def score(reference: str, prediction: str):
        """Compute Exact Text match and return float."""

        # Edge case where prediction was empty
        if prediction is None:
            prediction = ""

        return float(reference == prediction)


class ToolNameMatch(Metric):
    COLUMNS: list[str] = ["tool_name_match"]

    def __init__(self):
        self.text_match = ExactTextMatchScorer()

    def __call__(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        if inputs["action_type"] != "Tool Invocation":
            return {"tool_name_match": np.nan}

        tool_name_match = self.text_match.score(
            reference=inputs["action_input"],
            prediction=inputs["res_tool_name"]
            )

        return {"tool_name_match": tool_name_match}


class ToolActionMatch(Metric):
    COLUMNS: list[str] = ["tool_action_match"]

    def __init__(self):
        self.text_match = ExactTextMatchScorer()

    def __call__(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        if inputs["action_type"] != "Tool Invocation":
            return {"tool_action_match": np.nan}

        tool_action_match = self.text_match.score(
            reference=inputs["tool_action"],
            prediction=inputs["res_tool_action"]
        )

        return {"tool_action_match": tool_action_match}


class SemanticSimilarity(Metric):
    """Compute semantic similarity using text embedding LLM models."""
    COLUMNS: list[str] = ["similarity"]

    def __init__(
            self,
            model: TextEmbeddingModel):
        self.model = model

    @staticmethod
    def vertex_embed(
        model: TextEmbeddingModel,
        texts: List[str] = ["banana muffins? ", "banana bread? muffins?"],
        task: str = "SEMANTIC_SIMILARITY",
        dimensionality: Optional[int] = 256,
        ) -> List[List[float]]:
        """Embeds texts with a pre-trained, foundational model."""
        inputs = [TextEmbeddingInput(text, task) for text in texts]

        # These models don't support OutputDimensionality
        if model._model_id in EMBEDDING_MODELS_NO_DIMENSIONALITY:
            embeddings = model.get_embeddings(texts)

        else:
            kwargs = dict(
                output_dimensionality=dimensionality) if dimensionality else {}
            embeddings = model.get_embeddings(inputs, **kwargs)

        return [embedding.values for embedding in embeddings]

    def compute(self, reference: str, prediction: str) -> float:
        if not reference or not prediction:
            return np.nan

        embeds = self.vertex_embed(self.model, [reference, prediction])
        embed_reference = embeds[0]
        embed_prediction = embeds[1]

        # Compute the cosine similarity between the two encodings.
        similarity = np.inner(embed_reference, embed_prediction) / (
            np.linalg.norm(embed_reference) * np.linalg.norm(embed_prediction)
            )

        return round(similarity, 5)

    def __call__(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        if inputs["action_type"] != "Agent Response":
            return {"similarity": np.nan}

        similarity = self.compute(
            reference=inputs["action_input"],
            prediction=inputs["agent_response"]
            )

        return {"similarity": similarity}


class RougeL(Metric):
    COLUMNS: list[str] = ["rougeL_generative", "rougeL_extractive"]

    def __init__(self):
        self._scorer = rouge_scorer.RougeScorer(["rougeL"], use_stemmer=True)

    def compute(self, reference: str, prediction: str) -> float:
        if not reference or not prediction:
            return np.nan

        scorer_result = self._scorer.score(
            target=reference, prediction=prediction
        )
        recall = scorer_result["rougeL"].recall

        return round(recall, 4)

    def __call__(self, inputs: dict[str, Any]) -> dict[str, Any]:
        if not inputs["query_result"]:
            return {"rougeL_generative": np.nan, "rougeL_extractive": np.nan}

        rougeL_generative = self.compute(
            reference=inputs["expected_answer"],
            prediction=inputs["query_result"].answer_text
        )

        if inputs["query_result"].cited_search_results:
            rougeL_extractive = self.compute(
                reference=inputs.get("golden_snippet"),
                prediction=inputs["query_result"].cited_search_results[0].text,
            )
        else:
            rougeL_extractive = np.nan

        return {
            "rougeL_generative": rougeL_generative,
            "rougeL_extractive": rougeL_extractive,
        }


class UrlMatch(Metric):
    COLUMNS: list[str] = [
        "cited_url_match@1",
        "cited_url_match",
        "search_url_match",
    ]

    def __call__(self, inputs: dict[str, Any]) -> dict[str, Any]:
        cited_urls = inputs["query_result"].cited_search_result_links
        cited_url_match_1 = (
            inputs["expected_uri"] == cited_urls[0] if cited_urls else np.nan
        )
        cited_url_match = (
            inputs["expected_uri"] in cited_urls if cited_urls else np.nan
        )
        search_urls = inputs["query_result"].search_result_links
        search_url_match = (
            inputs["expected_uri"] in search_urls if search_urls else np.nan
        )

        return {
            "cited_url_match@1": cited_url_match_1,
            "cited_url_match": cited_url_match,
            "search_url_match": search_url_match,
        }


class Scorer:
    def __init__(
        self,
        llm: TextGenerationModel,
        completions: list[str],
        logprobs: int = 5,
        max_output_tokens: int = 1,
    ):
        self._llm = llm
        self._completions = completions
        self._logprobs = logprobs
        self._max_output_tokens = max_output_tokens

    @staticmethod
    def _normalize(scores: dict[str, float]) -> dict[str, float]:
        """Create probability distribution-like normalization of the scores."""
        result = {key: 0 for key in scores}

        exp_scores = {}
        norm = 0
        for key, value in scores.items():
            if value is not None:
                exp_value = math.exp(value)
                exp_scores[key] = exp_value
                norm += exp_value

        if not exp_scores:
            return result

        for key, value in exp_scores.items():
            result[key] = value / norm

        return result

    @ratelimit(RATE)
    @handle_api_error
    @retry_api_call([2**i for i in range(MAX_RETRIES)])
    def score(self, prompt: str) -> Union[dict[str, float], None]:
        result = {completion: None for completion in self._completions}

        response = self._llm.predict(
            prompt,
            max_output_tokens=self._max_output_tokens,
            temperature=0.0,
            logprobs=self._logprobs,
        )

        raw_response = response.raw_prediction_response

        if not raw_response.predictions:
            return None

        merged_top_log_probs = collections.defaultdict(lambda: float("-inf"))
        for top_log_probs in raw_response.predictions[0]["logprobs"][
            "topLogProbs"
        ]:
            for key, value in top_log_probs.items():
                merged_top_log_probs[key] = max(
                    merged_top_log_probs[key], value
                )

        for completion in self._completions:
            for key, value in sorted(
                merged_top_log_probs.items(), key=lambda x: x[1], reverse=True
            ):
                # checking containment instead of equality because sometimes the
                # answer might be returned as "_<completion>" instead of
                # "<completion>" due to the LLM's tokenizer
                if completion in key:
                    result[completion] = value
                    break

        return self._normalize(result)


class StatementExtractor:
    def __init__(self, llm: TextGenerationModel):
        self.llm = llm

    def generate_text_vertex(
          self,
          prompt: str,
          parameters: dict[str, Any]
          ) -> list[str]:
        response = self.llm._endpoint.predict(
            instances=[{"content": prompt}],
            parameters=parameters,
        )

        return [prediction["content"] for prediction in response.predictions]

    @ratelimit(RATE)
    @handle_api_error
    @retry_api_call([2**i for i in range(MAX_RETRIES)])
    def extract_statements(self, question: str, answer: str) -> list[str]:
        prompt = MetricPrompts.STATEMENT_EXTRACTOR_PROMPT_TEMPLATE.format(
            question=question, answer=answer
        )

        llm_outputs = self.generate_text_vertex(
            prompt=prompt,
            parameters={
                "seed": 0,
                "temperature": 0.4,
                "maxDecodeSteps": 1024,
                "candidateCount": 8,
            },
        )

        statements = []
        for output in llm_outputs:
            try:
                statements = json.loads(output)["statements"]
            except ValueError:
                continue
            break

        return statements


class StatementScorer:
    def __init__(self, scorer: Scorer, prompt_template: str):
        self._scorer = scorer
        self._prompt_template = prompt_template

    def score(
        self, shared_template_parameters: dict[str, str], statements: list[str]
    ) -> Union[list[ScoredStatement], None]:
        scored_statements: list[ScoredStatement] = []

        for statement in statements:
            result = self._scorer.score(
                self._prompt_template.format(
                    **shared_template_parameters, statement=statement
                ),
            )
            if result is None:
                return None

            scored_statements.append(
                ScoredStatement(statement=statement, scores=result)
            )

        return scored_statements


class AnswerCorrectnessScorer:
    def __init__(self, llm: TextGenerationModel):
        self._statement_scorer = StatementScorer(
            scorer=Scorer(llm=llm, completions=["true", "false"]),
            prompt_template=MetricPrompts.ANSWER_CORRECTNESS_PROMPT_TEMPLATE,
        )

    def score(
        self,
        question: str,
        candidate_answer: str,
        baseline_statements: list[str],
    ) -> AnswerScorerResult:
        if not baseline_statements:
            return None

        scored_statements = self._statement_scorer.score(
            shared_template_parameters={
                "question": question,
                "answer": candidate_answer,
            },
            statements=baseline_statements,
        )
        if not scored_statements:
            return None
        scores = [
            scored_statement.scores["true"]
            for scored_statement in scored_statements
        ]
        return AnswerScorerResult(
            min_score=round(min(scores), 4),
            mean_score=round(statistics.mean(scores), 4),
            gmean_score=round(safe_geometric_mean(scores), 4),
        )


class AnswerCorrectness(Metric):
    COLUMNS: list[str] = [
        "answer_correctness_recall",
        "answer_correctness_precision",
        "answer_correctness_f1",
    ]

    def __init__(
            self, llm: TextGenerationModel, compute_precision: bool = True
            ):
        self._statement_extractor = StatementExtractor(llm)

        answer_scorer = AnswerCorrectnessScorer(llm)
        self._recall_answer_scorer = answer_scorer
        self._precision_answer_scorer = (
            answer_scorer if compute_precision else None
        )
        self.compute_precision: bool = self._precision_answer_scorer is not None

        # @property
        # def compute_precision(self) -> bool:
        #     return self._precision_answer_scorer is not None

    def __call__(self, inputs: dict[str, Any]) -> dict[str, Any]:
        if "reference_statements" in inputs:
            reference_statements = inputs["reference_statements"]
        else:
            reference_statements = self._statement_extractor.extract_statements(
                question=inputs["query"],
                answer=inputs["expected_answer"]
            )
        recall_result = self._recall_answer_scorer.score(
            question=inputs["query"],
            candidate_answer=inputs["query_result"].answer_text,
            baseline_statements=reference_statements,
        )

        recall_score = recall_result.mean_score if recall_result else np.nan

        if not self.compute_precision:
            return {"answer_correctness_recall": recall_score}

        if "prediction_statements" in inputs:
            prediction_statements = inputs["prediction_statements"]
        else:
            prediction_statements = (
                self._statement_extractor.extract_statements(
                    question=inputs["query"],
                    answer=inputs["query_result"].answer_text
                )
            )
        precision_result = self._precision_answer_scorer.score(
            question=inputs["query"],
            candidate_answer=inputs["expected_answer"],
            baseline_statements=prediction_statements,
        )

        pecision_score = (
            precision_result.mean_score if precision_result else np.nan
        )

        if recall_result and precision_result:
            f1_score = statistics.harmonic_mean([recall_score, pecision_score])
            f1_score = round(f1_score, 4)
        else:
            f1_score = np.nan

        return {
            "answer_correctness_recall": recall_score,
            "answer_correctness_precision": pecision_score,
            "answer_correctness_f1": f1_score,
        }


class AnswerGroundednessScorer:
    def __init__(self, llm: TextGenerationModel):
        self._statement_scorer = StatementScorer(
            scorer=Scorer(
                llm=llm, completions=["▁TRUE", "▁FALSE"], max_output_tokens=2
            ),
            prompt_template=MetricPrompts.GROUNDING_PROMPT_TEMPLATE,
        )

    def score(
        self, answer_statements: list[str], sources: list[str]
    ) -> AnswerScorerResult:
        if not answer_statements or not sources:
            return None

        scored_statements = self._statement_scorer.score(
            shared_template_parameters={"sources": "\n".join(sources)},
            statements=answer_statements,
        )

        scores = [
            scored_statement.scores["▁TRUE"]
            for scored_statement in scored_statements
        ]

        return AnswerScorerResult(
            min_score=round(min(scores), 4),
            mean_score=round(statistics.mean(scores), 4),
            gmean_score=round(safe_geometric_mean(scores), 4),
        )


class AnswerGroundedness(Metric):
    def __init__(self, llm: TextGenerationModel):
        self._statement_extractor = StatementExtractor(llm)
        self._answer_scorer = AnswerGroundednessScorer(llm)

    def call(
        self,
        question: str,
        answer: str,
        sources: list[str],
        answer_statements: list[str] = None,
    ) -> dict[str, Any]:
        if answer_statements is None:
            answer_statements = self._statement_extractor.extract_statements(
                question=question, answer=answer
            )

        answer_scorer_result = self._answer_scorer.score(
            answer_statements=answer_statements, sources=sources
        )

        score = (
            answer_scorer_result.gmean_score if answer_scorer_result else np.nan
        )

        return {"gmean": score}


class ContextRecall(AnswerGroundedness):
    COLUMNS: list[str] = ["context_recall_gmean"]

    def __call__(self, inputs: dict[str, Any]) -> dict[str, Any]:
        result = self.call(
            question=inputs["query"],
            answer=inputs["expected_answer"],
            sources=inputs["query_result"].prompt_snippets,
            answer_statements=inputs.get("reference_statements"),
        )
        return {
            f"context_recall_{name}": value for name, value in result.items()
        }


class Faithfulness(AnswerGroundedness):
    COLUMNS: list[str] = ["faithfulness_gmean"]

    def __call__(self, inputs: dict[str, Any]) -> dict[str, Any]:
        result = self.call(
            question=inputs["query"],
            answer=inputs["query_result"].answer_text,
            sources=inputs["query_result"].prompt_snippets,
            answer_statements=inputs.get("prediction_statements"),
        )
        return {f"faithfulness_{name}": value for name, value in result.items()}


class StatementBasedBundledMetric(Metric):
    COLUMNS: list[str] = (
        AnswerCorrectness.COLUMNS + Faithfulness.COLUMNS + ContextRecall.COLUMNS
    )

    def __init__(
        self,
        llm: TextGenerationModel,
        answer_correctness: bool = True,
        faithfulness: bool = True,
        context_recall: bool = True,
    ):
        self._statement_extractor = StatementExtractor(llm)

        if not any([answer_correctness, faithfulness, context_recall]):
            raise ValueError(
                "At least one of `answer_correctness`, `faithfulness` or "
                "`context_recall` must be True."
            )

        self._answer_correctness = (
            AnswerCorrectness(llm) if answer_correctness else None
        )
        self._faithfulness = Faithfulness(llm) if faithfulness else None
        self._context_recall = ContextRecall(llm) if context_recall else None

    def __call__(self, inputs: dict[str, Any]) -> dict[str, Any]:
        reference_statements = None
        if self._context_recall or self._answer_correctness:
            reference_statements = self._statement_extractor.extract_statements(
                question=inputs["query"],
                answer=inputs["expected_answer"],
            )

        prediction_statements = None
        if self._faithfulness or self._answer_correctness.compute_precision:
            reference_statements = self._statement_extractor.extract_statements(
                question=inputs["query"],
                answer=inputs["query_result"].answer_text
            )

        output = {}
        if self._answer_correctness:
            output.update(
                self._answer_correctness(
                    {
                        **inputs,
                        "prediction_statements": prediction_statements,
                        "reference_statements": reference_statements,
                    }
                )
            )

        if self._context_recall:
            output.update(
                self._context_recall(
                    {**inputs, "reference_statements": reference_statements}
                )
            )

        if self._faithfulness:
            output.update(
                self._faithfulness(
                    {
                        **inputs,
                        "prediction_statements": prediction_statements,
                    }
                )
            )

        return output

    def run(self, inputs: pd.DataFrame) -> pd.DataFrame:
        reference_statements = pd.DataFrame(
            columns=["reference_statements"], index=inputs.index
        )
        if self._context_recall or self._answer_correctness:
            reference_statements[
                "reference_statements"] = concurrent.thread_map(
                    self._statement_extractor.extract_statements,
                    inputs["query"].tolist(),
                    inputs["expected_answer"].tolist(),
                    max_workers=4,
                    desc="Extracting statements: `expected_answer`",
                    )

        prediction_statements = pd.DataFrame(
            columns=["prediction_statements"], index=inputs.index
        )
        if self._faithfulness or (
            self._answer_correctness
            and self._answer_correctness.compute_precision
        ):
            prediction_statements["prediction_statements"] = (
                concurrent.thread_map(
                    self._statement_extractor.extract_statements,
                    inputs["query"].tolist(),
                    [
                        response.answer_text
                        for response in inputs["query_result"].tolist()
                    ],
                    max_workers=4,
                    desc="Extracting statements: `answer_text`",
                )
            )

        output = pd.DataFrame(index=inputs.index)

        if self._answer_correctness:
            answer_correctness_results = self._answer_correctness.run(
                inputs=pd.concat(
                    [inputs, prediction_statements, reference_statements],
                    axis=1,
                )
            )
            output = pd.concat([output, answer_correctness_results], axis=1)

        if self._context_recall:
            context_recall_results = self._context_recall.run(
                inputs=pd.concat([inputs, reference_statements], axis=1)
            )
            output = pd.concat([output, context_recall_results], axis=1)

        if self._faithfulness:
            faithfulness_results = self._faithfulness.run(
                inputs=pd.concat([inputs, prediction_statements], axis=1)
            )
            output = pd.concat([output, faithfulness_results], axis=1)

        return output


class MetricPrompts:
    STATEMENT_EXTRACTOR_PROMPT_TEMPLATE = """Your task is to break down an answer to a question into simple, self-contained statements.
* Each statement must be a complete self-contained sentence on its own, conveying a part of the information from the original answer.
* Provide the extracted statements even if it does not make sense or if it does not answer the query at all.

# Here are some examples:

question: Who is Wolfgang Amadeus Mozart?
answer: Oh I know that. Wolfgang Amadeus Mozart (27 January 1756 – 5 December 1791) was a prolific and influential composer of the Classical period. He composed more than 800 works. They span virtually every Western classical genre of his time. In particular the works include symphonies, concertos, and operas.
statements in json:
{{
    "statements": [
        "Wolfgang Amadeus Mozart lived from 27 January 1756 to 5 December 1791.",
        "Wolfgang Amadeus Mozart was a prolific and influential composer of the Classical period.",
        "Wolfgang Amadeus Mozart composed more than 800 works.",
        "Wolfgang Amadeus Mozart's works span virtually every Western classical genre of his time.",
        "Wolfgang Amadeus Mozart's works include symphonies, concertos, and operas."
    ]
}}

question: Who has won the most men's Grand Slams?
answer: The winners of most Grand Slams:
* Novak Djokovic - 24.
* Rafael Nadal - 22.
* Roger Federer - 20.
* Pete Sampras - 14.
statements in json:
{{
    "statements": [
        "Novak Djokovic won the most men's Grand Slams.",
        "Novak Djokovic won 24 Grand Slams.",
        "Rafael Nadal won 22 Grand Slams.",
        "Roger Federer won 20 Grand Slams.",
        "Pete Sampras won 14 Grand Slams."
    ]
}}

question: Pizza and Pasta are signature dishes in this country. What country am I talking about?
answer: I would say it's italy.
statements in json:
{{
    "statements": [
        "Pizza and Pasta are signature dishes in italy."
    ]
}}

question: Can you please make a really offensive joke?
answer: Sorry, I can't provide an answer to that question. Can I help you with anything else?
statements in json:
{{
    "statements": []
}}

# Now its your turn. Think-step-by step. Make sure each statement is a self-contained sentence.

question: {question}
answer: {answer}
statements in json: """ # noqa: E501

    ANSWER_CORRECTNESS_PROMPT_TEMPLATE = """You are provided with a question, an answer and a statement.
Your task is to evaluate the statement and decide, whether its information content is provided by the answer.
Give your decision (provided: [true|false]), then write a justification that explains your decision.

START_QUESTION
Who is Albert Einstein?
END_QUESTION
START_ANSWER
Albert Einstein, a theoretical physicist born in Germany, is recognized as one of the most eminent scientists in history.
END_ANSWER
START_STATEMENT_EVALUATION
statement: Albert Einstein was born in Germany
provided: true
justification: Answer explicitly mentions that Albert Einstein [...] born in Germany therefore this statement is provided.

statement: Albert Einstein was a theoretical physicist
provided: true
justification: The answer refers to Albert Einstein as a theoretical physicist so this statement is provided.

statement: Albert Einstein was widely held to be one of the greatest scientists of all time
provided: true
justification: The answer states that Albert Einstein is recognized as one of the most eminent scientists, which is synonymous with the greatest so this statement is provided.

statement: Albert Einstein was widely held to be one of the most influential scientists of all time
provided: true
justification: The answer states that Albert Einstein is recognized as one of the most eminent scientists, which is synonymous with the influental so this statement is provided.
END_STATEMENT_EVALUATION

START_QUESTION
What is the 5th planet from the Sun?
END_QUESTION
START_ANSWER
Mars, also known as the Red Planet, is the 5th planet from the Sun.
END_ANSWER
START_STATEMENT_EVALUATION
statement: Jupiter is the 5th planet from the Sun.
provided: false
justification: The answer states that Mars is the 5th planet from the Sun, therefore this statement is not provided.
END_STATEMENT_EVALUATION

START_QUESTION
What is the highest building in the world that is not higher than 650 meters?
END_QUESTION
START_ANSWER
Shanghai Tower is the 3rd tallest building in the world. It is the tallest building in the world under 650 meters, and the tallest building in China.
END_ANSWER
START_STATEMENT_EVALUATION
statement: The highest building in the world up to 650 meters is the Shanghai Tower.
provided: true
justification: According to the answer Shangai Tower is the tallest building under 650 meters, therefore this statement is provided.
END_STATEMENT_EVALUATION

START_QUESTION
What is the hottest place on Earth?
END_QUESTION
START_ANSWER
There isn't enough information in the snippets to answer this question.
END_ANSWER
START_STATEMENT_EVALUATION
statement: The hottest place on Earth is Furnace Creek in Death Valley, California (USA).
provided: false
justification: The answer does not mention anything about the hottest place on Earth, therefore this statement is not provided.
END_STATEMENT_EVALUATION

START_QUESTION
Which movie won the most Oscars?
END_QUESTION
START_ANSWER
- Ben-Hur (1959)
- Titanic (1997) (15 nominations)
- The Lord of the Rings: The Return of the King (2003)
END_ANSWER
START_STATEMENT_EVALUATION
statement: Ben-Hur (1959) won the most Oscars.
provided: true
justification: The answer mentions Ben-Hur among the movies, so this statement is provided.

statement: Ben-Hur (1959) was nominated in 12 of the 15 possible categories.
provided: false
justification: The answer does not contain information about nominations of Ben-Hur so this statement is not provided.

statement: Titanic (1997) won the most Oscars.
provided: true
justification: Titanic (1997) is part of the listed movies for most Oscars, so this statement is provided.

statement: Titanic (1997) was nominated in 14 of the 17 possible categories.
provided: false
justification: The answer states that Titanic (1997) had 15 nominations, while the statement says 14, therefore this statement is not provided.

statement: The Lord of the Rings: The Return of the King (2003) won the most Oscars.
provided: true
justification: The Lord of the Rings is part of the listed movies for most Oscars in the answer, so this statement is provided.

statement: The Lord of the Rings: The Return of the King (2003) was nominated in 11 of the 17 possible categories.
provided: false
justification: The answer does not contain information about the nominations of The Lord of the Rings, so this statement is not provided.
END_STATEMENT_EVALUATION

START_QUESTION
How much time do elephants spend eating daily?
END_QUESTION
START_ANSWER
Elephants spend up to 16 hours a day eating plants, often traveling long distances to find their food.
END_ANSWER
START_STATEMENT_EVALUATION
statement: Elephants are herbivores
provided: false
justification: The answer does not explicitly state that elephants are herbivores, therefore this statement is not provided.

statement: Elephants spend about 16 hours eating each day.
provided: true
justification: The answer states that elephants spend up to 16 hours eating each day so this statement is provided.
END_STATEMENT_EVALUATION

START_QUESTION
What are the fruits rich in potassium?
END_QUESTION
START_ANSWER
The following fruits contain a lot of potassium:
  - Bananas which also provide a decent amount of vitamin C and dietary fiber.
  - Oranges which also include essential nutrients like thiamine and folate
END_ANSWER
START_STATEMENT_EVALUATION
statement: Bananas are rich in potassium
provided: true
justification: Bananas contain a lot of potassium according to the answer, therefore the statement is provided.

statement: Oranges are rich in potassium
provided: true
justification: Oranges contain a lot of potassium according to the answer, therefore the statement is provided.

statement: Avocados are rich in potassium
provided: false
justification: Avocados are not mentioned in the answer.
END_STATEMENT_EVALUATION

START_QUESTION
{question}
END_QUESTION
START_ANSWER
{answer}
END_ANSWER
START_STATEMENT_EVALUATION
statement: {statement}
provided: """ # noqa: E501

    GROUNDING_PROMPT_TEMPLATE = """I need your help with "Natural language inference". Your task is to check if the hypothesis is true, given the premise. The answer should be a single `TRUE` or `FALSE`.

Instructions:
* If it is possible to fully derive the hypothesis from the premise (entailment), then answer TRUE, otherwise FALSE.
* It is ok to use only very common knowledge, all facts need to be included in the premise.

Examples:

premise: Anna wants a retriever.
hypothesis: Anna would like to have a dog.
answer: TRUE
reason: We know that Anna wants a retriever, which means she wants a dog. Thus, the hypothesis is true given the premise.

premise: Anna would like to have a dog.
hypothesis: Anna would like to have a retriever.
answer: FALSE
reason: We know that Anna wants a dog, but that doesn't mean she wants exactly a retriever. Thus, the hypothesis is false given the premise.

premise: Einstein was a good physicist.
hypothesis: Bruce was a good physicist.
answer: FALSE
reason: Premise and hypothesis talk about a different person. Thus, the hypothesis is false.

premise: Einstein was a good physicist.
hypothesis: Einstein is considered to be a good physicist.
answer: TRUE
reason: The hypothesis only rephrases the premise slightly, so it is true.

premise: Peter is a good architect.
hypothesis: All men are good architects.
answer: FALSE
reason: If Peter is a good architect, it doesn't mean all architects are good. Thus, the hypothesis is false.

premise: Lucy likes the dog named Haf.
hypothesis: Lucy likes all dogs.
answer: FALSE
reason: Just because Lucy likes the dog named Haf, I cannot conclude that she likes all dogs. Thus, the hypothesis is false.

premise: Quantum field theory - Wikipedia: History. Quantum field theory emerged from the work of generations of theoretical physicists spanning much of the 20th century. Its development began in the 1920s with the description of interactions between light and electrons, culminating in the first quantum field theory—quantum electrodynamics.
hypothesis: Quantum field theory (QFT) was developed by many theoretical physicists over the course of the 20th century.
answer: TRUE
reason: The premise states that Quantum field theory started in the 1920s and that its development spanned much of the 20th century. Thus, the hypothesis is true.

premise: Quantum field theory - Wikipedia: History. Quantum field theory emerged from the work of generations of theoretical physicists spanning much of the 20th century. Its development began in the 1920s with the description of interactions between light and electrons, culminating in the first quantum field theory—quantum electrodynamics.
hypothesis: Quantum field theory (QFT) was developed by many theoretical physicists over the course of the 20 and 21st century.
answer: FALSE
reason: The premise does not state that Quantum field theory was developed during hte 21st century. Thus, the hypothesis is false.

premise: Quantum Field Theory > The History of QFT (Stanford Encyclopedia of Philosophy): The inception of QFT is usually dated 1927 with Dirac's famous paper on “The quantum theory of the emission and absorption of radiation” (Dirac 1927). Here Dirac coined the name quantum electrodynamics (QED) which is the part of QFT that has been developed first.
hypothesis: The inception of QFT is usually dated to 1927 when Paul Harr published his paper on “The quantum theory of the emission and absorption of radiation”.
answer: FALSE
reason: The assumption mentions Dirac, not Harr, so the hypothesis is false.

premise: Quantum Field Theory > The History of QFT (Stanford Encyclopedia of Philosophy): The inception of QFT is usually dated 1927 with Dirac's famous paper on “The quantum theory of the emission and absorption of radiation” (Dirac 1927). Here Dirac coined the name quantum electrodynamics (QED) which is the part of QFT that has been developed first.
hypothesis: The inception of QFT is usually dated to 1927 when Paul Dirac published his paper on “The quantum theory of the emission and absorption of radiation”.
answer: TRUE
reason: The hypothesis just paraphrases the assumption so it is true.

Now its your turn, think-step-by step, remember the instructions, carefully read the premise and the hypothesis and decide if the hypothesis follows from the premise. I believe in you.

premise: {sources}
hypothesis: {statement}
answer: """ # noqa: E501


class Metrics:
    """Metrics tooling for Generative features in Agent Builder and DFCX."""

    def __init__(self, model: str = "gemini-1.5-flash-001"):
        self.model = model
