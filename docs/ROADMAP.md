# Roadmap

## Version 0.3.0 (Current Release)
✅ **COMPLETED** — Stable release with full feature set

### Features completed in 0.3.x series
- ✅ Direct audio transcription: first-class support for audio-only inputs (.mp3, .ogg, .wav, .m4a)
- ✅ Speaker diarization: pyannote.audio integration for speaker identification
- ✅ Docker images: base (~150MB), diarization CPU (~700MB), diarization GPU (~6.5GB)
- ✅ Stdin/stdout support: pipe audio/video through Docker containers
- ✅ PyPI packaging: `pip install vtt-transcribe` with automated OIDC publishing
- ✅ Comprehensive testing: 291 tests, 100% coverage on all `vtt_transcribe/` source files
- ✅ CI coverage: Python 3.10 tested in CI
- ✅ Docker Hub automation: description auto-updated from `docs/DOCKER_HUB.md`

## Version 0.4.0 (Next — API & Web Interface)
Objective: expose vtt-transcribe as a web service with user management and a browser-based frontend for uploading and processing files.

### Features
- **FastAPI backend**: REST API exposing transcription and diarization functionality
  - Upload audio/video files via multipart form data
  - Async transcription with job status polling
  - WebSocket support for real-time progress updates
  - Diarization endpoint with speaker labeling
- **Translation support**: Translate transcripts from language X to language Y
  - Language detection on input audio
  - Translation via OpenAI API or configurable translation backend
  - Output in original language, translated language, or side-by-side
- **User management**: Authentication and multi-user support
  - User registration and login (OAuth2 / API key)
  - Per-user API key management (OpenAI, HF tokens)
  - Job history and transcript storage per user
- **Web frontend**: Browser-based UI for file upload and transcript viewing
  - File upload with drag-and-drop
  - Real-time transcription progress
  - Transcript viewer with speaker labels and timestamps
  - Download transcripts in multiple formats (TXT, VTT, SRT)

### Technical considerations
- FastAPI with async workers for concurrent transcription jobs
- Database for user accounts and job metadata (SQLite for dev, PostgreSQL for production)
- Frontend framework TBD (React, Vue, or HTMX for simplicity)
- Docker Compose for local development (API + frontend + database)

## Version 0.5.0 (Local Processing)
Objective: add local-only Whisper processing for offline and air-gapped environments.

### Features
- **Local Whisper model support**: Run transcription without OpenAI API
  - Detect and validate local ffmpeg version (>= v8 for Whisper compatibility)
  - Model management: download, cache, and select Whisper model variants
  - Environment variable (`WHISPER_MODEL_PATH`) for custom model locations
  - Graceful fallback with clear error messages for air-gapped setups
- **Hybrid mode**: Choose between local and API-based transcription per job
- **Packaging options**: Self-contained artifacts for offline deployment
  - imageio-based ffmpeg download (default)
  - Bundled ffmpeg / PyInstaller single executable (optional)

**Why deferred to 0.5.0:**
- Local Whisper processing requires ffmpeg v8+, but current ecosystem tools (moviepy with imageio-ffmpeg and pyannote) don't yet support v8
- This allows time for upstream dependencies to mature
- The 0.4.0 API layer provides a natural integration point for plugging in local models later

## Technical Debt
- **Torch version locked to 2.8.0**: torch 2.10+ introduced breaking changes to `torch.load(..., weights_only=...)` that cause pyannote.audio 3.1 diarization models to fail. Upgrade to torch 2.10+ once pyannote.audio officially supports it.
