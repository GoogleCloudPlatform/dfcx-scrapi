from dfcx_scrapi.core.webhooks import Webhooks
import logging
import re

# logging config
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
web=Webhooks()

def updatewebhook(agent_id,env):
    weblist=web.list_webhooks(agent_id=agent_id)
    logging.info("got the webhooklist")

    for webhook in weblist:
        currenturi=webhook.generic_web_service.uri
        pattern = re.compile(r'\bdev\b')
        updateduri=re.sub(pattern, env, currenturi)
        webhook.generic_web_service.uri=updateduri
        kwargs={"generic_web_service":webhook.generic_web_service}
        web.update_webhook(webhook_id=webhook.name,webhook_obj=webhook,**kwargs)
    logging.info(f"replaced dev to {env} and updated all the webhook urls")