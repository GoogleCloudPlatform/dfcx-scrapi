"""Grouping of semantically similiar utterances.
For best results replace entities with a parameter name ex,
all countries with the word country or all dates with the word date"""

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
import re
import pandas as pd
from sklearn.cluster import DBSCAN
import tensorflow_hub as hub

# logging config
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


logging.info("embedder status: downloading")
embed = hub.load("https://tfhub.dev/google/universal-sentence-encoder/4")
logging.info("embedder status: imported")


class SemanticClustering:
    """Grouping semantically similiar utterances for a variety of tasks:
    - Intent identification
    - Reducing bloated intents
    - no-match patterns

    This class takes a set of utterances and groups them
        according to semantic similarity.
    Similarity is determined based on distance between
        instances in a feature array.

    Attributes:
        phrases: Indicates the utterances to be clustered.
            Need to specify format.
    """

    def __init__(self, phrases: pd.DataFrame):
        """Initializes SemanticClustering with a pandas data frame"""
        if "text" not in phrases.columns:
            raise ValueError("Utterances dataframe must have a text column")
        self.phrases = phrases

    @staticmethod
    def _string_cleaner(string):
        """Clean text by removing tokens, punctuation, and applying lower().
        Args:
            string: text string to be cleaned

        Returns:
            x: cleaned string
        """
        string = re.sub(r"[^\w\s]", "", string.lower())
        tokens = ["\n", "\r", "\t"]
        for token in tokens:
            string = string.replace(token, "")
        return string

    @staticmethod
    def _single_cluster_algo(
        data,
        eps=0.7,
        min_samples=2,
        metric="cosine",
        metric_params: dict = None,
        algorithm="auto",
        leaf_size=30,
        power=None,
        n_jobs=-1,
    ):
        """Cluster phrases using a model with set hyperparameters
        Args:
            data: DataFrame to cluster
            eps: max distance between two points for them to be
                considered in same neighborhood.
            min_samples: minimum number of samples a cluster can have
            metric: metric for measuring distance between instances
                in a feature array.
            metric_params: additional keywords for metric function
            algorithm: algo used to compute pointwise distances and
                find nearest neighbors.
            leaf-size: only passed to BallTree or cKDTree algorithms.
            p: power of Minkowski metric to calculate distance between points.
                DEFAULT = 2 (Euclidean distance)
            n_jobs: number of parallel jobs to run. -1 means all processors

        Returns:
            data: input data with associated clusters by the text column.
        """

        input_data = list(data["cleaned_text"])
        vectors = embed(input_data)
        model = DBSCAN(
            eps=eps,
            min_samples=min_samples,
            metric=metric,
            metric_params=metric_params,
            algorithm=algorithm,
            leaf_size=leaf_size,
            p=power,
            n_jobs=n_jobs,
        ).fit(vectors)
        data["cluster"] = model.labels_
        return data

    def _run_data_pipeline(self):
        clean_data = self.phrases.copy()
        clean_data["text"] = clean_data["text"].astype(str)
        clean_data["cleaned_text"] = clean_data.apply(
            lambda x: self._string_cleaner(x["text"]),
            axis=1,
        )
        self.clean_data = clean_data

    def cluster(
        self,
        stop_threshold: float = 0.5,
        max_rounds=50,
        iterator=0.05,
        min_samples=2,
        start_eps=0.1,
        metric="cosine",
        metric_params: dict = None,
        algorithm="auto",
        leaf_size=30,
        power=None,
        n_jobs=-1,
    ):
        """Cluster phrases using a model with set hyperparameters
            for the entire dataset.

        User can set stop metrics and multiple models will be generated
            with increasing neighborhood sizes.

        Args:
            stop_threshold: Percentage of data which can be in no cluster
                to signify that new models can stop being created.
            max_rounds: maximum number of rounds that take place of
                trying new model hyperparameters to get to the stop_threshold.
            iterator: eps value to change by in each round.
            start_eps: eps value to run on the first algo.
            min_samples: minimum number of samples a cluster can have
            metric: metric for measuring distance between instances
                in a feature array.
            metric_params: additional keywords for metric function
            algorithm: algo used to compute pointwise distances and find
                nearest neighbors.
            leaf-size: only passed to BallTree or cKDTree algorithms.
            p: power of Minkowski metric to calculate distance between points.
                DEFAULT = 2 (Euclidean distance)
            n_jobs: number of parallel jobs to run. -1 means all processors

        Returns:
            clustered: DataFrame of clustered data.
        """

        if not hasattr(self, "transformed_data"):
            self._run_data_pipeline()

        unclustered = self.clean_data
        instances, unclustered_count = (
            len(unclustered),
            len(unclustered),
        )
        clustered = pd.DataFrame()
        eps, max_cluster, cluster_round = (
            start_eps,
            0,
            1,
        )

        while (
            float(unclustered_count) / float(instances)
        ) > stop_threshold and cluster_round < max_rounds:
            cluster_attempt = self._single_cluster_algo(
                unclustered,
                eps=eps,
                min_samples=min_samples,
                metric=metric,
                metric_params=metric_params,
                algorithm=algorithm,
                leaf_size=leaf_size,
                power=power,
                n_jobs=n_jobs,
            )

            clustered_this_round = pd.DataFrame()
            clustered_this_round = cluster_attempt.copy()[
                cluster_attempt["cluster"] != -1
            ]

            if clustered_this_round.empty is False:
                clusters_refactored = clustered_this_round.apply(
                    lambda x: x["cluster"] + max_cluster,
                    axis=1,
                )
                clustered_this_round = clustered_this_round.drop(
                    columns=["cluster"]
                )
                clustered_this_round.insert(
                    0,
                    "cluster",
                    clusters_refactored,
                )
                clustered_this_round.insert(0, "eps", eps)
                clustered_this_round.insert(0, "round", cluster_round)
                clustered = clustered.append(clustered_this_round)
                unclustered = cluster_attempt.copy()[
                    cluster_attempt["cluster"] == -1
                ]
                max_cluster = clustered["cluster"].max() + 1
                unclustered_count = len(unclustered)

            eps += iterator
            cluster_round += 1

            print(
                "round: {0} unclusterd: {1}%\t\t".format(
                    cluster_round,
                    round(
                        float(unclustered_count) / float(instances) * 100,
                        0,
                    ),
                ),
                end="\r",
            )

        if clustered.empty:
            logging.info(
                "no clusters found, try increasing stop_threshold or max_rounds"
            )
            return clustered

        unclustered = unclustered.drop(columns="cluster")
        clustered = clustered.sort_values(by="cluster", ascending=True).append(
            unclustered
        )

        if cluster_round > max_rounds:
            logging.info("max clutering rounds reached before stop threshold")

        return clustered
