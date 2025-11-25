# Experimental Specialists

This directory contains specialist implementations that are **not currently integrated** into the AutifyME system.

## Status: Unimplemented / Future Features

These specialists were developed but never integrated into the Project Manager workflow or any active workflows.

### Marketing Suite Specialists

1. **audience_intelligence_specialist.py** - Audience analysis and targeting
2. **ad_copy_specialist.py** - Ad copy generation
3. **platform_adaptation_specialist.py** - Platform-specific content adaptation
4. **campaign_strategy_specialist.py** - Campaign strategy planning

### Current State

- ❌ Not imported in `specialists/__init__.py`
- ❌ Not used by Project Manager
- ❌ No active tests
- ❌ No integration with workflows

### Future Considerations

If marketing workflow support is planned, these specialists can be:
1. Reviewed and updated to current architecture patterns
2. Integrated into PM as SubAgents
3. Added to appropriate workflows
4. Tested and validated

### Maintenance

⚠️ **These files are not maintained and may be out of date with current architecture:**
- May use deprecated LangChain patterns
- May not follow current prompt engineering standards
- May not integrate with current middleware stack

**Last Updated:** 2025-01-24
**Audit Status:** Code audit identified as unused (0 references in codebase)
