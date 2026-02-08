"""
HeyGen Video Generation Tool
Creates an avatar video using HeyGen API with uploaded audio.
"""

import os
import sys
import json
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

HEYGEN_API_KEY = os.getenv("HEYGEN_API_KEY")
HEYGEN_AVATAR_ID = os.getenv("HEYGEN_AVATAR_ID")
VIDEO_GENERATE_URL = "https://api.heygen.com/v2/video/generate"


def create_video(audio_asset_id: str, avatar_id: str = None, background_color: str = "#ffffff") -> str:
    """
    Create an avatar video using HeyGen API.

    Args:
        audio_asset_id: The asset ID of the uploaded audio
        avatar_id: Optional avatar/talking_photo ID (uses env default if not provided)
        background_color: Background color in hex format

    Returns:
        The video_id for tracking the generation
    """
    if not HEYGEN_API_KEY:
        raise ValueError("HEYGEN_API_KEY not found in environment variables")

    avatar = avatar_id or HEYGEN_AVATAR_ID
    if not avatar:
        raise ValueError("Avatar ID not provided and HEYGEN_AVATAR_ID not found in environment")

    headers = {
        "X-Api-Key": HEYGEN_API_KEY,
        "Content-Type": "application/json"
    }

    # Video generation payload
    payload = {
        "video_inputs": [
            {
                "character": {
                    "type": "talking_photo",
                    "talking_photo_id": avatar
                },
                "voice": {
                    "type": "audio",
                    "audio_asset_id": audio_asset_id
                },
                "background": {
                    "type": "color",
                    "value": background_color
                }
            }
        ],
        "dimension": {
            "width": 1280,
            "height": 720
        }
    }

    print(f"Creating video with avatar: {avatar}")
    print(f"Using audio asset: {audio_asset_id}")

    response = requests.post(VIDEO_GENERATE_URL, headers=headers, json=payload)

    if response.status_code != 200:
        raise Exception(f"HeyGen video generation error: {response.status_code} - {response.text}")

    result = response.json()

    if result.get("error"):
        raise Exception(f"HeyGen video generation failed: {result['error']}")

    video_id = result.get("data", {}).get("video_id")

    if not video_id:
        raise Exception(f"No video_id returned: {result}")

    print(f"Video generation started!")
    print(f"  Video ID: {video_id}")

    return video_id


def main():
    """CLI entry point."""
    if len(sys.argv) < 2:
        print("Usage: python heygen_create_video.py <audio_asset_id> [avatar_id] [background_color]")
        print("Example: python heygen_create_video.py abc123 def456 #000000")
        sys.exit(1)

    audio_asset_id = sys.argv[1]
    avatar_id = sys.argv[2] if len(sys.argv) > 2 else None
    background_color = sys.argv[3] if len(sys.argv) > 3 else "#ffffff"

    try:
        video_id = create_video(audio_asset_id, avatar_id, background_color)
        print(f"\nVideo ID for status check: {video_id}")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
