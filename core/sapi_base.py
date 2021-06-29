# Copyright 2021 Google LLC. This software is provided as-is, without warranty
# or representation for any use or purpose. Your use of it is subject to your
# agreement with Google.
""" base for other SAPI classes."""

import logging
import json

from google.oauth2 import service_account
from google.auth.transport.requests import Request

from google.protobuf import json_format  # type: ignore

from typing import Dict, List


class SapiBase:
    global_scopes = [
        "https://www.googleapis.com/auth/cloud-platform",
        "https://www.googleapis.com/auth/dialogflow",
    ]

    def __init__(
        self,
        creds_path: str = None,
        creds_dict: Dict = None,
        creds=None,
        scope=False,
        agent_path=None,
    ):

        self.scopes = SapiBase.global_scopes
        if scope:
            self.scopes += scope

        if creds:
            self.creds = creds

        elif creds_path:
            self.creds = service_account.Credentials.from_service_account_file(
                creds_path, scopes=self.scopes
            )
        elif creds_dict:
            self.creds = service_account.Credentials.from_service_account_info(
                creds_dict, scopes=self.scopes
            )
        else:
            raise ValueError("creds_type must be of [creds_path, creds_dict]")

        self.creds.refresh(Request())
        self.token = self.creds.token

        if agent_path:
            self.agent_path = agent_path

    @staticmethod
    def _set_region(item_id):
        """different regions have different API endpoints

        Args:
            item_id: agent/flow/page - any type of long path id like
                `projects/<GCP PROJECT ID>/locations/<LOCATION ID>

        Returns:
            client_options: use when instantiating other library client objects
        """
        try:
            location = item_id.split("/")[3]
        except IndexError as err:
            logging.error("IndexError - path too short? %s", item_id)
            raise err

        if location != "global":
            api_endpoint = "{}-dialogflow.googleapis.com:443".format(location)
            client_options = {"api_endpoint": api_endpoint}
            return client_options

        else:
            return None  # explicit None return when not required

    @staticmethod
    def pbuf_to_dict(pbuf):
        """extractor of json from a protobuf"""
        blobstr = json_format.MessageToJson(
            pbuf
        )  # i think this returns JSON as a string
        blob = json.loads(blobstr)
        return blob

    @staticmethod
    def response_to_json(response):
        """response objects have a magical _pb field attached"""
        # return SapiBase.pbuf_to_dict(response._pb)
        return SapiBase.pbuf_to_dict(response._pb)

    @staticmethod
    def response_to_dict(response):
        """response objects have a magical _pb field attached"""
        return SapiBase.pbuf_to_dict(response._pb)

    @staticmethod
    def extract_payload(msg):
        """convert to json so we can get at the object"""
        blob = SapiBase.response_to_dict(msg)
        return blob.get("payload")  # deref for nesting
