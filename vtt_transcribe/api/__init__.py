"""FastAPI web service for vtt-transcribe."""

__all__ = ["app"]

try:
    from vtt_transcribe.api.app import app
except ImportError:
    # API dependencies not available
    app = None  # type: ignore[assignment]
