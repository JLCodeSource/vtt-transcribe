
PYTHON ?= python
PIP ?= pip

.PHONY: help install install-diarization test test-integration lint ruff-check ruff-fix mypy format clean

help:
	@echo "Available targets:"
	@echo "  install                - Install uv and sync basic environment (no diarization)"
	@echo "  install-diarization    - Install with diarization support (includes pyannote.audio + torch)"
	@echo "  test                   - Run all tests with coverage"
	@echo "  test-integration       - Run only integration tests"
	@echo "  lint                   - Run ruff and mypy checks"
	@echo "  ruff-check             - Run ruff linter"
	@echo "  ruff-fix               - Auto-fix with ruff formatter"
	@echo "  mypy                   - Run mypy type checking"
	@echo "  format                 - Alias for ruff-fix"
	@echo "  clean                  - Remove compiled Python artifacts"

# Install development tooling (uv) and sync basic environment (no diarization)
install:
	@set -e; \
	curl -LsSf https://astral.sh/uv/install.sh | sh; \
	uv venv --clear && \
	uv sync && \
	uv run pre-commit install

# Install with full diarization support (includes torch + pyannote.audio)
install-diarization:
	@set -e; \
	curl -LsSf https://astral.sh/uv/install.sh | sh; \
	uv venv --clear && \
	uv sync --extra diarization && \
	uv run pre-commit install

# Use `uv run` for all runtime targets so commands run inside the project's environment
test:
	@uv run pytest -v --cov=./ --cov-report=term-missing

test-integration:
	@uv run pytest -v -k integration

ruff-check:
	@uv run ruff check .

ruff-fix:
	@uv run ruff format .

mypy:
	@uv run mypy . --ignore-missing-imports --disallow-untyped-defs --disallow-incomplete-defs --check-untyped-defs --warn-unused-ignores --warn-redundant-casts

lint: ruff-check mypy

format: ruff-fix

clean:
	@find . -name "*.pyc" -delete || true
	@find . -name "__pycache__" -type d -exec rm -rf {} + || true
