"""Entity Types Resource functions."""

# Copyright 2021 Google LLC. This software is provided as-is, without warranty
# or representation for any use or purpose. Your use of it is subject to your
# agreement with Google.

import logging
from typing import Dict
import google.cloud.dialogflowcx_v3beta1.services as services
import google.cloud.dialogflowcx_v3beta1.types as types

from dfcx_sapi.core.sapi_base import SapiBase

# logging config
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
class EntityTypes(SapiBase):
    """Core Class for CX Entity Type Resource functions."""
    def __init__(
        self,
        creds_path: str = None,
        creds_dict: Dict = None,
        creds=None,
        scope=False,
        entity_id: str = None,
        agent_id: str = None
    ):
        super().__init__(
            creds_path=creds_path,
            creds_dict=creds_dict,
            creds=creds,
            scope=scope,
        )

        if entity_id:
            self.entity_id = entity_id
            self.client_options = self._set_region(entity_id)

        if agent_id:
            self.agent_id = agent_id

    def get_entities_map(self, agent_id: str = None, reverse=False):
        """Exports Agent Entityt Names and UUIDs into a user friendly dict.

        Args:
          - agent_id, the formatted CX Agent ID to use
          - reverse, (Optional) Boolean flag to swap key:value -> value:key

        Returns:
          - intents_map, Dictionary containing Entity UUIDs as keys and
              intent.display_name as values
        """
        if not agent_id:
            agent_id = self.agent_id

        if reverse:
            entities_dict = {
                entity.display_name: entity.name
                for entity in self.list_entity_types(agent_id)
            }

        else:
            entities_dict = {
                entity.name: entity.display_name
                for entity in self.list_entity_types(agent_id)
            }

        return entities_dict

    def list_entity_types(self, agent_id: str = None):
        """Returns a list of Entity Type objects.

        Args:
          - agent_id, the formatted CX Agent ID to use

        Returns:
          - entities, List of Entity Type objects
        """
        if not agent_id:
            agent_id = self.agent_id

        request = types.entity_type.ListEntityTypesRequest()
        request.parent = agent_id

        client_options = self._set_region(agent_id)
        client = services.entity_types.EntityTypesClient(
            credentials=self.creds, client_options=client_options
        )

        response = client.list_entity_types(request)

        entities = []
        for page in response.pages:
            for entity in page.entity_types:
                entities.append(entity)

        return entities

    def get_entity_type(self, entity_id: str = None):
        """Returns a single Entity Type object.

        Args:
          - entity_id, the formatted CX Entity ID to get

        Returns:
          - response, the single Entity Type object
        """
        if not entity_id:
            entity_id = self.entity_id

        client_options = self._set_region(entity_id)
        client = services.entity_types.EntityTypesClient(
            credentials=self.creds, client_options=client_options
        )
        response = client.get_entity_type(name=entity_id)

        return response

    def create_entity_type(self, agent_id: str = None, obj=None, **kwargs) -> types.EntityType:
        """Creates a single Entity Type object resource.

        Args:
          - agent_id, the formatted CX Agent ID to create the object on

        Returns:
          - response, copy of the Entity Type object created
        """
        if not agent_id:
            agent_id = self.agent_id

        # If entity_type_obj is given set entity_type to it
        if obj:
            entity_type = obj
            entity_type.name = ""
        else:
            entity_type = types.entity_type.EntityType()

        # set optional arguments to entity type attributes
        for key, value in kwargs.items():
            setattr(entity_type, key, value)

        # Apply any optional functions argument to entity_type object
        #         entity_type = set_entity_type_attr(entity_type, kwargs)

        client_options = self._set_region(agent_id)
        client = services.entity_types.EntityTypesClient(
            credentials=self.creds, client_options=client_options
        )
        response = client.create_entity_type(
            parent=agent_id, entity_type=entity_type
        )
        return response

    def delete_entity_type(self, entity_id: str = None, obj=None) -> None:
        """Deletes a single Entity Type resouce object.

        Args:
          entity_id, the formatted CX Entity ID to delete

        Returns:
          - None
        """
        if not entity_id:
            entity_id = self.entity_id

        if obj:
            _entity_id = obj.name
        else:
            client_options = self._set_region(entity_id)
            client = services.entity_types.EntityTypesClient(
                credentials=self.creds, client_options=client_options
            )
            client.delete_entity_type(name=entity_id)
