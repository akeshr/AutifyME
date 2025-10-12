# Test Workflow

Quick end-to-end workflow testing with common scenarios.

## Usage

```
/test-workflow [scenario]
```

**Scenarios**: `image-catalog`, `text-catalog`, `hitl-approve`, `hitl-reject`, `batch`, `interactive`

If no scenario specified, runs interactive mode.

## Task

Test AutifyME workflows using local CLI tools (pm_chat or simulate).

### 1. Setup Test Environment

```bash
cd agents
# Ensure .env is loaded
```

### 2. Run Scenario

**Image + Caption Cataloging**:
```bash
# Create test image if needed
cp tests/fixtures/test_image.jpg /tmp/test_product.jpg

# Run pm_chat in interactive mode
uv run python scripts/pm_chat.py --interactive

# Or simulate full workflow
uv run python scripts/simulate.py \
  --text "Catalog this sneaker, white canvas, $79.99, sizes 7-11" \
  --image /tmp/test_product.jpg
```

**Text-Only Cataloging**:
```bash
uv run python scripts/simulate.py \
  --text "Add product: Blue Cotton T-Shirt, $29.99, sizes S-XL"
```

**HITL Approval Flow**:
```bash
# Start workflow that triggers HITL
uv run python scripts/simulate.py \
  --text "Catalog red backpack, $49.99" \
  --image /tmp/test_product.jpg \
  --hitl

# Then approve
uv run python scripts/simulate.py \
  --approve <thread-id>
```

**HITL Rejection Flow**:
```bash
# Same as approval but reject
uv run python scripts/simulate.py \
  --reject <thread-id>
```

**Batch Products**:
```bash
uv run python scripts/simulate.py \
  --batch \
  --text "Catalog 3 items: sneakers $80, jacket $120, hat $25"
```

**Interactive Mode**:
```bash
uv run python scripts/pm_chat.py --interactive
# Then test conversationally
```

### 3. Verify Results

- Check LangSmith trace for tool calls
- Verify product saved to database (or approval pending)
- Check logs for errors
- Validate structured outputs

### 4. Report

Present results:
```markdown
## Test Results

**Scenario**: [name]
**Status**: ✅ Pass / ❌ Fail
**Duration**: [seconds]

**Tool Calls**:
- image_analysis_specialist: [✓/✗]
- cataloging_specialist: [✓/✗]
- save_product: [✓/✗]

**Issues Found**:
- [List any problems]

**LangSmith Trace**: [URL or ID]
```

## Notes

- Use test company profile (should exist in DB)
- Media files in /tmp are temporary
- Check docs/architecture/LOCAL_TESTING_STRATEGY.md for more details
