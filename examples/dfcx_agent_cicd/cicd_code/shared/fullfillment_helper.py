""" Helper functions for en vs lang"""

from google.cloud.dialogflowcx_v3beta1.services import pages
from google.cloud.dialogflowcx_v3beta1.types import page as gcdc_page

from dfcx_scrapi.core.pages import Pages


class PagesChild(Pages):
    """
    Iterates over the pages object to get the fullfillment details
    """
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



def get_entry_ff(page=None,page_id=None,language_code='en'):
    """
    Returns entry fullfillments stats
    """
    if not page:
        pagesobj=PagesChild()
        page=pagesobj.get_page(page_id=page_id,language_code=language_code)

    payloadc=0
    textc=0
    for i in page.entry_fulfillment.messages:
        try:
            temp=len(i.payload.items())
            payloadc=payloadc+temp
        except Exception:
            pass
        try:
            temp=len(i.text.text)
            textc=textc+temp
        except Exception:
            pass

    return payloadc,textc

def get_param_ff(param=None,page_id=None,idx=None,language_code='en'):
    """
    Returns params fullfillments stats
    """
    if not param:
        pagesobj=PagesChild()
        page=pagesobj.get_page(page_id=page_id,language_code=language_code)
        param=page.form.parameters[idx]
    payloadc=0
    textc=0
    for message in param.fill_behavior.initial_prompt_fulfillment.messages:
        try:
            temp=len(message.payload.items())
            payloadc=payloadc+temp
        except Exception:
            pass
        try:
            temp=len(message.text.text)
            textc=textc+temp
        except Exception:
            pass

    return payloadc,textc

def get_route_ff(route=None,page_id=None,idx=None,language_code='en'):
    """
    Returns route fullfillments stats
    """
    if not route:
        pagesobj=PagesChild()
        page=pagesobj.get_page(page_id=page_id,language_code=language_code)
        route=page.transition_routes[idx]
    payloadc=0
    textc=0
    for i in route.trigger_fulfillment.messages:
        try:
            temp=len(i.payload.items())
            payloadc=payloadc+temp
        except Exception:
            pass
        try:
            temp=len(i.text.text)
            textc=textc+temp
        except Exception:
            pass


    return payloadc,textc
