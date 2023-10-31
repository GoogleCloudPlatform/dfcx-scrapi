"""Collection of Type Classes used for offline processing."""

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

from typing import Dict, List, Any, Tuple
from dataclasses import dataclass, field

from dfcx_scrapi.agent_extract import graph as graph_class

@dataclass
class AgentMetadata:
    """Used to track the current Agent Metadata attrinbutes."""

    default_language_code: str = None
    dtmf_settings: bool = False
    logging_enabled: bool = False
    speech_adaptation: bool = False


@dataclass
class Flow:
    """Used to track current Flow Attributes."""
    agent_id: str = None
    all_pages: set = field(default_factory=set)
    active_pages: set = field(default_factory=set)
    data: Dict[str, Any] = field(default_factory=dict)
    dangling_pages: set = field(default_factory=set)
    dir_path: str = None  # Full Directory Path for this Flow
    display_name: str = None  # Flow Display Name (removed special chars)
    file_name: str = None  # Original Name of Flow (includes special chars)
    graph: graph_class.Graph = None
    resource_id: str = None
    resource_type: str = "flow"
    start_page_file: str = None  # File Path Location of START_PAGE
    unreachable_pages: set = field(default_factory=set)
    unused_pages: set = field(default_factory=set)

@dataclass
class Page:
    """Used to track current Page Attributes."""

    agent_id: str = None
    data: Dict[str, Any] = None
    display_name: str = None
    entry: Dict[str, Any] = None
    events: List[object] = None
    flow: Flow = None
    form: Dict[str, Any] = None
    has_webhook: bool = False
    has_webhook_event_handler: bool = False
    page_file: str = None
    resource_id: str = None
    resource_type: str = "page"
    routes: List[object] = None
    route_groups: List[str] = None

@dataclass
class FormParameter:
    """Tracks Form Paramter attributes within a Page."""

    advanced_settings: str = None
    agent_id: str = None
    data: Dict[str, Any] = None
    display_name: str = None
    dtmf_settings: str = None
    entity_type: str = None
    fill_behavior: Dict[str, Any] = None
    init_fulfillment: Dict[str, Any] = None
    page: Page = None
    reprompt_handlers: Dict[str, Any] = None
    required: bool = True


@dataclass
class RouteGroup:
    """Used to track current RouteGroup Attributes."""

    agent_id: str = None
    data: Dict[str, Any] = None
    display_name: str = None
    flow: Flow = None
    resource_id: str = None
    resource_type: str = "route_group"
    rg_file: str = None
    routes: List[object] = None

@dataclass
class Fulfillment:
    """Used to track current Fulfillment Attributes."""

    agent_id: str = None
    data: Dict[str, Any] = None
    display_name: str = None  # Inherit from Page easy logging
    fulfillment_type: str = None  # transition_route | event
    page: Page = None
    parameter: str = None # Used for Reprompt Event Handlers
    target_flow: str = None
    target_page: str = None
    text: str = None
    trigger: str = None
    resource_type: str = "fulfillment"

@dataclass
class Intent:
    """Used to track current Intent Attributes."""

    agent_id: str = None
    data: Dict[str, Any] = None
    description: str = None
    display_name: str = None
    dir_path: str = None
    labels: Dict[str, str] = None
    metadata_file: str = None
    parameters: List[Dict[str, str]] = field(default_factory=list)
    resource_id: str = None
    resource_type: str = "intent"
    training_phrases: Dict[str, Any] = field(default_factory=dict)

@dataclass
class EntityType:
    """Used to track current Flow Attributes."""

    agent_id: str = None
    auto_expansion: str = None
    data: Dict[str, Any] = None
    dir_path: str = None  # Full Directory Path for this Entity Type
    display_name: str = None  # Entity Type Display Name
    entities: Dict[str, Any] = field(default_factory=dict)  # Map
    excluded_phrases: Dict[str, Any] = field(default_factory=dict)  # Map
    fuzzy_extraction: bool = False
    kind: str = None  # The kind of Entity Type represented
    resource_id: str = None
    resource_type: str = "entity_type"

@dataclass
class TestCase:
    """Used to track current Test Case Attributes."""

    associated_intent_data: Dict[str, Any] = None
    agent_id: str = None
    agent_path: str = None
    conversation_turns: List[Any] = None
    data: Dict[str, Any] = None
    dir_path: str = None
    display_name: str = None
    has_invalid_intent: bool = False
    intent_data: List[str] = None
    qualified: bool = False
    resource_id: str = None
    resource_type: str = "test_case"
    tags: List[str] = None
    test_config: Dict[str, Any] = None

@dataclass
class Webhook:
    """Used to track current Webhook attributes."""

    agent_id: str = None
    agent_path: str = None
    data: Dict[str, Any] = None
    dir_path: str = None
    display_name: str = None
    resource_id: str = None
    resource_type: str = "webhook"
    service_type: str = None
    timeout: int = 0

@dataclass
class AgentData:
    """Used to track agent data for each section processed."""
    active_intents: Dict[str, List[Tuple[str, str]]] = field(
        default_factory=dict)
    active_pages: Dict[str, set] = field(default_factory=dict)
    agent_id: str = None
    entity_types: List[Dict[str, Any]] = field(default_factory=list)
    entity_types_map: Dict[str, Any] = field(default_factory=dict)
    flow_page_map: Dict[str, Any] = field(default_factory=dict)
    flows: List[Dict[str, Any]] = field(default_factory=list)
    flows_map: Dict[str, Any] = field(default_factory=dict)
    graph: graph_class.Graph = None
    intents: List[Dict[str, Any]] = field(default_factory=list)
    intents_map: Dict[str, Any] = field(default_factory=dict)
    lang_code: str = "en"
    pages: Dict[str, List[Dict[str, Any]]] = field(default_factory=dict)
    route_groups: Dict[str, List[Dict[str, Any]]] = field(default_factory=dict)
    route_groups_map: Dict[str, Any] = field(default_factory=dict)
    test_cases: List[Dict[str, Any]] = field(default_factory=list)
    unreachable_pages: Dict[str, set] = field(default_factory=dict)
    unused_pages: Dict[str, set] = field(default_factory=dict)
    webhooks: List[Dict[str, Any]] = field(default_factory=list)
    webhooks_map: Dict[str, Any] = field(default_factory=dict)

    total_flows: int = 0
    total_pages: int = 0
    total_intents: int = 0
    total_training_phrases: int = 0
    total_entity_types: int = 0
    total_route_groups: int = 0
    total_test_cases: int = 0
    total_webhooks: int = 0
