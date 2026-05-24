import pandas as pd

from dfcx_scrapi.tools.evaluations import Evaluations


class FakeAgentResponse:
    def _extract_text(self, response):
        return "detected agent response"


class FakeSessionsClient:
    def __init__(self, playbook_responses=None, flow_responses=None):
        self.playbook_responses = playbook_responses or []
        self.flow_responses = flow_responses or []

    def build_session_id(self, agent_id):
        return "session-1"

    def detect_intent(self, **kwargs):
        return object()

    def collect_playbook_responses(self, response):
        return list(self.playbook_responses)

    def collect_flow_responses(self, response):
        return list(self.flow_responses)


def build_evaluator(playbook_responses=None, flow_responses=None):
    evaluator = Evaluations.__new__(Evaluations)
    evaluator.agent_id = "projects/p/locations/l/agents/a"
    evaluator.session_id = None
    evaluator.sessions_client = FakeSessionsClient(
        playbook_responses=playbook_responses,
        flow_responses=flow_responses,
    )
    evaluator.ar = FakeAgentResponse()
    evaluator.user_input_metrics = []
    evaluator.unexpected_rows = []
    return evaluator


def test_scrape_results_adds_missing_utterance_pair_column():
    evaluator = build_evaluator()
    df = pd.DataFrame(
        [
            {
                "eval_id": "eval-1",
                "action_id": 1,
                "action_type": "User Utterance",
                "action_input": "hello",
            },
            {
                "eval_id": "eval-1",
                "action_id": 2,
                "action_type": "Agent Response",
                "action_input": "expected response",
            },
            {
                "eval_id": "eval-1",
                "action_id": 3,
                "action_type": "Agent Response",
                "action_input": "second response",
            },
        ]
    )

    result = evaluator.scrape_results(df)

    assert result.loc[0, "utterance_pair"] == "1"
    assert result.loc[1, "agent_response"] == "detected agent response"


def test_scrape_results_adds_missing_invocation_pair_columns():
    evaluator = build_evaluator(
        playbook_responses=[{"playbook_name": "playbook-1"}],
        flow_responses=[{"flow_name": "flow-1"}],
    )
    df = pd.DataFrame(
        [
            {
                "eval_id": "eval-1",
                "action_id": 1,
                "action_type": "User Utterance",
                "action_input": "hello",
            },
            {
                "eval_id": "eval-1",
                "action_id": 2,
                "action_type": "Agent Response",
                "action_input": "expected response",
            },
        ]
    )

    result = evaluator.scrape_results(df)

    assert result.loc[0, "tool_pair"] == ""
    assert result.loc[0, "playbook_pair"] == ""
    assert result.loc[0, "flow_pair"] == ""
    assert result.loc[0, "res_playbook_name"] == "playbook-1"
    assert result.loc[0, "res_flow_name"] == "flow-1"
