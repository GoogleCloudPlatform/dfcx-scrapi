# Main
from dfcx_scrapi import builders
from dfcx_scrapi import tools

from dfcx_scrapi.core.agents import Agents
from dfcx_scrapi.core.changelogs import Changelogs
from dfcx_scrapi.core.conversation import DialogflowConversation
from dfcx_scrapi.core.entity_types import EntityTypes
from dfcx_scrapi.core.environments import Environments
from dfcx_scrapi.core.experiments import ScrapiExperiments
from dfcx_scrapi.core.flows import Flows
from dfcx_scrapi.core.intents import Intents
from dfcx_scrapi.core.operations import Operations
from dfcx_scrapi.core.pages import Pages
from dfcx_scrapi.core.project import Project
from dfcx_scrapi.core.security_settings import SecuritySettings
from dfcx_scrapi.core.session_entity_types import SessionEntityTypes
from dfcx_scrapi.core.sessions import Sessions
from dfcx_scrapi.core.test_cases import TestCases
from dfcx_scrapi.core.transition_route_groups import TransitionRouteGroups
from dfcx_scrapi.core.versions import Versions
from dfcx_scrapi.core.webhooks import Webhooks


_DF_SCHEMAS = {
    "Intent": {
        "basic": ["display_name", "training_phrase"],
        "advanced": [
            "name", "display_name", "description", "priority",
            "is_fallback", "labels", "id", "repeat_count",
            "training_phrase", "training_phrase_idx",
            "text", "text_idx",
            "parameter_id", "entity_type", "is_list", "redact",
        ],
    },
    "EntityType": {
        "basic": ["display_name", "entity_value", "synonyms"],
        "advanced": [
            "entity_type_id", "display_name", "kind",
            "auto_expansion_mode", "fuzzy_extraction", "redact",
            "entity_value", "synonyms", "excluded_phrases",
        ],
    },
    "TransitionRouteGroup": {
        "basic": [
            "name", "display_name", "flow_id",
            "intent", "condition", "target_type", "target_id",
            "has_fulfillment", "has_fulfillment_webhook",
            "target_name", "flow_name", # "intent_name",
        ],
        "advanced": [
            "name", "display_name", "flow_id",
            "intent", "condition", "target_type", "target_id",
            "messages", "preset_parameters", "conditional_cases",
            "webhook", "webhook_tag", "return_partial_responses",
            "target_name", "flow_name", # "intent_name",
        ],
    },
    "Webhook": {
        "basic": ["display_name", "uri"],
        "advanced": [
            "name", "display_name", "timeout", "disabled",
            "service_type", "uri",
            "username", "password", "request_headers",
        ]
    },
    "Fulfillment": {
        "basic": ["has_fulfillment", "has_fulfillment_webhook"],
        "advanced": [
            "messages", "preset_parameters", "conditional_cases",
            "webhook", "webhook_tag", "return_partial_responses",
        ]
    },
    "TransitionRoute": {
        "basic": [
            "intent", "condition", "target_type", "target_id",
            "has_fulfillment", "has_fulfillment_webhook",
        ],
        "advanced": [
            "intent", "condition", "target_type", "target_id",
            "messages", "preset_parameters", "conditional_cases",
            "webhook", "webhook_tag", "return_partial_responses",
        ],
    }
}
