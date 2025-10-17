# Conversation Scenarios

This directory contains YAML-based multi-turn conversation scenarios for testing conversation continuity and context preservation.

## Scenario Format

```yaml
name: "Conversation Name"
description: "What this conversation tests"
sender: "test_user_identifier"  # Unique sender ID
hitl_mode: "auto_approve"        # Optional: interactive/auto_approve/auto_reject/auto_edit/question

turns:
  - turn: 1
    text: "User's message"       # Optional if media-only
    media: "path/to/file.jpg"    # Optional
    media_type: "image"          # image/video/audio/voice/document
    wait: 0.5                    # Seconds to wait before next turn
    expected_intent: "cataloging" # Expected PM classification
    validate_context:            # Optional validation rules
      - conversation_history_length: 2
      - pending_approval: true
      - no_pending_approval: false
      - approval_has_image_data: true

  - turn: 2
    text: "Second message"
    # ... same structure
```

## Available Validation Rules

- `conversation_history_length: N` - Verify message count equals N
- `pending_approval: true/false` - Check if approval is pending
- `no_pending_approval: true/false` - Check if no approval pending
- `approval_has_image_data: true/false` - Verify approval includes media

## Existing Scenarios

### greeting_to_cataloging.yaml
**Flow**: User greets → PM responds → User catalogs product
**Tests**: Conversation continuity, context switching
**Turns**: 2

### clarification_flow.yaml
**Flow**: Ambiguous request → PM clarifies → User provides info
**Tests**: Multi-turn clarification handling
**Turns**: 3

### approval_followup.yaml
**Flow**: Catalog → Approve → Follow-up question
**Tests**: Post-approval conversation continuity
**Turns**: 2

### multi_product.yaml
**Flow**: Catalog product 1 → Product 2 → Product 3
**Tests**: Context isolation, history preservation
**Turns**: 3

### conversation_mixed.yaml
**Flow**: Greeting → Inquiry → Cataloging → Follow-up
**Tests**: Mixed intents with context preservation
**Turns**: 4

### rejection_flow.yaml
**Flow**: Catalog → Reject → Retry
**Tests**: Rejection handling and retry workflows
**Turns**: 2

## Usage

```bash
# List scenarios
uv run python -m autifyme_agents.cli.conversation --list

# Run single scenario
uv run python -m autifyme_agents.cli.conversation --scenario greeting_to_cataloging

# Run all scenarios
uv run python -m autifyme_agents.cli.conversation --all

# Debug mode
uv run python -m autifyme_agents.cli.conversation --scenario greeting_to_cataloging --debug
```

## Creating New Scenarios

1. Create a new `.yaml` file in this directory
2. Follow the format above
3. Test with `--scenario <your_filename_without_extension>`
4. Add description to this README

## Tips

- Use unique `sender` IDs to avoid checkpoint pollution
- Add `wait` times between turns for realistic pacing
- Use `validate_context` to catch state preservation bugs
- Start with `hitl_mode: auto_approve` for faster iteration
- Use `--debug` flag to inspect state at each turn
