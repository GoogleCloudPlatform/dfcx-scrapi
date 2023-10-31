"""Session Entity Types Resource functions."""

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
from typing import Dict, List

from google.oauth2 import service_account
from google.cloud.dialogflowcx_v3beta1 import services
from google.cloud.dialogflowcx_v3beta1 import types
from google.protobuf import field_mask_pb2

from dfcx_scrapi.core import scrapi_base

# logging config
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


class SessionEntityTypes(scrapi_base.ScrapiBase):
    """Core Class for CX Session Entity Type functions.
    https://cloud.google.com/dialogflow/cx/docs/concept/entity-session
    """

    def init(
        self,
        creds_path: str = None,
        creds_dict: Dict = None,
        creds: service_account.Credentials = None,
        scope: bool = False,
        agent_id: str = None,
    ):

        super().__init__(
            creds_path=creds_path,
            creds_dict=creds_dict,
            creds=creds,
            scope=scope,
        )

        self.agent_id = agent_id

    def _merge_session_id_and_env_id(
        self, session_id: str, environment_id: str
    ) -> str:
        """Merges the Session ID and Environment ID into a valid Session ID.

        When using DFCX Environments, the Session ID needs to be modified to
        include the Environment ID as part of its fully qualified path. Use
        this method to merge the 2 IDs into a valid Session ID when a non-DRAFT
        environment is in use.

        session_id, The session to list all session entity types from.
            Format:
            ``projects/<Project ID>/locations/<Location ID>/agents/<Agent ID>/
              sessions/<Session ID>``
          environment_id, The Environment associated with the Session ID to
            list all session entity types from. Format:
            ``projects/<Project ID>/locations/<Location ID>/agents/<Agent ID>/
              environments/<Environment ID>`
        """
        env_parts = self._parse_resource_path("environment", environment_id)
        session_parts = self._parse_resource_path("session", session_id)

        parent_id = (
            f"projects/{session_parts['project']}/locations/"
            f"{session_parts['location']}/agents/{session_parts['agent']}"
            f"/environments/{env_parts['environment']}/sessions/"
            f"{session_parts['session']}"
        )

        return parent_id

    def _merge_session_entity_id_and_env_id(
        self, session_entity_type_id: str, environment_id: str
    ) -> str:
        """Merges the Session Entity Type ID and Environment ID.

        When using DFCX Environments, the Session Entity Type ID needs to be
        modified to include the Environment ID as part of its fully qualified
        path. Use this method to merge the 2 IDs into a valid Session Entity
        Type ID when a non-DRAFT environment is in use.

        Args:
          session_entity_type_id, The Session Entity Type ID to merge.
            Format:
            ``projects/<Project ID>/locations/<Location ID>/agents/<Agent ID>/
              sessions/<Session ID>/entityTypes/<Entity Type ID>``
          environment_id, The Environment associated with the Session Entity
            Type ID to merge. Format:
            ``projects/<Project ID>/locations/<Location ID>/agents/<Agent ID>/
              environments/<Environment ID>`
        """
        entity_parts = self._parse_resource_path(
            "session_entity_type", session_entity_type_id
        )
        environment_parts = self._parse_resource_path(
            "environment", environment_id
        )

        parent_id = (
            f"projects/{environment_parts['project']}/"
            f"locations/{environment_parts['location']}/"
            f"agents/{environment_parts['agent']}/"
            f"environments/{environment_parts['environment']}/"
            f"sessions/{environment_parts['session']}/"
            f"entityTypes/{entity_parts['entity']}"
        )

        return parent_id

    def build_session_entity_type(
        self,
        session_id: str,
        entity_id: str,
        entity_dict: Dict[str, List[str]],
        environment_id: str = None,
        entity_override_mode: str = "Override",
    ) -> types.SessionEntityType:
        """Builds a Session Entity Type object based on simple inputs.

        Args:
          session_id, The session to list all session entity types from.
            Format:
            ``projects/<Project ID>/locations/<Location ID>/agents/<Agent ID>/
              sessions/<Session ID>``
          entity_id, The Entity ID to replace or extend that currently exists
            in the DFCX Agent.
          entity_dict, The Values and associated Synonyms for the Session
          Entities to be created.
            Ex:
              [1] {'scallions': ['green onions']}
              [2] {'fruit': ['apple','orange'],
                'vegetables': ['cabbage','celery']}
          environment_id, The Environment associated with the Session ID to
            list all session entity types from. Format:
            ``projects/<Project ID>/locations/<Location ID>/agents/<Agent ID>/
              environments/<Environment ID>`
            If ``Environment ID`` is not specified, we assume default 'DRAFT'
              environment.
          entity_override_mode, ONEOF: `Override`, `Supplement`
            `Override` will override the current collection of Session Entity
              Types for the corresponding entity type.
            `Supplement` will extend the current collection of Session Entity
              Types for the corresponding entity type.
        """
        if environment_id:
            parent_id = self._merge_session_id_and_env_id(
                session_id, environment_id
            )

        else:
            parent_id = session_id

        # Append Entity ID to Parent ID
        entity_parts = self._parse_resource_path("entity_type", entity_id)
        parent_id += f"/entityTypes/{entity_parts['entity']}"

        st = types.SessionEntityType()
        st.name = parent_id

        entity_override_map = {
            "Override": "ENTITY_OVERRIDE_MODE_OVERRIDE",
            "Supplement": "ENTITY_OVERRIDE_MODE_SUPPLEMENT",
        }

        st.entity_override_mode = entity_override_map[entity_override_mode]

        entity_list = []

        for k, v in entity_dict.items():
            ent = types.EntityType.Entity()
            ent.value = k
            ent.synonyms = v
            entity_list.append(ent)

        st.entities = entity_list

        return st

    @scrapi_base.api_call_counter_decorator
    def list_session_entity_types(
        self, session_id: str, environment_id: str = None
    ) -> List[types.SessionEntityType]:
        """Lists all Session Entities currently active in the Session.

        Args:
          session_id, The session to list all session entity types from.
            Format:
            ``projects/<Project ID>/locations/<Location ID>/agents/<Agent ID>/
              sessions/<Session ID>``
          environment_id, The Environment associated with the Session ID to
            list all session entity types from. Format:
            ``projects/<Project ID>/locations/<Location ID>/agents/<Agent ID>/
              environments/<Environment ID>`
            If ``Environment ID`` is not specified, we assume default 'DRAFT'
              environment.
        """
        if environment_id:
            parent_id = self._merge_session_id_and_env_id(
                session_id, environment_id
            )

        else:
            parent_id = session_id

        request = types.session_entity_type.ListSessionEntityTypesRequest()
        request.parent = parent_id

        client_options = self._set_region(session_id)
        client = services.session_entity_types.SessionEntityTypesClient(
            credentials=self.creds, client_options=client_options
        )

        response = client.list_session_entity_types(request)

        session_entities = []
        for page in response.pages:
            print(page)
            # for entity in page.entity_types:
            #     session_entities.append(entity)

        return session_entities

    @scrapi_base.api_call_counter_decorator
    def get_session_entity_type(
        self, session_entity_type_id: str, environment_id: str = None
    ) -> types.SessionEntityType:
        """Retrieves the specified Session Entity Type.

        Args:
          session_entity_type_id, The Session Entity Type ID to retrieve.
            Format:
            ``projects/<Project ID>/locations/<Location ID>/agents/<Agent ID>/
            sessions/<Session ID>/entityTypes/<Entity Type ID>``
          environment_id, The Environment associated with the Session ID to
            list all session entity types from. Format:
            ``projects/<Project ID>/locations/<Location ID>/agents/<Agent ID>/
              environments/<Environment ID>`
            If ``Environment ID`` is not specified, we assume default 'DRAFT'
              environment.
        """
        if environment_id:
            parent_id = self._merge_session_entity_id_and_env_id(
                session_entity_type_id, environment_id
            )
        else:
            parent_id = session_entity_type_id

        request = types.GetSessionEntityTypeRequest()
        request.name = parent_id

        client_options = self._set_region(session_entity_type_id)
        client = services.session_entity_types.SessionEntityTypesClient(
            credentials=self.creds, client_options=client_options
        )

        response = client.get_session_entity_type(request)

        return response

    @scrapi_base.api_call_counter_decorator
    def create_session_entity_type(
        self, session_id: str, session_entity_type: types.SessionEntityType
    ) -> types.SessionEntityType:
        """Creates a Session Entity Type object from provided inputs.
        Args:
          session_id, The session to list all session entity types from.
            Format:
            ``projects/<Project ID>/locations/<Location ID>/agents/<Agent ID>/
              sessions/<Session ID>``
          session_entity_type, The Session Entity Type object to create for the
            provided session. Use `build_session_entity_type` to create a new
            object.

        """
        request = types.CreateSessionEntityTypeRequest()
        request.parent = session_id
        request.session_entity_type = session_entity_type

        client_options = self._set_region(session_id)
        client = services.session_entity_types.SessionEntityTypesClient(
            credentials=self.creds, client_options=client_options
        )

        response = client.create_session_entity_type(request)

        return response

    @scrapi_base.api_call_counter_decorator
    def update_session_entity_type(
        self,
        session_entity_type_id: str,
        environment_id: str = None,
        obj: types.SessionEntityType = None,
        **kwargs,
    ) -> types.SessionEntityType:
        """Updates the specified Session Entity Type object.

        This method will update the specific Sesssion Entity Type object based
        on the provided user inputs. If the user provides the entier Session
        Entity Type object, the entire existing object will be updated.
        Alternatively, kwargs can be provided to only update specific portions
        of the Session Entity Type object.

        Ref: https://github.com/googleapis/python-dialogflow-cx/blob/main/
          google/cloud/dialogflowcx_v3beta1/types/session_entity_type.py#L36

        Args:
          session_entity_type_id, the ID of the Session Entity Type to update
          Format:
            ``projects/<Project ID>/locations/<Location ID>/agents/<Agent ID>/
              sessions/<Session ID>/entityTypes/<Entity Type ID>`
          environment_id, The Environment associated with the Session Entity
            Type ID to update. Format:
            ``projects/<Project ID>/locations/<Location ID>/agents/<Agent ID>/
              environments/<Environment ID>`
            If ``Environment ID`` is not specified, we assume default 'DRAFT'
              environment.
          obj, the Session Entity Type object to send as update
        """
        if environment_id:
            parent_id = self._merge_session_entity_id_and_env_id(
                session_entity_type_id, environment_id
            )
        else:
            parent_id = session_entity_type_id

        if obj:
            session_entity_type = obj
            session_entity_type.name = parent_id
        else:
            session_entity_type = self.get_session_entity_type(parent_id)

        # set agent attributes to args
        for key, value in kwargs.items():
            setattr(session_entity_type, key, value)
        paths = kwargs.keys()
        mask = field_mask_pb2.FieldMask(paths=paths)

        client_options = self._set_region(parent_id)
        client = services.session_entity_types.SessionEntityTypesClient(
            credentials=self.creds, client_options=client_options
        )
        request = types.UpdateSessionEntityTypeRequest()
        request.session_entity_type = parent_id
        request.update_mask = mask

        response = client.update_session_entity_type(request)

        return response

    @scrapi_base.api_call_counter_decorator
    def delete_session_entity_type(
        self, session_entity_type_id: str, environment_id: str = None
    ) -> str:
        """Deletes the specified Session Entity Type.

        Args:
          session_entity_type_id, the ID of the Session Entity Type to update
            Format:
              ``projects/<Project ID>/locations/<Location ID>/agents/<Agent ID>/
                sessions/<Session ID>/entityTypes/<Entity Type ID>`
            environment_id, The Environment associated with the Session Entity
              Type ID to update. Format:
              ``projects/<Project ID>/locations/<Location ID>/agents/<Agent ID>/
                environments/<Environment ID>`
              If ``Environment ID`` is not specified, we assume default 'DRAFT'
                environment.
        """
        if environment_id:
            parent_id = self._merge_session_entity_id_and_env_id(
                session_entity_type_id, environment_id
            )

        else:
            parent_id = session_entity_type_id

        client_options = self._set_region(session_entity_type_id)
        client = services.session_entity_types.SessionEntityTypesClient(
            credentials=self.creds, client_options=client_options
        )

        request = types.DeleteSessionEntityTypeRequest()
        request.name = parent_id

        client.delete_session_entity_type(request)

        return f"Session Entity Type {session_entity_type_id} successfully "\
            "deleted."
