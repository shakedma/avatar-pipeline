"""
Upload project files to their respective Google Drive folders.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# Load environment variables
load_dotenv()

PROJECT_ROOT = Path(__file__).parent.parent
TOKEN_FILE = PROJECT_ROOT / 'token.json'

SCOPES = [
    'https://www.googleapis.com/auth/drive.file',
    'https://www.googleapis.com/auth/drive'
]


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


def upload_file(service, file_path, folder_id):
    """Upload a file to a specific folder."""
    path = Path(file_path)
    if not path.exists():
        print(f"  File not found: {path}")
        return None

    mime_types = {
        '.pdf': 'application/pdf',
        '.html': 'text/html',
        '.mp4': 'video/mp4',
        '.mp3': 'audio/mpeg'
    }
    mime_type = mime_types.get(path.suffix.lower(), 'application/octet-stream')

    file_metadata = {
        'name': path.name,
        'parents': [folder_id]
    }

    media = MediaFileUpload(str(path), mimetype=mime_type)
    file = service.files().create(
        body=file_metadata,
        media_body=media,
        fields='id, name, webViewLink'
    ).execute()

    # Make shareable
    service.permissions().create(
        fileId=file['id'],
        body={'type': 'anyone', 'role': 'reader'}
    ).execute()

    return file


def main():
    service = get_service()

    # Find main folder
    main_folder_id = find_folder(service, "Kabala project2801")
    if not main_folder_id:
        print("Error: Kabala project2801 folder not found!")
        return

    print(f"Found main folder: {main_folder_id}")

    # Find presentations subfolder
    presentations_folder_id = find_folder(service, "presentations", main_folder_id)
    if not presentations_folder_id:
        print("Error: presentations subfolder not found!")
        return

    print(f"Found presentations folder: {presentations_folder_id}")

    # Upload presentation files
    presentation_files = [
        PROJECT_ROOT / "presentation" / "AI_Avatar_Pipeline_Deck.pdf",
        PROJECT_ROOT / "presentation" / "AI_Avatar_Pipeline_Deck.html"
    ]

    print("\nUploading presentation files...")
    for file_path in presentation_files:
        if file_path.exists():
            print(f"  Uploading: {file_path.name}")
            result = upload_file(service, file_path, presentations_folder_id)
            if result:
                print(f"    Done: {result.get('webViewLink')}")
        else:
            print(f"  Skipping (not found): {file_path.name}")

    print("\nUpload complete!")
    print(f"\nView presentations: https://drive.google.com/drive/folders/{presentations_folder_id}")


if __name__ == "__main__":
    main()
