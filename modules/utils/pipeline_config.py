from __future__ import annotations

from PySide6.QtCore import QCoreApplication
from typing import TYPE_CHECKING
from modules.inpainting.lama import LaMa
from modules.inpainting.mi_gan import MIGAN
from modules.inpainting.aot import AOT
from modules.inpainting.schema import Config
from app.ui.messages import Messages
from app.ui.settings.settings_page import SettingsPage

if TYPE_CHECKING:
    from controller import ComicTranslate

inpaint_map = {
    "LaMa": LaMa,
    "MI-GAN": MIGAN,
    "AOT": AOT,
}


def get_inpainter_backend(inpainter_key: str) -> str:
    inpainter_cls = inpaint_map[inpainter_key]
    return getattr(inpainter_cls, "preferred_backend", "onnx")


def resolve_extra_context(main_page, settings_page):
    """The extra context for the current translation run.

    The settings page provides the user's global ``extra_context``; the
    project glossary is merged in on top when the main page carries a
    glossary store. Using this everywhere a translation request is built means
    a glossary change automatically invalidates the translation cache (the
    cache key includes the full context).
    """
    if settings_page is None:
        settings_page = resolve_pipeline_settings(main_page)
    try:
        extra_context = settings_page.get_llm_settings().get("extra_context", "")
    except Exception:
        extra_context = ""
    store = getattr(main_page, "glossary_store", None)
    if store is not None:
        try:
            return store.merged_extra_context(extra_context or "")
        except Exception:
            return extra_context
    return extra_context or ""


def resolve_pipeline_settings(main_page):
    """Settings object the pipeline should read for the current run.

    Normally the live settings page. While a "retry this page" run is active,
    the controller points this at a frozen snapshot of the settings the
    original batch used, so a retry cannot silently pick up a different model,
    language or custom system prompt. Stand-in main-page objects that only
    carry ``settings_page`` keep working.
    """
    getter = getattr(main_page, "active_pipeline_settings", None)
    if callable(getter):
        return getter()
    return main_page.settings_page


def get_config(settings_page: SettingsPage):
    strategy_settings = settings_page.get_hd_strategy_settings()
    if strategy_settings['strategy'] == settings_page.ui.tr("Resize"):
        config = Config(hd_strategy="Resize", hd_strategy_resize_limit = strategy_settings['resize_limit'])
    elif strategy_settings['strategy'] == settings_page.ui.tr("Crop"):
        config = Config(hd_strategy="Crop", hd_strategy_crop_margin = strategy_settings['crop_margin'],
                        hd_strategy_crop_trigger_size = strategy_settings['crop_trigger_size'])
    else:
        config = Config(hd_strategy="Original")

    return config

def validate_ocr(main: ComicTranslate):
    """Ensure either API credentials are set or the user is authenticated."""
    settings_page = main.settings_page
    tr = settings_page.ui.tr
    settings = settings_page.get_all_settings()
    credentials = settings.get('credentials', {})
    ocr_tool = settings['tools']['ocr']

    if not ocr_tool:
        Messages.show_missing_tool_error(main, QCoreApplication.translate("Messages", "Text Recognition model"))
        return False
    
    if not settings_page.is_logged_in():
        Messages.show_not_logged_in_error(main)
        return False
        
    return True


def validate_translator(main: ComicTranslate, target_lang: str):
    """Ensure either API credentials are set or the user is authenticated, plus check compatibility."""
    settings_page = main.settings_page
    tr = settings_page.ui.tr
    settings = settings_page.get_all_settings()
    credentials = settings.get('credentials', {})
    translator_tool = settings['tools']['translator']
    normalized = settings_page.ui.value_mappings.get(translator_tool, translator_tool)

    if not translator_tool:
        Messages.show_missing_tool_error(main, QCoreApplication.translate("Messages", "Translator"))
        return False

    # Google Translate uses the free public endpoint, so it needs no account
    # or API key and works without signing in.
    if normalized == "Google Translate":
        return True

    if not settings_page.is_logged_in():
        Messages.show_not_logged_in_error(main)
        return False

    # Credential checks
    if normalized == "Custom":
        # Custom requires api_key, api_url, and model to be configured LOCALLY
        service = tr('Custom')
        creds = credentials.get(service, {})
        # Check if all required fields are present and non-empty
        if not all([creds.get('api_key'), creds.get('api_url'), creds.get('model')]):
            Messages.show_custom_not_configured_error(main)
            return False
        return True
        
    return True

def font_selected(main: ComicTranslate):
    if not main.render_settings().font_family:
        Messages.select_font_error(main)
        return False
    return True

def validate_settings(main: ComicTranslate, target_lang: str):
    if not validate_ocr(main):
        return False
    if not validate_translator(main, target_lang):
        return False
    if not font_selected(main):
        return False
    
    return True
