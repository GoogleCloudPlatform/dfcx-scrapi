"""A set of builder methods to create CX proto resource objects"""

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

from typing import List, Union

from google.cloud.dialogflowcx_v3beta1.types import (
    Page, Form, Fulfillment, TransitionRoute, EventHandler
)


class PageBuilder:
    """Base Class for CX Page builder."""


    def __init__(self, obj: Page = None):
        self.proto_obj = None
        if obj:
            self.load_page(obj)


    def _check_page_exist(self):
        """Check if the proto_obj exists otherwise raise an error."""

        if not self.proto_obj:
            raise ValueError(
                "There is no proto_obj!"
                "\nUse create_new_page or load_page to continue."
            )
        elif not isinstance(self.proto_obj, Page):
            raise ValueError(
                "proto_obj is not a Page type."
                "\nPlease create or load the correct type to continue."
            )


    def load_page(self, obj: Page, overwrite: bool = False) -> Page:
        """Load an existing Page to proto_obj for further uses.

        Args:
          obj (Page):
            An existing Page obj.
          overwrite (bool)
            Overwrite the new proto_obj if proto_obj already
            contains a Page.

        Returns:
          A Page object stored in proto_obj
        """
        if not isinstance(obj, Page):
            raise ValueError(
                "The object you're trying to load is not a Page."
            )
        if self.proto_obj and not overwrite:
            raise Exception(
                "proto_obj already contains a Page."
                " If you wish to overwrite it, pass overwrite as True."
            )
        if overwrite or not self.proto_obj:
            self.proto_obj = obj

        return self.proto_obj


    def create_new_page(
        self,
        display_name: str,
        entry_fulfillment: Fulfillment = None,
        overwrite: bool = False
    ) -> Page:
        """Create a new Page.

        Args:
          display_name (str):
            Required. The human-readable name of the
            page, unique within the flow.
          entry_fulfillment (Fulfillment):
            The fulfillment to call when the session is entering the page.
          overwrite (bool)
            Overwrite the new proto_obj if proto_obj already contains a Flow.

        Returns:
          A Page object stored in proto_obj.
        """
        if not (display_name and isinstance(display_name, str)):
            raise ValueError("display_name should be a nonempty string.")
        if (entry_fulfillment and
            not isinstance(entry_fulfillment, Fulfillment)):
            raise ValueError(
                "The type of entry_fulfillment should be a Fulfillment."
            )
        if self.proto_obj and not overwrite:
            raise Exception(
                "proto_obj already contains a Flow."
                " If you wish to overwrite it, pass overwrite as True."
            )
        if overwrite or not self.proto_obj:
            if not entry_fulfillment:
                self.proto_obj = Page(
                    display_name=display_name,
                    entry_fulfillment=Fulfillment()
                )
            else:
                self.proto_obj = Page(
                    display_name=display_name,
                    entry_fulfillment=entry_fulfillment
                )

        return self.proto_obj


    def add_transition_route(
        self,
        transition_routes: Union[TransitionRoute, List[TransitionRoute]]
    ) -> Page:
        """Add single or multiple TransitionRoutes to the Page.

        Args:
          transition_routes (TransitionRoute | List[TransitionRoute]):
            A single or list of TransitionRoutes to add
            to the Page existed in proto_obj.
        Returns:
          A Page object stored in proto_obj.
        """
        self._check_page_exist()

        if ((not isinstance(transition_routes, TransitionRoute)) or
            (not isinstance(transition_routes, list) and all(
                (isinstance(tr, TransitionRoute) for tr in transition_routes)
            ))):
            raise ValueError(
                "transition_routes should be either a TransitionRoute or"
                " a list of TransitionRoutes."
            )

        if not isinstance(transition_routes, list):
            transition_routes = [transition_routes]
        self.proto_obj.transition_routes.extend(transition_routes)

        return self.proto_obj


    def add_event_handler(
        self,
        event_handlers: Union[EventHandler, List[EventHandler]]
    ) -> Page:
        """Add single or multiple EventHandlers to the Page.

        Args:
          event_handlers (EventHandler | List[EventHandler]):
            A single or list of EventHandler to add
            to the Page existed in proto_obj.
        Returns:
          A Page object stored in proto_obj.
        """
        self._check_page_exist()

        if ((not isinstance(event_handlers, EventHandler)) or
            (not isinstance(event_handlers, list) and all(
                (isinstance(eh, EventHandler) for eh in event_handlers)
            ))):
            raise ValueError(
                "event_handlers should be either a EventHandler or"
                " a list of EventHandlers."
            )

        if not isinstance(event_handlers, list):
            event_handlers = [event_handlers]
        self.proto_obj.event_handlers.extend(event_handlers)

        return self.proto_obj


    def add_transition_route_group(
        self,
        transition_route_groups: Union[str, List[str]]
    ) -> Page:
        """Add single or multiple TransitionRouteGroups to the Page.

        Args:
          transition_route_groups (str | List[str]):
            A single or list of TransitionRouteGroup's id to add
            to the Page existed in proto_obj. Format:
            ``projects/<Project ID>/locations/<Location ID>/agents/<Agent ID>/
              flows/<Flow ID>/transitionRouteGroups/<TransitionRouteGroup ID>``.
        Returns:
          A Page object stored in proto_obj.
        """
        self._check_page_exist()

        if ((not isinstance(transition_route_groups, str)) or
            (not isinstance(transition_route_groups, list) and all(
                (isinstance(trg, str) for trg in transition_route_groups)
            ))):
            raise ValueError(
                "transition_route_groups should be either a string or"
                " a list of strings."
            )

        if not isinstance(transition_route_groups, list):
            transition_route_groups = [transition_route_groups]
        self.proto_obj.transition_route_groups.extend(transition_route_groups)

        return self.proto_obj


    def add_parameter(
        self,
        display_name: str,
        entity_type: str,
        initial_prompt_fulfillment: Fulfillment,
        required: bool = True,
        default_value: str = None,
        is_list: bool = False,
        redact: bool = False,
        reprompt_event_handlers: Union[EventHandler, List[EventHandler]] = None
    ) -> Page:
        """Parameters to collect from the user.

        Args:
          display_name (str):
            Required. The human-readable name of the
            parameter, unique within the form.
          entity_type (str):
            Required. The entity type of the parameter. Format:
            ``projects/-/locations/-/agents/-/
              entityTypes/<System Entity Type ID>``
            for system entity types (for example,
            ``projects/-/locations/-/agents/-/entityTypes/sys.date``),
            or
            ``projects/<Project ID>/locations/<Location ID>/
              agents/<Agent ID>/entityTypes/<Entity Type ID>``
            for developer entity types.
          initial_prompt_fulfillment (Fulfillment):
            Required. The fulfillment to provide the initial prompt that
            the agent can present to the user in order to fill the parameter.
          required (bool):
            Indicates whether the parameter is required.
            Optional parameters will not trigger prompts;
            however, they are filled if the user specifies
            them. Required parameters must be filled before
            form filling concludes.
          default_value (str):
            The default value of an optional parameter.
            If the parameter is required, the default value
            will be ignored.
          is_list (bool):
            Indicates whether the parameter represents a
            list of values.
          redact (bool):
            Indicates whether the parameter content should be redacted
            in log. If redaction is enabled, the parameter content will
            be replaced by parameter name during logging.
          reprompt_event_handlers (EventHandler | List[EventHandler]):
            The handlers for parameter-level events, used to provide reprompt
            for the parameter or transition to a different page/flow.
            The supported events are:
              - ``sys.no-match-<N>``, where N can be from 1 to 6
              - ``sys.no-match-default``
              - ``sys.no-input-<N>``, where N can be from 1 to 6
              - ``sys.no-input-default``
              - ``sys.invalid-parameter``

            ``initial_prompt_fulfillment`` provides the first prompt for
            the parameter.

            If the event handler for the corresponding event can't be found on
            the parameter, ``initial_prompt_fulfillment`` will be re-prompted.

        Returns:
          A Page object stored in proto_obj.
        """
        self._check_page_exist()

        if not (display_name and isinstance(display_name, str)):
            raise ValueError("display_name should be a nonempty string.")
        if not (entity_type and isinstance(entity_type, str)):
            raise ValueError("entity_type should be a valid entity type id.")
        if not (initial_prompt_fulfillment and
            isinstance(initial_prompt_fulfillment, str)):
            raise ValueError(
                "initial_prompt_fulfillment should be a Fulfillment."
            )
        if not (isinstance(required, bool) and
            isinstance(is_list, bool) and
            isinstance(redact, bool)):
            raise ValueError(
                "`is_list`, `required`, and `redact` should be bool."
            )
        if ((not isinstance(reprompt_event_handlers, EventHandler)) or
            (not isinstance(reprompt_event_handlers, list) and all(
                (isinstance(eh, EventHandler) for eh in reprompt_event_handlers)
            ))):
            raise ValueError(
                "reprompt_event_handlers should be either a EventHandler or"
                " a list of EventHandlers."
            )
        if not isinstance(reprompt_event_handlers, list):
            reprompt_event_handlers = [reprompt_event_handlers]
        
        if required:
            the_param = Form.Parameter(
                display_name=display_name,
                required=required,
                entity_type=entity_type,
                is_list=is_list,
                redact=redact
            )
        else:
            if not isinstance(default_value, str):
                raise ValueError("`default_value` should be a string.")
            the_param = Form.Parameter(
                display_name=display_name,
                required=required,
                entity_type=entity_type,
                is_list=is_list,
                redact=redact,
                default_value=default_value
            )
        
        the_param.fill_behavior = Form.Parameter.FillBehavior(
            initial_prompt_fulfillment=initial_prompt_fulfillment,
            reprompt_event_handlers=reprompt_event_handlers
        )
        self.proto_obj.form.parameters.append(the_param)

        return self.proto_obj
