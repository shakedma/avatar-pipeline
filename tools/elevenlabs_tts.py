"""
ElevenLabs Text-to-Speech Tool
Converts text to audio using ElevenLabs API with a specified voice.

Supports Audio Tags (square brackets) for tone/emotion control:
  [excited] Hello!     - Speaks with excitement
  [whisper] Secret     - Whispers the text
  [sad] I'm sorry      - Sad tone
  [pause]              - Adds a pause

Note: Audio Tags require the Eleven v3 model. If v3 is not available,
the script will fall back to v2 and strip the tags.
"""

import os
import sys
import re
import requests
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def get_api_key():
    """Get API key - reads at call time to support Streamlit secrets."""
    return os.getenv("ELEVENLABS_API_KEY")

def get_voice_id():
    """Get voice ID - reads at call time to support Streamlit secrets."""
    return os.getenv("ELEVENLABS_VOICE_ID")

# Keep for backward compatibility with CLI usage
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID")

# Model options:
# - "eleven_v3" - Supports audio tags [emotion], newest model (alpha)
# - "eleven_turbo_v2_5" - Fast, good quality
# - "eleven_multilingual_v2" - Best for multiple languages
# - "eleven_monolingual_v1" - Original English model
DEFAULT_MODEL = os.getenv("ELEVENLABS_MODEL", "eleven_v3")
FALLBACK_MODEL = "eleven_multilingual_v2"


def strip_audio_tags(text: str) -> str:
    """
    Remove audio tags from text for models that don't support them.

    Example: "[excited] Hello there!" -> "Hello there!"
    """
    # Remove tags like [excited], [whisper], [pause], etc.
    return re.sub(r'\[[\w\s]+\]\s*', '', text)


def has_audio_tags(text: str) -> bool:
    """Check if text contains audio tags."""
    return bool(re.search(r'\[[\w\s]+\]', text))


def text_to_speech(
    text: str,
    output_path: str,
    voice_id: str = None,
    stability: float = 0.5,
    similarity_boost: float = 0.75,
    model_id: str = None
) -> str:
    """
    Convert text to speech using ElevenLabs API.

    Args:
        text: The text to convert to speech (supports [audio tags] with v3 model)
        output_path: Path where the audio file will be saved
        voice_id: Optional voice ID (uses env default if not provided)
        stability: Voice stability (0.0-1.0). Higher = more consistent, lower = more expressive
        similarity_boost: Voice similarity boost (0.0-1.0). Higher = closer to original voice
        model_id: Model to use (default: eleven_v3 for audio tag support)

    Returns:
        Path to the generated audio file
    """
    api_key = get_api_key()
    if not api_key:
        raise ValueError("ELEVENLABS_API_KEY not found in environment variables")

    voice = voice_id or get_voice_id()
    if not voice:
        raise ValueError("Voice ID not provided and ELEVENLABS_VOICE_ID not found in environment")

    # Use specified model, default, or fallback
    model = model_id or DEFAULT_MODEL

    # Check if text has audio tags
    contains_tags = has_audio_tags(text)
    if contains_tags:
        print(f"  Audio tags detected in script")

    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice}"

    headers = {
        "Accept": "audio/mpeg",
        "Content-Type": "application/json",
        "xi-api-key": api_key
    }

    data = {
        "text": text,
        "model_id": model,
        "voice_settings": {
            "stability": stability,
            "similarity_boost": similarity_boost
        }
    }

    print(f"Generating audio for {len(text)} characters using {model}...")
    print(f"  Settings: stability={stability}, similarity={similarity_boost}")
    response = requests.post(url, json=data, headers=headers)

    # If v3 model fails, try fallback with stripped tags
    if response.status_code != 200 and model == "eleven_v3":
        print(f"  Note: eleven_v3 model not available, falling back to {FALLBACK_MODEL}")

        # Strip audio tags for the fallback model
        if contains_tags:
            text = strip_audio_tags(text)
            print(f"  Audio tags removed for fallback model")

        data["model_id"] = FALLBACK_MODEL
        data["text"] = text
        response = requests.post(url, json=data, headers=headers)

    if response.status_code != 200:
        raise Exception(f"ElevenLabs API error: {response.status_code} - {response.text}")

    # Ensure output directory exists
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    # Save the audio file
    with open(output_path, "wb") as f:
        f.write(response.content)

    print(f"Audio saved to: {output_path}")
    return output_path


def text_to_speech_dual(text: str, output_base_path: str, voice_id: str = None) -> dict:
    """
    Generate two audio options with different voice settings.

    Option A: More stable/consistent delivery
    Option B: More expressive/dynamic delivery

    Args:
        text: The text to convert to speech
        output_base_path: Base path for output (without extension)
        voice_id: Optional voice ID (uses env default if not provided)

    Returns:
        dict with 'option_a' and 'option_b' paths
    """
    base = Path(output_base_path)
    parent = base.parent
    stem = base.stem

    # Option A: More stable, consistent delivery
    option_a_path = parent / f"{stem}_OptionA.mp3"
    print("\n  Generating Option A (stable/consistent)...")
    option_a = text_to_speech(
        text,
        str(option_a_path),
        voice_id,
        stability=0.7,
        similarity_boost=0.8
    )

    # Option B: More expressive, dynamic delivery
    option_b_path = parent / f"{stem}_OptionB.mp3"
    print("\n  Generating Option B (expressive/dynamic)...")
    option_b = text_to_speech(
        text,
        str(option_b_path),
        voice_id,
        stability=0.3,
        similarity_boost=0.9
    )

    return {
        'option_a': option_a,
        'option_b': option_b
    }


def main():
    """CLI entry point."""
    if len(sys.argv) < 3:
        print("Usage: python elevenlabs_tts.py <input_text_file> <output_audio_file>")
        print("Example: python elevenlabs_tts.py ../input/script.txt ../.tmp/audio/output.mp3")
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2]

    # Read the input text
    with open(input_file, "r", encoding="utf-8") as f:
        text = f.read().strip()

    if not text:
        print("Error: Input file is empty")
        sys.exit(1)

    # Generate audio
    try:
        result = text_to_speech(text, output_file)
        print(f"Success! Audio generated: {result}")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
