# Test Videos Directory

Place product videos here for local testing.

## Recommended Videos

- **product_demo.mp4** - Product demonstration video
- **unboxing.mp4** - Unboxing video
- **showcase.mp4** - Product showcase/rotation
- **tutorial.mp4** - Product usage tutorial

## Supported Formats

- MP4 (.mp4) - Most common video format
- MOV (.mov) - Apple video format
- AVI (.avi) - Windows video format
- WebM (.webm) - Web video format
- MKV (.mkv) - Matroska video format

## Usage

```bash
# Test with product video
uv run python -m autifyme_agents.cli.pm_chat "Analyze this video and catalog" --media test_videos/product_demo.mp4

# Full workflow
uv run python -m autifyme_agents.cli.simulate "Catalog from video" --media test_videos/showcase.mp4 --auto-approve
```

## Creating Test Videos

You can create test videos by:
1. Recording product videos on mobile devices
2. Screen recordings of product pages
3. Downloading sample product videos
4. Short clips from existing marketing material
