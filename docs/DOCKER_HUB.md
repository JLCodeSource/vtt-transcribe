# vtt-transcribe

**CLI tool to extract audio from video files and transcribe using OpenAI's Whisper API, with optional speaker diarization.**

[![PyPI](https://img.shields.io/pypi/v/vtt-transcribe)](https://pypi.org/project/vtt-transcribe/)
[![GitHub](https://img.shields.io/github/stars/jlcodesource/vtt-transcribe)](https://github.com/jlcodesource/vtt-transcribe)

## Image Variants

| Tag | Size | Arch | Description |
|-----|------|------|-------------|
| `latest` | ~150 MB | amd64, arm64 | Transcription only — lightweight, no diarization |
| `diarization` | ~700 MB | amd64 | Speaker diarization with PyTorch CPU + pyannote.audio |
| `diarization-gpu` | ~6.5 GB | amd64 | GPU-accelerated diarization with CUDA 12.8 |

### Version Tags

Each release also publishes version-specific tags using [PEP 440](https://peps.python.org/pep-0440/) format:

- `0.3.0b4` — Base image at specific version
- `0.3.0b4-diarization` — Diarization (CPU) at specific version
- `0.3.0b4-diarization-gpu` — Diarization GPU at specific version

## Quick Start

```bash
# Transcribe a video file (base image)
cat video.mp4 | docker run -i -e OPENAI_API_KEY="$OPENAI_API_KEY" \
  jlcodesource/vtt-transcribe:latest

# Save transcript to a file
cat video.mp4 | docker run -i -e OPENAI_API_KEY="$OPENAI_API_KEY" \
  jlcodesource/vtt-transcribe:latest > transcript.txt

# Transcribe with speaker diarization (CPU)
cat video.mp4 | docker run -i \
  -e OPENAI_API_KEY="$OPENAI_API_KEY" \
  -e HF_TOKEN="$HF_TOKEN" \
  jlcodesource/vtt-transcribe:diarization --diarize

# GPU-accelerated diarization (requires nvidia-docker)
cat video.mp4 | docker run -i --gpus all \
  -e OPENAI_API_KEY="$OPENAI_API_KEY" \
  -e HF_TOKEN="$HF_TOKEN" \
  jlcodesource/vtt-transcribe:diarization-gpu --diarize --device cuda
```

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `OPENAI_API_KEY` | **Yes** | OpenAI API key for Whisper transcription |
| `HF_TOKEN` | For `--diarize` | Hugging Face token for pyannote speaker diarization models |

### Diarization Prerequisites

Before using `--diarize`, accept the terms for these Hugging Face models:

- [pyannote/speaker-diarization-3.1](https://huggingface.co/pyannote/speaker-diarization-3.1)
- [pyannote/segmentation-3.0](https://huggingface.co/pyannote/segmentation-3.0)

## Supported Input Formats

- **Video:** MP4, AVI, WebM, MKV
- **Audio:** MP3, WAV, OGG, M4A

All input is piped via stdin. Output goes to stdout.

## Usage Notes

- **Stdin mode only** — Docker images use stdin/stdout (no volume mounts needed)
- Interactive speaker review is automatically disabled in stdin mode
- Speaker labels are generic: `SPEAKER_00`, `SPEAKER_01`, etc.
- The `-s`, `-o`, `--apply-diarization`, and `--scan-chunks` flags are not available in stdin mode

## Technical Details

### Diarization Images

- **torch 2.8.0** with **torchcodec 0.7.0** (pinned per [compatibility table](https://github.com/pytorch/torchcodec#installing-torchcodec))
- CPU image uses the PyTorch CPU-only index to keep image size small (~700 MB vs ~4 GB with bundled CUDA)
- GPU image uses `nvidia/cuda:12.8.1-runtime-ubuntu24.04` with multi-stage build and split Docker layers
- Both diarization images are **amd64 only** (no arm64 torchcodec wheels available)

### Large File Handling

Files exceeding the 25 MB Whisper API limit are automatically chunked into minute-aligned segments. Timestamps from each chunk are shifted to produce a continuous absolute timeline in the final transcript.

## Pipeline Examples

```bash
# Transcribe and search for a speaker
cat recording.mp3 | docker run -i \
  -e OPENAI_API_KEY="$OPENAI_API_KEY" \
  -e HF_TOKEN="$HF_TOKEN" \
  jlcodesource/vtt-transcribe:diarization --diarize \
  | grep "SPEAKER_00"

# Process multiple files
for f in *.mp4; do
  echo "=== $f ==="
  cat "$f" | docker run -i -e OPENAI_API_KEY="$OPENAI_API_KEY" \
    jlcodesource/vtt-transcribe:latest
done > all_transcripts.txt
```

## Links

- **Source:** [github.com/jlcodesource/vtt-transcribe](https://github.com/jlcodesource/vtt-transcribe)
- **PyPI:** [pypi.org/project/vtt-transcribe](https://pypi.org/project/vtt-transcribe/)
- **Issues:** [GitHub Issues](https://github.com/jlcodesource/vtt-transcribe/issues)
- **Changelog:** [CHANGELOG.md](https://github.com/jlcodesource/vtt-transcribe/blob/main/docs/CHANGELOG.md)

## License

MIT — see [LICENSE](https://github.com/jlcodesource/vtt-transcribe/blob/main/LICENSE)
