"""
Set up Google Drive folder structure for the AI Avatar Pipeline.
Creates organized folders matching the local project structure.
"""

import os
from pathlib import Path
from dotenv import load_dotenv, set_key

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

# Load environment variables
load_dotenv()

# OAuth scopes
SCOPES = [
    'https://www.googleapis.com/auth/drive.file',
    'https://www.googleapis.com/auth/drive'
]

# Paths
PROJECT_ROOT = Path(__file__).parent.parent
CREDENTIALS_FILE = PROJECT_ROOT / 'credentials.json'
TOKEN_FILE = PROJECT_ROOT / 'token.json'
ENV_FILE = PROJECT_ROOT / '.env'


def get_credentials():
    """Get or refresh OAuth credentials."""
    credentials = None

    if TOKEN_FILE.exists():
        credentials = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)

    if not credentials or not credentials.valid:
        if credentials and credentials.expired and credentials.refresh_token:
            print("Refreshing expired credentials...")
            credentials.refresh(Request())
        else:
            if not CREDENTIALS_FILE.exists():
                raise FileNotFoundError(
                    f"credentials.json not found at {CREDENTIALS_FILE}\n"
                    "Please download OAuth credentials from Google Cloud Console."
                )

            print("Opening browser for Google Drive authorization...")
            flow = InstalledAppFlow.from_client_secrets_file(str(CREDENTIALS_FILE), SCOPES)
            credentials = flow.run_local_server(port=0)

        with open(TOKEN_FILE, 'w') as token:
            token.write(credentials.to_json())

    return credentials


def find_folder(service, folder_name, parent_id=None):
    """Find a folder by name, optionally within a parent folder."""
    query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
    if parent_id:
        query += f" and '{parent_id}' in parents"

    results = service.files().list(
        q=query,
        spaces='drive',
        fields='files(id, name)'
    ).execute()

    files = results.get('files', [])
    return files[0] if files else None


def create_folder(service, folder_name, parent_id=None):
    """Create a folder in Google Drive."""
    file_metadata = {
        'name': folder_name,
        'mimeType': 'application/vnd.google-apps.folder'
    }
    if parent_id:
        file_metadata['parents'] = [parent_id]

    folder = service.files().create(
        body=file_metadata,
        fields='id, name, webViewLink'
    ).execute()

    return folder


def setup_drive_folders():
    """Create the folder structure in Google Drive."""

    credentials = get_credentials()
    service = build('drive', 'v3', credentials=credentials)

    print("Setting up Google Drive folder structure...")
    print("=" * 50)

    # Main project folder
    main_folder_name = "Kabala project2801"

    # Check if main folder exists
    main_folder = find_folder(service, main_folder_name)

    if main_folder:
        print(f"Found existing folder: {main_folder_name}")
        main_folder_id = main_folder['id']
    else:
        print(f"Creating folder: {main_folder_name}")
        main_folder = create_folder(service, main_folder_name)
        main_folder_id = main_folder['id']

    # Subfolders to create
    subfolders = ['output', 'presentations', 'input']
    folder_ids = {'main': main_folder_id}

    for subfolder_name in subfolders:
        existing = find_folder(service, subfolder_name, main_folder_id)
        if existing:
            print(f"  Found existing subfolder: {subfolder_name}")
            folder_ids[subfolder_name] = existing['id']
        else:
            print(f"  Creating subfolder: {subfolder_name}")
            subfolder = create_folder(service, subfolder_name, main_folder_id)
            folder_ids[subfolder_name] = subfolder['id']

    # Update .env file with the output folder ID (where videos go)
    print("\nUpdating .env file...")
    set_key(str(ENV_FILE), 'GOOGLE_DRIVE_FOLDER_ID', folder_ids['output'])

    # Get shareable links
    main_folder_link = f"https://drive.google.com/drive/folders/{main_folder_id}"
    output_folder_link = f"https://drive.google.com/drive/folders/{folder_ids['output']}"

    print("\n" + "=" * 50)
    print("FOLDER STRUCTURE CREATED")
    print("=" * 50)
    print(f"\nMain folder: {main_folder_link}")
    print(f"\nSubfolders:")
    print(f"  - output/       (videos will upload here)")
    print(f"  - presentations/")
    print(f"  - input/")
    print(f"\n.env updated with GOOGLE_DRIVE_FOLDER_ID={folder_ids['output']}")

    return {
        'main_folder_id': main_folder_id,
        'main_folder_link': main_folder_link,
        'folder_ids': folder_ids
    }


if __name__ == "__main__":
    result = setup_drive_folders()
    print(f"\nOpen your Drive folder: {result['main_folder_link']}")
