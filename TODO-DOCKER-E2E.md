# TODO: Full Docker Environment E2E Testing

## Priority: Medium (P2)
## Type: Task
## Status: Open

## Description
Create comprehensive E2E test suite that validates the full Docker stack (frontend, backend, database) working together in a production-like environment.

## Requirements
- Test real API calls (no mocks)
- Test authentication flow end-to-end
- Test transcription workflows with actual files
- Test file uploads through the full stack
- Test WebSocket connections for progress updates
- Test database persistence
- Test container networking and communication

## Acceptance Criteria
- [ ] Docker compose environment starts successfully
- [ ] Tests can access frontend at port 3000
- [ ] Tests can access backend API at port 8000
- [ ] Database connections work
- [ ] File upload -> transcription -> results flow works
- [ ] WebSocket real-time updates work
- [ ] Tests run in CI/CD pipeline
- [ ] Documentation for running Docker E2E tests

## Technical Approach
Consider using:
- Playwright with Docker network access
- Docker Compose test profile
- Wait strategies for service readiness
- Test fixtures for sample audio/video files
- Cleanup between test runs

## Blocked By
- Port mapping issues in dev containers need resolution
- Or: Run E2E tests in dedicated CI environment (not dev containers)

## Notes
- Current `make test-frontend` works well for component/UI testing
- This task is specifically for **integration** testing the full stack
- Should complement (not replace) existing unit and E2E tests
