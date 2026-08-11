import base64
import json
import re
import numpy as np
from .textblock import TextBlock
import imkit as imk


def _live_model_map() -> dict:
    """LLM map, read through the editable model registry.

    Imported lazily so that ``model_registry`` (which imports nothing from
    here) can stay a leaf module. The registry keeps the built-in defaults
    authoritative, so this behaves exactly like the historical hardcoded
    MODEL_MAP until a user edits the registry file.
    """
    from .model_registry import get_llm_model_map
    return get_llm_model_map()


MODEL_MAP = _live_model_map()

def encode_image_array(img_array: np.ndarray):
    img_bytes = imk.encode_image(img_array, ".png")
    return base64.b64encode(img_bytes).decode('utf-8')

def get_raw_text(blk_list: list[TextBlock]):
    rw_txts_dict = {}
    for idx, blk in enumerate(blk_list):
        block_key = f"block_{idx}"
        rw_txts_dict[block_key] = blk.text
    
    raw_texts_json = json.dumps(rw_txts_dict, ensure_ascii=False, indent=4)
    
    return raw_texts_json

def get_raw_translation(blk_list: list[TextBlock]):
    rw_translations_dict = {}
    for idx, blk in enumerate(blk_list):
        block_key = f"block_{idx}"
        rw_translations_dict[block_key] = blk.translation
    
    raw_translations_json = json.dumps(rw_translations_dict, ensure_ascii=False, indent=4)
    
    return raw_translations_json

def set_texts_from_json(blk_list: list[TextBlock], json_string: str):
    match = re.search(r"\{[\s\S]*\}", json_string)
    if match:
        # Extract the JSON string from the matched regular expression
        json_string = match.group(0)
        translation_dict = json.loads(json_string)
        
        for idx, blk in enumerate(blk_list):
            block_key = f"block_{idx}"
            if block_key in translation_dict:
                blk.translation = translation_dict[block_key]
            else:
                print(f"Warning: {block_key} not found in JSON string.")
    else:
        print("No JSON found in the input string.")

def set_upper_case(blk_list: list[TextBlock], upper_case: bool):
    for blk in blk_list:
        translation = blk.translation
        if translation is None:
            continue
        if upper_case and not translation.isupper():
            blk.translation = translation.upper() 
        elif not upper_case and translation.isupper():
            blk.translation = translation.lower().capitalize()
        else:
            blk.translation = translation

def format_translations(blk_list: list[TextBlock], trg_lng_cd: str, upper_case: bool = True):
    for blk in blk_list:
        translation = blk.translation
        if translation is None:
            continue
        if upper_case and not translation.isupper():
            blk.translation = translation.upper()
        elif not upper_case and translation.isupper():
            blk.translation = translation.lower().capitalize()
        else:
            blk.translation = translation

def is_there_text(blk_list: list[TextBlock]) -> bool:
    return any(blk.text for blk in blk_list)

def has_translatable_content(text: str | None) -> bool:
    """True when source text contains a letter or number worth translating."""
    if not text:
        return False
    return any(ch.isalnum() for ch in text)

def is_renderable_translation(translation: str | None) -> bool:
    """True if the render stage should draw this translation.

    Punctuation-only translations (an echoed "?", "!?", "...") aren't worth
    redrawing — the original artwork already shows the same thing. Anything
    gated on rendering (like inpainting) must skip them too, otherwise the
    bubble gets cleaned with nothing drawn over it. Unlike a length check,
    this keeps legitimate single-character translations (e.g. "何", "5").
    """
    return has_translatable_content(translation)
