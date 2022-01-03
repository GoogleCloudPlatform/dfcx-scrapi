"""Utility file for Google Sheets"""

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
import time

import google.auth
import gspread
from gspread_dataframe import set_with_dataframe
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd


class GoogleDriveConnector:
    """Class for google sheets operations"""

    global_scopes = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive",
    ]

    def __init__(
        self, creds_path: str = None, creds_dict: dict = None, scope=False
    ):
        scopes = GoogleDriveConnector.global_scopes
        if scope:
            scopes += scope

        if creds_path:
            creds = ServiceAccountCredentials.from_json_keyfile_name(
                filename=creds_path, scopes=scopes
            )
        elif creds_dict:
            creds = ServiceAccountCredentials.from_json_keyfile_dict(
                keyfile_dict=creds_dict, scopes=scopes
            )
        else:
            creds = google.auth.default(scopes=scopes)[0]

        self.client = gspread.authorize(creds)

    def create_google_sheet(self, sheet_name: str):
        """Create new google sheet object, this sheet is created
        under service account drive account and must be shared to an account
        to view it from that account.

        Args:
          sheet_name: name of the sheets object to create.
        """
        self.client.create(title=sheet_name)

    def delete_google_sheet(self, sheet_name: str):
        """Delete a google sheet object

        Args:
          sheet_name: name of the sheets object to delete.
        """
        g_sheets = self.client.open(sheet_name)
        self.client.del_spreadsheet(g_sheets.id)

    def sheets_to_dataframe(self, sheet_name: str, worksheet_name: str):
        """Move Intent/TP data from Google Sheets to a DataFrame.
        Args:
          sheet_name: name of the sheets object to pull data from.
          worksheet_name: name of the worksheet in the sheets objec to pull data from.

        Returns:
          data: pandas dataframe containing the data in the g-sheet and worksheet specified
        """
        g_sheets = self.client.open(sheet_name)
        sheet = g_sheets.worksheet(worksheet_name)
        data_pull = sheet.get_all_values()
        data = pd.DataFrame(columns=data_pull[0], data=data_pull[1:])
        return data

    def dataframe_to_existing_sheet(
        self, sheet_name: str, worksheet_name: str, dataframe: pd.DataFrame
    ):
        """Move Intent/TP data from a DataFrame to Google Sheets.

        Args:
          sheet_name: name of the sheets object to push data to.
          worksheet_name: name of the worksheet in the sheets objec to push data to.
          dataframe: pandas dataframe to push to the sheet and worksheet.

        """
        g_sheets = self.client.open(sheet_name)
        worksheet = g_sheets.worksheet(worksheet_name)
        set_with_dataframe(worksheet, dataframe)

    def list_permissions(self, sheet_name: str):
        """List existing permissions on a sheet

        Args:
          sheet_name: name of the sheets object to pull existing permissions from.

        Returns:
          permissions: list of permissions on the sheet object.
        """
        g_sheets = self.client.open(sheet_name)
        permissions = g_sheets.list_permissions()
        return permissions

    def share_sheet(
        self,
        sheet_name: str,
        email: str,
        role: str = "writer",
        perm_type: str = "user",
        notify: bool = True,
    ):
        """Share an existing google sheet with emails.

        Args:
          sheet_name: name of the sheets object share
          email: email to share the sheet with.
          role: can be writer, reader or owner
          perm_type: type of permissoin giving
              user
              group
              domain
              anyone
          notify: true to notify email that the sheets object has been shared.
        """
        g_sheets = self.client.open(sheet_name)
        g_sheets.share(email, role=role, perm_type=perm_type, notify=notify)

    def add_worksheet(
        self,
        sheet_name: str,
        worksheet_name: str,
        rows: int = 100,
        cols: int = 26,
    ):
        """Add worksheet to an existing google sheet.

        Args:
          sheet_name: name of the sheets object
          worksheet_name: name of worksheet in the sheets object to add
          rows: rows to add to the sheet
          column: columns to add to the sheet
        """
        g_sheets = self.client.open(sheet_name)
        g_sheets.add_worksheet(title=worksheet_name, rows=rows, cols=cols)

    def delete_worksheet(self, sheet_name: str, worksheet_name: str):
        """Delete worksheet from an existing google sheet.

        Args:
          sheet_name: name of the sheets object
          worksheet_name: name of worksheet in the sheets object to delete
        """
        g_sheets = self.client.open(sheet_name)
        worksheet = g_sheets.worksheet(title=worksheet_name)
        g_sheets.del_worksheet(worksheet=worksheet)

    def dataframe_to_new_sheet(
        self,
        sheet_name: str,
        worksheet_name: str,
        dataframe: pd.DataFrame,
        emails: list,
    ):
        """Create a new google sheet and worksheet, share it with specified
        emails and add data to it.
        Args:
          sheet_name: name of the sheets object
          worksheet_name: name of worksheet in the sheets object to add data to
          dataframe: pandas dataframe of data to add to the worksheet
          emails: list of emails to share the google sheet with.
        """
        self.create_google_sheet(sheet_name)
        self.add_worksheet(
            sheet_name,
            worksheet_name,
            rows=(len(dataframe) + 1),
            cols=len(dataframe.columns),
        )
        self.dataframe_to_existing_sheet(sheet_name, worksheet_name, dataframe)
        for email in emails:
            self.share_sheet(sheet_name, email)
            time.sleep(1)
        logging.info("Added data to %s - %s shared with emails: %s",
                     sheet_name, worksheet_name, emails)
