# Testing Guide

## Running Tests

### Backend Tests (Python)
```bash
make test              # All backend tests with coverage
make test-integration  # Integration tests only
```

### Frontend Tests
```bash
make test-frontend       # All frontend tests (unit + E2E)
make test-frontend-unit  # Unit tests only (Vitest)
make test-frontend-e2e   # E2E tests only (Playwright)
```

### All Tests
```bash
make test-all  # Backend + Frontend (all tests)
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

### Test Types

#### Unit Tests (Vitest)
- Fast component-level tests
- Test individual functions and components in isolation
- Mock external dependencies
- Run with: `make test-frontend-unit`
- **112+ tests covering all components**

#### E2E Tests (Playwright)
- Full browser automation tests
- Test complete user workflows
- Automatically starts Vite dev server on port 5173
- Run with: `make test-frontend-e2e`
- **12 tests covering navigation and settings**

### Running All Frontend Tests
```bash
make test-frontend  # Runs both unit tests + E2E tests
```

### Configuration
- Unit tests: Configured in `frontend/vite.config.ts`
- E2E tests: Configured in `frontend/playwright.config.ts`

## Coverage Requirements
- Backend: 97%+ coverage required
- Frontend Unit Tests: 112+ tests covering all components (92%+ passing)
- Frontend E2E Tests: 12 tests covering critical user paths (100% passing)

## Test Output
- HTML reports: `frontend/playwright-report/`
- Screenshots on failure: `frontend/test-results/`
- Coverage reports: `htmlcov/`
