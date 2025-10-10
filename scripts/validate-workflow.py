#!/usr/bin/env python3
"""Validate GitHub Actions workflow syntax."""

import yaml
import sys

def validate_workflow():
    """Validate the CI/CD workflow file."""
    workflow_path = ".github/workflows/ci-cd.yml"

    try:
        with open(workflow_path, 'r') as f:
            workflow = yaml.safe_load(f)

        print("✅ CI/CD workflow YAML syntax is valid")
        print("\n📋 Workflow Configuration:")

        # Check triggers
        triggers = workflow.get('on', {})
        print(f"Triggers: {list(triggers.keys())}")

        for event, config in triggers.items():
            if isinstance(config, dict) and 'branches' in config:
                print(f"  {event}: {config['branches']}")

        # Check jobs
        jobs = workflow.get('jobs', {})
        print(f"\nJobs: {list(jobs.keys())}")

        # Check environment
        env = workflow.get('env', {})
        if env:
            print(f"Environment: {env}")

        print("\n🎯 Workflow should trigger on:")
        print("- Pushes to: main, develop, InitialDesign")
        print("- PRs to: main, develop, InitialDesign")

        return True

    except yaml.YAMLError as e:
        print(f"❌ YAML syntax error: {e}")
        return False
    except FileNotFoundError:
        print(f"❌ Workflow file not found: {workflow_path}")
        return False
    except Exception as e:
        print(f"❌ Validation error: {e}")
        return False

if __name__ == "__main__":
    success = validate_workflow()
    sys.exit(0 if success else 1)
