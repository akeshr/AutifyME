#!/usr/bin/env python3
"""Test full department + HITL flow with complete product info."""

import time
from autifyme_agents.integrations.storage.supabase_client import SupabaseStorageClient
from autifyme_agents.workflows.orchestration.runner import WorkflowRunner
from autifyme_agents.cli.simulate import ConsoleChannel

print('=== FULL DEPARTMENT + HITL TEST ===')
print('Testing: Complete product info + image → Departments → HITL')

storage = SupabaseStorageClient()
channel = ConsoleChannel(auto_approve=False)  # Enable HITL
runner = WorkflowRunner(channel=channel, storage=storage)

print('\n📤 Sending: "Catalog these sneakers, price $79.99, sizes 7-11" + image')
start_time = time.time()

result = runner.handle_message(
    'test_user',
    'Catalog these sneakers, price $79.99, sizes 7-11',
    'test_images/WhatsApp.jpeg'
)

end_time = time.time()
print(f'⏱️  Total time: {end_time - start_time:.2f}s')

print('\n🔍 ANALYSIS:')
print('- If departments were called, we should see HITL approval request')
print('- Check for cataloging_department, image_analysis_specialist, cataloging_specialist')
print('- Look for HITL interrupt that pauses for user approval')

print('\n✅ Test completed - check LangSmith trace for department calls!')
