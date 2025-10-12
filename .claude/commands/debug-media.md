# Debug Media

Debug media file handling and image processing.

## Usage

```
/debug-media [media-path or thread-id]
```

## Task

Debug media download, storage, and processing issues.

### 1. List Downloaded Media Files

```bash
# List all media
ls -lh /tmp/media_downloads/

# Count files
echo "Total media files: $(ls -1 /tmp/media_downloads/ 2>/dev/null | wc -l)"

# Show recent files
ls -lt /tmp/media_downloads/ | head -10

# Show disk usage
du -sh /tmp/media_downloads/
```

### 2. Check Specific Media File

```bash
# Get file info
FILE_PATH="<path-to-media>"
echo "=== Media File Info ==="
echo "Path: $FILE_PATH"
echo "Size: $(stat -f%z "$FILE_PATH" 2>/dev/null || stat -c%s "$FILE_PATH")"
echo "Type: $(file --mime-type -b "$FILE_PATH")"
echo "Readable: $(test -r "$FILE_PATH" && echo "Yes" || echo "No")"
echo "Format: $(file "$FILE_PATH")"
```

### 3. Test Base64 Conversion

```bash
cd agents
uv run python -c "
from pathlib import Path
import base64

file_path = '<path-to-media>'
path = Path(file_path)

print(f'=== Base64 Conversion Test ===')
print(f'File: {file_path}')
print(f'Exists: {path.exists()}')
print(f'Size: {path.stat().st_size if path.exists() else \"N/A\"} bytes')

if path.exists():
    # Test conversion
    with open(path, 'rb') as f:
        data = f.read()
        encoded = base64.b64encode(data).decode('utf-8')

    print(f'Encoded size: {len(encoded)} chars')
    print(f'Data URI prefix: data:image/jpeg;base64,{encoded[:50]}...')
    print('✅ Conversion successful')
else:
    print('❌ File not found')
"
```

### 4. Test Image Analysis with Local File

```bash
cd agents
uv run python -c "
from dotenv import load_dotenv
load_dotenv('../.env')
from autifyme_agents.specialists.image_analysis_specialist import image_analysis_specialist_invoke

file_path = '<path-to-media>'

print(f'=== Image Analysis Test ===')
print(f'File: {file_path}')

try:
    result = image_analysis_specialist_invoke(
        image_url=file_path,
        company_profile={'brand_voice': 'professional', 'target_audience': 'general'}
    )

    print('✅ Analysis successful')
    print(f'Description: {result.visual_description[:200]}...')
    print(f'Colors: {result.identified_colors}')
    print(f'Style: {result.style_tags}')
except Exception as e:
    print(f'❌ Analysis failed: {e}')
"
```

### 5. Verify Vision API Access

```bash
cd agents
uv run python -c "
from dotenv import load_dotenv
load_dotenv('../.env')
from openai import OpenAI
import base64
from pathlib import Path

client = OpenAI()
file_path = '<path-to-media>'

print('=== Vision API Test ===')

# Test 1: Base64 data URI
path = Path(file_path)
with open(path, 'rb') as f:
    encoded = base64.b64encode(f.read()).decode('utf-8')

data_uri = f'data:image/jpeg;base64,{encoded}'

try:
    response = client.chat.completions.create(
        model='gpt-4.1-nano-2025-04-14',
        messages=[
            {
                'role': 'user',
                'content': [
                    {'type': 'text', 'text': 'Describe this image briefly.'},
                    {'type': 'image_url', 'image_url': {'url': data_uri}}
                ]
            }
        ],
        max_tokens=100
    )

    print('✅ Vision API working with base64')
    print(f'Response: {response.choices[0].message.content}')
except Exception as e:
    print(f'❌ Vision API error: {e}')

# Test 2: Direct file path (should fail)
try:
    response = client.chat.completions.create(
        model='gpt-4.1-nano-2025-04-14',
        messages=[
            {
                'role': 'user',
                'content': [
                    {'type': 'text', 'text': 'Describe this image.'},
                    {'type': 'image_url', 'image_url': {'url': f'file://{file_path}'}}
                ]
            }
        ],
        max_tokens=100
    )
    print('⚠️  Direct file path worked (unexpected)')
except Exception as e:
    print(f'✅ Direct file path correctly rejected: {str(e)[:100]}')
"
```

### 6. Check Media Download Flow

```bash
cd agents
# Check WhatsApp media client
uv run python -c "
from dotenv import load_dotenv
load_dotenv('../.env')
from autifyme_agents.integrations.communication.whatsapp_media_client import WhatsAppMediaClient

client = WhatsAppMediaClient()
print('WhatsApp media client initialized')
print(f'Download directory: {client.download_dir}')
print(f'Directory exists: {client.download_dir.exists()}')
"
```

### 7. Find Media for Thread

```bash
# Find media files for specific thread
THREAD_ID="<thread-id>"
ls -lh /tmp/media_downloads/ | grep "$THREAD_ID"

# Or search by timestamp
ls -lt /tmp/media_downloads/ | head -5
```

### 8. Test Complete Flow

```bash
cd agents
uv run python -c "
from dotenv import load_dotenv
from pathlib import Path
load_dotenv('../.env')

# Simulate complete media flow
file_path = '<test-image-path>'

print('=== Complete Media Flow Test ===')

# 1. Check file exists
path = Path(file_path)
print(f'1. File exists: {path.exists()}')

# 2. Test base64 conversion
if path.exists():
    from autifyme_agents.specialists.image_analysis_specialist import _encode_image_to_data_uri
    data_uri = _encode_image_to_data_uri(str(path))
    print(f'2. Base64 conversion: ✅ ({len(data_uri)} chars)')

    # 3. Test image analysis
    from autifyme_agents.specialists.image_analysis_specialist import image_analysis_specialist_invoke
    try:
        result = image_analysis_specialist_invoke(
            image_url=str(path),
            company_profile={'brand_voice': 'casual', 'target_audience': 'young adults'}
        )
        print(f'3. Image analysis: ✅')
        print(f'   Colors: {result.identified_colors}')
    except Exception as e:
        print(f'3. Image analysis: ❌ {e}')
else:
    print('2. Skipped (file not found)')
    print('3. Skipped (file not found)')
"
```

### 9. Generate Report

```markdown
## Media Debug Report

### Media File
- **Path**: [path]
- **Exists**: ✅/❌
- **Size**: [bytes] ([MB])
- **Type**: [image/jpeg, etc.]
- **Readable**: ✅/❌

### Base64 Conversion
- **Status**: ✅/❌
- **Encoded size**: [chars]
- **Data URI**: [preview]

### Image Analysis
- **Status**: ✅/❌
- **Description**: [preview]
- **Colors**: [list]
- **Tags**: [list]
- **Error**: [if failed]

### Vision API
- **Base64 access**: ✅/❌
- **Direct file access**: ❌ (expected)
- **Response time**: [ms]

### Issues Found
- [List any problems]

### Recommendations
- [Fixes needed]
```

## Common Issues

1. **File not found**
   - Check /tmp/media_downloads/
   - Verify download completed
   - Check file permissions

2. **Base64 conversion fails**
   - File may be corrupted
   - Unsupported format
   - File too large (check limits)

3. **Vision API rejects image**
   - Not using base64 data URI
   - Image format not supported
   - Image too large (>20MB)

4. **Image analysis hallucination**
   - Wrong image being passed
   - Local path not converted
   - Cached result from previous image

## Notes

- Media in /tmp is temporary (cleared on reboot)
- Base64 conversion required for Vision API
- Supported formats: JPEG, PNG, GIF, WebP
- Max file size for Vision API: 20MB
