"""
Script-to-Avatar Video Pipeline (Two-Phase Workflow)

PHASE 1: Audio Generation (--audio-only)
  - Read script file
  - Generate two audio options (A: stable, B: expressive)
  - Save to output folder
  - STOP for user review

PHASE 2: Video Generation (--continue <audio_file>)
  - Upload selected audio to HeyGen
  - Generate avatar video
  - Download video
  - (Optional) Upload to Drive, log to Sheets, send email

FULL PIPELINE (default - no flags):
  - Runs both phases automatically using Option A
"""

import os
import sys
import shutil
import argparse
import time
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables from project root
project_root = Path(__file__).parent.parent
load_dotenv(project_root / ".env")

# Import our tools
from elevenlabs_tts import text_to_speech, text_to_speech_dual
from heygen_upload_audio import upload_audio
from heygen_create_video import create_video
from heygen_download_video import wait_and_download
from google_drive_upload import upload_to_drive
from google_sheets_logger import log_video_generation
from send_email import send_video_notification
from youtube_upload import upload_video as upload_to_youtube

# Default notification email
NOTIFICATION_EMAIL = os.getenv("NOTIFICATION_EMAIL", "ShakadMagal@gmail.com")

# Default YouTube settings
YOUTUBE_PRIVACY = "unlisted"  # Options: private, unlisted, public

# Output directory
OUTPUT_DIR = project_root / "output"
TMP_DIR = project_root / ".tmp"


def read_script_file(file_path: str) -> str:
    """
    Read text content from various file formats.
    Supports: .txt, .docx, .pdf
    """
    path = Path(file_path)
    extension = path.suffix.lower()

    if extension == ".txt":
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read().strip()

    elif extension == ".docx":
        try:
            from docx import Document
        except ImportError:
            raise ImportError("python-docx is required for .docx files. Run: pip install python-docx")
        doc = Document(file_path)
        paragraphs = [para.text for para in doc.paragraphs if para.text.strip()]
        return "\n\n".join(paragraphs)

    elif extension == ".pdf":
        try:
            from PyPDF2 import PdfReader
        except ImportError:
            raise ImportError("PyPDF2 is required for .pdf files. Run: pip install PyPDF2")
        reader = PdfReader(file_path)
        text_parts = []
        for page in reader.pages:
            text = page.extract_text()
            if text:
                text_parts.append(text.strip())
        return "\n\n".join(text_parts)

    else:
        raise ValueError(f"Unsupported file format: {extension}. Supported: .txt, .docx, .pdf")


# =============================================================================
# PHASE 1: AUDIO GENERATION ONLY
# =============================================================================

def generate_audio_only(script_path: str) -> dict:
    """
    Phase 1: Generate audio options only, stop for user review.

    Args:
        script_path: Path to the script file

    Returns:
        dict with audio file paths and script info
    """
    start_time = time.time()

    # Get script name for output files
    script_name = Path(script_path).name
    script_stem = Path(script_path).stem

    print("=" * 60)
    print("PHASE 1: AUDIO GENERATION")
    print("=" * 60)

    # Step 1: Read the script
    file_ext = Path(script_path).suffix.lower()
    print(f"\n[STEP 1/4] Reading script ({file_ext} file)...")
    script_text = read_script_file(script_path)

    if not script_text:
        raise ValueError("Script file is empty")

    script_length = len(script_text)
    print(f"  Script: {script_name}")
    print(f"  Length: {script_length} characters")

    # Step 2: Generate Option A (stable)
    print(f"\n[STEP 2/4] Generating Option A (stable/consistent)...")
    audio_tmp_base = TMP_DIR / "audio" / script_stem
    audio_results = text_to_speech_dual(script_text, str(audio_tmp_base))

    # Step 3: Copy to output folder
    print(f"\n[STEP 3/4] Saving audio files to output folder...")
    audio_output_a = OUTPUT_DIR / f"{script_stem}_audio_OptionA.mp3"
    audio_output_b = OUTPUT_DIR / f"{script_stem}_audio_OptionB.mp3"

    # Ensure output directory exists
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    shutil.copy2(audio_results['option_a'], audio_output_a)
    shutil.copy2(audio_results['option_b'], audio_output_b)

    print(f"  Option A (stable): {audio_output_a}")
    print(f"  Option B (expressive): {audio_output_b}")

    # Step 4: Done - ready for review
    duration = int(time.time() - start_time)
    print(f"\n[STEP 4/4] Audio files ready for review")

    print("\n" + "=" * 60)
    print("AUDIO GENERATION COMPLETE")
    print("=" * 60)

    print(f"\nPlease review the audio files:")
    print(f"  - {audio_output_a}")
    print(f"    (stable/consistent delivery)")
    print(f"  - {audio_output_b}")
    print(f"    (expressive/dynamic delivery)")

    print(f"\nDelete the one you don't want, then run:")
    print(f"  python tools/run_pipeline.py --continue \"{audio_output_a}\"")
    print(f"  OR")
    print(f"  python tools/run_pipeline.py --continue \"{audio_output_b}\"")

    print(f"\nGeneration time: {duration} seconds")

    return {
        'script_name': script_name,
        'script_stem': script_stem,
        'script_length': script_length,
        'audio_option_a': str(audio_output_a),
        'audio_option_b': str(audio_output_b),
        'duration': duration
    }


