"""A set of Utility methods to check entities on DFCX Agents."""

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
from typing import Dict
import pandas as pd
import re
from dfcx_scrapi.core import scrapi_base
from dfcx_scrapi.core.intents import Intents
from dfcx_scrapi.core.entity_types import EntityTypes

# logging config
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)-8s %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)

class EntitiesCheckerUtil(scrapi_base.ScrapiBase):
    """Utility class for checking DFCX Agent's parameters."""
    def __init__(
        self,
        agent_id: str,
        creds_path: str = None,
        creds_dict: Dict = None,
        creds=None,
        scope=False,
    ):
        super().__init__(
            creds_path=creds_path,
            creds_dict=creds_dict,
            creds=creds,
            scope=scope,
        )
        self.agent_id = agent_id
        if creds_path:
            self.creds_path = creds_path

        self._intents = Intents(
            agent_id=self.agent_id, 
            creds_path=self.creds_path
        )
        self._entity_types = EntityTypes(
            agent_id=self.agent_id, 
            creds_path=self.creds_path
        )
        self.intents_df = pd.DataFrame()
        self.entity_types_df = pd.DataFrame()
        self._intents_list = []
        self._entity_types_list = []

    @staticmethod
    def _get_entity_by_param_id(parameters, parameter_id):
        """ static method that returns the entity type that 
            is paired with the given parameter id
        """

        entity_type = None
        for parameter in parameters:
            if parameter.id == parameter_id:
                entity_type = parameter.entity_type
                break

        return entity_type

    def _set_intents_df(self) -> pd.DataFrame:
        self.intents_df = pd.DataFrame({
                'intent': pd.Series(dtype='str'),
                'intent_id': pd.Series(dtype='str'),
                'training_phrase': pd.Series(dtype='str'),
                'tag_text': pd.Series(dtype='str'),
                'parameter_id': pd.Series(dtype='str'),
                'entity_type_id': pd.Series(dtype='str'),
                })

        if not self._intents_list:
            self._intents_list = self._intents.list_intents(
                agent_id=self.agent_id
            )

        for intent in self._intents_list:
            if 'parameters' in intent:
                for training_phrase in intent.training_phrases:
                    concat_training_phrase = ''
                    tag_texts = []
                    for part in training_phrase.parts:
                        concat_training_phrase += part.text
                        if 'parameter_id' in part:
                            text=part.text
                            params = intent.parameters
                            param_id = part.parameter_id
                            entity_type = self._get_entity_by_param_id(
                                params, param_id
                            )
                            tag_texts_set = (text, param_id, entity_type)
                            tag_texts.append(tag_texts_set)
                    if tag_texts:
                        for pair in tag_texts:
                            temp = pd.DataFrame({
                                'intent': [intent.display_name],
                                'intent_id': [intent.name],
                                'training_phrase': [concat_training_phrase],
                                'tag_text': [pair[0]],
                                'parameter_id': [pair[1]],
                                'entity_type_id': [pair[2]]
                                })
                            self.intents_df = pd.concat([self.intents_df, temp])

        self.intents_df = self.intents_df.reset_index(drop=True)

    def _set_entity_types_df(self):

        self.entity_types_df = pd.DataFrame({
            'entity_type_id': pd.Series(dtype='str'),
            'entity_type': pd.Series(dtype='str'),
            'kind': pd.Series(dtype='str'),
            'entity_values': pd.Series(dtype='str'),
            'synonyms': pd.Series(dtype='str')
            })

        if not self._entity_types_list:
            self._entity_types_list = self._entity_types.list_entity_types(agent_id = self.agent_id)

        for entity_type in self._entity_types_list:
            entity_values = []
            synonyms = []
            for entity in entity_type.entities:
                entity_values.append(entity.value)
                synonyms += list(entity.synonyms)

            temp = pd.DataFrame({
                'entity_type_id': [entity_type.name],
                'entity_type': [entity_type.display_name],
                'kind': [entity_type.kind.name],
                'entity_values': [entity_values],
                'synonyms': [synonyms]})
            self.entity_types_df = pd.concat([self.entity_types_df, temp])

        self.entity_types_df = self.entity_types_df.reset_index(drop=True)

    def _unpack_nested_entities(self, df, target_kind_type):
        """Unpacking the nested entity types to the comparable dataframe structure
            e.g:Nested entity type-> 
            entity_type:@child_entity_type1,@child_entity_type2  
            unpacked entity type-> 
            entity_type:[child1.entities,child2.entities]:[child1.synonyms,chilld.synonyms]

        Returns:
            A dataframe with columns
            entity_type_id
            entity_type
            kind
            entity_values - list of the [entity values]
            synonyms - list of the [synonyms]
        """
        for idx, row in df.iterrows():
            kind = row['kind']
            if kind == 'KIND_LIST':
                entity_values = row['entity_values']
                new_entity_values = []
                new_synonyms = []
                is_nested_entity_type = True
                for entity_value in entity_values:
                    if '@' == entity_value[0] and (df['entity_type'] == entity_value[1::]).any():
                        entity_value = entity_value[1::]
                        child_entity_type_row = df.loc[df['entity_type'] == entity_value]
                        child_index = child_entity_type_row.index[0]
                        child_entity_type_kind = child_entity_type_row['kind'][child_index]
                        if child_entity_type_kind == target_kind_type:
                            child_entity_values = child_entity_type_row['entity_values'][child_index]
                            child_entity_synonyms = child_entity_type_row['synonyms'][child_index]
                            new_entity_values += child_entity_values
                            new_synonyms += child_entity_synonyms
                        else:
                            is_nested_entity_type = False
                            break
                    else:
                        is_nested_entity_type = False
                        break
                if new_entity_values and is_nested_entity_type:
                    df.loc[idx, 'entity_values'] = new_entity_values
                    df.loc[idx, 'synonyms'] = new_synonyms
                    df.loc[idx, 'kind'] = target_kind_type

        return df

    def get_tag_texts_in_intents(self) -> pd.DataFrame:
        """ Get all the tag_texts that are referenced to the specific parameter id 
            & entity type id in the training phrases in the intents

        Returns:
            A dataframe with columns
            intent_id - the intent name
            intent - the intent display name
            training_phrase - the training phrase in the intent
            tag_text - the subset of the tp that is tagged with the specific entity id
            parameter_id - parameter id
            entity_type_id - entity id
        """
        if self.intents_df.empty:
            self._set_intents_df()

        return self.intents_df

    def get_entity_types_df(self) -> pd.DataFrame:
        """Get the entity types and store all the entities/synonyms in one row

        Returns:
            A dataframe with columns
            entity_type_id
            entity_type
            kind
            entity_values - list of the [entity values]
            synonyms - list of the [synonyms]
        """
        if self.entity_types_df.empty:
            self._set_entity_types_df()

        return self.entity_types_df

    def generate_hidden_synonym_tags(self) -> pd.DataFrame:
        """ Generate the overall stats that identify the incorrect tags in the tps 
            by comparing with the entity type's synonyms
            Merges the intents and the entity types dfs to create the comparable df
            Check if the tag_text is relevent in the entity type's synonyms
            if a tag_text in synonyms then is_hidden = YES else is_hidden = NO

        Returns:
            A dataframe with columns
            intent
            intent_id
            training_phrase
            tag_text
            parameter_id
            entity_type_id
            entity_type
            kind
            entity_values
            synonyms
            is_hidden
        """
        if self.intents_df.empty:
            self._set_intents_df()

        if self.entity_types_df.empty:
            self._set_entity_types_df()

        unpacked_ents_df = self._unpack_nested_entities(self.entity_types_df,'KIND_MAP')
        hidden_ents = pd.merge(self.intents_df,unpacked_ents_df,on='entity_type_id')
        drop_indexes = hidden_ents[~hidden_ents.kind.str.contains('KIND_MAP')].index
        hidden_ents = hidden_ents.drop(drop_indexes)
        hidden_ents = hidden_ents.reset_index(drop=True)
        hidden_ents['is_hidden'] = pd.Series(None,index=hidden_ents.index)

        for idx, row in hidden_ents.iterrows():
            synonyms = row['synonyms']
            tag_text = row['tag_text']
            for synonym in synonyms:
                synonym = [char.lower() for char in synonym if char.isalnum()]
                tag_text = [char.lower() for char in tag_text if char.isalnum()]
                if synonym == tag_text:
                    hidden_ents.loc[idx, 'is_hidden'] = 'NO'
            if pd.isna(hidden_ents.loc[idx, 'is_hidden']):
                hidden_ents.loc[idx, 'is_hidden'] = 'YES'

        return hidden_ents

    def generate_hidden_regex_tags(self) -> pd.DataFrame:
        """ Generate the overall stats that identify the incorrect tags in the tps
            by comparing with the entity type's regex
            if the tag text in Intent is not matched with the regex 
            then is_hidden = YES

        Returns:
            A dataframe with columns
            intent
            intent_id
            training_phrase
            tag_text
            parameter_id
            entity_type_id
            entity_type
            kind
            entity_values
            synonyms
            is_hidden
        """
        if self.intents_df.empty:
            self._set_intents_df()

        if self.entity_types_df.empty:
            self._set_entity_types_df()

        unpacked_ents_df = self._unpack_nested_entities(self.entity_types_df, 'KIND_REGEX')
        hidden_ents = pd.merge(self.intents_df, unpacked_ents_df, on = 'entity_type_id')
        drop_indexes = hidden_ents[~hidden_ents.kind.str.contains('KIND_REGEX')].index
        hidden_ents = hidden_ents.drop(drop_indexes)
        hidden_ents = hidden_ents.reset_index(drop=True)
        hidden_ents['is_hidden'] = pd.Series(None, index=hidden_ents.index)

        for idx,row in hidden_ents.iterrows():
            regexs=row['synonyms']
            tag_text=row['tag_text']
            for regex in regexs:
                if re.match(regex,tag_text):
                    hidden_ents.loc[idx, 'is_hidden'] = 'NO'
            if pd.isna(hidden_ents.loc[idx,'is_hidden']):
                hidden_ents.loc[idx, 'is_hidden'] = 'YES'

        return hidden_ents

    def space_in_entity_values(self) -> pd.DataFrame:
        """ Validating if there is any leading/trailing 
            space in the entity values   
            e.g: Phone: "iphone " => should be Phone: "iphone"
            
            Returns:
            A dataframe with columns
            entity_type_id
            entity_type
            kind
            entity_values 
            synonyms
            has_space:if the entity value have the space(s) then YES else NO 
            entities_w_space:list of the entity values that have a space
        """
        ent_mapper = self.get_entity_types_df()
        ent_mapper = self._unpack_nested_entity_types(ent_mapper, 'KIND_MAP')
        ent_mapper['has_space'] = pd.Series('NO', index=ent_mapper.index)
        ent_mapper['entities_w_space'] = pd.Series('NA', index=ent_mapper.index)

        for idx, row in ent_mapper.iterrows():
            entity_values = row['entity_values']
            tmp_ents = []
            for entity in entity_values:
                striped_entity = entity.strip()
                if not entity == striped_entity:
                    ent_mapper.loc[idx, 'has_space'] = 'YES'
                    tmp_ents.append(entity)
                    ent_mapper.loc[idx,'entities_w_space'] = tmp_ents

        return ent_mapper
