# Data Store Agent Self-serve Evaluation

This guide details how to evaluate
[Data Store agents](https://cloud.google.com/dialogflow/vertex/docs/concept/data-store-agent)
using the external Colab notebook and leverage quality tools to improve agent
performance based on the evaluation results.

## Overall Quality Methodology

Create an evaluation dataset in a google spreadsheet of 30-50 representative
queries with ideal answers and links using this schema:

conversation_id | turn_index | query                                   | expected_answer                                     | expected_uri [Optional]                                                                                                                  | golden_snippet [Optional]
--------------- | ---------- | --------------------------------------- | --------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------- | -------------------------
0               | 1          | Can I get an Uber without the Uber app? | You can request an Uber ride online via m.uber.com. | [https://www.uber.com/en-AE/blog/request-uber-online-without-app-3/](https://www.uber.com/en-AE/blog/request-uber-online-without-app-3/) |

*   Explanation of each column:
    *   **conversation_id**: Identifier of each conversation.
    *   **turn_index**: Identifier of each turn under the whole conversation.
    *   **query**: User utterance of each turn.
    *   **expected_answer**: Expected agent response.
    *   **expected_uri**: Expected URI used by the agent for reference.
    *   **golden_snippets**: Expected search snippets for each turn of query.
        Note that the current evaluation tooling only covers single turn
        evaluation. Until multi-turn evaluation is available, we encourage you
        to run manual evaluation for those.

1.  Create your
    [Data store agent](https://cloud.google.com/dialogflow/vertex/docs/concept/data-store-agent#create-agent).

2.  Run the [evaluation jupyter notebook](#how-to-run-evaluation) to get the
    quality baseline.

3.  Identify top losses and leverage quality tools to improve the baseline. Run
    evaluation every time you’re making a change.

## How to run evaluation?

[Self-serve evaluation notebook](https://github.com/GoogleCloudPlatform/dfcx-scrapi/blob/main/examples/vertex_ai_conversation/evaluation_tool__autoeval__colab.ipynb)
allows datastore agent users to run auto-evaluation on their Dialogflow agents
and gain valuable insights from the evaluation results. Users can simply run the
notebook with their evaluation dataset on the desired agent.

This will run all the queries in the evaluation dataset and save the responses
as well as a lot of debug information and metrics:

-   RougeL recall: simple text similarity between the golden answer and the
    actual answer.

-   URL match: if the URL of the returned snippet matches the golden URL.

-   Answer correctness: this checks if the actual answer matches the golden
    answer, using an LLM as a judge.

-   Faithfulness: this uses an LLM judge to check if the actual answer is
    grounded in the search results (i.e. if the answer is hallucinated or not).

-   Context recall: this measures the search quality. It uses an LLM judge to
    check if the golden answer can be formulated based on the retrieved search
    results.

**You can compare two model runs on the same evalset by comparing the actual
responses (human evaluation) as well as the autoeval metrics of the runs.**

## How to improve the quality baseline?

There are available
[settings](https://cloud.google.com/dialogflow/vertex/docs/concept/data-store-agent)
that will help you to customize your data store agents and tweak some of the
components in order to improve quality.

Based on the evaluation result, you can follow the guidelines to diagnose the
loss and improve your agent’s quality:

#### 1. If **URL match** and **Context Recall** scores are low, improve search performance using the Search Quality Tools:

*   **Boost & Bury + Filtering**: You can specify the Boost & Bury and Filter
    controls in the DetectIntent request’s Query parameters, see
    [how to use the feature](https://cloud.google.com/dialogflow/vertex/docs/concept/data-store-agent#search-configuration)
    and
    [the API reference.](https://cloud.google.com/dialogflow/cx/docs/reference/rest/v3/QueryParameters#SearchConfig)
*   **Layout parsing and document chunking**: You can
    [upload your own chunks](https://cloud.google.com/generative-ai-app-builder/docs/parse-chunk-documents#parse-chunk-rag)
    via API and choose layout parser by following the
    [documentation](https://cloud.google.com/generative-ai-app-builder/docs/parse-chunk-documents).
*   **Recrawl API**: You can follow the
    [Recrawl API documentation](https://cloud.google.com/generative-ai-app-builder/docs/recrawl-websites).

#### 2. If **Answer Correctness** scores are low, enhance generator performance with the Generator Quality Tools:

*   **Model selector**: You can follow the
    [model selection documentation](https://cloud.google.com/dialogflow/vertex/docs/concept/data-store-agent#model-selection).
*   **Custom summarization prompt**: You can follow the customization of
    [summarization prompt documentation](https://cloud.google.com/dialogflow/vertex/docs/concept/data-store-agent#customize-summarization-prompt).

#### 3. If **Faithfulness** scores are low, adjust the Grounding setting in the data store agent to address LLM hallucination.

*   **Grounding Setting**: You can follow the
    [grounding setting documentation here](https://cloud.google.com/dialogflow/vertex/docs/concept/data-store-agent#grounding).
    In the conversation history (Available on DialogFlow in the Test & Feedback
    section) you can identify conversation turns that had grounding failures.

#### 4. **Unmatched** Queries:

*   For styled generative fallback responses, use the generative fallback
    prompt:

    *   **Generative Fallback**: You can follow the
        [Generative Fallback documentation](https://cloud.google.com/dialogflow/cx/docs/concept/generative/generative-fallback).
        By default, the most appropriate link is returned when the data store
        agent fails to return an answer. You can disable this.

*   For expecting fixed answers with given queries, use the FAQ datastore:

    *   **FAQ to Point Fix Losses**: You can follow the
        [FAQ documentation](https://cloud.google.com/dialogflow/vertex/docs/concept/data-store-agent#improve).
    *   **Upload FAQ as Unstructured Data**: If you experience very low recall
        results with FAQ uploaded in a structured data store, uploading FAQs as
        [unstructured data](https://screenshot.googleplex.com/PdKwwBxjSGQeyyn.png)
        is recommended to improve recall quality: Format of FAQ csv files should
        contain columns: "question","answer", "title" (optional),"url"
        (optional).

#### 5. To preprocess or postprocess the datastore agent response, consider using the Generator to instruct an LLM in order to perform some processing tasks.

*   **Generator**: You can follow the
    [generator documentation](https://cloud.google.com/dialogflow/cx/docs/concept/generative/generators).

#### 6. To prevent specific wording in responses, add them to the Banned Phrase list.

*   **Banned Phrases**: You can follow the
    [banned phrases documentation](https://cloud.google.com/dialogflow/cx/docs/concept/agent#settings-generative-banned).
