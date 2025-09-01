# AutifyME - Agentic Business Operating System

AutifyME is the world's first Agentic Business Operating System that automates and orchestrates end-to-end business functions using AI agents, domain specialists, and deterministic tools.

## Quick Start

1. **Setup AutifyME**
   ```bash
   git clone <repository-url>
   cd AutifyME
   python scripts/setup.py
   ```

2. **Configure Credentials**
   ```bash
   # Edit .env with your API keys
   cp .env.example .env
   ```

3. **Validate Setup**
   ```bash
   uv run python scripts/validate_credentials.py
   ```

4. **Run Your First Workflow**
   ```bash
   uv run python -m src.workflows.cataloging
   ```

📖 **[Complete Setup Guide](./docs/guides/getting_started.md)**

## Architecture

- **Agents**: Orchestrate workflows with state management
- **Specialists**: Provide domain expertise 
- **Tools**: Execute deterministic operations

## Project Structure

```
AutifyME/
├── src/
│   ├── agents/          # Workflow orchestrators
│   ├── specialists/     # Domain experts
│   ├── tools/          # Deterministic functions
│   ├── core/           # Framework components
│   ├── workflows/      # End-to-end processes
│   └── api/            # REST API endpoints
├── tests/              # Test suites
├── docs/               # Documentation
├── config/             # Configuration files
└── scripts/            # Utility scripts
```

## Documentation

- 📖 **[Getting Started](./docs/guides/getting_started.md)** - Quick start guide
- 🏗️ **[Architecture](./docs/architecture/framework_design.md)** - System design
- ⚙️ **[Configuration](./docs/guides/configuration.md)** - Setup and configuration
- 🔄 **[Workflows](./docs/workflows/)** - Available workflows
- 🔧 **[API Reference](./docs/api/)** - Integration documentation

## Development

```bash
# Install development dependencies
uv sync

# Run tests
uv run pytest

# Format code
uv run black src/

# Type checking
uv run mypy src/
```

📚 **[Full Documentation](./docs/README.md)**

## License

MIT License - see LICENSE file for details.