# Testing Guide

## Running Tests

### Backend Tests (Python)
```bash
make test              # All backend tests with coverage
make test-integration  # Integration tests only
```

### Frontend Tests (E2E)
```bash
make test-frontend  # E2E tests with dev server
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

### Running Tests
- Automatically starts Vite dev server on port 5173
- Fast hot-reload during development
- Run with: `make test-frontend`

### Configuration
Tests configured in `frontend/playwright.config.ts` to use dev server on port 5173.

## Coverage Requirements
- Backend: 97%+ coverage required
- Frontend: E2E tests cover critical user paths (12/12 tests passing)

## Test Output
- HTML reports: `frontend/playwright-report/`
- Screenshots on failure: `frontend/test-results/`
- Coverage reports: `htmlcov/`
