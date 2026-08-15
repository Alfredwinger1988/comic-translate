"""Controller for the editable model registry.

The registry lives in ``<user data dir>/models/models.json`` and lets users
point the app's LLM / OCR entries at newer model IDs (or add brand-new
entries) without a code change. All reads go through
``modules/utils/model_registry``; this controller is only about the editing
workflow and the two lightweight network helpers:

* ``test_api_key`` — a zero-cost list-models request that validates a key
  (no translation call, nothing billed).
* ``fetch_models`` — the same list request, returning the model IDs so the
  user can add them to the registry in one click.

Account (hosted) mode is deliberately unaffected: when a ComicLabs account
is signed in, translation and OCR run server-side and the local registry is
not consulted. The dialog says so explicitly.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

import requests

if TYPE_CHECKING:
    from controller import ComicTranslate

GEMINI_MODELS_URL = "https://generativelanguage.googleapis.com/v1beta/models"
OPENAI_DEFAULT_BASE = "https://api.openai.com/v1"


def _list_openai_compatible_models(api_key: str, api_url: str = "") -> list[str]:
    """GET {base}/models; returns the list of model IDs (free of charge)."""
    base = (api_url or OPENAI_DEFAULT_BASE).rstrip("/")
    response = requests.get(
        f"{base}/models",
        headers={"Authorization": f"Bearer {api_key}"},
        timeout=20,
    )
    response.raise_for_status()
    payload = response.json()
    items = payload.get("data", []) if isinstance(payload, dict) else []
    ids = []
    for item in items:
        if isinstance(item, dict) and isinstance(item.get("id"), str):
            ids.append(item["id"])
    return ids


def _list_gemini_models(api_key: str) -> list[str]:
    """GET the Gemini models list; returns model names like
    "models/gemini-2.5-pro" (free of charge)."""
    response = requests.get(
        GEMINI_MODELS_URL,
        params={"key": api_key},
        timeout=20,
    )
    response.raise_for_status()
    payload = response.json()
    models = payload.get("models", []) if isinstance(payload, dict) else []
    names = []
    for item in models:
        if isinstance(item, dict) and isinstance(item.get("name"), str):
            name = item["name"]
            if name.startswith("models/"):
                name = name[len("models/"):]
            names.append(name)
    return names


def test_api_key(provider: str, api_key: str, api_url: str = "") -> tuple[bool, str]:
    """Validate an API key with the lightest possible request.

    Args:
        provider: "openai" (OpenAI-compatible) or "gemini".
        api_key: The key to test.
        api_url: Custom base URL for OpenAI-compatible providers.

    Returns:
        (ok, message) — message is human-readable and never contains the key.
    """
    if not api_key:
        return False, "Enter an API key first."
    try:
        if provider == "gemini":
            _list_gemini_models(api_key)
        else:
            _list_openai_compatible_models(api_key, api_url)
        return True, "API key is valid."
    except requests.exceptions.HTTPError as exc:
        status = exc.response.status_code if exc.response is not None else None
        if status == 401:
            return False, "Invalid API key (401)."
        if status == 403:
            return False, "The API key cannot access this endpoint (403)."
        if status == 404:
            return False, "Endpoint not found (404) — check the base URL."
        return False, f"Request failed (HTTP {status})."
    except requests.exceptions.Timeout:
        return False, "Request timed out."
    except requests.exceptions.ConnectionError:
        return False, "Could not reach the provider (network error)."
    except requests.exceptions.RequestException as exc:
        return False, f"Request failed: {exc.__class__.__name__}"


def fetch_models(provider: str, api_key: str, api_url: str = "") -> tuple[bool, list[str], str]:
    """Fetch the provider's model IDs with the lightweight list request.

    Returns (ok, ids, message). ``ids`` is empty on failure.
    """
    if not api_key:
        return False, [], "Enter an API key first."
    try:
        if provider == "gemini":
            ids = _list_gemini_models(api_key)
        else:
            ids = _list_openai_compatible_models(api_key, api_url)
        return True, ids, f"Found {len(ids)} model(s)."
    except requests.exceptions.HTTPError as exc:
        status = exc.response.status_code if exc.response is not None else None
        return False, [], f"Request failed (HTTP {status})."
    except requests.exceptions.Timeout:
        return False, [], "Request timed out."
    except requests.exceptions.ConnectionError:
        return False, [], "Could not reach the provider (network error)."
    except requests.exceptions.RequestException as exc:
        return False, [], f"Request failed: {exc.__class__.__name__}"


def friendly_llm_key(api_id: str) -> str:
    """A display key for a fetched API model ID that routes to the right engine.

    The translation factory picks the engine by substring on the display key
    (GPT / Claude / Gemini / Deepseek / Custom), so fetched IDs are prefixed
    with the matching identifier. Anything unrecognized gets the "GPT-"
    prefix, which routes to the OpenAI-compatible engine.
    """
    api_id = (api_id or "").strip()
    if not api_id:
        return ""
    lowered = api_id.lower()
    if "gemini" in lowered:
        return f"Gemini-{api_id}"
    if "deepseek" in lowered:
        return f"Deepseek-{api_id}"
    if lowered.startswith("gpt-"):
        return f"GPT-{api_id[len('gpt-'):]}"
    return f"GPT-{api_id}"


class ModelRegistryController:
    """Dialog lifecycle for the model registry editor."""

    def __init__(self, main: "ComicTranslate"):
        self.main = main
        self._dialog = None

    def open_dialog(self) -> None:
        from app.ui.model_registry_dialog import ModelRegistryDialog

        if self._dialog is not None:
            try:
                self._dialog.raise_()
                self._dialog.activateWindow()
                return
            except Exception:
                self._dialog = None
        dialog = ModelRegistryDialog(self.main, parent=self.main)
        dialog.sig_saved.connect(self._on_saved)
        self._dialog = dialog
        dialog.show()

    def _on_saved(self) -> None:
        """Refresh the settings combos so new entries appear immediately."""
        try:
            self.main.settings_page.ui.refresh_registry_combos()
        except Exception:
            pass
        # Keep the Automatic-mode mirror combos in sync with the registry too.
        try:
            sync = getattr(self.main, "sync_automatic_mode_options", None)
            if callable(sync):
                sync()
        except Exception:
            pass
