"""
AI Avatar Pipeline - Web Interface
Streamlit app for generating avatar videos from scripts.
"""

import os
import sys
import tempfile
import time
from pathlib import Path

import streamlit as st

# Add tools directory to path for imports
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "tools"))

from dotenv import load_dotenv

# Load environment variables - check both .env and Streamlit secrets
load_dotenv(project_root / ".env")

# Override with Streamlit secrets if available (for cloud deployment)
if hasattr(st, 'secrets'):
    for key in ['ELEVENLABS_API_KEY', 'ELEVENLABS_VOICE_ID', 'ELEVENLABS_MODEL',
                'HEYGEN_API_KEY', 'HEYGEN_AVATAR_ID', 'NOTIFICATION_EMAIL',
                'GOOGLE_SHEET_ID', 'GOOGLE_DRIVE_FOLDER_ID']:
        if key in st.secrets:
            os.environ[key] = st.secrets[key]

# Import pipeline tools (after setting up environment)
from elevenlabs_tts import text_to_speech_dual
from heygen_upload_audio import upload_audio
from heygen_create_video import create_video
from heygen_download_video import wait_and_download

# Directories
OUTPUT_DIR = project_root / "output"
TMP_DIR = project_root / ".tmp"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
TMP_DIR.mkdir(parents=True, exist_ok=True)


def check_password():
    """Simple password protection."""
    # Check if password is configured
    if 'APP_PASSWORD' not in st.secrets:
        # No password configured - allow access (for local dev)
        return True

    if 'authenticated' in st.session_state and st.session_state.authenticated:
        return True

    st.title("AI Avatar Pipeline")
    password = st.text_input("Enter password to continue:", type="password")

    if password:
        if password == st.secrets["APP_PASSWORD"]:
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("Incorrect password")

    return False


def read_script_file(uploaded_file) -> str:
    """Read text content from uploaded file."""
    file_ext = Path(uploaded_file.name).suffix.lower()

    if file_ext == ".txt":
        return uploaded_file.read().decode("utf-8").strip()

    elif file_ext == ".docx":
        from docx import Document
        import io
        doc = Document(io.BytesIO(uploaded_file.read()))
        paragraphs = [para.text for para in doc.paragraphs if para.text.strip()]
        return "\n\n".join(paragraphs)

    elif file_ext == ".pdf":
        from PyPDF2 import PdfReader
        import io
        reader = PdfReader(io.BytesIO(uploaded_file.read()))
        text_parts = []
        for page in reader.pages:
            text = page.extract_text()
            if text:
                text_parts.append(text.strip())
        return "\n\n".join(text_parts)

    else:
        raise ValueError(f"Unsupported file format: {file_ext}")


