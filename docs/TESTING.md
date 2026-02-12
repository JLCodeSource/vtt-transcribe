# Testing Guide

## Running Tests

### Backend Tests (Python)
```bash
make test              # All backend tests with coverage
make test-integration  # Integration tests only
```

### Frontend Tests (E2E)
```bash
make test-frontend         # E2E tests with dev server (default)
make test-frontend-docker  # E2E tests against Docker container
```

### All Tests
```bash
make test-all  # Backend + Frontend
```

## Pre-commit Hooks

Pre-commit hooks automatically run:
- `make format` - Auto-format code
- `make lint` - Check code quality

Pre-push hooks automatically run:
- `make test` - Backend unit tests
- `make test-frontend` - Frontend E2E tests

### Installing Hooks
```bash
uv run pre-commit install --hook-type pre-commit --hook-type pre-push
```

### Bypassing Hooks (not recommended)
```bash
git push --no-verify
```

## Frontend Testing Details

### Prerequisites
1. Node.js and npm installed
2. Playwright browsers: `cd frontend && npx playwright install chromium --with-deps`

### Test Modes

#### Dev Server Mode (Default)
- Automatically starts Vite dev server on port 5173
- Fast hot-reload during development
- Run with: `make test-frontend`

#### Docker Mode
- Tests against production build in Docker container
- Requires: `docker-compose --profile frontend up -d`
- Run with: `make test-frontend-docker`

### Configuration
Tests configured in `frontend/playwright.config.ts`:
- Set `DOCKER_FRONTEND=true` to test against Docker (port 3000)
- Default is dev server mode (port 5173)

### Known Test Issues
As of 2026-02-11, 3 tests have selector issues that need fixing:
- `should open user menu dropdown` - "Settings" button ambiguous
- `should display all settings sections` - "Translation" text ambiguous  
- `should have language dropdown with options` - Options visibility check needs update

These are test quality issues, not application bugs.

## Coverage Requirements
- Backend: 97%+ coverage required
- Frontend: E2E tests cover critical user paths

## Test Output
- HTML reports: `frontend/playwright-report/`
- Screenshots on failure: `frontend/test-results/`
- Coverage reports: `htmlcov/`
