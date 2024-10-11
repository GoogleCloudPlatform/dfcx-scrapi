""" Compare the fullfillments of en vs french langauge or etc"""
from dfcx_scrapi.core.flows import Flows

import pandas as pd

from .fullfillment_helper import get_entry_ff,get_param_ff,get_route_ff
from .fullfillment_helper import PagesChild

def en_vs_lang(agent_id,flows,lang):
    """Compares fulfillment coverage between English and a specified language.

    This function analyzes the fulfillment configurations (entry fulfillments, 
    parameter fulfillments, and route fulfillments) for a given Dialogflow CX agent
    and a set of flows. It compares the coverage of the specified language (`lang`)
    with the English language ('en'), generating dataframes that highlight any
    discrepancies in fulfillment setup.

    Args:
        agent_id: The ID of the Dialogflow CX agent.
        flows: A list of flow display names to analyze.
        lang: The language code to compare against English (e.g., 'fr-ca').

    Returns:
        A tuple containing:
        - entry_df: DataFrame with statistics on entry fulfillment coverage.
        - param_df: DataFrame with statistics on parameter fulfillment coverage.
        - route_df: DataFrame with statistics on route fulfillment coverage.
        - result: A boolean indicating if all elements have agent responses 
        in the specified language.
    """
    entry_columns = ['flow','page', 'text_entry_en', f'text_entry_{lang}',
                     'payload_entry_en', f'payload_entry_{lang}']
    entry_df = pd.DataFrame(columns=entry_columns)
    params_columns =['flow','page','parameter','text_param_en',
                     f'text_param_{lang}','payload_param_en',
                     f'payload_param_{lang}']
    param_df = pd.DataFrame(columns=params_columns)
    route_columns=['flow','page','route','text_route_en',
                   f'text_route_{lang}', 'payload_route_en',
                   f'payload_route_{lang}']
    route_df = pd.DataFrame(columns=route_columns)
    flowobj=Flows()
    pagesobj=PagesChild()
    for flow in flows:
        flow_details=flowobj.get_flow_by_display_name(display_name=flow,
                                               agent_id=agent_id)
        flow_id=flow_details.name
        pages_list=pagesobj.list_pages(flow_id=flow_id)

        for page in pages_list:
            page_name=page.display_name
            p_entry_en=0
            t_entry_en=0
            #getting entry fullfillment details
            p_entry_en,t_entry_en=get_entry_ff(page=page,language_code='en')

            if p_entry_en >0 or t_entry_en >0:
                p_entry_lang,t_entry_lang=get_entry_ff(
                    page_id=page.name,
                    language_code=lang)
                new_row = pd.DataFrame({
                    'flow': [flow],
                    'page': [page_name],
                    'text_entry_en':[t_entry_en] ,
                    f'text_entry_{lang}': [t_entry_lang],
                    'payload_entry_en':[p_entry_en],
                    f'payload_entry_{lang}': [p_entry_lang]
                    })
                entry_df = pd.concat([entry_df, new_row], ignore_index=True)

            #getting fullfillemnt in Parameters
            for idx,param in enumerate(page.form.parameters):
                param_name=param.display_name
                p_param_en,t_param_en=get_param_ff(param=param,language_code='en')
                if p_param_en> 0 or t_param_en >0:
                    p_param_lang,t_param_lang=get_param_ff(page_id=page.name,
                                                           idx=idx,
                                                           language_code='fr-ca')

                    new_row = pd.DataFrame({
                        'flow': [flow],
                        'page': [page_name],
                        'parameter' : [param_name],
                        'text_param_en':[t_param_en] ,
                        f'text_param_{lang}': [t_param_lang],
                        'payload_param_en':[p_param_en],
                        f'payload_param_{lang}': [p_param_lang]
                        })
                    param_df = pd.concat([param_df, new_row], ignore_index=True)

            #getting fullfillment details in page routes
            for idx,route in enumerate(page.transition_routes):
                route_name=route.name
                p_route_en,t_route_en=get_route_ff(route=route,language_code='en')
                if p_route_en>0 or t_route_en>0:
                    p_route_lang,t_route_lang=get_route_ff(page_id=page.name,
                                                           idx=idx,
                                                           language_code='fr-ca')

                    new_row = pd.DataFrame({
                        'flow': [flow],
                        'page': [page_name],
                        'route' : [route_name],
                        'text_route_en':[t_route_en] ,
                        f'text_route_{lang}': [t_route_lang],
                        'payload_route_en':[p_route_en],
                        f'payload_route_{lang}': [p_route_lang]
                        })
                    route_df=pd.concat([route_df, new_row],
                                         ignore_index=True)
    condition1 = (
        (entry_df.iloc[:, 2] != entry_df.iloc[:, 3]) |
        (entry_df.iloc[:, 4] != entry_df.iloc[:, 5])
    )
    condition2 = (
        (param_df.iloc[:, 3] != param_df.iloc[:, 4]) |
        (param_df.iloc[:, 5] != param_df.iloc[:, 6])
    )
    condition3 =(
        (route_df.iloc[:, 3] != route_df.iloc[:, 4]) |
        (route_df.iloc[:, 5] != route_df.iloc[:, 6])
    )

    result1 = entry_df[condition1]
    result2 = param_df[condition2]
    result3 = route_df[condition3]
    if result1.empty and result2.empty and result3.empty:
        result=True
    else:
        result=False

    return entry_df,param_df,route_df,result
