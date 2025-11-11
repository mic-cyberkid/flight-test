#!/usr/bin/env python3
"""
Head-less Google-Drive uploader for GitHub Actions.
Uses client_secret.json (injected as a secret) + a cached token.pickle.
"""

import os
import pickle
import sys
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# ----------------------------------------------------------------------
# CONFIG – you can also override via env vars (see workflow)
# ----------------------------------------------------------------------
SCOPES = ['https://www.googleapis.com/auth/drive.file']
CLIENT_SECRET_JSON = os.getenv('GDRIVE_CLIENT_SECRET_JSON')   # whole JSON string
TOKEN_PICKLE = 'token.pickle'
DRIVE_FOLDER_ID = "1zmZ63MZVWkpMPagZ6FEGVEgB7UkMiaIT"

# Files to upload – change/extend as you like
FILES_TO_UPLOAD = [
    # (local_path, mime_type, optional_new_name)
    ("results.zip", "application/zip"),
]

# ----------------------------------------------------------------------
def load_or_create_token():
    """Return a valid Credentials object. Creates/refreshes token.pickle."""
    creds = None
    if os.path.exists(TOKEN_PICKLE):
        with open(TOKEN_PICKLE, 'rb') as f:
            creds = pickle.load(f)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            # First run – need a refresh token (will be cached later)
            # We use the JSON string that was injected as a secret
            import json, tempfile
            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as tmp:
                tmp.write(CLIENT_SECRET_JSON)
                tmp_path = tmp.name
            flow = InstalledAppFlow.from_client_secrets_file(tmp_path, SCOPES)
            # **Headless** – use the console flow (GitHub prints the URL)
            creds = flow.run_console()
            os.unlink(tmp_path)

        # Save for next runs
        with open(TOKEN_PICKLE, 'wb') as f:
            pickle.dump(creds, f)

    return creds


def upload_file(service, local_path, mime, folder_id, new_name=None):
    name = new_name or os.path.basename(local_path)
    metadata = {'name': name, 'parents': [folder_id]}
    media = MediaFileUpload(local_path, mimetype=mime, resumable=True)

    print(f"Uploading {local_path} to Drive:{name}")
    file = service.files().create(
        body=metadata,
        media_body=media,
        fields='id,name,webViewLink'
    ).execute()
    print(f"Uploaded {file.get('name')} (ID: {file.get('id')})")
    print(f"Link: {file.get('webViewLink')}")
    return file.get('id')


def main():
    if not CLIENT_SECRET_JSON:
        sys.exit("ERROR: GDRIVE_CLIENT_SECRET_JSON secret is missing")
        

    creds = load_or_create_token()
    service = build('drive', 'v3', credentials=creds)

    for path, mime, *rest in FILES_TO_UPLOAD:
        new_name = rest[0] if rest else None
        if not os.path.exists(path):
            print(f"Warning: {path} not found -- skipping")
            continue
        upload_file(service, path, mime, DRIVE_FOLDER_ID, new_name)


if __name__ == '__main__':
    main()
