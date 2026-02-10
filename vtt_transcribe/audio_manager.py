"""Audio file management utilities for video transcription."""

import time
from pathlib import Path

from moviepy.audio.io.AudioFileClip import AudioFileClip
from moviepy.video.io.VideoFileClip import VideoFileClip

from vtt_transcribe.logging_config import get_logger

# Constants
AUDIO_EXTENSION = ".mp3"
AUDIO_CODEC = "libmp3lame"

logger = get_logger(__name__)


class AudioFileManager:
    """Manage audio file operations including extraction and cleanup."""

    @staticmethod
    def extract_from_video(video_path: Path, audio_path: Path, *, force: bool = False) -> None:
        """Extract audio from video file.

        Args:
            video_path: Path to input video file.
            audio_path: Path where audio file will be saved.
            force: If True, overwrite existing audio file.
        """
        logger.info(
            "Starting audio extraction", extra={"video_path": str(video_path), "audio_path": str(audio_path), "force": force}
        )

        if audio_path.exists() and not force:
            logger.debug("Audio file already exists, skipping extraction")
            print(f"Audio file already exists: {audio_path}")
            return

        start_time = time.time()
        with VideoFileClip(str(video_path)) as video_clip:
            if video_clip.audio is None:
                logger.warning("No audio track found in video", extra={"video_path": str(video_path)})
                print(f"Warning: No audio track found in {video_path}")
                return

            print(f"Extracting audio from {video_path} to {audio_path}...")
            video_clip.audio.write_audiofile(str(audio_path), codec=AUDIO_CODEC, logger=None)

        duration = time.time() - start_time
        audio_size = audio_path.stat().st_size if audio_path.exists() else 0
        logger.info(
            "Audio extraction complete",
            extra={
                "duration_seconds": round(duration, 2),
                "audio_size_mb": round(audio_size / 1024 / 1024, 2),
                "audio_path": str(audio_path),
            },
        )

    @staticmethod
    def get_duration(audio_path: Path) -> float:
        """Get duration of audio file in seconds.

        Args:
            audio_path: Path to audio file.

        Returns:
            Duration in seconds.
        """
        logger.debug("Getting audio duration", extra={"audio_path": str(audio_path)})
        with AudioFileClip(str(audio_path)) as audio_clip:
            duration = float(audio_clip.duration)
        logger.debug("Audio duration retrieved", extra={"duration_seconds": duration})
        return duration

    @staticmethod
    def extract_chunk(audio_path: Path, start_time: float, end_time: float, chunk_index: int) -> Path:
        """Extract a chunk from audio file.

        Args:
            audio_path: Path to source audio file.
            start_time: Start time in seconds.
            end_time: End time in seconds.
            chunk_index: Index number for the chunk.

        Returns:
            Path to the extracted chunk file.
        """
        chunk_path = audio_path.parent / f"{audio_path.stem}_chunk{chunk_index}{AUDIO_EXTENSION}"
        logger.debug(
            "Extracting audio chunk",
            extra={
                "chunk_index": chunk_index,
                "start_time": start_time,
                "end_time": end_time,
                "duration": end_time - start_time,
            },
        )

        extract_start = time.time()
        with AudioFileClip(str(audio_path)) as audio_clip:
            chunk = audio_clip.subclipped(start_time, end_time)
            chunk.write_audiofile(str(chunk_path), codec=AUDIO_CODEC, logger=None)

        extract_duration = time.time() - extract_start
        chunk_size = chunk_path.stat().st_size if chunk_path.exists() else 0
        logger.info(
            "Audio chunk extracted",
            extra={
                "chunk_index": chunk_index,
                "chunk_path": str(chunk_path),
                "chunk_size_mb": round(chunk_size / 1024 / 1024, 2),
                "extraction_time_seconds": round(extract_duration, 2),
            },
        )

        return chunk_path

    @staticmethod
    def find_chunks(audio_path: Path) -> list[Path]:
        """Find all chunk files for given audio file.

        Args:
            audio_path: Path to main audio file.

        Returns:
            List of chunk file paths, sorted by chunk index.
        """
        if not audio_path.parent.exists():
            return []

        pattern = f"{audio_path.stem}_chunk*{AUDIO_EXTENSION}"
        return sorted(
            audio_path.parent.glob(pattern),
            key=lambda p: int(p.stem.split("_chunk")[1]),
        )

    @staticmethod
    def cleanup_files(audio_path: Path) -> None:
        """Delete audio file and all its chunks.

        Args:
            audio_path: Path to main audio file.
        """
        chunks = AudioFileManager.find_chunks(audio_path)
        logger.info("Starting audio cleanup", extra={"audio_path": str(audio_path), "chunk_count": len(chunks)})

        # Delete main audio file
        if audio_path.exists():
            audio_path.unlink()
            logger.debug("Deleted main audio file", extra={"path": str(audio_path)})

        # Delete all chunks
        for chunk in AudioFileManager.find_chunks(audio_path):
            if chunk.exists():
                chunk.unlink()

    @staticmethod
    def cleanup_chunks_only(audio_path: Path) -> None:
        """Delete only chunk files, keeping main audio file.

        Args:
            audio_path: Path to main audio file.
        """
        for chunk in AudioFileManager.find_chunks(audio_path):
            if chunk.exists():
                chunk.unlink()