def main():
    st.set_page_config(
        page_title="AI Avatar Pipeline",
        page_icon="🎬",
        layout="centered"
    )

    # Password check
    if not check_password():
        return

    # Header
    st.title("🎬 AI Avatar Pipeline")
    st.markdown("Transform your scripts into professional avatar videos")

    # Initialize session state
    if 'phase' not in st.session_state:
        st.session_state.phase = 'upload'  # upload, audio_generated, video_generated
    if 'script_text' not in st.session_state:
        st.session_state.script_text = None
    if 'script_name' not in st.session_state:
        st.session_state.script_name = None
    if 'audio_a_path' not in st.session_state:
        st.session_state.audio_a_path = None
    if 'audio_b_path' not in st.session_state:
        st.session_state.audio_b_path = None
    if 'selected_audio' not in st.session_state:
        st.session_state.selected_audio = None
    if 'video_path' not in st.session_state:
        st.session_state.video_path = None

    # Reset button
    if st.session_state.phase != 'upload':
        if st.button("Start Over", type="secondary"):
            for key in ['phase', 'script_text', 'script_name', 'audio_a_path',
                       'audio_b_path', 'selected_audio', 'video_path']:
                if key in st.session_state:
                    del st.session_state[key]
            st.rerun()

    st.divider()

    # ==========================================================================
    # PHASE 1: Upload Script
    # ==========================================================================

    st.subheader("📄 Step 1: Upload Script")

    if st.session_state.phase == 'upload':
        uploaded_file = st.file_uploader(
            "Choose a script file",
            type=["txt", "docx", "pdf"],
            help="Supported formats: .txt, .docx, .pdf"
        )

        if uploaded_file:
            try:
                script_text = read_script_file(uploaded_file)
                st.session_state.script_text = script_text
                st.session_state.script_name = Path(uploaded_file.name).stem

                st.success(f"Script loaded: {len(script_text)} characters")

                with st.expander("Preview script"):
                    st.text(script_text[:1000] + ("..." if len(script_text) > 1000 else ""))

                if st.button("🎵 Generate Audio Options", type="primary"):
                    st.session_state.phase = 'generating_audio'
                    st.rerun()

            except Exception as e:
                st.error(f"Error reading file: {e}")
    else:
        st.success(f"Script: {st.session_state.script_name} ({len(st.session_state.script_text)} characters)")

    # ==========================================================================
    # PHASE 2: Generate Audio
    # ==========================================================================

    if st.session_state.phase == 'generating_audio':
        st.subheader("🎵 Step 2: Generating Audio...")

        progress_bar = st.progress(0)
        status_text = st.empty()

        try:
            status_text.text("Generating Option A (stable delivery)...")
            progress_bar.progress(25)

            # Generate audio files
            audio_base = TMP_DIR / "audio" / st.session_state.script_name
            audio_base.parent.mkdir(parents=True, exist_ok=True)

            results = text_to_speech_dual(
                st.session_state.script_text,
                str(audio_base)
            )

            progress_bar.progress(75)
            status_text.text("Saving audio files...")

            # Copy to output
            import shutil
            audio_a_output = OUTPUT_DIR / f"{st.session_state.script_name}_audio_OptionA.mp3"
            audio_b_output = OUTPUT_DIR / f"{st.session_state.script_name}_audio_OptionB.mp3"

            shutil.copy2(results['option_a'], audio_a_output)
            shutil.copy2(results['option_b'], audio_b_output)

            st.session_state.audio_a_path = str(audio_a_output)
            st.session_state.audio_b_path = str(audio_b_output)

            progress_bar.progress(100)
            status_text.text("Audio generation complete!")

            st.session_state.phase = 'audio_generated'
            time.sleep(1)
            st.rerun()

        except Exception as e:
            st.error(f"Error generating audio: {e}")
            st.session_state.phase = 'upload'

    # ==========================================================================
    # PHASE 3: Select Audio
    # ==========================================================================

    if st.session_state.phase in ['audio_generated', 'video_generated']:
        st.subheader("🎧 Step 2: Select Audio")

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**Option A** (Stable)")
            st.audio(st.session_state.audio_a_path)
            if st.session_state.phase == 'audio_generated':
                if st.button("Select Option A", key="select_a"):
                    st.session_state.selected_audio = st.session_state.audio_a_path

        with col2:
            st.markdown("**Option B** (Expressive)")
            st.audio(st.session_state.audio_b_path)
            if st.session_state.phase == 'audio_generated':
                if st.button("Select Option B", key="select_b"):
                    st.session_state.selected_audio = st.session_state.audio_b_path

        if st.session_state.selected_audio and st.session_state.phase == 'audio_generated':
            selected_name = "Option A" if "OptionA" in st.session_state.selected_audio else "Option B"
            st.success(f"Selected: {selected_name}")

            if st.button("🎬 Generate Video", type="primary"):
                st.session_state.phase = 'generating_video'
                st.rerun()

    # ==========================================================================
    # PHASE 4: Generate Video
    # ==========================================================================

    if st.session_state.phase == 'generating_video':
        st.subheader("🎬 Step 3: Generating Video...")

        progress_bar = st.progress(0)
        status_text = st.empty()

        try:
            # Step 1: Upload audio to HeyGen
            status_text.text("Uploading audio to HeyGen...")
            progress_bar.progress(10)

            upload_result = upload_audio(st.session_state.selected_audio)
            audio_asset_id = upload_result["asset_id"]

            # Step 2: Create video
            status_text.text("Creating avatar video (this may take a few minutes)...")
            progress_bar.progress(25)

            video_id = create_video(audio_asset_id)

            # Step 3: Wait and download
            status_text.text("Waiting for video generation...")
            progress_bar.progress(40)

            video_output = OUTPUT_DIR / f"{st.session_state.script_name}_video.mp4"

            # Poll for completion with progress updates
            final_video = wait_and_download(video_id, str(video_output))

            progress_bar.progress(100)
            status_text.text("Video generation complete!")

            st.session_state.video_path = final_video
            st.session_state.phase = 'video_generated'
            time.sleep(1)
            st.rerun()

        except Exception as e:
            st.error(f"Error generating video: {e}")
            import traceback
            st.code(traceback.format_exc())
            st.session_state.phase = 'audio_generated'

    # ==========================================================================
    # PHASE 5: Download Video
    # ==========================================================================

    if st.session_state.phase == 'video_generated':
        st.subheader("✅ Step 3: Video Ready!")

        st.video(st.session_state.video_path)

        # Download button
        with open(st.session_state.video_path, 'rb') as f:
            video_bytes = f.read()

        st.download_button(
            label="⬇️ Download Video",
            data=video_bytes,
            file_name=f"{st.session_state.script_name}_video.mp4",
            mime="video/mp4",
            type="primary"
        )

        st.success("Your video is ready! Click above to download.")

    # Footer
    st.divider()
    st.caption("AI Avatar Pipeline - Powered by ElevenLabs & HeyGen")


if __name__ == "__main__":
    main()