# =============================================================================
# PHASE 2: VIDEO GENERATION (Continue with selected audio)
# =============================================================================

def continue_with_audio(
    audio_path: str,
    output_name: str = None,
    background_color: str = "#ffffff",
    skip_cloud: bool = False,
    email: str = None,
    upload_youtube: bool = False,
    youtube_title: str = None,
    youtube_privacy: str = YOUTUBE_PRIVACY
) -> dict:
    """
    Phase 2: Continue pipeline with selected audio file.

    Args:
        audio_path: Path to the selected audio file
        output_name: Optional name for video file
        background_color: Background color for video
        skip_cloud: Skip Google integrations
        email: Email for notification
        upload_youtube: Upload to YouTube
        youtube_title: Custom YouTube title (default: video name)
        youtube_privacy: YouTube privacy: private, unlisted, public

    Returns:
        dict with video path and other results
    """
    start_time = time.time()

    # Validate audio file exists
    audio_file = Path(audio_path)
    if not audio_file.exists():
        raise FileNotFoundError(f"Audio file not found: {audio_path}")

    # Determine output name from audio filename
    # e.g., "sample_script_audio_OptionA.mp3" -> "sample_script"
    audio_stem = audio_file.stem  # "sample_script_audio_OptionA"
    if "_audio_OptionA" in audio_stem or "_audio_OptionB" in audio_stem:
        # New naming convention: script_audio_OptionA
        base_name = audio_stem.replace("_audio_OptionA", "").replace("_audio_OptionB", "")
        selected_option = "OptionA" if "_audio_OptionA" in audio_stem else "OptionB"
    elif audio_stem.endswith("_OptionA") or audio_stem.endswith("_OptionB"):
        # Legacy naming: script_OptionA (for backwards compatibility)
        base_name = audio_stem.rsplit("_", 1)[0]
        selected_option = audio_stem.rsplit("_", 1)[1]
    else:
        base_name = audio_stem
        selected_option = "Custom"

    video_name = output_name or base_name
    video_path = OUTPUT_DIR / f"{video_name}_video.mp4"

    # Notification email
    notification_email = email or NOTIFICATION_EMAIL

    # Calculate total steps
    total_steps = 3  # Base: upload, generate, download
    if not skip_cloud:
        total_steps += 3  # Drive, Sheets, Email
    if upload_youtube:
        total_steps += 1  # YouTube

    print("=" * 60)
    print("PHASE 2: VIDEO GENERATION")
    print("=" * 60)
    print(f"\nUsing audio: {audio_path}")
    print(f"Selected option: {selected_option}")

    # Step 1: Upload audio to HeyGen
    print(f"\n[STEP 1/{total_steps}] Uploading audio to HeyGen...")
    upload_result = upload_audio(str(audio_file))
    audio_asset_id = upload_result["asset_id"]
    print(f"  Asset ID: {audio_asset_id}")

    # Step 2: Generate avatar video
    print(f"\n[STEP 2/{total_steps}] Generating avatar video (HeyGen)...")
    video_id = create_video(audio_asset_id, background_color=background_color)
    print(f"  Video ID: {video_id}")

    # Step 3: Wait and download
    print(f"\n[STEP 3/{total_steps}] Waiting for video and downloading...")
    final_video = wait_and_download(video_id, str(video_path))

    # Calculate duration
    duration = int(time.time() - start_time)

    # Initialize results
    result = {
        'video_path': final_video,
        'audio_path': str(audio_file),
        'selected_option': selected_option,
        'drive_link': None,
        'sheet_link': None,
        'youtube_url': None,
        'duration': duration
    }

    current_step = 3  # We've completed 3 steps

    # Cloud integration steps (optional)
    if not skip_cloud:
        try:
            # Upload to Google Drive
            current_step += 1
            print(f"\n[STEP {current_step}/{total_steps}] Uploading video to Google Drive...")
            drive_result = upload_to_drive(final_video)
            result['drive_link'] = drive_result['shareable_link']

            # Log to Google Sheets
            current_step += 1
            print(f"\n[STEP {current_step}/{total_steps}] Logging to Google Sheets...")
            sheet_result = log_video_generation(
                script_name=base_name,
                script_length=0,  # Not available in Phase 2
                audio_file=audio_file.name,
                video_file=f"{video_name}_video.mp4",
                drive_link=result['drive_link'],
                status="Completed",
                duration=duration
            )
            result['sheet_link'] = sheet_result['sheet_link']

            # Send email notification
            current_step += 1
            print(f"\n[STEP {current_step}/{total_steps}] Sending email notification...")
            send_video_notification(
                to_email=notification_email,
                video_name=video_name,
                video_link=result['drive_link'],
                script_name=base_name,
                duration=duration,
                sheet_link=result['sheet_link']
            )
            print(f"  Email sent to: {notification_email}")

        except Exception as cloud_error:
            print(f"\n  Warning: Cloud integration error: {cloud_error}")
            print("  Video was created successfully but cloud steps failed.")
            print("  You may need to set up Google credentials (credentials.json)")

    # YouTube upload (optional)
    if upload_youtube:
        try:
            current_step += 1
            print(f"\n[STEP {current_step}/{total_steps}] Uploading to YouTube...")
            yt_title = youtube_title or f"Avatar Video: {video_name}"
            yt_description = f"Generated with AYO Engineering AI Avatar Pipeline\n\nScript: {base_name}"

            youtube_result = upload_to_youtube(
                video_path=final_video,
                title=yt_title,
                description=yt_description,
                privacy_status=youtube_privacy
            )
            result['youtube_url'] = youtube_result['url']
            print(f"  YouTube URL: {result['youtube_url']}")

        except Exception as yt_error:
            print(f"\n  Warning: YouTube upload error: {yt_error}")
            print("  Video was created successfully but YouTube upload failed.")

    print("\n" + "=" * 60)
    print("PIPELINE COMPLETE!")
    print("=" * 60)
    print(f"\nFinal video: {final_video}")
    print(f"Audio used: {audio_file.name} ({selected_option})")
    if result['drive_link']:
        print(f"Google Drive: {result['drive_link']}")
    if result['youtube_url']:
        print(f"YouTube: {result['youtube_url']}")
    if result['sheet_link']:
        print(f"Tracking sheet: {result['sheet_link']}")
    print(f"Total time: {duration} seconds")
    print(f"\nYou can now import this video into Filmora.")

    return result


