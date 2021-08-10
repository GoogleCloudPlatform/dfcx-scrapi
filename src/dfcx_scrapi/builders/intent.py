"""A set of builder methods to create CX proto resource objects"""

# Copyright 2021 Google LLC
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
