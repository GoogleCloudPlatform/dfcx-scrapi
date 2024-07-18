from google.cloud.dialogflowcx_v3beta1.services import pages
from google.cloud.dialogflowcx_v3beta1.types import page as gcdc_page
from dfcx_scrapi.core.agents import Agents
from dfcx_scrapi.core.versions import Versions
from dfcx_scrapi.core.environments import Environments
from dfcx_scrapi.core.flows import Flows
from dfcx_scrapi.core.pages import Pages

from fullfillmentHelper import getEntryff,getParamff,getRouteff

import pandas as pd


class Pageschild(Pages):
  def __init__(self,*args,**kwargs):
    super().__init__(*args,**kwargs)
  
  def get_page(self, page_id,language_code) -> gcdc_page.Page:
      """Get a single CX Page object based on the provided Page ID.

        Args:
          page_id: a properly formatted CX Page ID

        Returns:
          A single CX Page Object
        """
      if not page_id:
          page_id = self.page_id
      request = gcdc_page.GetPageRequest()
      request.name=page_id
      request.language_code = language_code
      client_options = self._set_region(page_id)
      client = pages.PagesClient(
          credentials=self.creds, client_options=client_options
      )

      response = client.get_page(request)

      return response


def enVslang(agent_id,flows,lang):
    entry_columns = ['flow','page', 'text_entry_en', f'text_entry_{lang}', 'payload_entry_en', f'payload_entry_{lang}']
    entry_df = pd.DataFrame(columns=entry_columns)
    params_columns =['flow','page','parameter','text_param_en', f'text_param_{lang}','payload_param_en', f'payload_param_{lang}']
    param_df = pd.DataFrame(columns=params_columns)
    route_columns=['flow','page','route','text_route_en', f'text_route_{lang}', 'payload_route_en', f'payload_route_{lang}']
    route_df = pd.DataFrame(columns=route_columns)
    flowobj=Flows()
    pagesobj=Pageschild()
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
            p_entry_en,t_entry_en=getEntryff(page=page,language_code='en')
    
            if p_entry_en >0 or t_entry_en >0:
                p_entry_lang,t_entry_lang=getEntryff(page_id=page.name,language_code=lang)
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
                p_param_en,t_param_en=getParamff(param=param,language_code='en')
                if p_param_en> 0 or t_param_en >0:
                    p_param_lang,t_param_lang=getParamff(page_id=page.name,idx=idx,language_code='fr-ca')

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
            payloadc_route_en=0
            textc_route_en=0
            for idx,route in enumerate(page.transition_routes):
                route_name=route.name
                p_route_en,t_route_en=getRouteff(route=route,language_code='en')
                if p_route_en>0 or t_route_en>0:
                    p_route_lang,t_route_lang=getRouteff(page_id=page.name,idx=idx,language_code='fr-ca')

                    new_row = pd.DataFrame({
                        'flow': [flow],
                        'page': [page_name],
                        'route' : [route_name],
                        'text_route_en':[t_route_en] ,
                        f'text_route_{lang}': [t_route_lang],
                        'payload_route_en':[p_route_en],
                        f'payload_route_{lang}': [p_route_lang]
                        })
                    route_df = pd.concat([route_df, new_row], ignore_index=True)
    condition1 = (entry_df.iloc[:, 2] != entry_df.iloc[:, 3]) | (entry_df.iloc[:, 4] != entry_df.iloc[:, 5])
    condition2 = (param_df.iloc[:, 3] != param_df.iloc[:, 4]) | (param_df.iloc[:, 5] != param_df.iloc[:, 6])
    condition3 = (route_df.iloc[:, 3] != route_df.iloc[:, 4]) | (route_df.iloc[:, 5] != route_df.iloc[:, 6])

    result1 = entry_df[condition1]
    result2 = param_df[condition2]
    result3 = route_df[condition3]
    
    if result1.empty and result2.empty and result3.empty:
        result=True
    else:
        result=False

    return entry_df,param_df,route_df,result














            








