"""Optional progress reporting shared by the transcription, diarization and translation steps.

A progress callback is any callable ``callback(fraction: float, message: str) -> None``. ``fraction`` is
the progress *within the step that is running* (0.0-1.0, monotonic, 1.0 when the step is done); ``message``
is a short human-readable status such as ``"Transcribing 00:12:03 / 00:45:00"``. Combine steps yourself
if you want a single overall bar. With no callback set, behaviour is unchanged. A callback that raises
never aborts the work: the error is logged and ignored.
"""

from collections.abc import Callable

from vtt_transcribe.logging_config import get_logger

ProgressCallback = Callable[[float, str], None]

logger = get_logger(__name__)


def report(callback: ProgressCallback | None, fraction: float, message: str) -> None:
    """Call ``callback`` (if any) with ``fraction`` clamped to 0-1; never raises."""
    if callback is None:
        return
    try:
        callback(min(1.0, max(0.0, fraction)), message)
    except Exception:
        logger.warning("Progress callback raised; ignoring", exc_info=True)


def format_clock(seconds: float) -> str:
    """Format seconds as HH:MM:SS."""
    s = int(max(0, seconds))
    return f"{s // 3600:02d}:{s % 3600 // 60:02d}:{s % 60:02d}"
