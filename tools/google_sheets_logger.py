"""
Google Sheets Logger Tool
Logs video generation data to a Google Sheet for tracking and verification.
Creates the sheet if it doesn't exist.
"""

import os
import sys
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv, set_key

from googleapiclient.discovery import build

# Import shared credentials helper
from google_drive_upload import get_google_credentials

# Load environment variables from project root
project_root = Path(__file__).parent.parent
env_file = project_root / ".env"
load_dotenv(env_file)

# Sheet configuration
SHEET_ID = os.getenv("GOOGLE_SHEET_ID")
SHEET_NAME = "Video Generation Log"

# Column headers
HEADERS = [
    "Timestamp",
    "Script Name",
    "Script Length",
    "Audio File",
    "Video File",
    "Drive Link",
    "Status",
    "Duration (s)",
    "Error Message"
]


def get_sheets_service():
    """
    Build and return Google Sheets API service.

    Returns:
        googleapiclient.discovery.Resource for Sheets API
    """
    creds = get_google_credentials()
    return build('sheets', 'v4', credentials=creds)


def create_spreadsheet(title: str = "Video Generation Log") -> str:
    """
    Create a new Google Spreadsheet.

    Args:
        title: Name of the spreadsheet

    Returns:
        Spreadsheet ID
    """
    print(f"Creating new spreadsheet: {title}")

    service = get_sheets_service()

    spreadsheet = {
        'properties': {'title': title},
        'sheets': [{
            'properties': {
                'title': SHEET_NAME,
                'gridProperties': {
                    'frozenRowCount': 1  # Freeze header row
                }
            }
        }]
    }

    result = service.spreadsheets().create(body=spreadsheet).execute()
    sheet_id = result.get('spreadsheetId')

    print(f"  Spreadsheet created with ID: {sheet_id}")

    # Add headers
    add_headers(service, sheet_id)

    # Format header row
    format_header(service, sheet_id)

    return sheet_id


def add_headers(service, sheet_id: str):
    """Add header row to the sheet."""
    service.spreadsheets().values().update(
        spreadsheetId=sheet_id,
        range=f"{SHEET_NAME}!A1:{chr(65 + len(HEADERS) - 1)}1",
        valueInputOption='RAW',
        body={'values': [HEADERS]}
    ).execute()
    print("  Headers added")


def format_header(service, sheet_id: str):
    """Format the header row (bold, background color)."""
    # Get the sheet ID (not spreadsheet ID)
    spreadsheet = service.spreadsheets().get(spreadsheetId=sheet_id).execute()
    sheet_gid = spreadsheet['sheets'][0]['properties']['sheetId']

    requests = [
        # Bold header
        {
            'repeatCell': {
                'range': {
                    'sheetId': sheet_gid,
                    'startRowIndex': 0,
                    'endRowIndex': 1
                },
                'cell': {
                    'userEnteredFormat': {
                        'textFormat': {'bold': True},
                        'backgroundColor': {
                            'red': 0.2,
                            'green': 0.4,
                            'blue': 0.8
                        },
                        'horizontalAlignment': 'CENTER'
                    }
                },
                'fields': 'userEnteredFormat(textFormat,backgroundColor,horizontalAlignment)'
            }
        },
        # Auto-resize columns
        {
            'autoResizeDimensions': {
                'dimensions': {
                    'sheetId': sheet_gid,
                    'dimension': 'COLUMNS',
                    'startIndex': 0,
                    'endIndex': len(HEADERS)
                }
            }
        }
    ]

    service.spreadsheets().batchUpdate(
        spreadsheetId=sheet_id,
        body={'requests': requests}
    ).execute()
    print("  Header formatted")


def get_or_create_sheet() -> tuple:
    """
    Get existing sheet ID or create a new one.

    Returns:
        tuple of (sheet_id, sheet_link)
    """
    global SHEET_ID

    if SHEET_ID:
        # Verify sheet exists
        try:
            service = get_sheets_service()
            service.spreadsheets().get(spreadsheetId=SHEET_ID).execute()
            sheet_link = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}"
            return SHEET_ID, sheet_link
        except Exception:
            print(f"  Sheet {SHEET_ID} not accessible, creating new one...")

    # Create new sheet
    SHEET_ID = create_spreadsheet()

    # Save to .env for future use
    if env_file.exists():
        set_key(str(env_file), "GOOGLE_SHEET_ID", SHEET_ID)
        print(f"  Sheet ID saved to .env")

    sheet_link = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}"
    return SHEET_ID, sheet_link


def log_video_generation(
    script_name: str,
    script_length: int,
    audio_file: str,
    video_file: str,
    drive_link: str,
    status: str,
    duration: int = None,
    error_message: str = None
) -> dict:
    """
    Log a video generation to the Google Sheet.

    Args:
        script_name: Original script filename
        script_length: Character count of the script
        audio_file: Name of the audio file in output
        video_file: Name of the video file in output
        drive_link: Shareable Google Drive link
        status: Success / Failed / Pending
        duration: Processing time in seconds (optional)
        error_message: Error details if failed (optional)

    Returns:
        dict with 'sheet_id', 'sheet_link', 'row_number'
    """
    print("Logging to Google Sheet...")

    sheet_id, sheet_link = get_or_create_sheet()
    service = get_sheets_service()

    # Prepare row data
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    row = [
        timestamp,
        script_name,
        f"{script_length} chars",
        audio_file,
        video_file,
        drive_link,
        status,
        str(duration) if duration else "",
        error_message or ""
    ]

    # Append row
    result = service.spreadsheets().values().append(
        spreadsheetId=sheet_id,
        range=f"{SHEET_NAME}!A:I",
        valueInputOption='USER_ENTERED',
        insertDataOption='INSERT_ROWS',
        body={'values': [row]}
    ).execute()

    # Get row number from updated range
    updated_range = result.get('updates', {}).get('updatedRange', '')
    row_number = updated_range.split('!')[-1].split(':')[0].replace('A', '') if updated_range else 'unknown'

    print(f"  Logged to row {row_number}")
    print(f"  Sheet link: {sheet_link}")

    return {
        'sheet_id': sheet_id,
        'sheet_link': sheet_link,
        'row_number': row_number
    }


def main():
    """CLI entry point."""
    if len(sys.argv) < 4:
        print("Usage: python google_sheets_logger.py <script_name> <status> <drive_link> [video_file] [duration]")
        print("\nLogs video generation data to a Google Sheet.")
        print("\nArguments:")
        print("  script_name  Original script filename")
        print("  status       Success / Failed / Pending")
        print("  drive_link   Google Drive shareable link")
        print("  video_file   Optional: Video filename")
        print("  duration     Optional: Processing time in seconds")
        sys.exit(1)

    script_name = sys.argv[1]
    status = sys.argv[2]
    drive_link = sys.argv[3]
    video_file = sys.argv[4] if len(sys.argv) > 4 else "unknown.mp4"
    duration = int(sys.argv[5]) if len(sys.argv) > 5 else None

    try:
        result = log_video_generation(
            script_name=script_name,
            script_length=0,  # Unknown in CLI mode
            audio_file=video_file.replace('.mp4', '.mp3'),
            video_file=video_file,
            drive_link=drive_link,
            status=status,
            duration=duration
        )
        print(f"\nSuccess!")
        print(f"  Sheet Link: {result['sheet_link']}")
        print(f"  Row Number: {result['row_number']}")
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
