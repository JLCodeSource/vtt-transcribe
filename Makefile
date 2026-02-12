
PYTHON ?= python
PIP ?= pip

.PHONY: help install-uv install-base install-api install-diarization-cpu install-diarization-gpu install-diarization install-dev install-build install-all install test test-integration lint ruff-check ruff-fix mypy format clean build build-check publish-test publish

help:
	@echo "Available installation targets:"
	@echo "  install-uv             - Install uv package manager only"
	@echo "  install-base           - Install base dependencies only (moviepy, openai, python-dotenv)"
	@echo "  install-api            - Install with API server support (FastAPI, uvicorn, database drivers)"
	@echo "  install-diarization-cpu - Install diarization with CPU-only torch (faster install, CPU inference)"
	@echo "  install-diarization-gpu - Install diarization with GPU torch (CUDA support for faster inference)"
	@echo "  install-diarization    - Install diarization (alias for install-diarization-gpu; GPU by default)"
	@echo "  install-dev            - Install development tools (pytest, mypy, ruff, pre-commit)"
	@echo "  install-build          - Install build and publishing tools (build, twine, hatchling)"
	@echo "  install-all            - Install everything (base + api + diarization + dev + build)"
	@echo "  install                - Install everything (alias for install-all; backward compatibility)"
	@echo ""
	@echo "Common installation workflows:"
	@echo "  For basic CLI usage:      make install-base"
	@echo "  For development:          make install-dev"
	@echo "  For API server:           make install-api"
	@echo "  For diarization (CPU):    make install-diarization-cpu"
	@echo "  For diarization (GPU):    make install-diarization-gpu"
	@echo "  For everything:           make install-all"
	@echo ""
	@echo "Available development targets:"
	@echo "  test                   - Run backend tests with coverage"
	@echo "  test-frontend          - Run frontend E2E tests with dev server"
	@echo "  test-frontend-docker   - Run frontend E2E tests against Docker"
	@echo "  test-all               - Run all tests (backend + frontend)"
	@echo "  test-integration       - Run only integration tests"
	@echo "  lint                   - Run ruff and mypy checks"
	@echo "  ruff-check             - Run ruff linter"
	@echo "  ruff-fix               - Auto-fix with ruff formatter"
	@echo "  mypy                   - Run mypy type checking"
	@echo "  format                 - Alias for ruff-fix"
	@echo ""
	@echo "Available build targets:"
	@echo "  build                  - Build distribution packages (wheel + sdist)"
	@echo "  build-check            - Validate built packages with twine"
	@echo "  publish-test           - Publish to TestPyPI (requires TestPyPI setup)"
	@echo "  publish                - Publish to PyPI (requires PyPI setup)"
	@echo "  clean                  - Remove compiled Python artifacts and build artifacts"

# Install uv package manager only
install-uv:
	@echo "Checking for uv package manager..."
	@if command -v uv >/dev/null 2>&1; then \
		echo "uv is already installed (version: $$(uv --version))"; \
	else \
		echo "Installing uv package manager..."; \
		curl -LsSf https://astral.sh/uv/install.sh | sh; \
		echo "uv installed successfully!"; \
	fi

# Create virtual environment and install base dependencies only
install-base: install-uv
	@echo "Setting up base environment..."
	@if [ -d ".venv" ] && [ -f ".venv/pyvenv.cfg" ]; then \
		echo "Virtual environment already exists, updating dependencies..."; \
	else \
		echo "Creating new virtual environment..."; \
		uv venv --clear; \
	fi
	@echo "Installing base dependencies (moviepy, openai, python-dotenv)..."
	@uv sync
	@echo "Base dependencies installed successfully!"

# Install with API server support (FastAPI, uvicorn, database drivers)
install-api: install-base
	@echo "Installing API server dependencies..."
	@uv sync --extra api
	@echo "API dependencies installed successfully!"

# Install diarization with CPU-only torch (faster install, CPU inference)
# Note: Uses uv pip install to bypass lockfile for CPU-specific torch installation
# This creates an unlocked environment for CPU-only PyTorch from the torch CPU index
install-diarization-cpu: install-base
	@echo "Installing diarization dependencies with CPU-only torch..."
	@uv pip install --index-url https://download.pytorch.org/whl/cpu torch==2.8.0 torchaudio>=2.2.0
	@uv pip install pyannote.audio>=4.0.0 "torchcodec>=0.6.0,<0.8"
	@echo "Diarization (CPU) dependencies installed successfully!"
	@echo "Note: This installation uses CPU-only torch for faster installation and CPU inference."

# Install diarization with GPU torch (CUDA support for faster inference)
install-diarization-gpu: install-base
	@echo "Installing diarization dependencies with GPU torch..."
	@uv sync --extra api --extra diarization
	@echo "Diarization (GPU) dependencies installed successfully!"
	@echo "Note: This installation includes CUDA support for GPU acceleration."

# Alias for GPU diarization (default diarization behavior)
install-diarization: install-diarization-gpu

