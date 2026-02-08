# Docker Registry Configuration

This document describes the GitHub secrets required for publishing Docker images to Docker Hub and GitHub Container Registry (GHCR).

## Image Strategy

This project publishes three Docker images:

1. **Base Image** (`latest`) - Lightweight, transcription-only
   - Fast build (~27s)
   - Small size (~150 MB)
   - Suitable for basic transcription workflows
   - Multi-arch: amd64, arm64

2. **Diarization Image** (`diarization`) - Speaker diarization (CPU)
   - Includes PyTorch CPU (`torch==2.8.0` from CPU index) and pyannote.audio
   - `torchcodec==0.7.0` pinned for torch 2.8 compatibility
   - Image size: ~700 MB (uses CPU-only PyTorch index to avoid 4 GB CUDA bundle)
   - Supports speaker identification on CPU
   - **amd64 only** (no arm64 torchcodec CPU wheel available)

3. **Diarization GPU Image** (`diarization-gpu`) - Speaker diarization (CUDA)
   - Includes PyTorch with CUDA 12.8 (`torch==2.8.0+cu128`) and pyannote.audio
   - `torchcodec==0.7.0` pinned for torch 2.8 compatibility
   - Image size: ~6.5 GB (multi-stage build with split layers)
   - 10-100x faster diarization with NVIDIA GPU
   - **amd64 only** (CUDA runtime requirement)
   - Requires `--gpus all` at runtime
   - Base: `nvidia/cuda:12.8.1-runtime-ubuntu24.04` (Python 3.12)

## Required Secrets

Configure these secrets in your GitHub repository settings under **Settings > Secrets and variables > Actions**:

### Docker Hub

1. **DOCKERHUB_USERNAME**
   - Your Docker Hub username
   - Example: `jlcodesource`

2. **DOCKERHUB_TOKEN**
   - Docker Hub access token (NOT your password)
   - Create at: https://hub.docker.com/settings/security
   - Recommended permissions: Read, Write, Delete

### GitHub Container Registry

No additional secrets required. The workflow uses `GITHUB_TOKEN` which is automatically provided by GitHub Actions.

## Setting Up Secrets

### Via GitHub Web UI

1. Navigate to your repository on GitHub
2. Go to **Settings > Secrets and variables > Actions**
3. Click **New repository secret**
4. Add each secret with its name and value
5. Click **Add secret**

### Via GitHub CLI

```bash
# Set Docker Hub credentials
gh secret set DOCKERHUB_USERNAME --body "your-username"
gh secret set DOCKERHUB_TOKEN --body "your-token"
```

## Creating Docker Hub Access Token

1. Log in to Docker Hub: https://hub.docker.com
2. Click on your username > **Account Settings**
3. Go to **Security** tab
4. Click **New Access Token**
5. Name it (e.g., "GitHub Actions CI/CD")
6. Select permissions: **Read, Write, Delete**
7. Click **Generate**
8. Copy the token immediately (you won't see it again)
9. Add it as `DOCKERHUB_TOKEN` secret in GitHub

## Testing the Configuration

After setting up secrets, the Docker publish workflow will:
- Trigger automatically on release publication
- Can be manually triggered via **Actions > Docker CD - Publish Images > Run workflow**

### Manual Workflow Dispatch

To manually publish images:
```bash
# Using GitHub CLI (note: input version includes 'v' prefix, output tags will not)
gh workflow run docker-publish.yml -f version=v0.3.0b3

# Or via GitHub web UI
# Go to Actions > Docker CD - Publish Images > Run workflow
# Enter the version tag with 'v' prefix (e.g., v0.3.0b3)
# The workflow strips the 'v' when publishing Docker tags
```

## Published Images

Once configured, images will be available at:

**Base Image (transcription-only):**
- Docker Hub: `docker pull jlcodesource/vtt-transcribe:latest`
- GHCR: `docker pull ghcr.io/jlcodesource/vtt-transcribe:latest`

**Diarization Image (CPU, amd64 only):**
- Docker Hub: `docker pull jlcodesource/vtt-transcribe:diarization`
- GHCR: `docker pull ghcr.io/jlcodesource/vtt-transcribe:diarization`

**Diarization GPU Image (CUDA, amd64 only):**
- Docker Hub: `docker pull jlcodesource/vtt-transcribe:diarization-gpu`
- GHCR: `docker pull ghcr.io/jlcodesource/vtt-transcribe:diarization-gpu`

### Image Tags

All registries publish the following tags:

**Base Image:**
- `latest` - Latest stable release
- `0.3.0b4` - Specific version (PEP 440 format)

**Diarization Image (CPU):**
- `diarization` - Latest stable release
- `0.3.0b4-diarization` - Specific version (PEP 440 format)

**Diarization GPU Image (CUDA):**
- `diarization-gpu` - Latest stable release
- `0.3.0b4-diarization-gpu` - Specific version (PEP 440 format)

> **Note:** This project uses [PEP 440](https://peps.python.org/pep-0440/) versioning (e.g., `0.3.0b3` for beta releases). Major and minor version tags (e.g., `0.3`, `0`) are not provided to maintain compatibility with Python packaging standards.

## CI/CD Build Strategy

To optimize CI/CD performance:

- **Base image**: Built and tested on all PRs and main branch pushes
- **Diarization image**: Built and tested only on main branch (skipped for PRs to save ~10-15 minutes build time)
- **Publishing**: Both images published only on releases or manual workflow dispatch

## Troubleshooting

**Authentication failed:**
- Verify secrets are set correctly (no extra spaces)
- Ensure Docker Hub token has write permissions
- Check token hasn't expired

**Build fails:**
- Check workflow logs in Actions tab
- Verify Dockerfile builds locally: `docker build -t test .`

**Multi-platform build issues:**
- Ensure Docker Buildx is available (handled by workflow)
- May need to enable experimental features for some runners
