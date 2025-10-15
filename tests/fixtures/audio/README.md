# Test Audio Directory

Place voice notes and audio files here for local testing.

## Recommended Audio Files

- **voice_note.ogg** - WhatsApp-style voice note (cataloging request)
- **voice_inquiry.ogg** - Voice note asking about products
- **voice_greeting.ogg** - Conversational voice message
- **recording.m4a** - iOS voice recording
- **audio.mp3** - Standard audio file

## Supported Formats

- OGG (.ogg) - WhatsApp voice notes
- M4A (.m4a) - iOS recordings
- MP3 (.mp3) - Standard audio
- WAV (.wav) - Uncompressed audio
- AAC (.aac) - Advanced audio codec

## Usage

```bash
# Test with voice note
uv run python -m autifyme_agents.cli.pm_chat "Transcribe and catalog" --media test_audio/voice_note.ogg

# Full workflow simulation
uv run python -m autifyme_agents.cli.simulate "Process this voice message" --media test_audio/voice_note.ogg
```

## Creating Test Voice Notes

You can create test voice notes by:
1. Recording a voice message on WhatsApp and downloading it
2. Using voice recorder apps on mobile devices
3. Using text-to-speech tools to generate sample audio
4. Recording directly on your computer
