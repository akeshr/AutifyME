"""CLI entry point for autifyme_agents.cli module."""

import sys

def main():
    if len(sys.argv) < 2:
        print("AutifyME Agents CLI")
        print()
        print("Available commands:")
        print("  python -m autifyme_agents.cli.pm_chat         - Chat with PM directly")
        print("  python -m autifyme_agents.cli.simulate        - Full workflow simulation with HITL")
        print()
        print("For help on specific command:")
        print("  python -m autifyme_agents.cli.pm_chat --help")
        sys.exit(1)

    command = sys.argv[1]
    # Delegate to specific CLI module
    if command == "pm_chat":
        from autifyme_agents.cli.pm_chat import main as pm_chat_main
        pm_chat_main()
    elif command == "simulate":
        from autifyme_agents.cli.simulate import main as simulate_main
        simulate_main()
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)

if __name__ == "__main__":
    main()
