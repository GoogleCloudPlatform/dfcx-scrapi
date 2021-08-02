"""
methods for creating CX object types
such as transition routes or fulfillments
"""

# Copyright 2021 Google LLC
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
import google.cloud.dialogflowcx_v3beta1.types as types

# logging config
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

SCOPES = [
    "https://www.googleapis.com/auth/cloud-platform",
    "https://www.googleapis.com/auth/dialogflow",
]


class MakerUtil:
    """Util class to create CX objects like transition routes"""
    @classmethod
    def make_generic(cls, obj, obj_type, default, conditionals=None):
        if conditionals is None:
            conditionals = dict()

        if isinstance(obj, obj_type):
            return obj

        elif isinstance(obj, dict):
            obj_ins = obj_type()
            for key, value in obj.items():
                if key in conditionals.keys():
                    func = conditionals[key]
                    out = func(value)
                    setattr(obj_ins, key, out)
                else:
                    print(value)
                    setattr(obj_ins, key, value)
            return obj_ins

        elif isinstance(obj, str):
            dic = {
                "unspecified": 0,
                "map": 1,
                "list": 2,
                "regexp": 3,
                "default": 1,
            }
            t = dic.get(obj.lower())
            if t:
                return obj_type(t)
            else:
                return default
        else:
            return default

    @classmethod
    def make_seq(cls, obj, obj_type, default, conditionals=None):
        if conditionals is None:
            conditionals = dict()
        assert isinstance(obj, list)
        l = []
        for x in obj:
            l.append(cls.make_generic(
                x, obj_type, default, conditionals))
        return l

    @classmethod
    def make_transition_route(cls, obj=None, **kwargs):
        """Creates a single Transition Route object for Dialogflow CX.

        Transition routes are used to navigate a user from page to page, or
        page to flow in Dialogflow CX. Routes can be part of a Page object or
        they can also be associated with Route Groups. In either case, the
        structure of the Route is the same. This method allows the user to
        create a single Route object that can be used interchangeably with
        Pages or Route Groups as needed.

        Note: if no args are provided, a blank Route object will be created.

        Args:
          obj, (Optional) an existing Route object can be provided if the
              user wants to modify or duplicate the object.

        Keyword Args:
          intent, (str): The UUID of the Intent to route to
          condition, (str): The condition to evaluate on the route
          target_page, (str): The UUID of the target page to transition to
          target_flow, (str): The UUID of the target flow to transition to
          trigger_fulfillment, (obj): Requires an object in the format of type
          <google.cloud.dialogflowcx_v3beta1.types.fulfillment.Fulfillment>

        Returns:
          Route object of type
          <google.cloud.dialogflowcx_v3beta1.types.page.TransitionRoute>
        """

        if obj:
            route = obj

            # make sure the route name is cleared if this is a copy of
            # another existing route object
            route.name = ""

        else:
            route = types.page.TransitionRoute()

        # Set route attributes to args
        for key, value in kwargs.items():
            if key == "trigger_fulfillment":
                tf = cls.make_trigger_fulfillment(value)
                setattr(route, key, tf)
            else:
                setattr(route, key, value)

        return route

    @classmethod
    def make_trigger_fulfillment(
        cls, messages=None, webhook_id=None, webhook_tag=None
    ):
        """Creates a single Fulfillment object for Dialogflow CX.

        Fulfillments are used as part of Transition Routes to add Dialogue
        messages back to the user, trigger webhooks, set parameter presets,
        and enable IVR options where applicable.

        Note: if no args are provided, a blank Fulfillment object will be
        returned.

        Args:
            messages: Optional list of Dialogue messages to send
            webhook_id, (str): (Optional)
                The UUID of the Dialogflow CX webhook to trigger
                when the Fulfillment is triggered by the conversation.
            webhook_tag, (str): (Required if webhook_id is provided)
                User defined tag associated with

        Returns:
            Fulfillment object of type
            <google.cloud.dialogflowcx_v3beta1.types.fulfillment.Fulfillment>
        """
        fulfillment = types.fulfillment.Fulfillment()

        if messages:
            response_message = types.response_message.ResponseMessage()
            message_text = response_message.Text()

            message_text.text = messages
            response_message.text = message_text
            fulfillment.messages = [response_message]

        if webhook_id:
            fulfillment.webhook = webhook_id

            if not webhook_tag:
                logging.info(
                    "webhook_tag is required when specifying webhook_id")
                return None

            else:
                fulfillment.tag = webhook_tag

        # print(fulfillment)
        return fulfillment

    @classmethod
    def set_entity_type_attr(cls, entity_type, kwargs):
        for key, value in kwargs.items():
            if key == "kind":
                kind = types.entity_type.EntityType.Kind
                obj = cls.make_generic(value, kind, kind(0))
                setattr(entity_type, key, obj)
            # For the auto expansion mode case create helper object to set at
            # entity_type attribute
            elif key == "auto_expansion_mode":
                aem = types.entity_type.EntityType.AutoExpansionMode
                obj = cls.make_generic(value, aem, aem(1))
                setattr(entity_type, key, obj)

            # For the entities case iterate over dictionary and assign key value
            # pairs to entity type elements of entities list
            elif key == "entities":
                entity = types.entity_type.EntityType.Entity
                obj = cls.make_seq(value, entity, entity())
                setattr(entity_type, key, obj)

            # For the excluded phrases case assign value to the excluded phrase
            # object then set as the entity_type attribute
            elif key == "excluded_phrases":
                ep = types.entity_type.EntityType.ExcludedPhrase
                obj = cls.make_seq(value, ep, ep())
                setattr(entity_type, key, obj)

            else:
                setattr(entity_type, key, value)
