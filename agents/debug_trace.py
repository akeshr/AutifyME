#!/usr/bin/env python3
"""Debug the LangSmith trace for the latest run."""

import requests
import os
from pathlib import Path

def get_langsmith_trace():
    # Load env
    project_root = Path(__file__).parent
    env_file = project_root / ".env"

    if env_file.exists():
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    key, value = line.split('=', 1)
                    os.environ[key.strip()] = value.strip()

    api_key = os.getenv("LANGCHAIN_API_KEY")
    if not api_key:
        print("❌ LANGCHAIN_API_KEY not found")
        return

    # Get recent runs
    headers = {"x-api-key": api_key, "Content-Type": "application/json"}
    endpoint = os.getenv("LANGCHAIN_ENDPOINT", "https://api.smith.langchain.com")

    # Get recent runs for the project
    runs_url = f"{endpoint}/runs"
    params = {
        "project_name": "autifyme-agents",
        "limit": 5,
        "order_by": "start_time DESC"
    }

    response = requests.get(runs_url, headers=headers, params=params)

    if response.status_code == 200:
        runs = response.json()
        if runs:
            latest_run = runs[0]
            run_id = latest_run['id']
            print(f"Latest run ID: {run_id}")
            print(f"Name: {latest_run.get('name', 'N/A')}")
            print(f"Status: {latest_run.get('status', 'N/A')}")

            # Get full trace
            trace_url = f"{endpoint}/runs/{run_id}"
            trace_response = requests.get(trace_url, headers=headers)

            if trace_response.status_code == 200:
                trace = trace_response.json()
                print("\n=== TRACE ANALYSIS ===")

                # Check for child runs
                child_run_ids = trace.get('child_run_ids', [])
                print(f"Child runs: {len(child_run_ids)}")

                if child_run_ids:
                    print("DEPARTMENTS WERE CALLED! ✅")
                    for child_id in child_run_ids[:3]:  # Show first 3
                        child_url = f"{endpoint}/runs/{child_id}"
                        child_response = requests.get(child_url, headers=headers)
                        if child_response.status_code == 200:
                            child_data = child_response.json()
                            print(f"  - {child_data.get('name', 'Unknown')} ({child_id[:8]}...) - {child_data.get('status', 'unknown')}")
                else:
                    print("NO DEPARTMENTS CALLED ❌")
                    print("PM did not delegate - likely asked for clarification")

                # Check inputs/outputs
                inputs = trace.get('inputs', {})
                outputs = trace.get('outputs', {})

                print(f"\nInputs: {inputs}")
                print(f"Outputs: {outputs}")

            else:
                print(f"❌ Failed to get trace: {trace_response.status_code}")
        else:
            print("❌ No runs found")
    else:
        print(f"❌ Failed to get runs: {response.status_code}")

if __name__ == "__main__":
    get_langsmith_trace()
