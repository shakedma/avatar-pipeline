"""
HeyGen Audio Upload Tool
Uploads an audio file to HeyGen and returns the asset ID.
"""

import os
import sys
import requests
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

UPLOAD_URL = "https://upload.heygen.com/v1/asset"

def get_api_key():
    """Get API key at call time for Streamlit secrets support."""
    return os.getenv("HEYGEN_API_KEY")


def upload_audio(audio_path: str) -> dict:
    """
    Upload an audio file to HeyGen.

    Args:
        audio_path: Path to the audio file (MP3)

    Returns:
        Dictionary containing asset_id and asset_url
    """
    api_key = get_api_key()
    if not api_key:
        raise ValueError("HEYGEN_API_KEY not found in environment variables")

    if not os.path.exists(audio_path):
        raise FileNotFoundError(f"Audio file not found: {audio_path}")

    headers = {
        "X-API-KEY": api_key,
        "Content-Type": "audio/mpeg"
    }

    print(f"Uploading audio file: {audio_path}")

    with open(audio_path, "rb") as f:
        audio_data = f.read()

    response = requests.post(UPLOAD_URL, headers=headers, data=audio_data)

    if response.status_code != 200:
        raise Exception(f"HeyGen upload error: {response.status_code} - {response.text}")

    result = response.json()

    if result.get("code") != 100:
        raise Exception(f"HeyGen upload failed: {result}")

    data = result.get("data", {})
    asset_id = data.get("id")
    asset_url = data.get("url")

    print(f"Upload successful!")
    print(f"  Asset ID: {asset_id}")
    print(f"  Asset URL: {asset_url}")

    return {
        "asset_id": asset_id,
        "asset_url": asset_url
    }


def main():
    """CLI entry point."""
    if len(sys.argv) < 2:
        print("Usage: python heygen_upload_audio.py <audio_file_path>")
        print("Example: python heygen_upload_audio.py ../.tmp/audio/output.mp3")
        sys.exit(1)

    audio_path = sys.argv[1]

    try:
        result = upload_audio(audio_path)
        print(f"\nAsset ID for video generation: {result['asset_id']}")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
