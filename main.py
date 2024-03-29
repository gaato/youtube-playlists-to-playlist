import os
import sys
import re

import httplib2
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from oauth2client.client import flow_from_clientsecrets
from oauth2client.file import Storage
from oauth2client.tools import argparser, run_flow

from config import my_playlist_id, target_playlist_ids

# The CLIENT_SECRETS_FILE variable specifies the name of a file that contains
# the OAuth 2.0 information for this application, including its client_id and
# client_secret. You can acquire an OAuth 2.0 client ID and client secret from
# the Google API Console at
# https://console.developers.google.com/.
# Please ensure that you have enabled the YouTube Data API for your project.
# For more information about using OAuth2 to access the YouTube Data API, see:
#   https://developers.google.com/youtube/v3/guides/authentication
# For more information about the client_secrets.json file format, see:
#   https://developers.google.com/api-client-library/python/guide/aaa_client_secrets
CLIENT_SECRETS_FILE = "client_secrets.json"

# This variable defines a message to display if the CLIENT_SECRETS_FILE is
# missing.
MISSING_CLIENT_SECRETS_MESSAGE = """
WARNING: Please configure OAuth 2.0

To make this sample run you will need to populate the client_secrets.json file
found at:

   %s

with information from the API Console
https://console.developers.google.com/

For more information about the client_secrets.json file format, please visit:
https://developers.google.com/api-client-library/python/guide/aaa_client_secrets
""" % os.path.abspath(os.path.join(os.path.dirname(__file__),
                                   CLIENT_SECRETS_FILE))

# This OAuth 2.0 access scope allows for full read/write access to the
# authenticated user's account.
YOUTUBE_READ_WRITE_SCOPE = "https://www.googleapis.com/auth/youtube"
YOUTUBE_API_SERVICE_NAME = "youtube"
YOUTUBE_API_VERSION = "v3"

flow = flow_from_clientsecrets(CLIENT_SECRETS_FILE,
                               message=MISSING_CLIENT_SECRETS_MESSAGE,
                               scope=YOUTUBE_READ_WRITE_SCOPE)

storage = Storage("%s-oauth2.json" % sys.argv[0])
credentials = storage.get()

if credentials is None or credentials.invalid:
    flags = argparser.parse_args()
    credentials = run_flow(flow, storage, flags)

youtube = build(YOUTUBE_API_SERVICE_NAME, YOUTUBE_API_VERSION,
                http=credentials.authorize(httplib2.Http()))


def get_items_from_playlist(playlist_id):
    query = youtube.playlistItems().list(
        part="snippet",
        playlistId=playlist_id,
        maxResults=50
    )
    result = []
    while query:
        response = query.execute()
        result += [item["snippet"]["resourceId"]["videoId"] for item in response["items"]]
        query = youtube.playlistItems().list_next(
            query,
            response,
        )
    return result


def get_durations_from_videos(video_ids):
    result = {}
    for i in range(0, len(video_ids), 50):
        query = youtube.videos().list(
            part="contentDetails",
            id=','.join(video_ids[i: i + 50]),
            maxResults=50
        )
        response = query.execute()
        for item in response["items"]:
            result[item["id"]] = item["contentDetails"]["duration"]
    return result


def is_less_than_10min(duration):
    if "H" in duration:
        return False
    if "M" not in duration:
        return True
    m = re.search(r'(\d+)M', duration)
    return int(m.group(1)) < 10


my_playlist_items = get_items_from_playlist(my_playlist_id)

for target_playlist_id in target_playlist_ids:
    items = get_items_from_playlist(target_playlist_id)
    durations = get_durations_from_videos(items)
    for id, duration in durations.items():
        if id not in my_playlist_items and is_less_than_10min(duration):
            try:
                response = youtube.playlistItems().insert(
                    part="snippet",
                    body={
                        "snippet": {
                            "playlistId": my_playlist_id,
                            "resourceId": {
                                "videoId": id,
                                "kind": "youtube#video"
                            }
                        }
                    }
                ).execute()
            except HttpError as e:
                print(id, e)
            else:
                print(f"{response['snippet']['title']} を追加しました")

