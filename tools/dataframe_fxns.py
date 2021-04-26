'''DFCX manipulation functions to extend dfcx_sapi lib'''

from typing import List
import time
import json
import logging
import pandas as pd
import os
import google.cloud.dialogflowcx_v3beta1.types as types
from oauth2client.service_account import ServiceAccountCredentials
import gspread
from gspread_dataframe import set_with_dataframe
from tabulate import tabulate
from ..core import entity_types, intents, flows, pages, transition_route_groups


# logging config
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)-8s %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S')


class Dataframe_fxns:
    def __init__(self, creds_path: str):
        logging.info('create dfcx creds %s', creds_path)
        self.entities = entity_types.EntityTypes(creds_path)
        self.intents = intents.Intents(creds_path)
        self.flows = flows.Flows(creds_path)
        self.pages = pages.Pages(creds_path)
        self.route_groups = transition_route_groups.TransitionRouteGroups(
            creds_path)
        self.creds_path = creds_path

    def gsheets2df(self, gsheetName, worksheetName):
        scope = ['https://spreadsheets.google.com/feeds',
                 'https://www.googleapis.com/auth/drive']
        creds_gdrive = ServiceAccountCredentials.from_json_keyfile_name(
            self.creds_path, scope)
        client = gspread.authorize(creds_gdrive)
        g_sheets = client.open(gsheetName)
        sheet = g_sheets.worksheet(worksheetName)
        dataPull = sheet.get_all_values()
        return pd.DataFrame(columns=dataPull[0], data=dataPull[1:])

    def df2Sheets(self, gsheetName, worksheetName, df):
        scope = ['https://spreadsheets.google.com/feeds',
                 'https://www.googleapis.com/auth/drive']
        creds_gdrive = ServiceAccountCredentials.from_json_keyfile_name(
            self.creds_path, scope)
        client = gspread.authorize(creds_gdrive)
        g_sheets = client.open(gsheetName)
        worksheet = g_sheets.worksheet(worksheetName)
        set_with_dataframe(worksheet, df)

    def progressBar(self, current, total, barLength=50, type_='Progress'):
        percent = float(current) * 100 / total
        arrow = '-' * int(percent / 100 * barLength - 1) + '>'
        spaces = ' ' * (barLength - len(arrow))
        print('{2}({0}/{1})'.format(current, total, type_) +
              '[%s%s] %d %%' % (arrow, spaces, percent), end='\r')

    def update_intent_from_dataframe(self, intent_id: str, train_phrases,
                                     params=pd.DataFrame(), mode='basic'):
        """update an existing intents training phrases and parameters
        the intent must exist in the agent
        this function has a dependency on the agent

        Args:
            intent_id: name parameter of the intent to update
            train_phrases: dataframe of training phrases
                in advanced have training_phrase and parts column to track the build
            params(optional): dataframe of parameters
            mode:
                basic - build assuming one row is one training phrase no entities,
                advance - build keeping track of training phrases and
                    parts with the training_phrase and parts column.

        Returns:
            intent_pb: the new intents protobuf object
        """

        if mode == 'basic':
            try:
                train_phrases = train_phrases[['text']]
                train_phrases = train_phrases.astype({'text': 'string'})
            except BaseException:
                tpSchema = pd.DataFrame(index=['text', 'parameter_id'], columns=[0], data=[
                                        'string', 'string']).astype({0: 'string'})
                logging.error('{0} mode train_phrases schema must be {1} \n'.format(
                    mode, tabulate(tpSchema.transpose(), headers='keys', tablefmt='psql')))

        elif mode == 'advanced':
            try:
                train_phrases = train_phrases[[
                    'training_phrase', 'part', 'text', 'parameter_id']]
                train_phrases = train_phrases.astype({'training_phrase': 'int32', 'part': 'int32',
                                                      'text': 'string', 'parameter_id': 'string'})
                if len(params) > 0:
                    params = params[['id', 'entity_type']]
                    params = params.astype({'id': 'string',
                                            'entity_type': 'string'})
            except BaseException:
                tpSchema = pd.DataFrame(index=['training_phrase', 'part', 'text', 'parameter_id'], columns=[
                                        0], data=['int32', 'int32', 'string', 'string']).astype({0: 'string'})
                pSchema = pd.DataFrame(index=['id', 'entity_type'], columns=[0], data=[
                                       'string', 'string']).astype({0: 'string'})
                logging.error('{0} mode train_phrases schema must be {1} \n'.format(
                    mode, tabulate(tpSchema.transpose(), headers='keys', tablefmt='psql')))
                logging.error(
                    '{0} mode parameter schema must be {1} \n'.format(
                        mode,
                        tabulate(
                            pSchema.transpose(),
                            headers='keys',
                            tablefmt='psql')))

        else:
            raise ValueError('mode must be basic or advanced')

        # phrase_schema_user = train_phrases.dtypes.to_frame().astype({0:'string'})
        # param_schema_user = params.dtypes.to_frame().astype({0:'string'})
        # if (phrase_schema_user.equals(phrase_schema_master))==False:
        #     raise ValueError('training phrase schema must be {} for {} mode'.format(tabulate(phrase_schema_master.transpose(), headers='keys', tablefmt='psql'), mode))
        # if mode == 'advanced':
        #     if (param_schema_user.equals(param_schema_master))==False and len(params)>0:
        #         raise ValueError('parameter schema must be {}'.format(tabulate(phrase_schema_master.transpose(), headers='keys', tablefmt='psql')))

        original = self.intents.get_intent(intent_id=intent_id)
        intent = {}
        intent['name'] = original.name
        intent['display_name'] = original.display_name
        intent['priority'] = original.priority
        intent['is_fallback'] = original.is_fallback
        intent['labels'] = dict(original.labels)
        intent['description'] = original.description

        # training phrases
        if mode == 'advanced':
            trainingPhrases = []
            for tp in range(
                0, int(
                    train_phrases['training_phrase'].astype(int).max() + 1)):
                tpParts = train_phrases[train_phrases['training_phrase'].astype(
                    int) == int(tp)]
                parts = []
                for _index, row in tpParts.iterrows():
                    part = {
                        'text': row['text'],
                        'parameter_id': row['parameter_id']
                    }
                    parts.append(part)

                trainingPhrase = {'parts': parts,
                                  'repeat_count': 1,
                                  'id': ''}
                trainingPhrases.append(trainingPhrase)

            intent['training_phrases'] = trainingPhrases
            parameters = []
            for _index, row in params.iterrows():
                parameter = {
                    'id': row['id'],
                    'entity_type': row['entity_type'],
                    'is_list': False,
                    'redact': False
                }
                parameters.append(parameter)

            if len(parameters) > 0:
                intent['parameters'] = parameters

        elif mode == 'basic':
            trainingPhrases = []
            for index, row in train_phrases.iterrows():
                part = {
                    'text': row['text'],
                    'parameter_id': None
                }
                parts = [part]
                trainingPhrase = {'parts': parts,
                                  'repeat_count': 1,
                                  'id': ''}
                trainingPhrases.append(trainingPhrase)
            intent['training_phrases'] = trainingPhrases
        else:
            raise ValueError('mode must be basic or advanced')

        jsonIntent = json.dumps(intent)
        intent_pb = types.Intent.from_json(jsonIntent)
        return intent_pb

    def bulk_update_intents_from_dataframe(self, agent_id, train_phrases_df,
                                           params_df=pd.DataFrame(),
                                           mode='basic', update_flag=False):
        """update an existing intents training phrases and parameters

        Args:
            agent_id: name parameter of the agent to update_flag - full path to agent
            train_phrases_df: dataframe of bulk training phrases
                required columns: text, display_name
                in advanced mode have training_phrase and parts column to track the build
            params_df(optional): dataframe of bulk parameters
            mode: basic|advanced
                basic: build assuming one row is one training phrase no entities
                advanced: build keeping track of training phrases and parts with the training_phrase and parts column.
            update_flag: True to update_flag the intents in the agent

        Returns:
            modified_intents: dictionary with intent display names as keys
                and the new intent protobufs as values

        """
        if mode == 'basic':
            try:
                train_phrases_df = train_phrases_df[['display_name', 'text']]
                train_phrases_df = train_phrases_df.astype(
                    {'display_name': 'string', 'text': 'string'})
            except BaseException:
                tpSchema = pd.DataFrame(index=['display_name', 'text', 'parameter_id'], columns=[
                                        0], data=['string', 'string', 'string']).astype({0: 'string'})
                logging.error('{0} mode train_phrases schema must be {1} \n'.format(
                    mode, tabulate(tpSchema.transpose(), headers='keys', tablefmt='psql')))

        elif mode == 'advanced':
            try:
                train_phrases_df = train_phrases_df[[
                    'display_name', 'training_phrase', 'part', 'text', 'parameter_id']]
                train_phrases_df = train_phrases_df.astype(
                    {
                        'display_name': 'string',
                        'training_phrase': 'int32',
                        'part': 'int32',
                        'text': 'string',
                        'parameter_id': 'string'})
                if len(params_df) > 0:
                    params_df = params_df[[
                        'display_name', 'id', 'entity_type']]
                    params_df = params_df.astype({'display_name': 'string', 'id': 'string',
                                                  'entity_type': 'string'})
            except BaseException:
                tpSchema = pd.DataFrame(
                    index=[
                        'display_name',
                        'training_phrase',
                        'part',
                        'text',
                        'parameter_id'],
                    columns=[0],
                    data=[
                        'string',
                        'int32',
                        'int32',
                        'string',
                        'string']).astype(
                    {
                        0: 'string'})
                pSchema = pd.DataFrame(index=['display_name', 'id', 'entity_type'], columns=[
                                       0], data=['string', 'string', 'string']).astype({0: 'string'})
                logging.error('{0} mode train_phrases schema must be {1} \n'.format(
                    mode, tabulate(tpSchema.transpose(), headers='keys', tablefmt='psql')))
                logging.error(
                    '{0} mode parameter schema must be {1} \n'.format(
                        mode,
                        tabulate(
                            pSchema.transpose(),
                            headers='keys',
                            tablefmt='psql')))

        else:
            raise ValueError('mode must be basic or advanced')

        # TODO - check if user provided DF is in the right shape
        # phrase_schema_user = train_phrases_df.dtypes.to_frame().astype({0:'string'})
        # param_schema_user = params_df.dtypes.to_frame().astype({0:'string'})

        # if (phrase_schema_user.equals(phrase_schema_master))==False:
        #     logging.error('training phrase schema must be\n {} \n'.format(
        #         tabulate(phrase_schema_master.transpose(), headers='keys', tablefmt='psql')))
        #     logging.error('got schema \n {}'.format(
        #         tabulate(phrase_schema_user.transpose(), headers='keys', tablefmt='psql')))
        #     logging.error('df.head \n%s', train_phrases_df.head() )
            # raise ValueError('wrong schema format \n%s' % phrase_schema_user)

        # if mode =='advanced':
        #     if (param_schema_user.equals(param_schema_master))==False and len(params_df)>0:
        #         raise ValueError('parameter schema must be {}'.format(tabulate(phrase_schema_master.transpose(), headers='keys', tablefmt='psql')))

        logging.info('updating agent_id %s', agent_id)
        intents_map = self.intents.get_intents_map(
            agent_id=agent_id, reverse=True)
        intent_names = list(set(train_phrases_df['display_name']))

        new_intents = {}
        i = 0
        for intent_name in intent_names:
            # logging.info('process intent_name: %s type: %s', intent_name, type(intent_name))

            # easier way to compare for empty pd cell values?
            if isinstance(intent_name, pd._libs.missing.NAType):
                logging.warning('empty intent_name')
                continue

            tps = train_phrases_df.copy()[
                train_phrases_df['display_name'] == intent_name].drop(
                columns='display_name')
            params = pd.DataFrame()
            if mode == 'advanced':
                params = params_df.copy()[
                    params_df['display_name'] == intent_name].drop(
                    columns='display_name')

            if intent_name not in intents_map.keys():
                logging.error(
                    'FAIL to update - intent not found: [%s]',
                    intent_name)
                continue

            # logging.info('update intent %s', intent_name)
            new_intent = self.update_intent_from_dataframe(
                intent_id=intents_map[intent_name],
                train_phrases=tps,
                params=params,
                mode=mode)
            new_intents[intent_name] = new_intent
            i += 1
            self.progressBar(i, len(intent_names))
            if update_flag:
                logging.info('updating_intent %s', intent_name)
                self.intents.update_intent(
                    intent_id=new_intent.name, obj=new_intent)
                if i % 179 == 0:
                    time.sleep(62)

        return new_intents

    def create_intent_from_dataframe(
            self,
            display_name: str,
            train_phrases,
            params=pd.DataFrame(),
            meta={},
            mode='basic'):
        """create an intent

        Args:
            display_name: display_name parameter of the intent to create
            train_phrases: dataframe of training phrases
                in advanced have training_phrase and parts column to track the build
            params(optional): dataframe of parameters
            mode:
                basic - build assuming one row is one training phrase no entities,
                advance - build keeping track of training phrases and
                    parts with the training_phrase and parts column.

        Returns:
            intent_pb: the new intents protobuf object
        """
        if mode == 'basic':
            try:
                train_phrases = train_phrases[['text']]
                train_phrases = train_phrases.astype({'text': 'string'})
            except BaseException:
                tpSchema = pd.DataFrame(index=['text', 'parameter_id'], columns=[0], data=[
                                        'string', 'string']).astype({0: 'string'})
                logging.error('{0} mode train_phrases schema must be {1} \n'.format(
                    mode, tabulate(tpSchema.transpose(), headers='keys', tablefmt='psql')))

        elif mode == 'advanced':
            try:
                train_phrases = train_phrases[[
                    'training_phrase', 'part', 'text', 'parameter_id']]
                train_phrases = train_phrases.astype({'training_phrase': 'int32', 'part': 'int32',
                                                      'text': 'string', 'parameter_id': 'string'})
                if len(params) > 0:
                    params = params[['id', 'entity_type']]
                    params = params.astype({'id': 'string',
                                            'entity_type': 'string'})
            except BaseException:
                tpSchema = pd.DataFrame(index=['training_phrase', 'part', 'text', 'parameter_id'], columns=[
                                        0], data=['int32', 'int32', 'string', 'string']).astype({0: 'string'})
                pSchema = pd.DataFrame(index=['id', 'entity_type'], columns=[0], data=[
                                       'string', 'string']).astype({0: 'string'})
                logging.error('{0} mode train_phrases schema must be {1} \n'.format(
                    mode, tabulate(tpSchema.transpose(), headers='keys', tablefmt='psql')))
                logging.error(
                    '{0} mode parameter schema must be {1} \n'.format(
                        mode,
                        tabulate(
                            pSchema.transpose(),
                            headers='keys',
                            tablefmt='psql')))

        else:
            raise ValueError('mode must be basic or advanced')

        intent = {}
        intent['display_name'] = display_name
        intent['priority'] = meta.get('priority', 500000)
        intent['is_fallback'] = meta.get('is_fallback', False)
        intent['labels'] = meta.get('labels', {})
        intent['description'] = meta.get('description', '')

        # training phrases
        if mode == 'advanced':
            trainingPhrases = []
            for tp in range(
                0, int(
                    train_phrases['training_phrase'].astype(int).max() + 1)):
                tpParts = train_phrases[train_phrases['training_phrase'].astype(
                    int) == int(tp)]
                parts = []
                for _index, row in tpParts.iterrows():
                    part = {
                        'text': row['text'],
                        'parameter_id': row['parameter_id']
                    }
                    parts.append(part)

                trainingPhrase = {'parts': parts,
                                  'repeat_count': 1,
                                  'id': ''}
                trainingPhrases.append(trainingPhrase)

            intent['training_phrases'] = trainingPhrases
            parameters = []
            for _index, row in params.iterrows():
                parameter = {
                    'id': row['id'],
                    'entity_type': row['entity_type'],
                    'is_list': False,
                    'redact': False
                }
                parameters.append(parameter)

            if len(parameters) > 0:
                intent['parameters'] = parameters

        elif mode == 'basic':
            trainingPhrases = []
            for index, row in train_phrases.iterrows():
                part = {
                    'text': row['text'],
                    'parameter_id': None
                }
                parts = [part]
                trainingPhrase = {'parts': parts,
                                  'repeat_count': 1,
                                  'id': ''}
                trainingPhrases.append(trainingPhrase)
            intent['training_phrases'] = trainingPhrases
        else:
            raise ValueError('mode must be basic or advanced')

        jsonIntent = json.dumps(intent)
        intent_pb = types.Intent.from_json(jsonIntent)

        return intent_pb

    def bulk_create_intent_from_dataframe(
            self,
            agent_id,
            train_phrases_df,
            params_df=pd.DataFrame(),
            mode='basic',
            update_flag=False):
        """create intents

        Args:
            agent_id: name parameter of the agent to update_flag - full path to agent
            train_phrases_df: dataframe of bulk training phrases
                required columns: text, display_name
                in advanced mode have training_phrase and parts column to track the build
            params_df(optional): dataframe of bulk parameters
            mode: basic|advanced
                basic: build assuming one row is one training phrase no entities
                advanced: build keeping track of training phrases and parts with the training_phrase and parts column.
            update_flag: True to update_flag the intents in the agent

        Returns:
            new_intents: dictionary with intent display names as keys and the new intent protobufs as values

        """
        # remove any unnecessary columns
        if mode == 'basic':
            try:
                train_phrases_df = train_phrases_df[['display_name', 'text']]
                train_phrases_df = train_phrases_df.astype(
                    {'display_name': 'string', 'text': 'string'})
            except BaseException:
                tpSchema = pd.DataFrame(index=['display_name', 'text', 'parameter_id'], columns=[
                                        0], data=['string', 'string', 'string']).astype({0: 'string'})
                raise ValueError('{0} mode train_phrases schema must be {1}'.format(
                    mode, tabulate(tpSchema.transpose(), headers='keys', tablefmt='psql')))

        elif mode == 'advanced':
            try:
                if 'meta' not in train_phrases_df.columns:
                    train_phrases_df['meta'] = [dict()] * len(train_phrases_df)

                train_phrases_df = train_phrases_df[[
                    'display_name', 'training_phrase', 'part', 'text', 'parameter_id', 'meta']]
                train_phrases_df = train_phrases_df.astype(
                    {
                        'display_name': 'string',
                        'training_phrase': 'int32',
                        'part': 'int32',
                        'text': 'string',
                        'parameter_id': 'string'})
                if len(params_df) > 0:
                    params_df = params_df[[
                        'display_name', 'id', 'entity_type']]
                    params_df = params_df.astype({'display_name': 'string', 'id': 'string',
                                                  'entity_type': 'string'})
            except BaseException:
                tpSchema = pd.DataFrame(
                    index=[
                        'display_name',
                        'training_phrase',
                        'part',
                        'text',
                        'parameter_id'],
                    columns=[0],
                    data=[
                        'string',
                        'int32',
                        'int32',
                        'string',
                        'string']).astype(
                    {
                        0: 'string'})
                pSchema = pd.DataFrame(index=['display_name', 'id', 'entity_type'], columns=[
                                       0], data=['string', 'string', 'string']).astype({0: 'string'})
                raise ValueError(
                    '{0} mode train_phrases schema must be {1} \n parameter schema must be {2}'.format(
                        mode, tabulate(
                            tpSchema.transpose(), headers='keys', tablefmt='psql'), tabulate(
                            pSchema.transpose(), headers='keys', tablefmt='psql')))

        else:
            raise ValueError('mode must be basic or advanced')

        intents = list(set(train_phrases_df['display_name']))
        newIntents = {}
        i = 0
        for instance in intents:
            tps = train_phrases_df.copy()[
                train_phrases_df['display_name'] == instance].drop(
                columns='display_name')
            params = pd.DataFrame()
            if mode == 'advanced':
                params = params_df.copy()[
                    params_df['display_name'] == instance].drop(
                    columns='display_name')
            newIntent = self.create_intent_from_dataframe(
                display_name=instance, train_phrases=tps, params=params, mode=mode)
            newIntents[instance] = newIntent
            i += 1
            self.progressBar(i, len(intents))
            if update_flag:
                if i % 100 == 0:
                    time.sleep(70)
                self.intents.create_intent(agent_id=agent_id, obj=newIntent)

        return newIntents

    def create_entity_from_dataframe(self, display_name, entity_df, meta={}):
        """create an entity

        Args:
            display_name: display_name parameter of the entity to update
            entity_df: dataframe values and synonyms .

        Returns:
            entity_pb: the new entity protobuf object
        """

        entityObj = {}
        entityObj['display_name'] = display_name
        entityObj['kind'] = meta.get('kind', 1)
        entityObj['auto_expansion_mode'] = meta.get('auto_expansion_mode', 0)
        entityObj['excluded_phrases'] = meta.get('excluded_phrases', [])
        entityObj['enable_fuzzy_extraction'] = meta.get(
            'enable_fuzzy_extraction', False)

        values = []
        for index, row in entity_df.iterrows():
            value = row['value']
            synonyms = json.loads(row['synonyms'])

            part = {'value': value,
                    'synonyms': synonyms}
            values.append(part)

        entityObj['entities'] = values
        entity_pb = types.EntityType.from_json(json.dumps(entityObj))

        return entity_pb

    def bulk_create_entity_from_dataframe(
            self, agent_id, entities_df, update_flag=False):
        """create entities

        Args:
            agent_id: name parameter of the agent to update_flag - full path to agent
             entities_df: dataframe of bulk entities
                required columns: display_name, value, synonyms
            update_flag: True to update_flag the entiites in the agent

        Returns:
            new_entities: dictionary with entity display names as keys and the new entity protobufs as values

        """

        if 'meta' in entities_df.columns:
            meta = entities_df.copy()[['display_name',
                                       'meta']].drop_duplicates().reset_index()

        i, custom_entites = 0, {}
        for e in list(set(entities_df['display_name'])):
            oneEntity = entities_df[entities_df['display_name'] == e]
            if 'meta' in locals():
                meta_ = meta[meta['display_name'] == e]['meta'].iloc[0]
                meta_ = json.loads(meta_)
                new_entity = self.create_entity_from_dataframe(
                    display_name=e, entity_df=oneEntity, meta=meta)

            else:
                new_entity = self.create_entity_from_dataframe(
                    display_name=e, entity_df=oneEntity)

            custom_entites[e] = new_entity
            i += 1

            if update_flag:
                self.entities.create_entity_type(
                    agent_id=agent_id, obj=new_entity)
                if i % 179 == 0:
                    time.sleep(61)

            self.progressBar(i,
                             len(list(set(entities_df['display_name']))),
                             type_='entities')
        return custom_entites

    def create_transition_route_from_dataframe(self, route_df):
        '''
        create transition route

            Args:
                route_df: dataframe with a singular routes data. Should only be one row
                    intent: intent id
                    condition: string condition. ex. $session.params.dtmf_diy_opt_in = 1 AND $session.params.dtmf_2_techinternet = 2
                    target_page: page id
                    target_flow: flow id
                    webhook: webhook id
                    webhook_tag: string webhook tag
                    custom_payload: a singular payload or list of payloads ex. [{}, {}]
                    fullfillment_text: = list of text ["yo", "hi"]
                    parameter_presets: = dictionary of parameter presets ex. {"param1":"value","param2":"othervalues"}

            Returns:
                transitionRoute: transition route protobuf
        '''

        transitionRoute = types.TransitionRoute()

        route_dict = route_df.to_dict()
        transitionRoute.intent = route_dict.get('intent', None)
        transitionRoute.condition = route_dict.get('condition', None)
        transitionRoute.target_page = route_dict.get('target_page', None)
        transitionRoute.target_flow = route_dict.get('target_flow', None)

        # fulfillment
        fulfillment = types.Fulfillment()
        fulfillment.webhook = route_dict.get('webhook', None)
        fulfillment.tag = route_dict.get('webhook_tag', None)

        customPayload = route_dict.get('custom_payload', None)
        custy_payloads = []
        if customPayload:
            customPayload = json.loads(customPayload)
            if ~isinstance(customPayload, list):
                customPayload = [customPayload]
            for cp in customPayload:
                custy_payloads.append({'payload': cp})

        fulfillment_text = route_dict.get('fullfillment_text', None)
        if fulfillment_text:
            fulfillment_text = ast.literal_eval(fulfillment_text)

        # custom payloads and text
        payload = {"messages":
                   custy_payloads +
                   [{'text': {'text': fulfillment_text}}]
                   }

        payload_json = json.dumps(payload)
        payload_json = json.dumps(payload)
        fulfillment = types.Fulfillment.from_json(payload_json)

        #parameter - presets
        set_param_actions = []
        parameter_presets = route_dict.get('parameter_presets', None)
        if parameter_presets:
            parameter_presets = json.loads(parameter_presets)
            for param in parameter_presets.keys():
                set_param_action = types.Fulfillment.SetParameterAction()
                set_param_action.parameter = param
                set_param_action.value = parameter_presets[param]
                set_param_actions.append(set_param_action)
        fulfillment.set_parameter_actions = set_param_actions
        transitionRoute.trigger_fulfillment = fulfillment

        return transitionRoute

    def bulk_create_route_group_from_dataframe(
            self,
            display_name,
            agent_id,
            flow_id,
            route_group_df,
            update_flag=False):
        '''
         create transition route - no support for end_session yet just end flow.

            Args:
                display_name: name for the route group
                agent_id: agent id of target agent
                flow_id: flow id where to create route group
                route_group_df: dataframe with a routes data
                    intent: intent id
                    condition: string condition. ex. $session.params.dtmf_diy_opt_in = 1 AND $session.params.dtmf_2_techinternet = 2
                    target_page: page id
                    target_flow: flow id
                    webhook: webhook id
                    webhook_tag: string webhook tag
                    custom_payload: a singular payload or list of payloads ex. [{}, {}]
                    fullfillment_text: = list of text ["yo", "hi"]
                    parameter_presets: = dictionary of parameter presets ex. {"param1":"value","param2":"othervalues"}
                update_flag: True to create the route group in the provided flow id

            Returns:
                rg: route group protobuf
        '''
        if 'intent' in route_group_df.columns:
            intentsMap = self.intents.get_intents_map(
                agent_id=agent_id, reverse=True)
            route_group_df['intent'] = route_group_df.apply(
                lambda x: intentsMap[x['intent']], axis=1)

        if 'target_flow' in route_group_df.columns:
            flowsMap = self.flows.get_flows_map(
                agent_id=agent_id, reverse=True)
            route_group_df['target_flow'] = route_group_df.apply(
                lambda x: flowsMap[x['target_flow']], axis=1)

        if 'target_page' in route_group_df.columns:
            pageMap = self.pages.get_pages_map(flow_id=flow_id, reverse=True)
            pageMap['End Flow'] = flow_id + '/pages/END_FLOW'
            route_group_df['target_page'] = route_group_df.apply(
                lambda x: pageMap[x['target_page']], axis=1)

        transition_routes = []
        for index, row in route_group_df.iterrows():
            transition_route = self.create_transition_route_from_dataframe(row)
            transition_routes.append(transition_route)

        rg = types.TransitionRouteGroup()
        rg.display_name = display_name
        rg.transition_routes = transition_routes

        if update_flag:
            self.route_groups.create_transition_route_group(
                flow_id=flow_id, obj=rg)
        return rg

    def intent_to_df(self, intent_id):
        i_obj = self.intents.get_intent(intent_id=intent_id)
        tps = i_obj.training_phrases
        tp_df = pd.DataFrame()
        tp_id = 0
        for tp in tps:
            part_id = 0
            for part in tp.parts:
                tp_df = tp_df.append(
                    pd.DataFrame(
                        columns=[
                            'display_name',
                            'name',
                            'tp_id',
                            'part_id',
                            'text',
                            'parameter_id',
                            'repeat_count',
                            'id'],
                        data=[
                            [
                                i_obj.display_name,
                                intent_id,
                                tp_id,
                                part_id,
                                part.text,
                                part.parameter_id,
                                tp.repeat_count,
                                tp.id]]))
                part_id += 1
            tp_id += 1

        phrases = tp_df.copy()

        phrase_lst = phrases.groupby(
            ['tp_id'])['text'].apply(
            lambda x: ''.join(x)).reset_index().rename(
            columns={
                'text': 'phrase'})
        phrases = pd.merge(phrases, phrase_lst, on=['tp_id'], how='outer')

        return phrases
