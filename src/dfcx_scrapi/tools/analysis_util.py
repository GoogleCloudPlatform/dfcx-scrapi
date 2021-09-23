"""Util class for performing analysis on DFCX objects and data."""

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
import pandas
import numpy as np
from typing import Union
from dfcx_scrapi.core.intents import Intents
import google.cloud.dialogflowcx_v3beta1.types as types

# logging config
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S")

class AnalysisUtil():
    """Utils class for performing analysis on DFCX data."""

    @staticmethod
    def __levenshtein_ratio(s: str, t: str) -> float:
        """ levenshtein_ratio_and_distance:
            Calculates levenshtein distance between two strings.
        """
        rows = len(s)+1
        cols = len(t)+1
        distance = np.zeros((rows,cols),dtype = int)

        for i in range(1, rows):
            for k in range(1,cols):
                distance[i][0] = i
                distance[0][k] = k

        for col in range(1, cols):
            for row in range(1, rows):
                if s[row-1] == t[col-1]:
                    cost = 0
                else:
                    cost = 2

                distance[row][col] =  min(
                    distance[row-1][col] + 1,
                    distance[row][col-1] + 1,
                    distance[row-1][col-1] + cost
                )

        # Computation of the Levenshtein Distance Ratio
        ratio = ((len(s)+len(t)) - distance[row][col]) / (len(s)+len(t))
        return ratio


    @staticmethod
    def calc_tp_distances(
        intent_key: Union[types.Intent, pandas.core.frame.DataFrame],
        intent_comparator: Union[types.Intent, pandas.core.frame.DataFrame],
        threshold: float = 0.75,
        silent: bool = False
    ):
        """
        compares the training phrases between two intents to find the
        levenshtein distance between all training phrases. Structure of the
        returned object depends on which intent is the key, and which is the
        comparator.

        Args:
          intent_key: intent protobuf or dataframe object. In the returned
          object, the utterances of this intent are paired with a list of
          utterances from the comparator.

          intent_comparator: intent protobuf or dataframe object. In the
          returned object, the utterances of this intent will be included
          in a list associated with every phrase whose similarity ratio
          is above the defined threshold.

          threshold: float describing the levenshtein distance above which
          a pair of phrases should be associated. Default: .75

          silent: When set to True, the program will execute without
          creating Info logs or updating the progress on the console.
          Default=False

        Returns:
          Dict containing two major parts. The first ("stats") contains
          statistics surrounding the outcome of the execution.
          The second ("distances") is a list of pairings, with phrases
          from intent_key as the key, and utterance from intent_comparator
          with a similarity ratio above the defined threshold as the value.
        """

        if isinstance(intent_key, types.Intent):
            list_keys = Intents.intent_proto_to_dataframe(
                intent_key
            ).tp
        elif isinstance(intent_key, pandas.core.frame.DataFrame):
            list_keys = intent_key.tp
        else:
            logging.warning(
                """parameter list_keys must be of type
                dialogflowcx_v3beta1.types.intent.Intent
                or pandas.core.frame.DataFrame.
                """)
            return None

        if isinstance(intent_comparator, types.Intent):
            list_comparators = Intents.intent_proto_to_dataframe(
                intent_comparator
            ).tp
        elif isinstance(intent_comparator, pandas.core.frame.DataFrame):
            list_comparators = intent_comparator.tp
        else:
            logging.warning(
                """parameter intent_comparator must be of type
                dialogflowcx_v3beta1.types.intent.Intent
                or pandas.core.frame.DataFrame.
                """)
            return None

        it = 0
        completed = 0.0
        tp_distances = {}
        num_keys_overlapped = 0
        num_comparators_overlapped = 0

        for line1 in list_keys:

            phrase_similarity_list = {}
            found_key_similarity = False

            if not silent:
                completed = float(it/len(list_keys))*100.0
                #print instead of logging.info is intentional.
                #Needed to avoid spamming new lines with every percentile.
                print(
                    " {}% complete. \r".format(round(completed,1)),
                    end="",
                    flush=True
                     )

            for line2 in list_comparators:

                distance = AnalysisUtil.__levenshtein_ratio(
                    line1,
                    line2
                )

                if distance>threshold:
                    phrase_similarity_list[line2] = round(distance,3)
                    num_comparators_overlapped += 1

                    if found_key_similarity is False:
                        num_keys_overlapped += 1
                        found_key_similarity = True


            it += 1

            #float greatest similarities to top
            phrase_similarity_list = dict(sorted(
                phrase_similarity_list.items(),
                key=lambda item: item[1],
                reverse=True,))

            tp_distances[line1] = phrase_similarity_list

        #calculate statistics
        total_keys = len(list_keys)
        key_percent_overlap = 100*num_keys_overlapped/total_keys
        key_percent_overlap = round(key_percent_overlap, 3)

        total_comps = len(list_comparators)*total_keys
        comp_percent_overlap = 100*num_comparators_overlapped/total_comps
        comp_percent_overlap = round(comp_percent_overlap, 3)

        stats = {"keys":{
                    "total:":total_keys,
                    "num_overlap":num_keys_overlapped,
                    "percent_overlap":"{}%".format(key_percent_overlap)
                    },
                 "comparators":{
                    "total:":total_comps,
                    "num_overlap":num_comparators_overlapped,
                    "percent_overlap":"{}%".format(comp_percent_overlap)
                    }
                }

        if not silent:
            #print instead of logging.info intentional.
            print("100% -- Done.      ", flush=True)
            print("")
            logging.info("Statistics:\n%s", stats)

        results = {"stats":stats,"distances":tp_distances}
        return results
