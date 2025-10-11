#!/usr/bin/env python3
"""Debug script to fetch and analyze a specific LangSmith run using direct API."""

import os
import sys
import requests
from pathlib import Path

def load_env_file():
    """Load .env file from project root."""
    project_root = Path(__file__).parent.parent
    env_file = project_root / ".env"

    if env_file.exists():
        print(f"Loading .env file from: {env_file}")
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    key, value = line.split('=', 1)
                    os.environ[key.strip()] = value.strip()
        return True
    else:
        print(f"❌ .env file not found at: {env_file}")
        return False

def main():
    print("Starting debug script...")
    print(f"Python version: {sys.version}")

    # Load .env file
    env_loaded = load_env_file()
    print(f".env file loaded: {env_loaded}")

    # Check environment variables
    api_key = os.getenv("LANGCHAIN_API_KEY")
    if api_key:
        print(f"LANGCHAIN_API_KEY found: {api_key[:20]}...")
    else:
        print("❌ LANGCHAIN_API_KEY not found in environment")

    tracing_v2 = os.getenv("LANGCHAIN_TRACING_V2")
    print(f"LANGCHAIN_TRACING_V2: {tracing_v2}")

    endpoint = os.getenv("LANGCHAIN_ENDPOINT", "https://api.smith.langchain.com")
    print(f"LANGCHAIN_ENDPOINT: {endpoint}")

    # Latest trace ID provided by user
    run_id = '3901952c-3068-470d-9f2c-1286392a10e5'
    print(f"Attempting to fetch run: {run_id}")

    if not api_key:
        print("❌ Cannot proceed without LANGCHAIN_API_KEY")
        return

    try:
        # Try direct API approach as per LangSmith docs
        headers = {
            "x-api-key": api_key,
            "Content-Type": "application/json"
        }

        url = f"{endpoint}/runs/{run_id}"
        print(f"Making GET request to: {url}")

        response = requests.get(url, headers=headers)

        print(f"Response status: {response.status_code}")

        if response.status_code == 200:
            trace_data = response.json()
            print("✅ Trace fetched successfully!")

            # Print key information
            print(f"\n{'='*50}")
            print(f"Run ID: {trace_data.get('id')}")
            print(f"Name: {trace_data.get('name')}")
            print(f"Status: {trace_data.get('status')}")
            print(f"Start Time: {trace_data.get('start_time')}")
            print(f"End Time: {trace_data.get('end_time')}")
            print(f"{'='*50}")

            # Check for errors
            if trace_data.get('error'):
                print(f"\n❌ ERROR: {trace_data['error']}")

            # Print inputs
            if trace_data.get('inputs'):
                print(f"\n📥 INPUTS:")
                inputs = trace_data['inputs']
                if isinstance(inputs, dict):
                    for key, value in inputs.items():
                        print(f"  {key}: {value}")
                else:
                    print(f"  {inputs}")

            # Print outputs
            if trace_data.get('outputs'):
                print(f"\n📤 OUTPUTS:")
                outputs = trace_data['outputs']
                if isinstance(outputs, dict):
                    for key, value in outputs.items():
                        print(f"  {key}: {value}")
                else:
                    print(f"  {outputs}")

            # Check for child runs
            if trace_data.get('child_run_ids'):
                print(f"\n🔍 CHILD RUNS ({len(trace_data['child_run_ids'])}):")
                for child_id in trace_data['child_run_ids']:
                    try:
                        child_response = requests.get(f"{endpoint}/runs/{child_id}", headers=headers)
                        if child_response.status_code == 200:
                            child_data = child_response.json()
                            status_icon = "✅" if child_data.get('status') == "success" else "❌" if child_data.get('status') == "error" else "⏳"
                            print(f"  {status_icon} {child_data.get('name')} ({child_id}) - {child_data.get('status')}")

                            if child_data.get('error'):
                                print(f"      ❌ Error: {child_data['error']}")

                            # Print inputs and outputs for child runs
                            if child_data.get('inputs'):
                                print(f"      📥 Inputs: {child_data['inputs']}")

                            if child_data.get('outputs'):
                                print(f"      📤 Outputs: {child_data['outputs']}")

                            # Check for child run's child runs
                            if child_data.get('child_run_ids'):
                                print(f"      🔍 Has {len(child_data['child_run_ids'])} sub-child runs")

                            print()  # Add spacing between runs
                        else:
                            print(f"  ❌ Failed to fetch child run {child_id}: {child_response.status_code}")
                    except Exception as e:
                        print(f"  ❌ Error fetching child run {child_id}: {e}")
            else:
                print("\n🔄 No child runs found")

        else:
            print(f"❌ Failed to fetch trace: {response.status_code}")
            print(f"Response: {response.text}")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
