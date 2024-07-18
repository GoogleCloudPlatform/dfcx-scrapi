

def getEntryff(page=None,page_id=None,language_code='en'):
    if not page:
        from enVsOtherLang import Pageschild
        pagesobj=Pageschild()
        page=pagesobj.get_page(page_id=page_id,language_code=language_code)

    payloadc=0
    textc=0
    for i in page.entry_fulfillment.messages:
        try:
            temp=len(i.payload.items())
            payloadc=payloadc+temp
        except Exception as e:
            pass
        try:
            temp=len(i.text.text)
            textc=textc+temp
        except Exception as e:
            pass

    return payloadc,textc

def getParamff(param=None,page_id=None,idx=None,language_code='en'):
    if not param:
        from enVsOtherLang import Pageschild
        pagesobj=Pageschild()
        page=pagesobj.get_page(page_id=page_id,language_code=language_code)
        param=page.form.parameters[idx]
    payloadc=0
    textc=0
    for message in param.fill_behavior.initial_prompt_fulfillment.messages:
        try:
            temp=len(message.payload.items())
            payloadc=payloadc+temp
        except Exception as e:
            pass
        try:
            temp=len(message.text.text)
            textc=textc+temp
        except Exception as e:
            pass

    return payloadc,textc

def getRouteff(route=None,page_id=None,idx=None,language_code='en'):
    if not route:
        from enVsOtherLang import Pageschild
        pagesobj=Pageschild()
        page=pagesobj.get_page(page_id=page_id,language_code=language_code)
        route=page.transition_routes[idx]
    payloadc=0
    textc=0
    for i in route.trigger_fulfillment.messages:
        try:
            temp=len(i.payload.items())
            payloadc=payloadc+temp
        except Exception as e:
            pass
        try:
            temp=len(i.text.text)
            textc=textc+temp
        except Exception as e:
            pass


    return payloadc,textc