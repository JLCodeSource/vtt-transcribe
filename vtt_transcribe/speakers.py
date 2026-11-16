"""Speaker bookkeeping and export for a transcript (pure functions, no I/O).

A transcript is a list of segments ``{"start", "end", "text", "speaker", "translation"?}`` where ``speaker`` is the
diarizer's stable id (``SPEAKER_00``) or ``None``, plus a ``names`` map ``{speaker_id: display name}``.
Merge / split / rename only edit those two structures; every export renders names through :func:`display_name`
so a rename is reflected everywhere as ``Name: text`` (mirrors vtt-transcribe-web's ``speakers.ts``).

Used by the CLI and by vtt-transcribe-server; keep the rules here so every front end behaves the same.
"""

import re
from collections.abc import Callable
from typing import Any

from vtt_transcribe.transcript_formatter import TranscriptFormatter

Segment = dict[str, Any]

# core emits "[HH:MM:SS - HH:MM:SS] SPEAKER_00: text"; older/other output may use MM:SS and omit the speaker
_LINE = re.compile(
    r"^\[(?:(\d{2}):)?(\d{2}):(\d{2})\s*-\s*(?:(\d{2}):)?(\d{2}):(\d{2})\]\s*(?:(SPEAKER_\d+)(?::\s*|\s*$))?(.*)$"
)
_ID = re.compile(r"^SPEAKER_(\d+)$")

SAMPLES_PER_SPEAKER = 3
MAX_SAMPLE_SECONDS = 8.0


__all__ = [
    "MAX_SAMPLE_SECONDS",
    "SAMPLES_PER_SPEAKER",
    "Segment",
    "SpeakerError",
    "default_name",
    "display_name",
    "labelled",
    "merge",
    "parse_transcript",
    "rename",
    "speaker_ids",
    "split",
    "summarize",
    "to_result",
    "to_srt",
    "to_txt",
    "to_vtt",
    "translate_segments",
    "turns_to_segments",
]


class SpeakerError(ValueError):
    """An invalid speaker operation (unknown id, empty selection, ...)."""


def parse_transcript(transcript: str) -> list[Segment]:
    """Parse core's timestamped transcript into segments (speaker is ``None`` when absent)."""
    segments: list[Segment] = []
    for raw in transcript.split("\n"):
        match = _LINE.match(raw.strip())
        if not match:
            continue
        sh, sm, ss, eh, em, es, speaker, text = match.groups()
        segments.append(
            {
                "start": int(sh or 0) * 3600 + int(sm) * 60 + int(ss),
                "end": int(eh or 0) * 3600 + int(em) * 60 + int(es),
                "text": text.strip(),
                "speaker": speaker,
            }
        )
    return segments


def turns_to_segments(turns: list[tuple[float, float, str]]) -> list[Segment]:
    """Diarization-only result: speaker turns become text-less segments."""
    return [{"start": s, "end": e, "text": "", "speaker": spk} for s, e, spk in turns]


def default_name(speaker_id: str) -> str:
    """``SPEAKER_00`` -> ``Speaker 1`` (same default as the web app)."""
    match = _ID.match(speaker_id)
    return f"Speaker {int(match.group(1)) + 1}" if match else speaker_id


def display_name(speaker_id: str | None, names: dict[str, str]) -> str | None:
    """User-chosen name, falling back to the default label; ``None`` for unlabelled segments."""
    if speaker_id is None:
        return None
    return (names.get(speaker_id) or "").strip() or default_name(speaker_id)


def speaker_ids(segments: list[Segment]) -> list[str]:
    """Distinct speaker ids in order of first appearance."""
    seen: dict[str, None] = {}
    for seg in segments:
        if seg.get("speaker"):
            seen.setdefault(seg["speaker"], None)
    return list(seen)


def _require(segments: list[Segment], speaker_id: str) -> None:
    if speaker_id not in speaker_ids(segments):
        msg = f"Unknown speaker: {speaker_id}"
        raise SpeakerError(msg)


def summarize(segments: list[Segment], names: dict[str, str]) -> list[dict[str, Any]]:
    """One entry per speaker: names, talk time, a quote, and the longest turns to use as audio samples."""
    out = []
    for sid in speaker_ids(segments):
        mine = [s for s in segments if s.get("speaker") == sid]
        longest = sorted(mine, key=lambda s: s["end"] - s["start"], reverse=True)[:SAMPLES_PER_SPEAKER]
        quote = next((s["text"] for s in mine if s["text"].strip()), "")
        out.append(
            {
                "id": sid,
                "name": names.get(sid) or None,
                "display_name": display_name(sid, names),
                "seconds": sum(s["end"] - s["start"] for s in mine),
                "segment_count": len(mine),
                "sample_text": quote,
                "samples": [
                    {"start": s["start"], "end": min(s["end"], s["start"] + MAX_SAMPLE_SECONDS)}
                    for s in sorted(longest, key=lambda s: s["start"])
                ],
            }
        )
    return out


def rename(segments: list[Segment], names: dict[str, str], speaker_id: str, name: str) -> dict[str, str]:
    """Set (or, with a blank name, clear) a speaker's display name."""
    _require(segments, speaker_id)
    updated = dict(names)
    cleaned = name.strip()
    if cleaned:
        updated[speaker_id] = cleaned
    else:
        updated.pop(speaker_id, None)
    return updated


