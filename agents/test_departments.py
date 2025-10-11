#!/usr/bin/env python3
"""Test to verify departments are being called in simulation."""

import time
from autifyme_agents.integrations.storage.supabase_client import SupabaseStorageClient
from autifyme_agents.workflows.orchestration.runner import WorkflowRunner
from autifyme_agents.cli.simulate import ConsoleChannel

print('=== SIMULATION TEST: Image + Simple Text ===')
storage = SupabaseStorageClient()
channel = ConsoleChannel(auto_approve=False)
runner = WorkflowRunner(channel=channel, storage=storage)

print('📤 Sending: Image + "catalog this"')
start_time = time.time()
result = runner.handle_message('test_user', 'catalog this', 'test_images/WhatsApp.jpeg')
end_time = time.time()

print(f'⏱️  Time: {end_time - start_time:.2f}s')
print('✅ Message processed')

print('\n=== CHECKING IF DEPARTMENTS WERE CALLED ===')
print('Expected behavior:')
print('- PM should analyze "catalog this" + image')
print('- PM should classify as catalog_new intent')
print('- PM should delegate to cataloging_department')
print('- Department should call image analysis specialist')
print('- Department should call cataloging specialist')
print('- Department should pause at HITL for approval')
