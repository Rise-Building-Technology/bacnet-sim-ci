# Contributing

## Development Setup

```bash
# Clone
git clone https://github.com/Rise-Building-Technology/bacnet-sim-ci.git
cd bacnet-sim-ci

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows

# Install with dev dependencies
pip install -e ".[dev]"

# Install pre-commit hooks
pre-commit install
```

Pre-commit hooks run ruff linting and formatting automatically on each commit.

## Running Tests

```bash
# All tests
pytest tests/ -v

# Specific test file
pytest tests/test_config.py -v
```

## Linting

```bash
ruff check src/ tests/

# Auto-fix
ruff check --fix src/ tests/
```

## Building the Docker Image

```bash
docker build -t bacnet-sim-ci .

# Run locally
docker run -d --cap-add=NET_ADMIN -p 47808:47808/udp -p 8099:8099 bacnet-sim-ci
```

## Project Structure

```
src/bacnet_sim/
  config.py       # Pydantic config models, YAML + env var loading
  defaults.py     # Default HVAC controller config
  devices.py      # BAC0 device creation and management
  networking.py   # Virtual IP allocation (ip addr add)
  lag.py          # Network lag simulation profiles
  api.py          # FastAPI REST API
  health.py       # Health check logic
  setup_ips.py    # Standalone IP setup (used by Docker entrypoint)
  main.py         # Entry point
```

## Code Style

- Python 3.11+
- Ruff for linting (config in `pyproject.toml`)
- Line length: 100
- Type hints on all public functions
- Pydantic v2 for config validation

## Pull Requests

1. Fork and create a feature branch
2. Write tests for new functionality
3. Ensure `pytest` and `ruff check` pass
4. Submit a PR with a clear description
