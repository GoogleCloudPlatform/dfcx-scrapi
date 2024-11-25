"""Utility and helper methods for using Google Cloud Storage."""

# Copyright 2024 Google LLC
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

import json

from google.api_core.exceptions import NotFound
from google.cloud import storage


class GcsUtils:
    def __init__(self, gcs_path: str = None):
        self.client = storage.Client()

        if gcs_path:
            self.gcs_path = gcs_path
            self.bucket_name, self.file_path = self.get_bucket_name_and_path(
                gcs_path
                )
            self.bucket_exists(self.bucket_name)

    @staticmethod
    def get_bucket_name_and_path(gcs_path: str):
        """Strip gs:// or extract proper bucket name."""
        _, bucket_and_path = gcs_path.split("gs://")
        bucket_name, file_path = bucket_and_path.split("/", 1)

        return bucket_name, file_path

    def get_fully_qualified_path(self, filename: str):
        """Get the fully qualified path of the filename."""
        if self.file_path:
            return f"{self.file_path}/{filename}"
        else:
            return filename

    def read_file(self, filepath: str):
        """Read a file from GCS bucket."""

        # 1. Validate the file path
        if not filepath.startswith("gs://"):
            raise ValueError("Invalid filepath. Must start with 'gs://'")

        # 2. Split and extract components
        _, gcs_path = filepath.split("gs://")
        bucket_name, file_path = self.get_bucket_name_and_path(gcs_path)

        # 3. Access Google Cloud Storage
        bucket = self.client.bucket(bucket_name)
        blob = bucket.blob(file_path)

        # 4. Read the file content
        file_content = blob.download_as_text()

        return file_content

    def write_file(
            self,
            bucket_name: str,
            local_file_path: str,
            destination_name: str = None):
        """Write a file to GCS bucket."""

        # 1. Validate bucket name
        if not bucket_name:
            raise ValueError("Bucket name cannot be empty")

        # 2. Determine destination file path
        if destination_name:
            file_path = destination_name
        else:
            file_path = local_file_path.split("/")[-1]

        # 3. Access Google Cloud Storage
        bucket = self.client.bucket(bucket_name)
        blob = bucket.blob(file_path)

        # 4. Upload the file
        with open(local_file_path, "rb") as f:
            blob.upload_from_file(f)

        return f"File uploaded to gs://{bucket_name}/{file_path}"

    def write_dict_to_gcs(self, bucket_name: str, data: dict, filename: str):
        """Write a dict as a JSON file to a GCS bucket."""
        if not bucket_name or not filename:
            raise ValueError("Bucket name and filename cannot be empty")
        bucket = self.client.bucket(bucket_name)
        blob = bucket.blob(filename)
        json_string = json.dumps(data, indent=4)
        blob.upload_from_string(json_string, content_type="application/json")

    def load_file_if_exists(self, bucket_name: str, filename: str):
        bucket = self.client.bucket(bucket_name)
        blob = bucket.blob(filename)

        if blob.exists():
            full_path = f"gs://{bucket_name}/{filename}"
            return self.read_file(filepath=full_path)
        else:
            return None

    def bucket_exists(self, bucket_name: str):
        """Checks if a GCS bucket exists."""
        try:
            storage_client = storage.Client()
            storage_client.get_bucket(bucket_name)
        except NotFound:
            raise NotFound(f"GCS Bucket `{bucket_name}` does not exist.")
