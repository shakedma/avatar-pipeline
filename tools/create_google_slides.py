"""
Create Google Slides presentation for AI Avatar Pipeline.
Uses the Google Slides API to create an editable presentation.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

# Load environment variables
load_dotenv()

# OAuth scopes
SCOPES = [
    'https://www.googleapis.com/auth/presentations',
    'https://www.googleapis.com/auth/drive.file'
]

# Paths
PROJECT_ROOT = Path(__file__).parent.parent
CREDENTIALS_FILE = PROJECT_ROOT / 'credentials.json'
TOKEN_FILE = PROJECT_ROOT / 'slides_token.json'

# Slide dimensions (in EMU - English Metric Units)
# 1 inch = 914400 EMU
SLIDE_WIDTH = 9144000  # 10 inches
SLIDE_HEIGHT = 5143500  # ~5.63 inches (16:9)


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

            print("Opening browser for Google Slides authorization...")
            flow = InstalledAppFlow.from_client_secrets_file(str(CREDENTIALS_FILE), SCOPES)
            credentials = flow.run_local_server(port=0)

        with open(TOKEN_FILE, 'w') as token:
            token.write(credentials.to_json())
        print(f"Credentials saved to {TOKEN_FILE}")

    return credentials


def create_presentation():
    """Create the AI Avatar Pipeline presentation in Google Slides."""

    credentials = get_credentials()
    slides_service = build('slides', 'v1', credentials=credentials)

    # Create new presentation
    presentation = slides_service.presentations().create(
        body={'title': 'AYO Engineering - AI Avatar Video Pipeline'}
    ).execute()

    presentation_id = presentation['presentationId']
    print(f"Created presentation: {presentation_id}")

    # Define slide content
    slides_content = [
        {
            'title': 'AI Avatar Video Pipeline',
            'subtitle': 'Automated Script-to-Video Generation\n\nElevenLabs  |  HeyGen  |  Google Cloud  |  YouTube',
            'is_title_slide': True
        },
        {
            'title': 'The Challenge',
            'body': '''• Creating professional avatar videos is time-consuming

• Manual process: Script → Record → Edit → Upload → Share

• Multiple platforms to manage

• No centralized tracking or automation'''
        },
        {
            'title': 'Our Solution',
            'body': '''A fully automated pipeline that:

• Converts text scripts to professional AI avatar videos

• Generates multiple audio options for review

• Uploads to Google Drive & YouTube automatically

• Tracks everything in a dashboard

• Sends email notifications when complete'''
        },
        {
            'title': 'Two-Phase Workflow',
            'body': '''PHASE 1: Audio Generation
   • Read script (.txt, .docx, .pdf)
   • Generate 2 audio options (stable & expressive)
   • Review & select preferred audio

PHASE 2: Video Generation
   • Generate avatar video with selected audio
   • Upload to Google Drive & YouTube
   • Log to dashboard & send notification'''
        },
        {
            'title': 'Audio Options',
            'body': '''Two voice styles generated from the same script:


Option A - Stable, Consistent
   Best for: Professional presentations, tutorials


Option B - Expressive, Dynamic
   Best for: Marketing, storytelling, engagement


You choose which one to use before video generation!'''
        },
        {
            'title': 'Cloud Integrations',
            'body': '''✓  Google Drive - Video storage & sharing

✓  Google Sheets - Dashboard & tracking

✓  Gmail - Email notifications

✓  YouTube - Video publishing


All integrations are active and automated.'''
        },
        {
            'title': 'Status Dashboard',
            'body': '''Real-time tracking in Google Sheets:

🟢 Green = Completed (Video delivered)
🟡 Yellow = Audio Ready (Waiting for review)
🟠 Orange = Processing (Video generating)
🔴 Red = Error (Something failed)

Dashboard includes: Timestamp, script name, audio/video files,
Drive links, processing duration, and error tracking.'''
        },
        {
            'title': 'File Organization',
            'body': '''input/
   Script files (.txt, .docx, .pdf)

output/
   Audio files & videos

Google Drive
   Videos with shareable links

YouTube
   Published videos (unlisted by default)'''
        },
        {
            'title': 'How to Use',
            'body': '''Step 1: Generate Audio
   python tools/run_pipeline.py input/script.pdf --audio-only

Step 2: Review & Select Audio
   Listen to both options, delete the one you don't want

Step 3: Generate Video
   python tools/run_pipeline.py --continue output/script_OptionA.mp3 --youtube'''
        },
        {
            'title': 'Ready to Scale',
            'subtitle': 'Automated  •  Integrated  •  Trackable\n\n✓ ElevenLabs TTS    ✓ HeyGen Avatar\n✓ Google Suite       ✓ YouTube\n\n\nAYO Engineering  |  ShakadMagal@gmail.com',
            'is_title_slide': True
        }
    ]

    requests = []

    # Create additional slides (first slide already exists)
    for i in range(1, len(slides_content)):
        requests.append({
            'createSlide': {
                'objectId': f'slide_{i}',
                'insertionIndex': i,
                'slideLayoutReference': {
                    'predefinedLayout': 'BLANK'
                }
            }
        })

    # Execute slide creation
    if requests:
        slides_service.presentations().batchUpdate(
            presentationId=presentation_id,
            body={'requests': requests}
        ).execute()

    # Get slide IDs
    presentation = slides_service.presentations().get(
        presentationId=presentation_id
    ).execute()

    slide_ids = [slide['objectId'] for slide in presentation['slides']]

    # Add content to each slide
    for i, (slide_id, content) in enumerate(zip(slide_ids, slides_content)):
        text_requests = []

        is_title_slide = content.get('is_title_slide', False)

        # Title text box
        title_box_id = f'title_box_{i}'
        text_requests.append({
            'createShape': {
                'objectId': title_box_id,
                'shapeType': 'TEXT_BOX',
                'elementProperties': {
                    'pageObjectId': slide_id,
                    'size': {
                        'width': {'magnitude': 8000000, 'unit': 'EMU'},
                        'height': {'magnitude': 800000 if is_title_slide else 600000, 'unit': 'EMU'}
                    },
                    'transform': {
                        'scaleX': 1,
                        'scaleY': 1,
                        'translateX': 572000,
                        'translateY': 1500000 if is_title_slide else 300000,
                        'unit': 'EMU'
                    }
                }
            }
        })

        # Insert title text
        text_requests.append({
            'insertText': {
                'objectId': title_box_id,
                'text': content['title']
            }
        })

        # Style title
        text_requests.append({
            'updateTextStyle': {
                'objectId': title_box_id,
                'style': {
                    'fontSize': {'magnitude': 44 if is_title_slide else 36, 'unit': 'PT'},
                    'bold': True,
                    'foregroundColor': {
                        'opaqueColor': {
                            'rgbColor': {'red': 0.0, 'green': 0.5, 'blue': 0.8}
                        }
                    }
                },
                'fields': 'fontSize,bold,foregroundColor'
            }
        })

        # Center title for title slides
        text_requests.append({
            'updateParagraphStyle': {
                'objectId': title_box_id,
                'style': {
                    'alignment': 'CENTER' if is_title_slide else 'START'
                },
                'fields': 'alignment'
            }
        })

        # Body/Subtitle text box
        if content.get('subtitle') or content.get('body'):
            body_box_id = f'body_box_{i}'
            body_text = content.get('subtitle') or content.get('body')

            text_requests.append({
                'createShape': {
                    'objectId': body_box_id,
                    'shapeType': 'TEXT_BOX',
                    'elementProperties': {
                        'pageObjectId': slide_id,
                        'size': {
                            'width': {'magnitude': 8000000, 'unit': 'EMU'},
                            'height': {'magnitude': 3500000, 'unit': 'EMU'}
                        },
                        'transform': {
                            'scaleX': 1,
                            'scaleY': 1,
                            'translateX': 572000,
                            'translateY': 2500000 if is_title_slide else 1000000,
                            'unit': 'EMU'
                        }
                    }
                }
            })

            text_requests.append({
                'insertText': {
                    'objectId': body_box_id,
                    'text': body_text
                }
            })

            # Style body text
            text_requests.append({
                'updateTextStyle': {
                    'objectId': body_box_id,
                    'style': {
                        'fontSize': {'magnitude': 24 if is_title_slide else 18, 'unit': 'PT'},
                        'foregroundColor': {
                            'opaqueColor': {
                                'rgbColor': {'red': 0.3, 'green': 0.3, 'blue': 0.3}
                            }
                        }
                    },
                    'fields': 'fontSize,foregroundColor'
                }
            })

            # Center subtitle for title slides
            if is_title_slide:
                text_requests.append({
                    'updateParagraphStyle': {
                        'objectId': body_box_id,
                        'style': {
                            'alignment': 'CENTER'
                        },
                        'fields': 'alignment'
                    }
                })

        # Execute requests for this slide
        if text_requests:
            slides_service.presentations().batchUpdate(
                presentationId=presentation_id,
                body={'requests': text_requests}
            ).execute()

        print(f"  Added slide {i + 1}: {content['title']}")

    presentation_url = f"https://docs.google.com/presentation/d/{presentation_id}/edit"
    print(f"\nPresentation created successfully!")
    print(f"URL: {presentation_url}")

    return {
        'presentation_id': presentation_id,
        'url': presentation_url
    }


if __name__ == "__main__":
    result = create_presentation()
    print(f"\nOpen your presentation: {result['url']}")
