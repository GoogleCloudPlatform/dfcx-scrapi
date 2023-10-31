"""Webhook processing methods and functions."""

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

import json
import os

from dfcx_scrapi.agent_extract import common
from dfcx_scrapi.agent_extract import types

class Webhooks:
    """Webhook linter methods and functions."""

    def __init__(self):
        self.common = common.Common()

    @staticmethod
    def build_webhook_path_list(agent_local_path: str):
        """Builds a list of webhook file locations."""
        root_dir = agent_local_path + "/webhooks"

        webhook_paths = []

        for webhook_file in os.listdir(root_dir):
            webhook_file_path = f"{root_dir}/{webhook_file}"
            webhook_paths.append(webhook_file_path)

        return webhook_paths

    @staticmethod
    def get_service_type(webhook: types.Webhook) -> str:
        """Get the type of Webhook Service that is cofigured."""
        if "genericWebService" in webhook.data:
            webhook.service_type = "Generic Web Service"

        else:
            webhook.service_type = "Other"

        return webhook.service_type

    def process_webhook(self, webhook: types.Webhook, stats: types.AgentData
            ) -> types.AgentData:
        """Process a single Webhook file."""

        with open(webhook.dir_path, "r", encoding="UTF-8") as webhook_file:
            webhook.data = json.load(webhook_file)
            webhook.resource_id = webhook.data.get("name", None)
            webhook.display_name = webhook.data.get("displayName", None)
            webhook.service_type = self.get_service_type(webhook)

            timeout_dict = webhook.data.get("timeout", None)
            if timeout_dict:
                webhook.timeout = timeout_dict.get("seconds", None)

            webhook_file.close()

        full_webhook_id = f"{stats.agent_id}/webhooks/{webhook.resource_id}"
        webhook.data["name"] = full_webhook_id
        stats.webhooks.append(webhook.data)
        stats.total_webhooks += 1

        return stats

    def process_webhooks_directory(self, agent_local_path: str,
                                   stats: types.AgentData) -> types.AgentData:
        """Processing the top level Webhooks Dir in the JSON Package structure.

        The following files exist under the `webhooks` dir:
        - <webhook-name>.json
        """
        # Create a list of all Webhook paths to iter through
        webhook_paths = self.build_webhook_path_list(agent_local_path)

        for webhook_path in webhook_paths:
            webhook = types.Webhook()
            webhook.dir_path = webhook_path

            stats = self.process_webhook(webhook, stats)

            full_webhook_id = f"{stats.agent_id}/webhooks/{webhook.resource_id}"
            stats.webhooks_map[webhook.display_name] = full_webhook_id

        return stats