def merge(
    segments: list[Segment], names: dict[str, str], source_ids: list[str], target_id: str
) -> tuple[list[Segment], dict[str, str]]:
    """Fold ``source_ids`` into ``target_id``. The target keeps its name; sources' names are dropped."""
    _require(segments, target_id)
    for sid in source_ids:
        _require(segments, sid)
    sources = {sid for sid in source_ids if sid != target_id}
    if not sources:
        msg = "Nothing to merge: give at least one speaker other than the target"
        raise SpeakerError(msg)
    merged = [{**s, "speaker": target_id} if s.get("speaker") in sources else dict(s) for s in segments]
    return merged, {k: v for k, v in names.items() if k not in sources}


def split(segments: list[Segment], speaker_id: str, segment_indices: list[int]) -> tuple[list[Segment], str]:
    """Move the chosen segments (by index) of ``speaker_id`` to a brand-new speaker; returns the new id.

    No voice embeddings are involved, so the reviewer picks the lines that belong to the other person
    (a UI can offer "this line and everything after" as a shortcut). To re-cluster automatically instead,
    re-run diarization with a different ``num_speakers``.
    """
    _require(segments, speaker_id)
    chosen = set(segment_indices)
    if not chosen:
        msg = "Select at least one segment to split off"
        raise SpeakerError(msg)
    for i in chosen:
        if not 0 <= i < len(segments) or segments[i].get("speaker") != speaker_id:
            msg = f"Segment {i} does not belong to {speaker_id}"
            raise SpeakerError(msg)
    if len(chosen) == sum(1 for s in segments if s.get("speaker") == speaker_id):
        msg = "Cannot split off every segment of a speaker; merge or rename instead"
        raise SpeakerError(msg)
    used = [int(m.group(1)) for sid in speaker_ids(segments) if (m := _ID.match(sid))]
    new_id = f"SPEAKER_{(max(used) + 1 if used else 0):02d}"
    return [{**s, "speaker": new_id} if i in chosen else dict(s) for i, s in enumerate(segments)], new_id


# ----------------------------------------------------------------------------- rendering


def labelled(segments: list[Segment], names: dict[str, str], *, translated: bool = False) -> list[Segment]:
    """Segments with ``speaker`` replaced by the display name and (optionally) the translation as text."""
    out = []
    for s in segments:
        text = (s.get("translation") or s["text"]) if translated else s["text"]
        out.append({**s, "speaker": display_name(s.get("speaker"), names), "text": text})
    return out


def _clock(seconds: float, sep: str = ".") -> str:
    ms = round(seconds * 1000)
    h, rem = divmod(ms, 3_600_000)
    m, rem = divmod(rem, 60_000)
    s, milli = divmod(rem, 1000)
    return f"{h:02d}:{m:02d}:{s:02d}{sep}{milli:03d}"


def _line(seg: Segment) -> str:
    text = " ".join(seg["text"].split())
    return f"{seg['speaker']}: {text}" if seg.get("speaker") else text


def to_result(segments: list[Segment]) -> str:
    """Core-style timestamped transcript (``[HH:MM:SS - HH:MM:SS] Name: text``), used as the job ``result``."""

    fmt = TranscriptFormatter.format_timestamp
    return "\n".join(f"[{fmt(s['start'])} - {fmt(s['end'])}] {_line(s)}" for s in segments)


def to_txt(segments: list[Segment]) -> str:
    """Plain text, one ``Name: text`` per line."""
    return "\n".join(_line(s) for s in segments)


def to_srt(segments: list[Segment]) -> str:
    """SubRip with ``Name: text`` cues."""
    return "\n".join(
        f"{i}\n{_clock(s['start'], ',')} --> {_clock(s['end'], ',')}\n{_line(s)}\n" for i, s in enumerate(segments, 1)
    )


def to_vtt(segments: list[Segment]) -> str:
    """WebVTT with ``<v Name>`` voice tags."""
    cues = []
    for i, s in enumerate(segments, 1):
        body = " ".join(s["text"].split())
        if s.get("speaker"):
            body = f"<v {s['speaker']}>{body}"
        cues.append(f"{i}\n{_clock(s['start'])} --> {_clock(s['end'])}\n{body}\n")
    return "WEBVTT\n\n" + "\n".join(cues)


def translate_segments(segments: list[Segment], translate: Callable[[str], str]) -> list[Segment]:
    """Return ``segments`` with a ``translation`` per segment, translating through ``translate``.

    ``translate`` maps a timestamped transcript to a translated one that keeps the line structure, e.g.
    ``lambda t: AudioTranslator(key).translate_transcript(t, "French")`` or
    ``lambda t: LocalTextTranslator("en").translate_text(t, "French")``. Speakers are not sent to the
    model (only ``[ts] text`` lines, zipped back by index), so names can be renamed or merged before
    or after translating. Raises :class:`SpeakerError` if the line count changes.
    """
    plain = [{**s, "speaker": None} for s in segments]
    parsed = parse_transcript(translate(to_result(plain)))
    if len(parsed) != len(segments):
        msg = f"Translation returned {len(parsed)} lines for {len(segments)} segments"
        raise SpeakerError(msg)
    return [{**seg, "translation": tr["text"]} for seg, tr in zip(segments, parsed, strict=True)]
