#!/usr/bin/env python3
"""Test to clearly show departments are being called with debug logging."""

import logging
import time
from autifyme_agents.integrations.storage.supabase_client import SupabaseStorageClient
from autifyme_agents.workflows.orchestration.runner import WorkflowRunner
from autifyme_agents.cli.simulate import ConsoleChannel

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger()

print('=== DEPARTMENT CALL TEST WITH DEBUG LOGGING ===')
print('Testing: Complete product info + image → Departments → HITL')
print()

storage = SupabaseStorageClient()
channel = ConsoleChannel(auto_approve=False)  # Enable HITL
runner = WorkflowRunner(channel=channel, storage=storage)

print('📤 Sending: "Catalog these sneakers, price $79.99, sizes 7-11" + image')
print('Expected sequence:')
print('  1. PM analyzes request')
print('  2. PM calls image_analysis_specialist')
print('  3. PM calls cataloging_specialist')
print('  4. PM calls save_product tool')
print('  5. HITL interrupt triggered')
print()

start_time = time.time()

result = runner.handle_message(
    'test_user',
    'Catalog these sneakers, price $79.99, sizes 7-11',
    'test_images/WhatsApp.jpeg'
)

end_time = time.time()
print(f'\n⏱️  Time: {end_time - start_time:.2f}s')

print('\n🎯 RESULTS:')
if result:
    print('✅ SUCCESS - Workflow completed')
    print('✅ Departments were called (check debug logs above)')
    print('✅ HITL interrupt was triggered')
else:
    print('❌ FAILED - Check logs for details')

print('\n🔍 Look for these in the debug logs:')
print('   - "image_analysis_specialist" calls')
print('   - "cataloging_specialist" calls')
print('   - "save_product" tool calls')
print('   - HITL interrupt handling')
