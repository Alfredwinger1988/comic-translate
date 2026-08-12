"""Editable model registry for LLM and OCR models.

The app ships with a hardcoded default model map (the ``MODEL_MAP`` in
``translator_utils``). Users who want to point a provider at a newer model
(one the app hasn't shipped yet) can edit the registry file; the editor
dialog in the Tools settings page is the supported way to do that.

Design rules:

* **Never crash on a bad file.** If the registry file is missing, corrupt,
  or contains a non-dict value, every accessor falls back to the built-in
  defaults. The file is only *written* when the user edits something, so a
  fresh install never creates it.
* **Defaults stay authoritative.** ``get_default_map`` returns the built-in
  map; a registry entry only *overrides* a key. Removed default keys are
  restored from defaults, so a user cannot accidentally delete a model that
  the UI's ``value_mappings`` still refers to.
* **File location:** ``<user data dir>/models/models.json`` (same directory
  the model downloader uses), so it travels with the user's data and is
  respected by the headless test harness via ``XDG_DATA_HOME``.
"""
from __future__ import annotations

import json
import os

from .paths import get_user_data_dir

# --------------------------------------------------------------------------
# Built-in defaults. These must stay exactly in sync with the historical
# MODEL_MAP, so existing installs and projects behave identically.
# --------------------------------------------------------------------------
DEFAULT_LLM_MODELS = {
    "Custom": "",
    "Deepseek": "deepseek-v4-flash",
    "GPT-4.1": "gpt-4.1",
    "GPT-4.1-mini": "gpt-4.1-mini",
    "Claude-4.6-Sonnet": "claude-sonnet-4-6",
    "Claude-4.5-Haiku": "claude-haiku-4-5-20251001",
    "Gemini-2.5-Flash-Lite": "gemini-2.5-flash-lite",
    "Gemini-3.1-Flash-Lite": "gemini-3.1-flash-lite",
    "Gemini-2.5-Pro": "gemini-2.5-pro",
}

DEFAULT_OCR_MODELS = {
    "GPT-4.1-mini": "gpt-4.1-mini",
    "Gemini-2.5-Flash-Lite": "gemini-2.5-flash-lite",
}

_REGISTRY_VERSION = 1


def registry_path() -> str:
    """Absolute path of the registry file."""
    return os.path.join(get_user_data_dir(), "models", "models.json")


def _load_raw() -> dict:
    """Read the file as a plain dict; tolerate every failure mode."""
    path = registry_path()
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, ValueError, TypeError):
        return {}
    if not isinstance(data, dict):
        return {}
    return data


def _read_models(section: str) -> dict:
    """The *stored* overrides for a section (empty dict when absent)."""
    raw = _load_raw()
    section_data = raw.get(section)
    if not isinstance(section_data, dict):
        return {}
    out = {}
    for key, value in section_data.items():
        if isinstance(key, str) and isinstance(value, str):
            out[key] = value
    return out


def _defaults_for(section: str) -> dict:
    return dict(DEFAULT_LLM_MODELS if section == "llm" else DEFAULT_OCR_MODELS)


def get_model_map(section: str) -> dict:
    """The effective model map: defaults overridden by the registry file."""
    merged = _defaults_for(section)
    merged.update(_read_models(section))
    return merged


def get_llm_model_map() -> dict:
    """Effective LLM map (see ``MODEL_MAP`` in translator_utils)."""
    return get_model_map("llm")


def get_ocr_model_map() -> dict:
    """Effective OCR map (see ``MODEL_MAP`` consumers in modules/ocr)."""
    return get_model_map("ocr")


def get_registry_data() -> dict:
    """Full registry for the editor dialog: {'llm': {...}, 'ocr': {...}}."""
    return {
        "llm": get_model_map("llm"),
        "ocr": get_model_map("ocr"),
    }


def _write_registry(section: str, models: dict) -> None:
    """Persist one section, preserving the other section's stored overrides."""
    raw = _load_raw()
    raw["version"] = _REGISTRY_VERSION
    # Keep only string -> string entries.
    raw[section] = {k: v for k, v in models.items() if isinstance(k, str) and isinstance(v, str)}
    path = registry_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp_path = f"{path}.tmp"
    with open(tmp_path, "w", encoding="utf-8") as fh:
        json.dump(raw, fh, ensure_ascii=False, indent=2)
    os.replace(tmp_path, path)


def set_llm_models(models: dict) -> None:
    """Replace the LLM section; keys removed from the defaults come back."""
    _write_registry("llm", models)


def set_ocr_models(models: dict) -> None:
    """Replace the OCR section; keys removed from the defaults come back."""
    _write_registry("ocr", models)


def reset_registry() -> None:
    """Delete the file so everything falls back to the built-in defaults."""
    try:
        os.remove(registry_path())
    except OSError:
        pass
