# GitHub Actions Workflows

This directory contains automated CI/CD workflows for AutifyME.

## Workflows

### 🔄 CI/CD Pipeline (`ci.yml`)
**Triggers**: Push to `main`/`develop`, Pull Requests

**Jobs**:
- **Code Quality**: Black formatting, flake8 linting, mypy type checking, isort import sorting
- **Security Scanning**: Safety vulnerability checks, bandit security analysis
- **Testing**: pytest with coverage across Python 3.11 and 3.12
- **Build**: Package building and Docker image testing
- **Dependency Analysis**: pip-audit for dependency vulnerabilities

### 🚀 Release (`release.yml`)
**Triggers**: Git tags starting with `v*`

**Jobs**:
- Run full test suite
- Build and publish package to PyPI
- Create GitHub release with artifacts

## Setup Instructions

### 1. Install Pre-commit Hooks (Recommended)
```bash
# Install pre-commit
uv add --dev pre-commit

# Install hooks
uv run pre-commit install

# Run on all files (optional)
uv run pre-commit run --all-files
```

### 2. Local Development Commands
```bash
# Format code
uv run black src/ tests/

# Sort imports
uv run isort src/ tests/

# Lint code
uv run flake8 src/ tests/

# Type check
uv run mypy src/

# Run tests with coverage
uv run pytest tests/ --cov=src --cov-report=html

# Security scan
uv run bandit -r src/
uv run safety check
```

### 3. Repository Secrets (for releases)
Add these secrets in GitHub repository settings:
- `PYPI_API_TOKEN`: PyPI API token for package publishing

## Workflow Status
Add this badge to your README.md:
```markdown
[![CI/CD Pipeline](https://github.com/autifyme/autifyme/actions/workflows/ci.yml/badge.svg)](https://github.com/autifyme/autifyme/actions/workflows/ci.yml)
```

## Quality Gates
All PRs must pass:
- ✅ Code formatting (Black)
- ✅ Linting (flake8)
- ✅ Type checking (mypy)
- ✅ Import sorting (isort)
- ✅ Security scanning (bandit, safety)
- ✅ All tests passing
- ✅ Coverage requirements
- ✅ Dependency vulnerability checks