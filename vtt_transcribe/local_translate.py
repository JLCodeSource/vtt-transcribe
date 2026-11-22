"""Local text translation (M2M100 418M via CTranslate2): no OpenAI key, no network after first run.

Used by ``--engine local --translate-to LANG``. The model is Meta's MIT-licensed M2M100 418M converted
to CTranslate2 int8 (about 490 MB, ~100 languages, any pair). It downloads once from a pinned revision of a
public Hugging Face repository (no token) into ``<model dir>/translate``. CTranslate2 and
``huggingface-hub`` already come with faster-whisper; the only extra dependency is ``sentencepiece``.

Timestamps and speaker labels are kept as they are; only the spoken text of each line is translated.
"""

import re
import sys
from pathlib import Path
from typing import Any

from vtt_transcribe.local_whisper import resolve_device, whisper_model_dir
from vtt_transcribe.logging_config import get_logger
from vtt_transcribe.progress import ProgressCallback, report

logger = get_logger(__name__)

MODEL_REPO = "auralmira/m2m100-418M-ct2-int8"
MODEL_REVISION = "e205afefce2fd6933a1dca3b92b5063894f2f2bb"
MODEL_FILES = ("model.bin", "config.json", "shared_vocabulary.json", "sentencepiece.bpe.model")
TRANSLATE_DEPS_ERROR_MSG = "Local translation needs sentencepiece. Install with: pip install vtt-transcribe[local]"

# M2M100 language codes by English name (the names users pass to --translate-to).
_NAMES = """af Afrikaans|am Amharic|ar Arabic|ast Asturian|az Azerbaijani|ba Bashkir|be Belarusian|bg Bulgarian|bn Bengali|
br Breton|bs Bosnian|ca Catalan|ceb Cebuano|cs Czech|cy Welsh|da Danish|de German|el Greek|en English|es Spanish|
et Estonian|fa Persian|ff Fulah|fi Finnish|fr French|fy Frisian|ga Irish|gd Gaelic|gl Galician|gu Gujarati|ha Hausa|
he Hebrew|hi Hindi|hr Croatian|ht Haitian|hu Hungarian|hy Armenian|id Indonesian|ig Igbo|ilo Ilokano|is Icelandic|
it Italian|ja Japanese|jv Javanese|ka Georgian|kk Kazakh|km Khmer|kn Kannada|ko Korean|lb Luxembourgish|lg Ganda|
ln Lingala|lo Lao|lt Lithuanian|lv Latvian|mg Malagasy|mk Macedonian|ml Malayalam|mn Mongolian|mr Marathi|ms Malay|
my Burmese|ne Nepali|nl Dutch|no Norwegian|ns Northern Sotho|oc Occitan|or Oriya|pa Punjabi|pl Polish|ps Pashto|
pt Portuguese|ro Romanian|ru Russian|sd Sindhi|si Sinhala|sk Slovak|sl Slovenian|so Somali|sq Albanian|sr Serbian|
ss Swati|su Sundanese|sv Swedish|sw Swahili|ta Tamil|th Thai|tl Tagalog|tn Tswana|tr Turkish|uk Ukrainian|ur Urdu|
uz Uzbek|vi Vietnamese|wo Wolof|xh Xhosa|yi Yiddish|yo Yoruba|zh Chinese|zu Zulu"""
LANGUAGES: dict[str, str] = {}
for _entry in _NAMES.replace("\n", "").split("|"):
    _code, _name = _entry.split(" ", 1)
    LANGUAGES[_code] = _code
    LANGUAGES[_name.lower()] = _code
LANGUAGES.update({"flemish": "nl", "mandarin": "zh", "farsi": "fa", "filipino": "tl", "scottish gaelic": "gd"})

_LINE = re.compile(r"^(\[[^\]]*\]\s*)(.*)$")
# Sentence boundary: after . ! ? (and CJK/Arabic/Devanagari equivalents) plus whitespace, or right after CJK stops.
_SENTENCE_END = re.compile(r"(?<=[.!?\u061f\u0964\u06d4])\s+|(?<=[\u3002\uff01\uff1f])")
_SPEAKER = re.compile(r"^([^\s:][^:]{0,40}:\s+)(.*)$")


