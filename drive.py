import logging
import os
import pickle
from math import floor

from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

import util


class TeamDrive:
    def __init__(self, client_secrets_filepath, credentials_filepath=None):
        """
        client_secrets: Path to client_secrets.json file
        credentials: Path to token.pickle file
        """
        self.client_secrets = client_secrets_filepath
        if credentials_filepath is None:
            self.credentials = "token.pickle"
        else:
            self.credentials = credentials_filepath
        self.log = logging.getLogger("TeamDrive")
        self.service_instance = self.service()

    def service(self) -> build:
        scopes = ["https://www.googleapis.com/auth/drive"]
        if os.path.exists(self.credentials):
            with open(self.credentials, "rb") as token:
                creds = pickle.load(token)
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.client_secrets, scopes
                )
                creds = flow.run_local_server(port=8080)
            with open(self.credentials, "wb") as token:
                pickle.dump(creds, token)
        service = build("drive", "v3", credentials=creds)
        self.log.info("Service created")
        return service

    def folder_query_builder(self, queries: list) -> str:
        """
        Builds a query string from a list of queries
        queries: List of queries
        """
        query = "mimeType = 'application/vnd.google-apps.folder' and ("
        for q in queries:
            query += "name contains '{}' or ".format(q)
        query = query[:-4] + ") and trashed = false"
        self.log.debug(query)
        return query

    def list_files(self, query: str) -> list:
        """
        Returns a list of files matching the query
        query: Query string
        """
        self.log.info("Listing files")
        service = self.service_instance
        list_file = []
        page_token = None
        while True:
            try:
                response = (
                    service.files()
                    .list(
                        q=query,
                        includeItemsFromAllDrives=True,
                        supportsAllDrives=True,
                        corpora="allDrives",
                        fields="nextPageToken, files(id, name, size, mimeType, parents, driveId)",
                        pageToken=page_token,
                    )
                    .execute()
                )
                # add additional info to the list of files
                # TODO: move this somewhere at the end of the flow to minimize api calls
                for file in response.get("files", []):
                    self.log.debug("found file: {}".format(file["name"]))
                    file["driveName"] = self.drive_id_to_name(file.get("driveId"))
                    if "size" in file:
                        file["size"] = floor(int(file["size"]) / 1000000)
                    file["parentNames"] = []
                    for parent in file.get("parents", []):
                        file["parentNames"].append(self.id_to_name(parent))
                list_file.extend(response.get("files", []))
                page_token = response.get("nextPageToken", None)
                if not page_token:
                    break
            except HttpError as e:
                self.log.error("An error occurred: {}".format(e))
                break
        self.log.info("Found {} files".format(len(list_file)))
        return list_file

    def create_folder(self, name: str, parent_id: str) -> str:
        """
        Creates a folder in the parent_id folder

        args:
        name: Name of the folder
        parent_id: ID of the parent folder

        returns:
        a dict containing the folder's ID and name
        """
        service = self.service_instance
        file_metadata = {
            "name": name,
            "mimeType": "application/vnd.google-apps.folder",
            "parents": [parent_id],
            "supportsAllDrives": True,
        }
        file = service.files().create(body=file_metadata, fields="id, name", supportsAllDrives=True).execute()
        self.log.info("Created folder: {}".format(file.get("name")))
        return file["id"]

    def copy_folder(self, src_id, src_name, dst):
        """
        Copies the folder with the given id to the destination folder

        args:
        src_id: ID of the folder to copy
        src_name: Name of the folder to copy
        dst: Destination folder

        returns:
        folder's url
        """
        service = self.service_instance
        nextPageToken = ""
        while True:
            file_list = (
                service.files()
                .list(
                    q="'%s' in parents" % src_id,
                    fields="nextPageToken, files(id, name, mimeType, parents)",
                    pageSize=1000,
                    pageToken=nextPageToken or "",
                    includeItemsFromAllDrives=True,
                    supportsAllDrives=True,
                )
                .execute()
            )
            dst_parent_id = self.create_folder(src_name, dst)

            files = file_list.get("files", [])

            self.log.info("Found {} files".format(len(files)))
            self.log.debug("Files: {}".format(files))

            for file in files:
                if file.get("mimeType") != "application/vnd.google-apps.folder" or None:
                    clone = (
                        service.files()
                        .copy(
                            fileId=file.get("id"),
                            body={
                                "name": util.clean_name(file.get("name")),
                                "parents": [dst_parent_id],
                            },
                            supportsAllDrives=True,
                        )
                        .execute()
                    )

                    try:
                        service.files().update(
                            fileId=clone.get("id"),
                            addParents=dst_parent_id,
                            removeParents=src_id,
                            fields="id, parents",
                            supportsAllDrives=True,
                        ).execute()
                    except:
                        self.log.error("Error updating file {}".format(file.get("name")))
                        pass
                else:
                    self.log.debug(f"file {file.get('name')} is a folder")
                    self.copy_folder(file.get("id"), file.get("name"), dst_parent_id)
            nextPageToken = file_list.get("nextPageToken")
            if nextPageToken is None:
                self.log.info(f"Copied folder {src_name} to {dst}")
                break
        return "https://drive.google.com/drive/folders/%s" % dst_parent_id

    def drive_id_to_name(self, drive_id):
        """
        Returns the name of the team drive with the given id
        """
        service = self.service_instance
        drive = service.drives().get(driveId=drive_id).execute()
        return drive.get("name")

    def id_to_name(self, id):
        """
        Returns the name of the file with the given id
        """
        service = self.service_instance
        file = service.files().get(fileId=id, supportsAllDrives=True).execute()
        return file.get("name")
    
    # TODO: create a function to check if folder contains video files