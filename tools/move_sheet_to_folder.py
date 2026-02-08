"""
Move the tracking Google Sheet into the Kabala project2801 folder.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

load_dotenv()

PROJECT_ROOT = Path(__file__).parent.parent
TOKEN_FILE = PROJECT_ROOT / 'token.json'

SCOPES = [
    'https://www.googleapis.com/auth/drive.file',
    'https://www.googleapis.com/auth/drive'
]

# Sheet ID from .env
SHEET_ID = os.getenv("GOOGLE_SHEET_ID", "").strip("'\"")


def get_service():
    """Get authenticated Drive service."""
    credentials = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)
    return build('drive', 'v3', credentials=credentials)


def find_folder(service, folder_name, parent_id=None):
    """Find a folder by name."""
    query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
    if parent_id:
        query += f" and '{parent_id}' in parents"

    results = service.files().list(q=query, fields='files(id, name)').execute()
    files = results.get('files', [])
    return files[0]['id'] if files else None


def move_file_to_folder(service, file_id, folder_id):
    """Move a file to a specific folder."""
    # Get current parents
    file = service.files().get(fileId=file_id, fields='parents').execute()
    previous_parents = ",".join(file.get('parents', []))

    # Move to new folder
    file = service.files().update(
        fileId=file_id,
        addParents=folder_id,
        removeParents=previous_parents,
        fields='id, parents, webViewLink'
    ).execute()

    return file


def main():
    if not SHEET_ID:
        print("Error: GOOGLE_SHEET_ID not found in .env")
        return

    print(f"Sheet ID: {SHEET_ID}")

    service = get_service()

    # Find main folder
    main_folder_id = find_folder(service, "Kabala project2801")
    if not main_folder_id:
        print("Error: Kabala project2801 folder not found!")
        return

    print(f"Found main folder: {main_folder_id}")

    # Move the sheet
    print(f"\nMoving tracking sheet to Kabala project2801 folder...")
    try:
        result = move_file_to_folder(service, SHEET_ID, main_folder_id)
        print(f"Done!")
        print(f"\nSheet location: https://drive.google.com/drive/folders/{main_folder_id}")
        print(f"Sheet link: https://docs.google.com/spreadsheets/d/{SHEET_ID}/edit")
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()
