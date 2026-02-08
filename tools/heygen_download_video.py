"""
HeyGen Video Download Tool
Polls for video status and downloads the completed video.
"""

import os
import sys
import time
import requests
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

HEYGEN_API_KEY = os.getenv("HEYGEN_API_KEY")
VIDEO_STATUS_URL = "https://api.heygen.com/v1/video_status.get"


def check_video_status(video_id: str) -> dict:
    """
    Check the status of a video generation.

    Args:
        video_id: The video ID to check

    Returns:
        Dictionary with status info including video_url when complete
    """
    if not HEYGEN_API_KEY:
        raise ValueError("HEYGEN_API_KEY not found in environment variables")

    headers = {
        "X-Api-Key": HEYGEN_API_KEY
    }

    params = {
        "video_id": video_id
    }

    response = requests.get(VIDEO_STATUS_URL, headers=headers, params=params, timeout=30)

    if response.status_code != 200:
        raise Exception(f"HeyGen status check error: {response.status_code} - {response.text}")

    result = response.json()
    return result.get("data", {})


def wait_for_video(video_id: str, poll_interval: int = 10, max_wait: int = 900) -> dict:
    """
    Poll for video completion.

    Args:
        video_id: The video ID to wait for
        poll_interval: Seconds between status checks
        max_wait: Maximum seconds to wait (default 15 minutes)

    Returns:
        Dictionary with video data including video_url
    """
    print(f"Waiting for video {video_id} to complete...")
    print(f"(This may take 5-10 minutes for HeyGen to process)")
    start_time = time.time()
    retry_count = 0
    max_retries = 3

    while True:
        elapsed = time.time() - start_time
        if elapsed > max_wait:
            raise TimeoutError(f"Video generation timed out after {max_wait} seconds")

        try:
            status_data = check_video_status(video_id)
            retry_count = 0  # Reset retry count on success
        except requests.exceptions.Timeout:
            retry_count += 1
            if retry_count >= max_retries:
                raise
            print(f"  Network timeout, retrying ({retry_count}/{max_retries})...")
            time.sleep(5)
            continue
        except requests.exceptions.RequestException as e:
            retry_count += 1
            if retry_count >= max_retries:
                raise
            print(f"  Network error: {e}, retrying ({retry_count}/{max_retries})...")
            time.sleep(5)
            continue

        status = status_data.get("status")

        print(f"  Status: {status} (elapsed: {int(elapsed)}s)")

        if status == "completed":
            print("Video generation completed!")
            return status_data
        elif status == "failed":
            error = status_data.get("error", "Unknown error")
            raise Exception(f"Video generation failed: {error}")
        elif status in ["pending", "processing", "waiting"]:
            time.sleep(poll_interval)
        else:
            print(f"  Unknown status: {status}")
            time.sleep(poll_interval)


def download_video(video_url: str, output_path: str) -> str:
    """
    Download a video from URL.

    Args:
        video_url: URL of the video to download
        output_path: Local path to save the video

    Returns:
        Path to the downloaded video
    """
    print(f"Downloading video to: {output_path}")

    response = requests.get(video_url, stream=True)

    if response.status_code != 200:
        raise Exception(f"Download error: {response.status_code}")

    # Ensure output directory exists
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "wb") as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)

    print(f"Video downloaded successfully: {output_path}")
    return output_path


def wait_and_download(video_id: str, output_path: str, poll_interval: int = 10, max_wait: int = 600) -> str:
    """
    Wait for video completion and download it.

    Args:
        video_id: The video ID to wait for
        output_path: Local path to save the video
        poll_interval: Seconds between status checks
        max_wait: Maximum seconds to wait

    Returns:
        Path to the downloaded video
    """
    status_data = wait_for_video(video_id, poll_interval, max_wait)
    video_url = status_data.get("video_url")

    if not video_url:
        raise Exception("No video URL in completed status")

    return download_video(video_url, output_path)


def main():
    """CLI entry point."""
    if len(sys.argv) < 3:
        print("Usage: python heygen_download_video.py <video_id> <output_path>")
        print("Example: python heygen_download_video.py abc123 ../output/avatar_video.mp4")
        sys.exit(1)

    video_id = sys.argv[1]
    output_path = sys.argv[2]

    try:
        result = wait_and_download(video_id, output_path)
        print(f"\nVideo saved to: {result}")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
