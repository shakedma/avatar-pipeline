# Script-to-Avatar Video Workflow

## Objective
Convert a text script into an AI avatar video using your cloned voice and custom photo avatar.

## Prerequisites
- ElevenLabs API key (stored in `.env`)
- HeyGen API key (stored in `.env`)
- Cloned voice ID from ElevenLabs
- Photo avatar ID from HeyGen
- Python 3.8+ with `requests` and `python-dotenv` packages

## Quick Start

### 1. Place your script
Save your text script to `input/script.txt`

### 2. Run the pipeline
```bash
cd tools
python run_pipeline.py ../input/script.txt
```

### 3. Get your video
Find the completed video in `output/` folder

---

## Detailed Steps

### Step 1: Prepare Your Script
- Create your script in any of these formats:
  - **Text file (.txt)** - Plain text, UTF-8 encoding
  - **Word document (.docx)** - Microsoft Word format
  - **PDF file (.pdf)** - Portable Document Format
- Save it to `input/` folder (e.g., `input/script.txt`)
- Keep under 5000 characters for HeyGen compatibility

### Step 2: Run the Pipeline
```bash
# Basic usage
python tools/run_pipeline.py input/script.txt

# With custom output name
python tools/run_pipeline.py input/script.txt -n my_video

# With custom background color
python tools/run_pipeline.py input/script.txt -b "#000000"
```

### Step 3: Wait for Processing
- ElevenLabs TTS: ~10-30 seconds
- HeyGen video generation: ~1-5 minutes
- The script will poll for completion automatically

### Step 4: Import to Filmora
- Open Filmora
- File → Import Media
- Navigate to `output/` folder
- Select your video file

---

## Individual Tools

You can also run each tool separately:

### Text-to-Speech (ElevenLabs)
```bash
python tools/elevenlabs_tts.py input/script.txt .tmp/audio/output.mp3
```

### Upload Audio (HeyGen)
```bash
python tools/heygen_upload_audio.py .tmp/audio/output.mp3
# Returns: asset_id
```

### Create Video (HeyGen)
```bash
python tools/heygen_create_video.py <audio_asset_id>
# Returns: video_id
```

### Download Video (HeyGen)
```bash
python tools/heygen_download_video.py <video_id> output/final.mp4
```

---

## Configuration

### Environment Variables (`.env`)
```
ELEVENLABS_API_KEY=your_key_here
HEYGEN_API_KEY=your_key_here
ELEVENLABS_VOICE_ID=your_voice_id
HEYGEN_AVATAR_ID=your_avatar_id
```

### Default Settings
- Audio format: MP3
- Video resolution: 1280x720
- Background: White (#ffffff)
- Model: eleven_multilingual_v2

---

## Troubleshooting

### "API key not found"
- Check that `.env` file exists in project root
- Verify the key names match exactly

### "Voice/Avatar ID not found"
- Ensure IDs are set in `.env`
- Verify IDs are correct in ElevenLabs/HeyGen dashboards

### "Video generation failed"
- Check HeyGen API credits
- Verify avatar ID is valid
- Ensure audio uploaded successfully

### "Timeout waiting for video"
- HeyGen may be under heavy load
- Try again later
- Check HeyGen dashboard for video status

---

## Cost Considerations

### ElevenLabs
- Free tier: 10,000 characters/month
- Billed per character

### HeyGen
- Free trial includes API access
- Pro/Scale tiers for higher usage
- Billed per video minute

---

## File Structure
```
project/
├── .env                    # API keys
├── input/
│   └── script.txt          # Your text script
├── .tmp/
│   ├── audio/              # Generated audio files
│   └── video/              # Intermediate video files
├── output/                 # Final videos for Filmora
├── tools/
│   ├── elevenlabs_tts.py
│   ├── heygen_upload_audio.py
│   ├── heygen_create_video.py
│   ├── heygen_download_video.py
│   └── run_pipeline.py     # Main pipeline script
└── workflows/
    └── script_to_avatar.md # This file
```
