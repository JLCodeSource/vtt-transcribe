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

## Version 0.4.0 (Done — server and web interface moved out)
The API server, user management and web frontend are developed in a separate, private repository (`vtt-transcribe-server`). This package keeps the transcription library and CLI. Translation support (language X to Y) stays here.

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
