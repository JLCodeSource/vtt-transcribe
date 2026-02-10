# Infrastructure CI/CD Implementation

This document describes the CI/CD workflows needed to complete the Infrastructure & Deployment epic (vtt-transcribe-78y).

## Task 78y.2: CI Pipeline for API and Frontend Testing

### Requirements
- Run API tests with pytest and coverage
- Run frontend tests (lint, type check, unit tests, build)
- Add Docker Compose integration tests

### Implementation Needed

Create `.github/workflows/api-frontend-ci.yml`:

```yaml
name: API & Frontend CI

on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]

jobs:
  api-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v4
        with:
          python-version: '3.13'
      - run: |
          make install
          uv pip install ".[api]"
      - run: uv run pytest tests/test_api/ -v --cov=vtt_transcribe/api

  frontend-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
      - working-directory: ./frontend
        run: |
          npm ci
          npm run lint
          npm run check
          npm test
          npm run build

  integration-test:
    needs: [api-test, frontend-test]
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: |
          cat > .env << EOF
          POSTGRES_PASSWORD=test_password
          OPENAI_API_KEY=sk-test
          SECRET_KEY=test_secret_key_min_32_chars
          EOF
      - run: docker-compose up -d db api
      - run: timeout 60 bash -c 'until curl -f http://localhost:8000/health; do sleep 2; done'
      - run: docker-compose down -v
```

## Task 78y.3: Production Docker Images

### Requirements
- Build API Docker image from Dockerfile (target: api)
- Build frontend Docker image from frontend/Dockerfile
- Multi-platform support (amd64, arm64)
- Publish to GitHub Container Registry
- Version tagging with semantic versioning

### Implementation Needed

Create `.github/workflows/docker-prod.yml`:

```yaml
name: Build & Publish Production Images

on:
  release:
    types: [published]
  push:
    branches: [ main ]
  workflow_dispatch:

env:
  REGISTRY: ghcr.io

jobs:
  build-api:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: docker/setup-buildx-action@v3
      - uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}
      - uses: docker/build-push-action@v5
        with:
          context: .
          file: ./Dockerfile
          target: api
          platforms: linux/amd64,linux/arm64
          push: true
          tags: |
            ghcr.io/${{ github.repository }}/api:latest
            ghcr.io/${{ github.repository }}/api:${{ github.ref_name }}

  build-frontend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: docker/setup-buildx-action@v3
      - uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}
      - uses: docker/build-push-action@v5
        with:
          context: ./frontend
          file: ./frontend/Dockerfile
          platforms: linux/amd64,linux/arm64
          push: true
          tags: |
            ghcr.io/${{ github.repository }}/frontend:latest
            ghcr.io/${{ github.repository }}/frontend:${{ github.ref_name }}
```

## Current Status

Both workflows are designed and ready for implementation. However, they cannot be added programmatically due to GitHub OAuth App limitations (requires `workflow` scope).

**Next Steps:**
1. User with appropriate permissions should create these workflows manually
2. Or: Update OAuth App permissions to include `workflow` scope
3. Test workflows by triggering a PR or push to main

## Verification

Once workflows are added:
- Push to a PR branch to trigger CI
- Check that API tests run successfully
- Check that frontend tests run successfully
- Check that integration tests pass
- For production images: Create a release or push to main
- Verify images are published to ghcr.io

## Alternative: Manual Setup

If unable to add workflows, the infrastructure can still be used:

### Local Testing
```bash
# API tests
make install && uv pip install ".[api]"
uv run pytest tests/test_api/ -v

# Frontend tests
cd frontend
npm ci && npm run lint && npm test && npm run build

# Integration test
docker-compose up -d db api
curl http://localhost:8000/health
docker-compose down -v
```

### Manual Image Building
```bash
# Build API image
docker build -t ghcr.io/jlcodesource/vtt-transcribe/api:v0.4.0 --target api .

# Build frontend image
docker build -t ghcr.io/jlcodesource/vtt-transcribe/frontend:v0.4.0 frontend/

# Push images
docker push ghcr.io/jlcodesource/vtt-transcribe/api:v0.4.0
docker push ghcr.io/jlcodesource/vtt-transcribe/frontend:v0.4.0
```

## Infrastructure Already Complete

Note: The core infrastructure is already in place:
- ✅ Docker Compose configuration (docker-compose.yml)
- ✅ Multi-stage Dockerfile with API target
- ✅ Frontend Dockerfile
- ✅ Database initialization scripts
- ✅ Environment variable configuration (.env.example)

What's missing is only the automated CI/CD workflows for testing and publishing.
