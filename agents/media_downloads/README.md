# Media Downloads Directory

This directory stores media files downloaded from messaging platforms (WhatsApp, Telegram, etc.) during workflow execution.

## Purpose

- **Persistent storage**: Media files are saved here (not temp files) so they're accessible in codespace
- **Debugging**: Inspect actual media received from users during testing and production
- **Auditing**: Track media inputs for compliance and troubleshooting
- **Development**: Access real media files for testing and analysis

## File Naming Convention

```
{timestamp}_{media_id}.{ext}
```

**Example**: `20251009_154532_ABC123DEF456.jpg`

- **timestamp**: `YYYYMMDD_HHMMSS` when media was downloaded
- **media_id**: Platform-specific media identifier
- **ext**: File extension derived from MIME type

## Supported Media Types

### Images
- `.jpg`, `.png`, `.webp`, `.gif`

### Audio/Voice
- `.ogg` (WhatsApp voice notes)
- `.mp3`, `.m4a`, `.wav`, `.aac`

### Videos
- `.mp4`, `.mov`, `.avi`, `.webm`, `.mkv`

### Documents
- `.pdf`, `.xlsx`, `.xls`, `.csv`, `.docx`, `.doc`, `.txt`

## Location

```
AutifyME/
├── agents/
│   ├── logs/              # Application logs
│   └── media_downloads/   # Downloaded media (this directory)
```

Media downloads are stored alongside logs for easy access in codespace and local development.

## Cleanup

Media files accumulate over time. Consider periodic cleanup:

```bash
# List media files by date
ls -lt media_downloads/

# Remove files older than 7 days
find media_downloads/ -type f -mtime +7 -delete
```

## .gitignore

Media files are excluded from version control (see `.gitignore`):
- Directory structure is tracked
- Actual media files are ignored to avoid bloating repository