# Install development tools (pytest, mypy, ruff, pre-commit)
install-dev: install-base
	@echo "Installing development dependencies..."
	@uv sync --extra dev
	@if uv run python -c "import pre_commit" 2>/dev/null; then \
		echo "Installing pre-commit hooks..."; \
		uv run pre-commit install; \
		echo "Pre-commit hooks have been installed."; \
	else \
		echo "Warning: pre-commit not available, skipping hooks installation"; \
	fi
	@echo "Development dependencies installed successfully!"

# Install build and publishing tools
install-build: install-base
	@echo "Installing build dependencies..."
	@uv sync --extra build
	@echo "Build dependencies installed successfully!"

# Install everything (base + api + diarization + dev + build)
install-all: install-uv
	@echo "Setting up complete development environment..."
	@if [ -d ".venv" ] && [ -f ".venv/pyvenv.cfg" ]; then \
		echo "Virtual environment already exists, updating dependencies..."; \
	else \
		echo "Creating new virtual environment..."; \
		uv venv --clear; \
	fi
	@echo "Installing all dependencies (base + api + diarization + dev + build)..."
	@uv sync --extra api --extra diarization --extra dev --extra build
	@echo "Checking for pre-commit in uv-managed environment..."
	@if uv run python -c "import pre_commit" >/dev/null 2>&1; then \
		echo "Installing pre-commit hooks..."; \
		uv run pre-commit install; \
	else \
		echo "Warning: pre-commit not available in uv environment, skipping hooks installation"; \
	fi
	@echo "All dependencies installed successfully!"
	@echo "Pre-commit hook installation step completed (see messages above)."

# Legacy compatibility - install everything (alias for install-all)
install: install-all

# Use `uv run` for all runtime targets so commands run inside the project's environment
test:
	@uv run pytest -v --cov=./ --cov-report=term-missing

test-integration:
	@uv run pytest -v -k integration

# Frontend testing (requires Node.js and npm)
# Default: Tests with dev server (no Docker needed)
test-frontend:
	@echo "Running frontend E2E tests with dev server..."
	@if [ ! -d "frontend/node_modules" ]; then \
		echo "Installing frontend dependencies..."; \
		cd frontend && npm install; \
	fi
	@if [ ! -d "$(HOME)/.cache/ms-playwright/chromium-"* ]; then \
		echo "Installing Playwright browsers..."; \
		cd frontend && npx playwright install chromium --with-deps || npx playwright install chromium; \
	fi
	@cd frontend && npm run test:e2e -- --project=chromium

# Frontend testing against Docker container (for production-like testing)
test-frontend-docker:
	@echo "Running frontend E2E tests against Docker container..."
	@if ! docker ps | grep -q vtt-transcribe-frontend; then \
		echo "Error: Frontend container not running. Start with: docker-compose --profile frontend up -d"; \
		exit 1; \
	fi
	@if [ ! -d "frontend/node_modules" ]; then \
		echo "Installing frontend dependencies..."; \
		cd frontend && npm install; \
	fi
	@if [ ! -d "$(HOME)/.cache/ms-playwright/chromium-"* ]; then \
		echo "Installing Playwright browsers..."; \
		cd frontend && npx playwright install chromium --with-deps || npx playwright install chromium; \
	fi
	@cd frontend && DOCKER_FRONTEND=true npm run test:e2e -- --project=chromium

# Run all tests (backend + frontend)
test-all: test test-frontend

ruff-check:
	@uv run ruff check .

ruff-fix:
	@uv run ruff format .

mypy:
	@uv run mypy vtt_transcribe --ignore-missing-imports --disallow-untyped-defs --disallow-incomplete-defs --check-untyped-defs --warn-unused-ignores --warn-redundant-casts

# Pylance type checking via pyright (what VS Code uses)
pylance:
	@echo "Running Pylance (pyright) type checking..."
	@uv run pyright

lint: ruff-check mypy pylance

format: ruff-fix

clean:
	@find . -name "*.pyc" -delete || true
	@find . -name "__pycache__" -type d -exec rm -rf {} + || true
	@rm -rf dist/ build/ *.egg-info/ || true

# Build distribution packages (wheel + source distribution)
build: install-build
	@echo "Building distribution packages..."
	@uv run python -m build --sdist --wheel
	@echo "Build complete! Artifacts in dist/"
	@ls -lh dist/

# Validate built packages
build-check: build
	@echo "Checking distribution packages..."
	@uv run twine check dist/*

# Publish to TestPyPI (for testing)
publish-test: build-check
	@echo "Publishing to TestPyPI..."
	@TWINE_USERNAME=__token__ TWINE_PASSWORD=$${TESTPYPI_API_TOKEN} uv run twine upload --repository testpypi dist/*
	@echo "Published to TestPyPI! View at: https://test.pypi.org/project/vtt-transcribe/"
	@echo "Install with: pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ vtt-transcribe"

# Publish to production PyPI
publish: build-check
	@echo "⚠️  WARNING: Publishing to production PyPI!"
	@echo "Press Ctrl+C to cancel, or Enter to continue..."
	@read dummy
	@TWINE_USERNAME=__token__ TWINE_PASSWORD=$${PYPI_API_TOKEN} uv run twine upload dist/*
	@echo "Published to PyPI! View at: https://pypi.org/project/vtt-transcribe/"
	@echo "Install with: pip install vtt-transcribe"
