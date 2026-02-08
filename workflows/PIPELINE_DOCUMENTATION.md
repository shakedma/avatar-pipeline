# AYO Engineering - AI Avatar Video Pipeline

## Complete Documentation

---

## Overview

This pipeline converts text scripts into AI avatar videos using:
- **ElevenLabs** - Text-to-speech with custom voice
- **HeyGen** - AI avatar video generation
- **Google Drive** - Cloud storage with shareable links
- **Google Sheets** - Dashboard tracking
- **Gmail** - Email notifications
- **YouTube** - Video publishing

---

## File Locations

### Local Files

```
Kabala project2801/
├── input/                          # Drop script files here
│   └── script.pdf                  # Supported: .txt, .docx, .pdf
│
├── output/                         # All generated files
│   ├── script_audio_OptionA.mp3   # Audio option A (stable)
│   ├── script_audio_OptionB.mp3   # Audio option B (expressive)
│   └── script_video.mp4           # Final video
│
├── .tmp/                           # Temporary processing files
│   └── audio/                      # Intermediate audio files
│
├── tools/                          # Python scripts
├── workflows/                      # Documentation
└── .env                            # API keys and settings
```

### Google Drive

| File Type | Location | Access |
|-----------|----------|--------|
| Videos | My Drive (root) | Shareable link (anyone with link) |
| Future | Can set GOOGLE_DRIVE_FOLDER_ID in .env | Specific folder |

### Google Sheets Dashboard

| Item | Link |
|------|------|
| Tracking Sheet | https://docs.google.com/spreadsheets/d/1xts-bHU3EKR1Px5HL7K6lK3jQZa3cEONCQ0_Xgu7iIM |

### YouTube

| Setting | Value |
|---------|-------|
| Default Privacy | Unlisted |
| Channel | Your connected Google account |

---

## Two-Phase Workflow

### Phase 1: Audio Generation

```bash
python tools/run_pipeline.py input/script.pdf --audio-only
```

**Output:**
- `output/script_audio_OptionA.mp3` - Stable, consistent delivery
- `output/script_audio_OptionB.mp3` - Expressive, dynamic delivery

**User Action:** Listen to both, delete the one you don't want.

### Phase 2: Video Generation

```bash
python tools/run_pipeline.py --continue output/script_audio_OptionA.mp3
```

**With YouTube upload:**
```bash
python tools/run_pipeline.py --continue output/script_audio_OptionA.mp3 --youtube
```

**Output:**
- Video file in `output/`
- Video uploaded to Google Drive
- Entry logged in Google Sheets
- Email notification sent
- (Optional) Video uploaded to YouTube

---

## CLI Commands Reference

### Full Pipeline (Auto)
```bash
python tools/run_pipeline.py input/script.pdf
```

### Phase 1: Audio Only
```bash
python tools/run_pipeline.py input/script.pdf --audio-only
```

### Phase 2: Continue with Audio
```bash
python tools/run_pipeline.py --continue output/script_audio_OptionA.mp3
```

### All Options
```bash
python tools/run_pipeline.py input/script.pdf \
    --name "custom_name" \
    --background "#ffffff" \
    --email "other@email.com" \
    --youtube \
    --youtube-title "My Video Title" \
    --youtube-privacy unlisted
```

### Skip Cloud Integrations
```bash
python tools/run_pipeline.py input/script.pdf --skip-cloud
```

---

## Individual Tools

| Tool | Purpose | Example |
|------|---------|---------|
| `elevenlabs_tts.py` | Text to speech | `python elevenlabs_tts.py script.txt output.mp3` |
| `heygen_create_video.py` | Create avatar video | Internal use |
| `google_drive_upload.py` | Upload to Drive | `python google_drive_upload.py video.mp4` |
| `google_sheets_logger.py` | Log to sheet | `python google_sheets_logger.py "name" "status" "link"` |
| `send_email.py` | Send notification | `python send_email.py email@example.com "link" "title"` |
| `youtube_upload.py` | Upload to YouTube | `python youtube_upload.py video.mp4 "Title"` |

---

## Dashboard (Google Sheets)

### Columns

| Column | Description |
|--------|-------------|
| Timestamp | When generated |
| Script Name | Source filename |
| Script Length | Character count |
| Audio File | Audio filename |
| Video File | Video filename |
| Drive Link | Shareable link |
| Status | Completed / Error |
| Duration | Processing time |
| Error | Error message (if any) |

### Status Colors

| Color | Status | Meaning |
|-------|--------|---------|
| 🟢 Green | Completed | Video delivered |
| 🟡 Yellow | Audio Ready | Waiting for review |
| 🟠 Orange | Processing | Video generating |
| 🔴 Red | Error | Something failed |

---

## API Services Used

| Service | Purpose | Pricing |
|---------|---------|---------|
| ElevenLabs | Voice synthesis | Per character |
| HeyGen | Avatar video | Per video/minute |
| Google Drive | Storage | Free (15GB) |
| Google Sheets | Dashboard | Free |
| Gmail | Notifications | Free |
| YouTube | Publishing | Free |

---

## Environment Variables (.env)

```env
# ElevenLabs
ELEVENLABS_API_KEY=sk_...
ELEVENLABS_VOICE_ID=...

# HeyGen
HEYGEN_API_KEY=sk_...
HEYGEN_AVATAR_ID=...

# Google
NOTIFICATION_EMAIL=ShakadMagal@gmail.com
GOOGLE_SHEET_ID=1xts-bHU3EKR1Px5HL7K6lK3jQZa3cEONCQ0_Xgu7iIM
GOOGLE_DRIVE_FOLDER_ID=  # Optional: specific folder
```

---

## Troubleshooting

### OAuth Issues
- Delete `token.json` or `youtube_token.json` and re-authenticate
- Ensure APIs are enabled in Google Cloud Console

### Video Generation Slow
- HeyGen typically takes 60-120 seconds per video
- Network issues may cause longer upload/download times

### Audio Quality
- Option A: More stable, professional
- Option B: More expressive, dynamic
- Adjust stability/similarity_boost in code if needed

---

## Contact

**AYO Engineering**
- Email: ShakadMagal@gmail.com
