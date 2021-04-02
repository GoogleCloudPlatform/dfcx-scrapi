'''build funcs around intent'''

import logging

from typing import List


def build_intent(display_name, phrases: List[str]):
    '''build an intent from list of phrases plus meta'''
    tps = {
        'text': row['text'] for row in phrases
    }
    intent = {
        'display_name': display_name,
        'training_phrases': tps
    }
    logging.info('intent %s', intent)
    return intent