def split_sentences(text: str) -> list[str]:
    """Split a line into sentences. M2M100 tends to translate only one sentence of a multi-sentence input."""
    return [p for p in (s.strip() for s in _SENTENCE_END.split(text)) if p]


def language_code(language: str) -> str:
    """Map a language name ("Spanish") or code ("es", "zh-CN") to an M2M100 code; ValueError if unsupported."""
    key = language.strip().lower()
    code = LANGUAGES.get(key) or LANGUAGES.get(key.split("-")[0].split("_")[0])
    if code is None:
        msg = f"Unsupported language for local translation: {language!r}. Use an English language name or ISO 639-1 code."
        raise ValueError(msg)
    return code


class LocalTextTranslator:
    """Translate transcripts with a local M2M100 model; same ``translate_text`` shape as ``AudioTranslator``."""

    def __init__(
        self,
        source_language: str | None = None,
        device: str = "auto",
        model_dir: Path | None = None,
        progress_callback: ProgressCallback | None = None,
    ) -> None:
        """Remember settings; the model loads lazily on first use.

        ``progress_callback(fraction, message)`` is called when translation starts (0.0) and finishes (1.0).
        """
        self.progress_callback = progress_callback
        self.source_language = source_language
        self.device = resolve_device(device)
        self.model_dir = model_dir or whisper_model_dir().parent / "translate"
        self._translator: Any = None
        self._sp: Any = None

    def _load(self) -> None:
        if self._translator is not None:
            return
        try:
            import ctranslate2  # pyright: ignore[reportMissingImports]
            import sentencepiece  # pyright: ignore[reportMissingImports]
            from huggingface_hub import snapshot_download  # pyright: ignore[reportMissingImports]
        except ImportError as e:
            raise ImportError(TRANSLATE_DEPS_ERROR_MSG) from e
        print("Loading translation model (M2M100 418M, int8)...", file=sys.stderr)
        self.model_dir.mkdir(parents=True, exist_ok=True)
        path = snapshot_download(
            MODEL_REPO, revision=MODEL_REVISION, allow_patterns=list(MODEL_FILES), cache_dir=str(self.model_dir)
        )
        compute = "int8_float16" if self.device == "cuda" else "int8"
        self._translator = ctranslate2.Translator(path, device=self.device, compute_type=compute)
        self._sp = sentencepiece.SentencePieceProcessor(model_file=str(Path(path) / "sentencepiece.bpe.model"))

    def _translate_lines(self, texts: list[str], source: str, target: str) -> list[str]:
        """Translate each line sentence by sentence (one model call per batch) and rejoin the sentences."""
        self._load()
        pieces = [split_sentences(t) or [t] for t in texts]
        flat = [sentence for group in pieces for sentence in group]
        batch = [[f"__{source}__", *self._sp.encode(t, out_type=str), "</s>"] for t in flat]
        results = self._translator.translate_batch(batch, target_prefix=[[f"__{target}__"]] * len(batch), beam_size=4)
        decoded = [self._sp.decode(r.hypotheses[0][1:]) for r in results]
        out: list[str] = []
        pos = 0
        for group in pieces:
            out.append(" ".join(decoded[pos : pos + len(group)]))
            pos += len(group)
        return out

    def translate_text(self, text: str, target_language: str, *, speakers: bool = False) -> str:
        """Translate each transcript line's text, keeping ``[timestamps]`` (and speaker labels if ``speakers``)."""
        target = language_code(target_language)
        source = language_code(self.source_language) if self.source_language else "en"
        parts: list[tuple[str, str]] = []
        for line in text.split("\n"):
            prefix, body = "", line
            if m := _LINE.match(line):
                prefix, body = m.group(1), m.group(2)
                if speakers and (s := _SPEAKER.match(body)):
                    prefix, body = prefix + s.group(1), s.group(2)
            parts.append((prefix, body))
        if source == target:
            return text
        report(self.progress_callback, 0.0, f"Translating to {target_language}")
        todo = [i for i, (_, body) in enumerate(parts) if body.strip()]
        translated = self._translate_lines([parts[i][1] for i in todo], source, target) if todo else []
        out = [p + b for p, b in parts]
        for i, t in zip(todo, translated, strict=True):
            out[i] = parts[i][0] + t
        report(self.progress_callback, 1.0, "Translation complete")
        logger.info("Local translation complete", extra={"lines": len(todo), "target": target, "source": source})
        return "\n".join(out)
