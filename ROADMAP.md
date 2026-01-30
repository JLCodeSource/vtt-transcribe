Roadmap

Version 0.3 (current)
Last updated: 2026-01-27T10:24:11.434Z
- TDD Github agent skill: add workflows and tests that enable a GitHub agent to run test-driven tasks, validate patches, and report status back to PRs.
- .devcontainer structure: include a .devcontainer with recommended VS Code settings, extensions, and a consistent dev image for contributors.

Features and behavior
- ✅ Direct audio transcription: first-class support for audio-only inputs (.mp3, .ogg, .wav, .m4a). If the provided file is an individual chunk, default to processing that chunk only; provide a --scan-chunks flag to detect sibling chunk files and process them all in order when requested.
- ✅ Speaker diarization: integrate pyannote.audio for speaker identification/diarization so transcripts can label speech segments by speaker; requires HF_TOKEN environment variable or --hf-token flag (user must have accepted pyannote model access on Hugging Face); expose a --diarize flag to enable diarization, --device flag for GPU/CPU selection, and interactive speaker review.
- ✅ Tests and validation: comprehensive unit and integration tests covering direct-audio paths, chunk scanning/ordering, diarization toggle, and various edge cases.

Version 0.4 (local processing & packaging)
Objective: add local-only Whisper processing and comprehensive packaging options for both connected and air-gapped environments.

**Why deferred to 0.4:**
- Local Whisper processing requires ffmpeg v8+, but current ecosystem tools (moviepy with imageio-ffmpeg and pyannote) don't yet support v8
- This allows time for upstream dependencies to mature and for proper testing of ffmpeg version detection and fallback mechanisms
- Packaging strategy can be finalized alongside local processing implementation

Features and behavior
- Local-only processing via ffmpeg + Whisper model: on first run, search PATH for ffmpeg, check its version (must be >= v8 for Whisper compatibility) and notify the user if the system ffmpeg is too old, including instructions to set an environment variable to point to a different ffmpeg binary.
  - Model handling: check for an env var (e.g., WHISPER_MODEL_PATH) that points to a local Whisper model; if absent, offer to download a selected optional Whisper model (show model size and a download link). If automatic download fails, present manual download instructions and ask the user to set the env var to the downloaded model path for next runs.
- UX details: provide clear prompts and non-blocking flags to perform downloads or to skip them for air-gapped setups; surface helpful error messages and next steps when checks fail.
- Tests and validation: add unit and integration tests covering ffmpeg version checks and model download/error flows.

# Packaging options

This needs a rethink given the new functionality, but initially, the intention was to use one of these approaches:

1) imageio-based ffmpeg (recommended default)
- Rely on imageio-ffmpeg (used by moviepy) to download an ffmpeg binary on first run.
- Advantages: smaller wheel/artifact, no need to ship a large ffmpeg binary, leverages imageio's single-download-per-environment behaviour.
- UX notes: document that the download happens once per environment and provide guidance when running in CI or constrained networks.

2) Bundled ffmpeg / self-contained artifacts
- Produce self-contained artifacts that include an ffmpeg binary built on ManyLinux2010 (or equivalent) or provide a PyInstaller-built single executable bundling ffmpeg.
- Advantages: works in air-gapped environments and on systems without a system ffmpeg available.
- Build notes: implement a manylinux/CI build pipeline that compiles ffmpeg against ManyLinux2010, runs auditwheel to produce a compliant wheel, and publishes artifacts alongside the main release.

Implementation plan
- Document both options in README and ROADMAP, and make imageio-based behaviour the default runtime path.
- Add CI jobs for manylinux builds and PyInstaller packaging; publish bundled artifacts for users who need them.
- Provide clear installation docs showing how to opt into bundled artifacts vs the default imageio behaviour.

Next steps
- Add packaging CI jobs and test wheels/artifacts; optionally add a small packaging script that automates building and publishing bundled artifacts.
