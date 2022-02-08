"""CCAI Security Settings Methods"""

# Copyright 2022 Google LLC
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

from __future__ import annotations

import json
import logging
from google.cloud.dialogflowcx_v3beta1 import services
from google.cloud.dialogflowcx_v3beta1 import types
from google.protobuf import field_mask_pb2
from dfcx_scrapi.core.scrapi_base import ScrapiBase


# logging config
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

class SecuritySettings(ScrapiBase):
  """Core Class for CCAI Security Settings."""

  def __init__(
        self,
        creds_path: str = None,
        creds_dict: dict = None,
        creds=None,
        scope=False,
        agent_id: str = None
    ):
        super().__init__(
            creds_path=creds_path,
            creds_dict=creds_dict,
            creds=creds,
            scope=scope,
        )

        if agent_id:
            self.agent_id = agent_id
  
  def list_security_settings(self, location_id: str):
      """List Security Settings for a given Project and Region.

      Args:
          location_id: CX Agent ID string in the following format
          projects/<PROJECT ID>/locations/<LOCATION ID>/

      Returns:
          results: Dict of results
      """

      request = types.security_settings.ListSecuritySettingsRequest()

      request.parent = location_id
      client_options = self._set_region(location_id)
      client = services.security_settings_service.SecuritySettingsServiceClient(
          credentials=self.creds, client_options=client_options
      )

      response = client.list_security_settings(request)

      security_settings = []
      for page in response.pages:
        for ss in page.security_settings:
          security_settings.append(ss)

      return security_settings


  def get_security_settings(self, security_setting_id: str):
      """Get specified CCAI Security Setting.

      Args:
          security_setting_id: Security Setting ID string in the following
            format: projects/<PROJECT ID>/locations/<LOCATION ID>/
            securitySettings/<SECURITY SETTINGS ID>

      Returns:
          response: a single Security Settings object of types.SecuritySettings
      """

      request = types.security_settings.GetSecuritySettingsRequest()

      request.name = security_setting_id
      client_options = self._set_region(security_setting_id)
      client = services.security_settings_service.SecuritySettingsServiceClient(
          credentials=self.creds, client_options=client_options
      )

      response = client.get_security_settings(request)

      return response

  def create_security_settings(
      self,
      project_id: str,
      obj: types.SecuritySettings = None,
      security_settings_dict: dict[str,str] = None):
      """Create CCAI Security Settings profile in the specified project.

      One of `obj` or `security_settings_dict` should be provided to create a
      new security settings profile.

      Args:
        project_id: the GCP project ID string where the Security Settings should
          be created
        obj: An object of types.SecuritySettings representing the Security
          Settings object to be created
        security_settings_dict: An optional dictionary of key/value pairs that
          correspond to the fields and values necessary for creating a new
          Security Settings profile

      Returns:
          response: a single Security Settings object of types.SecuritySettings
      """

      if obj and security_settings_dict:
        raise ValueError("Cannot provide both obj and security_settings_dict")
      elif obj:
        security_settings = obj
        security_settings.name = ""
      elif security_settings_dict:
        security_settings = types.security_settings.SecuritySettings.from_json(
            json.dumps(security_settings_dict)
        )
      else:
        raise ValueError("Must provide either obj or security_settings_dict")

      request = types.security_settings.CreateSecuritySettingsRequest()

      request.parent = project_id
      request.security_settings = security_settings

      client_options = self._set_region(project_id)
      client = services.security_settings_service.SecuritySettingsServiceClient(
          credentials=self.creds, client_options=client_options
      )

      response = client.create_security_settings(request)

      return response

  def update_security_settings(self, security_setting_id: str, **kwargs):
      """Update specified CCAI Security Setting.

      Args:
          security_setting_id: Security Setting ID string in the following
            format: projects/<PROJECT ID>/locations/<LOCATION ID>/
            securitySettings/<SECURITY SETTINGS ID>

      Returns:
          response: a single Security Settings object of types.SecuritySettings
      """

      security_settings = self.get_security_settings(security_setting_id)

      # set intent attributes from kwargs
      for key, value in kwargs.items():
        setattr(security_settings, key, value)
      paths = kwargs.keys()
      mask = field_mask_pb2.FieldMask(paths=paths)

      request = types.security_settings.UpdateSecuritySettingsRequest()

      request.security_settings = security_settings
      request.update_mask = mask

      client_options = self._set_region(security_setting_id)
      client = services.security_settings_service.SecuritySettingsServiceClient(
          credentials=self.creds, client_options=client_options
      )

      response = client.update_security_settings(request)

      return response
