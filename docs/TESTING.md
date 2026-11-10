# Testing Guide

## Running Tests

### Tests (Python)
```bash
make test              # All backend tests with coverage
make test-integration  # Integration tests only
```

## Pre-commit Hooks

Pre-commit hooks automatically run:
- `make format` - Auto-format code
- `make lint` - Check code quality

Currently, no pre-push hooks are configured. Before pushing, it is recommended to run:
- `make test` - Unit tests

### Installing Hooks
```bash
uv run pre-commit install --hook-type pre-commit
```

## Coverage Requirements
- 97%+ coverage required

## Test Output
- Coverage reports: `htmlcov/`
