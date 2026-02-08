"""
Google Drive Upload Tool
Uploads files to Google Drive and returns a shareable link.
Uses OAuth2 for authentication with credentials.json/token.json.
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# Load environment variables from project root
project_root = Path(__file__).parent.parent
load_dotenv(project_root / ".env")

# OAuth scopes for Google Drive
SCOPES = [
    'https://www.googleapis.com/auth/drive.file',
    'https://www.googleapis.com/auth/gmail.send',
    'https://www.googleapis.com/auth/spreadsheets'
]

CREDENTIALS_FILE = project_root / "credentials.json"
TOKEN_FILE = project_root / "token.json"

# Optional: specific folder to upload to
DRIVE_FOLDER_ID = os.getenv("GOOGLE_DRIVE_FOLDER_ID")


def get_google_credentials():
    """
    Get or refresh Google OAuth2 credentials.

    Returns:
        google.oauth2.credentials.Credentials object
    """
    creds = None

    # Check for existing token
    if TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)

    # If no valid credentials, authenticate
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("Refreshing expired token...")
            creds.refresh(Request())
        else:
            if not CREDENTIALS_FILE.exists():
                raise FileNotFoundError(
                    f"credentials.json not found at {CREDENTIALS_FILE}\n"
                    "Please download OAuth credentials from Google Cloud Console:\n"
                    "1. Go to https://console.cloud.google.com\n"
                    "2. Create a project and enable Drive, Gmail, and Sheets APIs\n"
                    "3. Create OAuth 2.0 credentials (Desktop app)\n"
                    "4. Download and save as credentials.json in project root"
                )

            print("Opening browser for Google OAuth consent...")
            flow = InstalledAppFlow.from_client_secrets_file(
                str(CREDENTIALS_FILE), SCOPES
            )
            creds = flow.run_local_server(port=0)

        # Save credentials for next run
        with open(TOKEN_FILE, 'w') as token:
            token.write(creds.to_json())
        print(f"Token saved to {TOKEN_FILE}")

    return creds


def get_drive_service():
    """
    Build and return Google Drive API service.

    Returns:
        googleapiclient.discovery.Resource for Drive API
    """
    creds = get_google_credentials()
    return build('drive', 'v3', credentials=creds)


def upload_to_drive(file_path: str, folder_id: str = None) -> dict:
    """
    Upload a file to Google Drive.

    Args:
        file_path: Path to the file to upload
        folder_id: Optional Drive folder ID (uses env var or root if not specified)

    Returns:
        dict with 'file_id', 'file_name', 'shareable_link'
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    # Use provided folder_id, env var, or None (root)
    target_folder = folder_id or DRIVE_FOLDER_ID

    print(f"Uploading {path.name} to Google Drive...")

    service = get_drive_service()

    # Prepare file metadata
    file_metadata = {'name': path.name}
    if target_folder:
        file_metadata['parents'] = [target_folder]

    # Determine MIME type
    mime_types = {
        '.mp4': 'video/mp4',
        '.mp3': 'audio/mpeg',
        '.wav': 'audio/wav',
        '.pdf': 'application/pdf',
        '.txt': 'text/plain',
        '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    }
    mime_type = mime_types.get(path.suffix.lower(), 'application/octet-stream')

    # Upload file
    media = MediaFileUpload(str(path), mimetype=mime_type, resumable=True)

    file = service.files().create(
        body=file_metadata,
        media_body=media,
        fields='id, name, webViewLink'
    ).execute()

    file_id = file.get('id')
    print(f"  File uploaded with ID: {file_id}")

    # Make file shareable (anyone with link can view)
    shareable_link = make_shareable(service, file_id)

    return {
        'file_id': file_id,
        'file_name': file.get('name'),
        'shareable_link': shareable_link
    }


def make_shareable(service, file_id: str) -> str:
    """
    Make a file publicly viewable and return the shareable link.

    Args:
        service: Google Drive API service
        file_id: ID of the file to share

    Returns:
        Shareable link URL
    """
    # Create permission for anyone with the link
    permission = {
        'type': 'anyone',
        'role': 'reader'
    }

    service.permissions().create(
        fileId=file_id,
        body=permission
    ).execute()

    # Get the shareable link
    file = service.files().get(
        fileId=file_id,
        fields='webViewLink'
    ).execute()

    link = file.get('webViewLink')
    print(f"  Shareable link: {link}")

    return link


def main():
    """CLI entry point."""
    if len(sys.argv) < 2:
        print("Usage: python google_drive_upload.py <file_path> [folder_id]")
        print("\nUploads a file to Google Drive and returns a shareable link.")
        print("\nArguments:")
        print("  file_path  Path to the file to upload")
        print("  folder_id  Optional: Google Drive folder ID to upload to")
        sys.exit(1)

    file_path = sys.argv[1]
    folder_id = sys.argv[2] if len(sys.argv) > 2 else None

    try:
        result = upload_to_drive(file_path, folder_id)
        print(f"\nSuccess!")
        print(f"  File ID: {result['file_id']}")
        print(f"  File Name: {result['file_name']}")
        print(f"  Shareable Link: {result['shareable_link']}")
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
