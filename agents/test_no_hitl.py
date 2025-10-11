#!/usr/bin/env python3
"""Test department flow without HITL to isolate the issue."""

import time
from autifyme_agents.integrations.storage.supabase_client import SupabaseStorageClient
from autifyme_agents.workflows.orchestration.runner import WorkflowRunner
from autifyme_agents.cli.simulate import ConsoleChannel

print('=== TESTING WITHOUT HITL (Direct Save) ===')
storage = SupabaseStorageClient()
channel = ConsoleChannel(auto_approve=True)  # Skip HITL, save directly
runner = WorkflowRunner(channel=channel, storage=storage)

print('📤 Sending: "Catalog these sneakers, price $79.99, sizes 7-11" + image')
start_time = time.time()

result = runner.handle_message(
    'test_user',
    'Catalog these sneakers, price $79.99, sizes 7-11',
    'test_images/WhatsApp.jpeg'
)

end_time = time.time()
print(f'⏱️  Time: {end_time - start_time:.2f}s')

if result:
    print('✅ SUCCESS - Product saved directly without HITL!')
else:
    print('❌ FAILED - Check logs for details')
