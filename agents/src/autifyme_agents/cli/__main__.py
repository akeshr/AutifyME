"""CLI entry point for autifyme_agents.cli module."""

import sys

def main():
    if len(sys.argv) < 2:
        print("AutifyME Agents CLI")
        print()
        print("Available commands:")
        print("  python -m autifyme_agents.cli.pm_chat         - Chat with PM directly")
        print("  python -m autifyme_agents.cli.simulate        - Full workflow simulation with HITL")
        print("  python -m autifyme_agents.cli.conversation    - Multi-turn conversation testing")
        print("  python -m autifyme_agents.cli.permutation_test - Systematic permutation testing")
        print("  python -m autifyme_agents.cli.inspect         - State inspection tools")
        print("  python -m autifyme_agents.cli.debug           - Interactive workflow debugger")
        print()
        print("For help on specific command:")
        print("  python -m autifyme_agents.cli.pm_chat --help")
        print("  python -m autifyme_agents.cli.conversation --help")
        print("  python -m autifyme_agents.cli.inspect --help")
        sys.exit(1)

    command = sys.argv[1]
    # Delegate to specific CLI module
    if command == "pm_chat":
        from autifyme_agents.cli.pm_chat import main as pm_chat_main
        pm_chat_main()
    elif command == "simulate":
        from autifyme_agents.cli.simulate import main as simulate_main
        simulate_main()
    elif command == "conversation":
        from autifyme_agents.cli.conversation import main as conversation_main
        conversation_main()
    elif command == "permutation_test":
        from autifyme_agents.cli.permutation_test import main as permutation_main
        permutation_main()
    elif command == "inspect":
        from autifyme_agents.cli.inspect import main as inspect_main
        inspect_main()
    elif command == "debug":
        from autifyme_agents.cli.debug import main as debug_main
        debug_main()
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)

if __name__ == "__main__":
    main()
