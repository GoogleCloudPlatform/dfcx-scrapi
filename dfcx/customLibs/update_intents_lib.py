#!/usr/bin/env python
# coding: utf-8

# In[11]:


from nltk.tokenize import wordpunct_tokenize, WhitespaceTokenizer,word_tokenize
import itertools
import pandas as pd
import string as string_pckg
import re
import numpy as np
from spellchecker import SpellChecker
#


# In[35]:


class maniupulators:
    def __init__(self):
        return
    
    #lambda functions
    #
    def mutated_rmv_tp(self,display_name,op_seq,edited_intents ,op):
        op_seq = list(op_seq)
        if display_name in edited_intents:
            op_seq.append(op)
            return op_seq
        else:
            return op_seq
    #
    def mutated(self,text, new_text,op_seq, op):
        op_seq = list(op_seq)
        if text.lower() != new_text.lower():
            op_seq.append(op)
            return op_seq
        else:
            return op_seq
        
    #
    def mutated_int_dis(self,op_seq, op):
        op_seq = list(op_seq)
        op_seq.append(op)
        return op_seq

    #
    def initial_cleanup(self,input_txt):
        if input_txt.split():
            return self.white_space_punc_tokenizer(input_txt)
        else:
            return input_txt
    #
    def remove_verbage(self,update_if_entity,input_txt, parameter_id, verbage_list):
        if input_txt.split():
            text_ = self.white_space_punc_tokenizer(input_txt)
        else:
            text_ = input_txt

        if update_if_entity:
            param_id = [True,False]
        else:
            param_id = [True]

        if pd.isnull(parameter_id) in param_id:
            updated_text = [i for i in text_ if i not in verbage_list]
            if len(updated_text) != len(text_) and len(updated_text)>0:
                while True:
                    if any([item in updated_text[0] for item in ['?','!','.',',']]):
                        updated_text = updated_text[1:]
                        if len(updated_text)<1:
                            break
                    else:
                        break

            return ''.join(updated_text)
        else:
            return ''.join(text_)
        
        
    #
    def spell_check_phrase(self,update_if_entity,input_txt, parameter_id, spell = SpellChecker()):
        if input_txt.split():
            tokenized_sent = self.white_space_punc_tokenizer(input_txt)
            words = word_tokenize(input_txt)
        else:
            tokenized_sent = input_txt
            words = input_txt

        if update_if_entity:
            param_id = [True,False]
        else:
            param_id = [True]

        if pd.isnull(parameter_id) in param_id:
            misspelled = spell.unknown(words)
            for word in misspelled:
                correct_spelling = spell.correction(word)
                replacements = {word: correct_spelling}
                tokenized_sent = [replacements.get(x, x) for x in tokenized_sent]
            return ''.join(tokenized_sent)
        else:
            return ''.join(tokenized_sent)

        #
    def the_swap(self,update_if_entity,input_text, parameter_id, swaps):
        if update_if_entity:
            param_id = [True,False]
        else:
            param_id = [True]

        if pd.isnull(parameter_id) in param_id:
            for key in swaps:
                text_ = input_text.replace(key,swaps[key]['updated'])
            return text_
        else:
            return input_text


        
        
        
        
        
    '''
    ***The white space punc tokenizer function removes tokens such as \n and from a training phrase. It is responsible for the general cleanup. ***
    '''
    def white_space_punc_tokenizer(self,s):
        s = s.lower()
        if s[0] == ' ':
            front_space = True
        else:
            front_space = False
        if s[-1] == ' ':
            backspace = True
        else:
            backspace = False

        ll = [[wordpunct_tokenize(w), ' '] for w in s.split()]
        tokenized_spaces = list(itertools.chain(*list(itertools.chain(*ll))))

        if tokenized_spaces[0] == ' ' and front_space == False:
            tokenized_spaces = tokenized_spaces[1:]
        elif tokenized_spaces[0] != ' ' and front_space == True:
            tokenized_spaces = [' '] + tokenized_spaces

        if tokenized_spaces[-1] == ' ' and backspace == False:
            tokenized_spaces = tokenized_spaces[:-1]
        elif tokenized_spaces[-1] != ' ' and backspace == True:
            tokenized_spaces = tokenized_spaces + [' ']
        return tokenized_spaces
    
    
    
    '''
    ***The rmv tp spec intent function removes exact match trianing phrases from a specific intent ***
    '''
    def rmv_tp_spec_intent(self, training_phrase_data, params):
        removal_path = params.get('removal_path',None)
        rmv_obj = params.get('rmv_obj',None)
        op = params.get('op_seq')
        store_removals_path = params.get('store_removals_path', False)
        store_not_found_path = params.get('store_not_found_path', False)

        if removal_path:
            removals_df = pd.read_csv(removal_path)
            removals_df = removals_df[['display_name','phrase']]
            removals_df['phrase'] = removals_df.apply(lambda x: x['phrase'].strip().lower(),axis=1)
            removals_df['remove'] = True
            
        if rmv_obj:
            removals_df = pd.DataFrame()
            for key in rmv_obj.keys():
                iter_frame = pd.DataFrame()
                iter_frame['phrase'] = rmv_obj[key]
                iter_frame.insert(0,'display_name', key)
                iter_frame['phrase'] = iter_frame.apply(lambda x: x['phrase'].strip().lower(),axis=1)
                removals_df = removals_df.append(iter_frame)
            removals_df['remove'] = True
        
        removals_df['phrase'] = removals_df.apply(lambda x: x['phrase'].replace('\n','').replace('\t','').replace('\r',''),axis=1)
        
        phrases = training_phrase_data.copy()
        phrases['text'] = phrases.apply(lambda x: x['text'].strip().lower(),axis=1)
        phrases = phrases.groupby(['name','display_name','training_phrase'])['text'].apply(list).reset_index()
        phrases['phrase'] = phrases.apply(lambda x: ''.join(x['text']),axis=1)
        phrases = phrases.drop(columns='text')

        analysis_df = pd.merge(phrases,removals_df, on=['display_name','phrase'],how='outer')
        removals_df = analysis_df[(~analysis_df['name'].isna()) & (analysis_df['remove']==True)]
        not_found = analysis_df[analysis_df['name'].isna()].reset_index(drop=True)
        
        if store_removals_path:
            removals_df.to_csv(store_removals_path)
        if store_not_found_path:
            not_found.to_csv(store_not_found_path)

        remove_parts = removals_df[['name','training_phrase']]
        remove_parts.insert(2, 'remove',True)
        by_part = pd.merge(training_phrase_data, remove_parts,on=['name', 'training_phrase'],how='outer')
        by_part = by_part[by_part['remove']!=True].reset_index(drop=True)
        op_seq = by_part.apply(lambda x: self.mutated_rmv_tp(display_name=x['display_name'],
                                                   op_seq=x['op_seq'], edited_intents=list(set(removals_df['display_name'])), op=op),axis=1)
        by_part['op_seq'] = op_seq
        new_data_set = by_part[['name','display_name', 'training_phrase','part','parameter_id','original','op_seq','text','repeat_count','training_phrase_id']]
        return new_data_set

    
    
    '''
    ***The remove words from intents function removes specific strings from training phrases within certain intents and replaces them with blank***
    Auto performs generic cleanup but will not tag gcu
    '''
        #Dont split by spaces do tokenizing
    def remove_specific_words(self,training_phrase_data, params):
        intents_subset=params.get('intents_subset',[])
        verbage_list=params.get('verbage_list',[])
        intent_exceptions = params.get('intent_exceptions',[])
        update_if_entity=params.get('update_if_entity',False)
        op_seq = params.get('op_seq')

        if intents_subset:
            mutable_data = training_phrase_data[training_phrase_data['display_name'].isin(intents_subset)]
        else:
            mutable_data = training_phrase_data.copy()
        if intent_exceptions:
            mutable_data = mutable_data[~mutable_data['display_name'].isin(intent_exceptions)]
        mutable_data = mutable_data.reset_index(drop=True)
        unmutable_data = training_phrase_data[~training_phrase_data['display_name'].isin(list(set(mutable_data['display_name'])))]
        unmutable_data = unmutable_data.reset_index(drop=True)
        mutable_data['check_txt'] = mutable_data.apply(lambda x: self.initial_cleanup(x['text']),axis=1)
        mutable_data['check_txt'] = mutable_data.apply(lambda x: ''.join(x['check_txt']),axis=1)
        mutated_text = mutable_data.apply(lambda x: self.remove_verbage(update_if_entity=update_if_entity, input_txt=x['text'],parameter_id=x['parameter_id'],verbage_list=verbage_list),axis=1)
        mutated_data = mutable_data.copy()
        mutated_data['new_text'] = mutated_text
        op_seq_ = mutated_data.apply(lambda x: self.mutated(x['text'],x['new_text'],x['op_seq'], 'gcu'), axis=1)
        mutated_data.loc[:,'op_seq'] = op_seq_
        op_seq_ = mutated_data.apply(lambda x: self.mutated(x['check_txt'],x['new_text'],x['op_seq'], op_seq), axis=1)
        mutated_data.loc[:,'op_seq'] = op_seq_
        mutated_data = mutated_data.drop(columns= ['text','check_txt']).rename(columns={'new_text':'text'})
        mutated_data = mutated_data[['name','display_name', 'training_phrase','part','parameter_id','original','op_seq','text','repeat_count','training_phrase_id']]
        mutated_data['m'] = 1
        unmutable_data['m'] = 0
        new_data_set = mutated_data.append(unmutable_data)
        new_data_set = new_data_set.sort_values(by=['m'],ascending=False).drop_duplicates(subset=['name','training_phrase','part'], keep='first').sort_values(by=['display_name','training_phrase','part'],ascending=True).reset_index(drop=True)
        new_data_set = new_data_set[['name','display_name', 'training_phrase','part','parameter_id','original','op_seq','text','repeat_count','training_phrase_id']]

        return new_data_set  
    

    '''
    ***The spellchecker function autocorrects words***
    '''
    def spell_checker(self,training_phrase_data, params):
        intents_subset=params.get('intents_subset',[])
        intent_exceptions = params.get('intent_exceptions',[])
        update_if_entity=params.get('update_if_entity',False)
        op_seq = params.get('op_seq')

        if intents_subset:
            mutable_data = training_phrase_data[training_phrase_data['display_name'].isin(intents_subset)]
        else:
            mutable_data = training_phrase_data.copy()

        if intent_exceptions:
            mutable_data = mutable_data[~mutable_data['display_name'].isin(intent_exceptions)]
        mutable_data = mutable_data.reset_index(drop=True)
        unmutable_data = training_phrase_data[~training_phrase_data['display_name'].isin(list(set(mutable_data['display_name'])))]
        unmutable_data = unmutable_data.reset_index(drop=True)
        mutated_text = mutable_data.apply(lambda x: self.spell_check_phrase(update_if_entity=update_if_entity, input_txt=x['text'],parameter_id=x['parameter_id']),axis=1)
        mutated_data = mutable_data.copy()
        mutated_data['new_text'] = mutated_text
        op_seq = mutated_data.apply(lambda x: self.mutated(x['text'],x['new_text'],x['op_seq'], op_seq), axis=1)
        mutated_data['op_seq'] = op_seq
        mutated_data = mutated_data.drop(columns= ['text']).rename(columns={'new_text':'text'})
        mutated_data = mutated_data[['name','display_name', 'training_phrase','part','parameter_id','original','op_seq','text','repeat_count','training_phrase_id']]

        mutated_data['m'] = 1
        unmutable_data['m'] = 0
        new_data_set = mutated_data.append(unmutable_data)
        new_data_set = new_data_set.sort_values(by=['m'],ascending=False).drop_duplicates(subset=['name','training_phrase','part'], keep='first').sort_values(by=['display_name','training_phrase','part'],ascending=True).reset_index(drop=True)
        new_data_set = new_data_set[['name','display_name', 'training_phrase','part','parameter_id','original','op_seq','text','repeat_count','training_phrase_id']]
        return new_data_set   

        
        
    '''
    ***The Swap function takes exact strings and replaces them with other exact strings***
    '''
    def swap(self,training_phrase_data, params):
        intents_subset = params.get('intents_subset')
        swaps = params.get('swaps')
        swapspath = params.get('swapspath')
        intent_exceptions = params.get('intent_exceptions')
        update_if_entity = params.get('update_if_entity')
        op_seq = params.get('op_seq')
        if intents_subset:
            mutable_data = training_phrase_data[training_phrase_data['display_name'].isin(intents_subset)]
        else:
            mutable_data = training_phrase_data.copy()

        if intent_exceptions:
            mutable_data = mutable_data[~mutable_data['display_name'].isin(intent_exceptions)]
        mutable_data = mutable_data.reset_index(drop=True)
        unmutable_data = training_phrase_data[~training_phrase_data['display_name'].isin(list(set(mutable_data['display_name'])))]
        unmutable_data = unmutable_data.reset_index(drop=True)
        if swapspath:
            swaps = pd.read_csv(swapspath)
            swaps.columns.values[0] = "original"
            swaps.columns.values[1] = "updated"
            swaps = swaps.drop_duplicates(subset='original')
            swaps = swaps.set_index('original')
            swaps = swaps.to_dict('index')

        mutated_text = mutable_data.apply(lambda x: self.the_swap(update_if_entity=update_if_entity, input_text=x['text'],parameter_id=x['parameter_id'],swaps=swaps),axis=1)
        mutated_data = mutable_data.copy()
        mutated_data['new_text'] = mutated_text
        op_seq = mutated_data.apply(lambda x: self.mutated(x['text'],x['new_text'],x['op_seq'], op_seq), axis=1)
        mutated_data['op_seq'] = op_seq
        mutated_data = mutated_data.drop(columns= ['text']).rename(columns={'new_text':'text'})
        mutated_data = mutated_data[['name','display_name', 'training_phrase','part','parameter_id','original','op_seq','text','repeat_count','training_phrase_id']]
        mutated_data['m'] = 1
        unmutable_data['m'] = 0
        new_data_set = mutated_data.append(unmutable_data)
        new_data_set = new_data_set.sort_values(by=['m'],ascending=False).drop_duplicates(subset=['name','training_phrase','part'], keep='first').sort_values(by=['display_name','training_phrase','part'],ascending=True).reset_index(drop=True)
        new_data_set = new_data_set[['name','display_name', 'training_phrase','part','parameter_id','original','op_seq','text','repeat_count','training_phrase_id']]
        return new_data_set   
    
    
    
    '''
    *** The intent disambiguation function moves exact trianing phrases from one intent to another***
    '''
    def intent_disambiguation(self,training_phrase_data, parameter_data, params):
        '''Future improvement is to allow user to carry over entities or not. '''
        op_seq = params.get('op_seq')
        id_data_path = params.get('id_path', '')
        phrases = training_phrase_data.groupby(['name','display_name','training_phrase'])['text'].apply(list).reset_index()
        phrases['text'] = phrases.apply(lambda x: ''.join(x['text']),axis=1)
        phrases['text'] = phrases.apply(lambda x: x['text'].strip().lower(),axis=1)
        
        try:
            id_data = pd.read_csv(id_data_path)
        except:
            raise ValueError('path provided does not exist or contains a corrupt file')
        id_data['training_phrase'] = id_data.apply(lambda x: x['training_phrase'].strip().lower(),axis=1)
        id_data['training_phrase'] = id_data.apply(lambda x: x['training_phrase'].replace('\n','').replace('\t','').replace('\r',''),axis=1)
        
        granular = id_data[id_data['source_intent']!='all'].rename(columns={'source_intent':'display_name','training_phrase':'text'})
        all_ = id_data[id_data['source_intent']=='all'].rename(columns={'training_phrase':'text'}).drop(columns='source_intent')
        update_granular = pd.merge(phrases, granular, on=['display_name','text'],how='left')
        update_granular = update_granular[~update_granular['destination_intent'].isna()]
        update_all = pd.merge(phrases, all_, on=['text'],how='left') 
        update_all = update_all[~update_all['destination_intent'].isna()]
        update_all = update_all[update_all['display_name']!= update_all['destination_intent']]
        update = update_granular.append(update_all)
        
        destination_name_merger = training_phrase_data[['name','display_name']].drop_duplicates().rename(columns={'name':'destination_name', 'display_name':'destination_intent'})
        update = pd.merge(update, destination_name_merger, on='destination_intent', how='inner')
        

        
        update = update.drop(columns='text')
        update_intents_lst = list(set(list(update['name']) + list(update['destination_name'])))
        #update parameters 
        additional_parameters = pd.DataFrame()
        for index, row in update.iterrows():
            source_intent = row['name']
            source_params = parameter_data[(parameter_data['name']==source_intent) & (~(parameter_data['id'].isna()))]
            if len(source_params) > 0:
                for index_, row_ in source_params.iterrows():
                    if row_['entity_type'] not in (list(set(parameter_data[parameter_data['name']==row['destination_name']]['entity_type']))):
                        row_['name'] = row['destination_name']
                        row_['display_name'] = row['destination_intent']
                        addt  = pd.DataFrame(row_).transpose()
                        additional_parameters = additional_parameters.append(addt)
        
        parameter_data = parameter_data.append(additional_parameters)
        new_tps = pd.merge(training_phrase_data, update, on=['name','display_name','training_phrase'],how='left')
        new_tps['name'] = new_tps.apply(lambda x: x['name'] if pd.isna(x['destination_name']) else x['destination_name'],axis=1)
        new_tps['display_name'] = new_tps.apply(lambda x: x['display_name'] if pd.isna(x['destination_intent']) else x['destination_intent'],axis=1)
        updated_intents = list(set(new_tps[~new_tps['destination_intent'].isna()]['display_name']))
        new_tps = new_tps.drop(columns=['destination_intent', 'destination_name'])
        
        
        #reset tp_numbers
        re_indexed_new_tp = new_tps.copy()
        for intent in update_intents_lst:
            df_i = re_indexed_new_tp[re_indexed_new_tp['name']==intent].sort_index().reset_index(drop=True)
            re_indexed_new_tp = re_indexed_new_tp[re_indexed_new_tp['name']!=intent]
            tp_index = 0
            tp_indexes = []
            for index, row in df_i.iterrows():
                if row['part'] == float(0) and index != 0:
                    tp_index +=1
                tp_indexes.append(tp_index)

            df_i['training_phrase'] = tp_indexes
            df_i['op_seq'] = df_i.apply(lambda x: self.mutated_int_dis(x['op_seq'],op_seq),axis=1)
            re_indexed_new_tp = re_indexed_new_tp.append(df_i)
        return re_indexed_new_tp,parameter_data

    
    
    


# In[ ]:






# In[ ]:





# In[ ]:





# In[ ]:




