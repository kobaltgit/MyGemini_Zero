# services/error_parser.py
"""
Модуль для анализа ошибок Gemini API и преобразования их в понятные для пользователя ключи локализации.
"""
import json
from typing import Dict, Any

# Карта ключевых слов из ошибок API на ключи для файла локализации
# Порядок важен: более специфичные ошибки должны идти раньше.
ERROR_MAP = {
    # --- Специфичная ошибка для поиска ---
    "tool is not supported for this model": "gemini_error_search_not_supported",

    # --- Ошибка таймаута ---
    "service_timeout": "gemini_error_timeout",

    # --- Общие ошибки ---
    "permission_denied": "gemini_error_permission_denied",
    "PERMISSION_DENIED": "gemini_error_permission_denied",
    "was not found": "gemini_error_permission_denied",

    "api_key_invalid": "gemini_error_api_key_invalid",
    "API_KEY_NOT_FOUND": "gemini_error_api_key_invalid",
    "API_KEY_INVALID": "gemini_error_api_key_invalid",

    "resource_exhausted": "gemini_error_quota_exceeded",
    "RESOURCE_EXHAUSTED": "gemini_error_quota_exceeded",
    "429": "gemini_error_quota_exceeded",

    "finish_reason: SAFETY": "gemini_error_safety",
    "SAFETY": "gemini_error_safety",

    "service_unavailable": "gemini_error_unavailable",
    "model is overloaded": "gemini_error_unavailable",

    "invalid argument": "gemini_error_invalid_argument",
    "invalid_argument": "gemini_error_invalid_argument",
}

# Ключ по умолчанию
DEFAULT_ERROR_KEY = "gemini_error_unknown"

def get_user_friendly_error_key(error_detail: Dict[str, Any]) -> str:
    """
    Анализирует JSON-объект ошибки от API и возвращает ключ для локализации.
    """
    if not isinstance(error_detail, dict):
        return DEFAULT_ERROR_KEY

    error_str = json.dumps(error_detail).lower()

    for keyword, loc_key in ERROR_MAP.items():
        if keyword.lower() in error_str:
            return loc_key

    return DEFAULT_ERROR_KEY