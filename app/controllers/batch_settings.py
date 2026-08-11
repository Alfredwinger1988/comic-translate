"""Freeze the settings a batch run started with, so retries can reuse them.

The pipeline pulls settings live from ``main.settings_page`` (and render options
from ``main.render_settings()``) on every page. That is what we want for a fresh
run, but a "retry this page" hours later must not silently pick up a different
model, language or custom system prompt. So a snapshot is captured when a batch
starts and re-installed for the duration of a retry.

Credentials and GPU availability are deliberately *not* frozen: an expired key
replaced by the user must be picked up, and hardware may have changed.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from controller import ComicTranslate

logger = logging.getLogger(__name__)

TOOL_KEYS = ("translator", "ocr", "detector", "inpainter")


class SettingsSnapshotProxy:
    """Stands in for the settings page, answering with frozen values.

    Everything not explicitly frozen (credentials, widgets, auth client, ...)
    is delegated to the real settings page, so callers cannot tell the
    difference.
    """

    def __init__(self, real_settings: Any, snapshot: "BatchSettingsSnapshot"):
        # Bypass __getattr__ for our own attributes.
        object.__setattr__(self, "_real_settings", real_settings)
        object.__setattr__(self, "_snapshot", snapshot)

    def get_tool_selection(self, tool_type: str):
        tools = self._snapshot.tools
        if tool_type in tools:
            return tools[tool_type]
        return self._real_settings.get_tool_selection(tool_type)

    def get_llm_settings(self) -> dict:
        return dict(self._snapshot.llm_settings)

    def get_hd_strategy_settings(self) -> dict:
        return dict(self._snapshot.hd_strategy)

    def get_export_settings(self) -> dict:
        return dict(self._snapshot.export_settings)

    def is_page_language_detection_enabled(self) -> bool:
        return bool(self._snapshot.detect_page_language)

    def __getattr__(self, name):
        return getattr(object.__getattribute__(self, "_real_settings"), name)


class BatchSettingsSnapshot:
    """Values captured at the moment a batch started."""

    def __init__(self, main: "ComicTranslate", paths: list[str]):
        settings_page = main.settings_page
        self.tools: dict[str, str] = {}
        for key in TOOL_KEYS:
            try:
                self.tools[key] = settings_page.get_tool_selection(key)
            except Exception:
                logger.debug("Could not snapshot tool selection %r", key, exc_info=True)
        self.llm_settings: dict = dict(settings_page.get_llm_settings())
        self.hd_strategy: dict = dict(settings_page.get_hd_strategy_settings())
        self.export_settings: dict = dict(settings_page.get_export_settings())
        try:
            self.detect_page_language = bool(settings_page.is_page_language_detection_enabled())
        except Exception:
            self.detect_page_language = False
        try:
            self.render_settings = main.render_settings()
        except Exception:
            self.render_settings = None
            logger.debug("Could not snapshot render settings", exc_info=True)
        # Languages live per page, not in the settings page.
        self.languages: dict[str, tuple[str, str]] = {}
        for path in paths:
            state = main.image_states.get(path, {})
            self.languages[path] = (state.get('source_lang'), state.get('target_lang'))

    def describe(self) -> str:
        return (
            f"translator={self.tools.get('translator')!r} ocr={self.tools.get('ocr')!r} "
            f"custom_prompt={bool(self.llm_settings.get('custom_system_instructions_enabled'))}"
        )


class BatchSettingsOverride:
    """Installs a snapshot as the controller's active pipeline settings.

    The settings *widget* is never swapped out (it is a real QWidget the main
    window puts in its stack and compares by identity). Instead the controller
    exposes ``active_pipeline_settings()``, which the pipeline reads, and that
    is what points at the proxy while a retry runs.
    """

    def __init__(self, main: "ComicTranslate", snapshot: BatchSettingsSnapshot, paths: list[str]):
        self.main = main
        self.snapshot = snapshot
        self.paths = list(paths)
        self._real_render_settings = None
        self._previous_languages: dict[str, tuple[str, str]] = {}
        self._active = False

    def apply(self) -> None:
        if self._active:
            return
        self.main._pipeline_settings_proxy = SettingsSnapshotProxy(
            self.main.settings_page, self.snapshot
        )

        if self.snapshot.render_settings is not None:
            self._real_render_settings = self.main.__dict__.get("render_settings")
            frozen = self.snapshot.render_settings
            self.main.render_settings = lambda: frozen

        for path in self.paths:
            langs = self.snapshot.languages.get(path)
            if not langs:
                continue
            state = self.main.image_states.get(path)
            if state is None:
                continue
            self._previous_languages[path] = (state.get('source_lang'), state.get('target_lang'))
            if langs[0]:
                state['source_lang'] = langs[0]
            if langs[1]:
                state['target_lang'] = langs[1]

        self._active = True
        logger.info("Retry using original batch settings: %s", self.snapshot.describe())

    def note_language_detected(self, path: str, source_lang: str) -> None:
        """Keep a language detected *during* the run from being rolled back.

        ``restore()`` puts the pre-retry languages back. A page whose language
        was just recognised must keep the new value, so both the snapshot and
        the saved "previous" value are updated in place.
        """
        if not source_lang:
            return
        previous = self._previous_languages.get(path)
        if previous is not None:
            self._previous_languages[path] = (source_lang, previous[1])
        frozen = self.snapshot.languages.get(path)
        if frozen is not None:
            self.snapshot.languages[path] = (source_lang, frozen[1])

    def restore(self) -> None:
        if not self._active:
            return
        self._active = False
        self.main._pipeline_settings_proxy = None
        if self.snapshot.render_settings is not None:
            # Drop the instance attribute so the class method is visible again.
            self.main.__dict__.pop("render_settings", None)
            if self._real_render_settings is not None:
                self.main.render_settings = self._real_render_settings
        for path, langs in self._previous_languages.items():
            state = self.main.image_states.get(path)
            if state is None:
                continue
            if langs[0]:
                state['source_lang'] = langs[0]
            if langs[1]:
                state['target_lang'] = langs[1]
        self._previous_languages.clear()
