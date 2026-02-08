"""
YouTube Video Upload Tool
Uploads videos to YouTube using the YouTube Data API v3.
Supports private, unlisted, and public uploads with metadata.
"""

import os
import sys
import json
import time
import http.client
import httplib2
from pathlib import Path
from dotenv import load_dotenv

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

# Load environment variables
load_dotenv()

# OAuth 2.0 scopes required for YouTube upload
SCOPES = ['https://www.googleapis.com/auth/youtube.upload']

# Paths for credentials
PROJECT_ROOT = Path(__file__).parent.parent
CREDENTIALS_FILE = PROJECT_ROOT / 'credentials.json'
TOKEN_FILE = PROJECT_ROOT / 'youtube_token.json'

# Retry settings for resumable upload
MAX_RETRIES = 10
RETRIABLE_EXCEPTIONS = (httplib2.HttpLib2Error, IOError, http.client.NotConnected,
                        http.client.IncompleteRead, http.client.ImproperConnectionState,
                        http.client.CannotSendRequest, http.client.CannotSendHeader,
                        http.client.ResponseNotReady, http.client.BadStatusLine)
RETRIABLE_STATUS_CODES = [500, 502, 503, 504]


def get_authenticated_service():
    """
    Authenticate with YouTube API using OAuth 2.0.

    On first run, opens a browser for user authorization.
    Subsequent runs use the saved token.

    Returns:
        YouTube API service object
    """
    credentials = None

    # Check for existing token
    if TOKEN_FILE.exists():
        credentials = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)

    # If no valid credentials, get new ones
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

            print("Opening browser for YouTube authorization...")
            print("(You only need to do this once)")
            flow = InstalledAppFlow.from_client_secrets_file(str(CREDENTIALS_FILE), SCOPES)
            credentials = flow.run_local_server(port=0)  # Use any available port

        # Save credentials for future runs
        with open(TOKEN_FILE, 'w') as token:
            token.write(credentials.to_json())
        print(f"Credentials saved to {TOKEN_FILE}")

    return build('youtube', 'v3', credentials=credentials)


def upload_video(
    video_path: str,
    title: str,
    description: str = "",
    tags: list = None,
    category_id: str = "22",  # 22 = People & Blogs
    privacy_status: str = "private"
) -> dict:
    """
    Upload a video to YouTube.

    Args:
        video_path: Path to the video file
        title: Video title (required, max 100 chars)
        description: Video description (optional, max 5000 chars)
        tags: List of tags (optional)
        category_id: YouTube category ID (default: 22 = People & Blogs)
                    Other common IDs: 27=Education, 28=Science & Technology
        privacy_status: 'private', 'unlisted', or 'public'
                       Note: 'public' requires API audit approval

    Returns:
        dict with video ID and URL on success
    """
    video_path = Path(video_path)

    if not video_path.exists():
        raise FileNotFoundError(f"Video file not found: {video_path}")

    # Validate inputs
    if len(title) > 100:
        print(f"Warning: Title truncated to 100 characters")
        title = title[:100]

    if description and len(description) > 5000:
        print(f"Warning: Description truncated to 5000 characters")
        description = description[:5000]

    # Get authenticated YouTube service
    youtube = get_authenticated_service()

    # Prepare video metadata
    body = {
        'snippet': {
            'title': title,
            'description': description,
            'tags': tags or [],
            'categoryId': category_id
        },
        'status': {
            'privacyStatus': privacy_status,
            'selfDeclaredMadeForKids': False
        }
    }

    # Create MediaFileUpload with resumable upload
    media = MediaFileUpload(
        str(video_path),
        chunksize=1024*1024,  # 1MB chunks
        resumable=True
    )

    # Create the upload request
    request = youtube.videos().insert(
        part='snippet,status',
        body=body,
        media_body=media
    )

    print(f"Uploading: {video_path.name}")
    print(f"Title: {title}")
    print(f"Privacy: {privacy_status}")
    print("-" * 40)

    # Execute upload with retry logic
    response = None
    retry_count = 0

    while response is None:
        try:
            status, response = request.next_chunk()
            if status:
                progress = int(status.progress() * 100)
                print(f"Upload progress: {progress}%")

        except HttpError as e:
            if e.resp.status in RETRIABLE_STATUS_CODES:
                retry_count += 1
                if retry_count > MAX_RETRIES:
                    raise Exception(f"Maximum retries exceeded. Last error: {e}")

                sleep_seconds = 2 ** retry_count
                print(f"Retriable error (attempt {retry_count}/{MAX_RETRIES}). "
                      f"Retrying in {sleep_seconds} seconds...")
                time.sleep(sleep_seconds)
            else:
                raise

        except RETRIABLE_EXCEPTIONS as e:
            retry_count += 1
            if retry_count > MAX_RETRIES:
                raise Exception(f"Maximum retries exceeded. Last error: {e}")

            sleep_seconds = 2 ** retry_count
            print(f"Retriable error (attempt {retry_count}/{MAX_RETRIES}). "
                  f"Retrying in {sleep_seconds} seconds...")
            time.sleep(sleep_seconds)

    video_id = response['id']
    video_url = f"https://www.youtube.com/watch?v={video_id}"

    print("-" * 40)
    print(f"Upload complete!")
    print(f"Video ID: {video_id}")
    print(f"URL: {video_url}")

    return {
        'video_id': video_id,
        'url': video_url,
        'title': title,
        'privacy_status': privacy_status
    }


def main():
    """CLI entry point."""
    if len(sys.argv) < 3:
        print("Usage: python youtube_upload.py <video_file> <title> [description] [privacy]")
        print("")
        print("Arguments:")
        print("  video_file   Path to the video file to upload")
        print("  title        Video title (required)")
        print("  description  Video description (optional)")
        print("  privacy      Privacy status: private, unlisted, or public (default: private)")
        print("")
        print("Examples:")
        print('  python youtube_upload.py ../output/video.mp4 "My Video Title"')
        print('  python youtube_upload.py ../output/video.mp4 "My Video" "Description here" unlisted')
        sys.exit(1)

    video_file = sys.argv[1]
    title = sys.argv[2]
    description = sys.argv[3] if len(sys.argv) > 3 else ""
    privacy = sys.argv[4] if len(sys.argv) > 4 else "private"

    if privacy not in ['private', 'unlisted', 'public']:
        print(f"Error: Invalid privacy status '{privacy}'. Use: private, unlisted, or public")
        sys.exit(1)

    try:
        result = upload_video(
            video_path=video_file,
            title=title,
            description=description,
            privacy_status=privacy
        )
        print(f"\nSuccess! Video uploaded: {result['url']}")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
