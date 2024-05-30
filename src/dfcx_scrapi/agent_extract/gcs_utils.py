"""Utils for Cloud Storage and local file manipulation."""

# Copyright 2023 Google LLC
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

import zipfile
from google.cloud import storage
from google.oauth2 import service_account


class GcsUtils:
    """Utils for Cloud Storage and local file manipulation."""

    def __init__(self, creds_path: str = None, project_id: str = None):
        if creds_path and project_id:
            self.creds = service_account.Credentials.from_service_account_file(
                creds_path
            )
            self.gcs_client = storage.Client(
                credentials=self.creds, project=project_id
            )

        else:
            self.gcs_client = storage.Client()

    @staticmethod
    def unzip(agent_zip_file_path: str, extract_path: str):
        """Unzip file locally."""
        with zipfile.ZipFile(agent_zip_file_path, "r") as zip_ref:
            zip_ref.extractall(extract_path)

    @staticmethod
    def check_for_gcs_file(file_path: str) -> bool:
        """Validates GCS path vs. local path."""
        is_gcs_file = False

        file_prefix = file_path.split("/")[0]
        if file_prefix == "gs:":
            is_gcs_file = True

        return is_gcs_file

    def download_gcs(self, gcs_path: str, local_path: str = None):
        """Downloads the specified GCS file to local machine."""
        path = gcs_path.split("//")[1]
        bucket = path.split("/", 1)[0]
        gcs_object = path.split("/", 1)[1]
        file_name = gcs_object.split("/")[-1]
        bucket = self.gcs_client.bucket(bucket)
        blob = storage.Blob(gcs_object, bucket)

        if local_path:
            file_name = local_path + "/" + file_name

        blob.download_to_filename(file_name)

        return file_name
