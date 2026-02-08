"""
Email Notification Tool
Sends email notifications via Gmail API.
Uses OAuth2 for authentication (shared with Drive).
"""

import os
import sys
import base64
from pathlib import Path
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

from googleapiclient.discovery import build

# Import shared credentials helper
from google_drive_upload import get_google_credentials

# Load environment variables from project root
project_root = Path(__file__).parent.parent
load_dotenv(project_root / ".env")

# Default notification email
NOTIFICATION_EMAIL = os.getenv("NOTIFICATION_EMAIL", "ShakadMagal@gmail.com")


def get_gmail_service():
    """
    Build and return Gmail API service.

    Returns:
        googleapiclient.discovery.Resource for Gmail API
    """
    creds = get_google_credentials()
    return build('gmail', 'v1', credentials=creds)


def send_email(
    to_email: str,
    subject: str,
    body: str,
    html_body: str = None
) -> dict:
    """
    Send an email via Gmail API.

    Args:
        to_email: Recipient email address
        subject: Email subject line
        body: Email body (plain text)
        html_body: Optional HTML body

    Returns:
        dict with 'message_id', 'status'
    """
    print(f"Sending email to {to_email}...")

    service = get_gmail_service()

    # Create message
    if html_body:
        message = MIMEMultipart('alternative')
        message.attach(MIMEText(body, 'plain'))
        message.attach(MIMEText(html_body, 'html'))
    else:
        message = MIMEText(body)

    message['to'] = to_email
    message['subject'] = subject

    # Encode message
    raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')

    # Send message
    sent_message = service.users().messages().send(
        userId='me',
        body={'raw': raw_message}
    ).execute()

    message_id = sent_message.get('id')
    print(f"  Email sent! Message ID: {message_id}")

    return {
        'message_id': message_id,
        'status': 'sent',
        'to_email': to_email
    }


def send_video_notification(
    to_email: str,
    video_name: str,
    video_link: str,
    script_name: str = None,
    duration: int = None,
    sheet_link: str = None
) -> dict:
    """
    Send a formatted video completion notification.

    Args:
        to_email: Recipient email address
        video_name: Name of the generated video
        video_link: Google Drive shareable link
        script_name: Original script filename (optional)
        duration: Processing time in seconds (optional)
        sheet_link: Link to tracking spreadsheet (optional)

    Returns:
        dict with 'message_id', 'status'
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    subject = f"Your video is ready: {video_name}"

    # Plain text body
    body = f"""Hi,

Your avatar video "{video_name}" has been generated successfully!

Video link: {video_link}

Details:
- Script: {script_name or 'N/A'}
- Audio: Saved to output folder
- Processing time: {f'{duration} seconds' if duration else 'N/A'}

{f'View tracking sheet: {sheet_link}' if sheet_link else ''}

Generated on: {timestamp}

---
AYO Engineering - Automated Video Pipeline
"""

    # HTML body for nicer formatting
    html_body = f"""
<html>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
    <h2 style="color: #2c5282;">Your Video is Ready!</h2>

    <p>Your avatar video <strong>"{video_name}"</strong> has been generated successfully!</p>

    <p style="margin: 20px 0;">
        <a href="{video_link}"
           style="background-color: #4299e1; color: white; padding: 12px 24px;
                  text-decoration: none; border-radius: 5px; display: inline-block;">
            Watch Video
        </a>
    </p>

    <h3 style="color: #2c5282;">Details</h3>
    <ul>
        <li><strong>Script:</strong> {script_name or 'N/A'}</li>
        <li><strong>Audio:</strong> Saved to output folder</li>
        <li><strong>Processing time:</strong> {f'{duration} seconds' if duration else 'N/A'}</li>
    </ul>

    {f'<p><a href="{sheet_link}">View Tracking Sheet</a></p>' if sheet_link else ''}

    <hr style="border: none; border-top: 1px solid #e2e8f0; margin: 20px 0;">

    <p style="color: #718096; font-size: 12px;">
        Generated on: {timestamp}<br>
        AYO Engineering - Automated Video Pipeline
    </p>
</body>
</html>
"""

    return send_email(to_email, subject, body, html_body)


def main():
    """CLI entry point."""
    if len(sys.argv) < 3:
        print("Usage: python send_email.py <to_email> <video_link> [video_name]")
        print("\nSends a video completion notification email.")
        print("\nArguments:")
        print("  to_email    Recipient email address")
        print("  video_link  Google Drive shareable link to the video")
        print("  video_name  Optional: Name of the video (default: 'Avatar Video')")
        sys.exit(1)

    to_email = sys.argv[1]
    video_link = sys.argv[2]
    video_name = sys.argv[3] if len(sys.argv) > 3 else "Avatar Video"

    try:
        result = send_video_notification(
            to_email=to_email,
            video_name=video_name,
            video_link=video_link
        )
        print(f"\nSuccess!")
        print(f"  Message ID: {result['message_id']}")
        print(f"  Sent to: {result['to_email']}")
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
