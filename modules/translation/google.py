from __future__ import annotations

from typing import Any

import requests

from .base import TraditionalTranslation
from ..utils.textblock import TextBlock
from ..utils.retry import with_retry


class GoogleTranslation(TraditionalTranslation):
    """Translation engine using the free Google Translate endpoint.

    Uses the public ``translate_a/single`` endpoint, so it needs no API key
    and no account. It is therefore kept local-only (never proxied through the
    ComicLabs web API) and does not require sign-in.
    """

    def __init__(self):
        self.source_lang_code = "auto"
        self.target_lang_code = None
        self._settings_ref = None

    def initialize(self, settings: Any, source_lang: str, target_lang: str) -> None:
        src = self.get_language_code(source_lang)
        # "Auto" resolves to Google's auto-detection code.
        self.source_lang_code = src or "auto"
        self.target_lang_code = self.preprocess_language_code(
            self.get_language_code(target_lang)
        )
        self._settings_ref = settings

    def translate(self, blk_list: list[TextBlock]) -> list[TextBlock]:
        for blk in blk_list:
            text = self.preprocess_text(blk.text, self.source_lang_code)
            if not text.strip():
                blk.translation = ""
                continue

            blk.translation = with_retry(
                lambda t=text: self._translate_text(t),
                getattr(self, "_settings_ref", None),
                label=f"Google Translate ({self.target_lang_code})",
            )

        return blk_list

    def _translate_text(self, text: str) -> str:
        url = "https://translate.googleapis.com/translate_a/single"
        params = {
            "client": "gtx",
            "sl": self.source_lang_code,
            "tl": self.target_lang_code,
            "dt": "t",
            "q": text,
        }
        headers = {"User-Agent": "Mozilla/5.0"}
        resp = requests.get(url, params=params, headers=headers, timeout=30)
        resp.raise_for_status()
        data = resp.json()

        # Response layout: [[ [translated, original, ...], ... ], null, ...]
        segments = data[0] if isinstance(data, list) and data and isinstance(data[0], list) else []
        parts = []
        for segment in segments:
            if isinstance(segment, list) and segment and isinstance(segment[0], str):
                parts.append(segment[0])
        return "".join(parts)

    def preprocess_language_code(self, lang_code: str) -> str:
        if not lang_code:
            return lang_code
        # get_language_code emits lowercase for the Brazilian variant; Google
        # expects the uppercase region tag.
        if lang_code.lower() == "pt-br":
            return "pt-BR"
        return lang_code