# =============================================================================
# FULL PIPELINE (Both phases, auto-selects Option A)
# =============================================================================

def run_full_pipeline(
    script_path: str,
    output_name: str = None,
    background_color: str = "#ffffff",
    skip_cloud: bool = False,
    email: str = None,
    upload_youtube: bool = False,
    youtube_title: str = None,
    youtube_privacy: str = YOUTUBE_PRIVACY
) -> dict:
    """
    Run the full pipeline (both phases) automatically using Option A.
    """
    # Phase 1: Generate audio
    audio_result = generate_audio_only(script_path)

    print("\n" + "-" * 60)
    print("Automatically continuing with Option A...")
    print("-" * 60)

    # Phase 2: Generate video with Option A
    video_result = continue_with_audio(
        audio_result['audio_option_a'],
        output_name=output_name,
        background_color=background_color,
        skip_cloud=skip_cloud,
        email=email,
        upload_youtube=upload_youtube,
        youtube_title=youtube_title,
        youtube_privacy=youtube_privacy
    )

    # Combine results
    return {
        **audio_result,
        **video_result
    }


# =============================================================================
# CLI ENTRY POINT
# =============================================================================

def main():
    """CLI entry point with two-phase workflow support."""
    parser = argparse.ArgumentParser(
        description="Script-to-Avatar Video Pipeline (Two-Phase Workflow)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Phase 1: Generate audio only (for review)
  python run_pipeline.py input/script.txt --audio-only

  # Phase 2: Continue with selected audio
  python run_pipeline.py --continue output/script_OptionA.mp3

  # Full pipeline (both phases, auto-selects Option A)
  python run_pipeline.py input/script.txt
        """
    )

    parser.add_argument(
        "script",
        nargs="?",
        help="Path to the script file (.txt, .docx, or .pdf)"
    )
    parser.add_argument(
        "-n", "--name",
        help="Output file name (without extension)",
        default=None
    )
    parser.add_argument(
        "-b", "--background",
        help="Background color (hex format, e.g., #ffffff)",
        default="#ffffff"
    )
    parser.add_argument(
        "--skip-cloud",
        action="store_true",
        help="Skip Google Drive upload, Sheets logging, and email notification"
    )
    parser.add_argument(
        "--email",
        help=f"Email address for notification (default: {NOTIFICATION_EMAIL})",
        default=None
    )
    parser.add_argument(
        "--audio-only",
        action="store_true",
        help="PHASE 1: Generate audio options only, stop for review"
    )
    parser.add_argument(
        "--continue",
        dest="continue_audio",
        metavar="AUDIO_FILE",
        help="PHASE 2: Continue pipeline with selected audio file"
    )
    parser.add_argument(
        "--youtube",
        action="store_true",
        help="Upload video to YouTube (unlisted by default)"
    )
    parser.add_argument(
        "--youtube-title",
        help="Custom title for YouTube video",
        default=None
    )
    parser.add_argument(
        "--youtube-privacy",
        choices=["private", "unlisted", "public"],
        default="unlisted",
        help="YouTube privacy setting (default: unlisted)"
    )

    args = parser.parse_args()

    try:
        # PHASE 2: Continue with selected audio
        if args.continue_audio:
            audio_path = Path(args.continue_audio).resolve()
            if not audio_path.exists():
                print(f"Error: Audio file not found: {audio_path}")
                sys.exit(1)

            result = continue_with_audio(
                str(audio_path),
                output_name=args.name,
                background_color=args.background,
                skip_cloud=args.skip_cloud,
                email=args.email,
                upload_youtube=args.youtube,
                youtube_title=args.youtube_title,
                youtube_privacy=args.youtube_privacy
            )
            print(f"\nSuccess! Video created: {result['video_path']}")

        # PHASE 1: Audio only
        elif args.audio_only:
            if not args.script:
                print("Error: Script file required for --audio-only mode")
                print("Usage: python run_pipeline.py input/script.txt --audio-only")
                sys.exit(1)

            script_path = Path(args.script).resolve()
            if not script_path.exists():
                print(f"Error: Script file not found: {script_path}")
                sys.exit(1)

            result = generate_audio_only(str(script_path))
            print(f"\nAudio files ready for review!")

        # FULL PIPELINE (default)
        else:
            if not args.script:
                parser.print_help()
                sys.exit(1)

            script_path = Path(args.script).resolve()
            if not script_path.exists():
                print(f"Error: Script file not found: {script_path}")
                sys.exit(1)

            result = run_full_pipeline(
                str(script_path),
                output_name=args.name,
                background_color=args.background,
                skip_cloud=args.skip_cloud,
                email=args.email,
                upload_youtube=args.youtube,
                youtube_title=args.youtube_title,
                youtube_privacy=args.youtube_privacy
            )
            print(f"\nSuccess! Video created: {result['video_path']}")

    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
