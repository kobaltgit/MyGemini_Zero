# File: services/gemini_service.py

# Copyright (C) 2025 kobaltgit
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.

import asyncio
import aiohttp
import PIL.Image
from typing import List, Union, Dict, Optional, Any, Tuple
from io import BytesIO
import base64
import json
import re
from cachetools import LRUCache
from cryptography.fernet import Fernet

from config.settings import DEFAULT_MODEL_ID, GENERATION_CONFIG, MODELS_METADATA, SAFETY_SETTINGS, BOT_PERSONAS, BOT_STYLES
from utils import guide_manager
from logger_config import get_logger
from database import db_manager
from .error_parser import get_user_friendly_error_key
from .vector_store_manager import VectorStoreManager

gemini_logger = get_logger('gemini_api')

# Кэш для хранения истории диалогов. Ограничен по размеру для предотвращения утечек памяти.
# maxsize=100 означает, что в памяти будет храниться история 100 последних используемых диалогов.
dialog_chats_cache: LRUCache = LRUCache(maxsize=100)

GEMINI_API_BASE_URL = "https://generativelanguage.googleapis.com/v1beta"

# Конфигурация инструмента для поиска Google
GOOGLE_SEARCH_TOOL = {
    "tools": [{"google_search": {}}]
}


class GeminiAPIError(Exception):
    """Кастомное исключение для ошибок Gemini API."""
    def __init__(self, message: str, details: Optional[Dict] = None):
        super().__init__(message)
        self.details = details or {}
        self.error_key = get_user_friendly_error_key(self.details)

async def _make_gemini_request_async(api_key: str, url: str, payload: Optional[Dict] = None,
                                     method: str = 'POST') -> Dict[str, Any]:
    """
    Выполняет универсальный асинхронный HTTP-запрос к Gemini API.
    В случае ошибки выбрасывает GeminiAPIError.
    Реализует механизм повторных попыток для временных ошибок.
    """
    headers = {'Content-Type': 'application/json'}
    params = {'key': api_key}

    # --- НОВЫЙ БЛОК: Настройки для повторных попыток ---
    max_retries = 3
    retry_delay = 2  # задержка в секундах

    for attempt in range(max_retries):
        try:
            async with aiohttp.ClientSession() as session:
                request_args = {'params': params, 'headers': headers, 'timeout': aiohttp.ClientTimeout(total=60)}
                if payload:
                    request_args['json'] = payload

                async with session.request(method, url, **request_args) as response:
                    response_json = await response.json()
                    if response.status != 200:
                        error_details = response_json.get('error', {})
                        error_message = error_details.get('message', 'Неизвестная ошибка API')

                        # --- НОВЫЙ БЛОК: Логика повторных попыток ---
                        # Повторяем только для ошибок 5xx (проблемы на сервере) и 429 (превышение квот)
                        if response.status >= 500 or response.status == 429:
                            if attempt < max_retries - 1:
                                gemini_logger.warning(
                                    f"Попытка {attempt + 1}/{max_retries}: "
                                    f"Получена временная ошибка (HTTP {response.status}). "
                                    f"Повтор через {retry_delay} сек. Ошибка: {error_message}",
                                    extra={'user_id': 'System'}
                                )
                                await asyncio.sleep(retry_delay)
                                continue # Переходим к следующей попытке

                        # Если ошибка не временная или попытки закончились, выбрасываем исключение
                        gemini_logger.error(f"Ошибка API Gemini (HTTP {response.status}): {response_json}", extra={'user_id': 'System'})
                        raise GeminiAPIError(error_message, details=error_details)

                    return response_json # Успешный ответ

        except (asyncio.TimeoutError, aiohttp.ServerTimeoutError):
            gemini_logger.error(f"Тайм-аут при запросе к Gemini API после {attempt + 1} попыток.", extra={'user_id': 'System'})
            if attempt < max_retries - 1:
                await asyncio.sleep(retry_delay)
                continue
            # Если все попытки провалились по таймауту
            raise GeminiAPIError("Сервер не ответил вовремя.", details={"error": {"message": "service_timeout"}})
        except aiohttp.ClientError as e:
            gemini_logger.exception(f"Сетевая ошибка при запросе к Gemini API: {e}", extra={'user_id': 'System'})
            # Для сетевых ошибок тоже можно попробовать повторить
            if attempt < max_retries - 1:
                await asyncio.sleep(retry_delay)
                continue
            raise GeminiAPIError("Сетевая ошибка при подключении к сервису.", details={"error": {"message": "service_unavailable"}})
        except GeminiAPIError:
            # Пробрасываем "фатальные" ошибки API без повторных попыток
            raise
        except Exception as e:
            gemini_logger.exception(f"Неожиданная ошибка при выполнении запроса к Gemini API: {e}", extra={'user_id': 'System'})
            if attempt < max_retries - 1:
                await asyncio.sleep(retry_delay)
                continue
            raise GeminiAPIError(f"Неожиданная ошибка: {e}", details={"error": {"message": "unknown_error"}})

    # Этот код выполнится, только если все попытки провалились
    raise GeminiAPIError("Не удалось получить ответ от API после нескольких попыток.", details={"error": {"message": "service_unavailable"}})


async def _get_dialog_chat_history(dialog_id: int, fernet_instance: Fernet) -> List[Dict[str, Any]]:
    """
    Возвращает или создает историю чата для диалога из кэша или БД.

    Если история есть в LRU-кэше, возвращает ее. Иначе, загружает
    зашифрованную историю из базы данных, расшифровывает ее с помощью
    предоставленного ключа сессии, форматирует для Gemini API и
    сохраняет в кэш.

    Args:
        dialog_id: ID диалога, для которого нужно получить историю.
        fernet_instance: Экземпляр Fernet с ключом сессии для расшифровки.

    Returns:
        Список словарей, представляющий историю чата в формате Gemini.
    """
    if dialog_id not in dialog_chats_cache:
        gemini_logger.debug(f"Кэш истории для dialog_id: {dialog_id} не найден. Загрузка из БД.")
        # Передаем ключ для расшифровки истории из БД
        history_from_db = await db_manager.get_conversation_history(dialog_id, fernet_instance, limit=20)
        gemini_history = []
        for item in history_from_db:
            role = 'user' if item.get('role') == 'user' else 'model'
            # Убедимся, что message_text не None
            message_text = item.get('message_text', '')
            gemini_history.append({"role": role, "parts": [{"text": message_text}]})
        dialog_chats_cache[dialog_id] = gemini_history
        gemini_logger.info(f"История для dialog_id: {dialog_id} загружена в кэш ({len(gemini_history)} сообщений).")
    return dialog_chats_cache[dialog_id]

def reset_dialog_chat(dialog_id: int):
    """Сбрасывает историю чата для конкретного диалога в кэше."""
    if dialog_id in dialog_chats_cache:
        del dialog_chats_cache[dialog_id]
        gemini_logger.info(f"История чата в кэше для dialog_id: {dialog_id} сброшена.")

async def _get_system_instruction_text(user_id: int, fernet_instance: Fernet) -> Optional[str]:
    """
    Формирует текст системной инструкции, объединяя мета-инструкцию,
    профиль пользователя и персону/стиль.
    """
    lang_code = await db_manager.get_user_language(user_id)
    system_prompt_parts = []

    # --- Шаг 1: Добавляем мета-инструкцию ("паспорт") ---
    # Импортируем локализацию здесь, чтобы избежать циклических зависимостей
    from utils import localization as loc
    meta_instruction = loc.get_text('bot_meta_instruction', lang_code)
    system_prompt_parts.append(meta_instruction)
    system_prompt_parts.append("---")

    # --- Шаг 2: Загрузка и форматирование профиля пользователя ---
    user_profile = await db_manager.get_user_profile(user_id, fernet_instance)
    if user_profile:
        system_prompt_parts.append("Вот ключевая информация о твоем пользователе, которую ты должен всегда учитывать для персонализации ответов:")
        
        profile_key_map = {
            'role': 'Профессия', 'industry': 'Сфера', 'projects': 'Текущие проекты',
            'stack': 'Инструменты', 'purpose': 'Основная цель использования',
            'style': 'Предпочитаемый стиль общения', 'hobby': 'Хобби', 'rules': 'Особые правила'
        }
        
        profile_text = ""
        for key, value in user_profile.items():
            display_key = profile_key_map.get(key, key.capitalize())
            profile_text += f"- {display_key}: {value}\n"
        
        system_prompt_parts.append(profile_text.strip())
        system_prompt_parts.append("---")

    # --- Шаг 3: Добавление персоны или стиля ---
    persona_prompt = ""
    persona_id = await db_manager.get_user_persona(user_id)

    if persona_id != 'default':
        persona_info = BOT_PERSONAS.get(persona_id, BOT_PERSONAS['default'])
        prompt_key = f"prompt_{lang_code}"
        persona_prompt = persona_info.get(prompt_key, persona_info.get('prompt_ru', ''))
    else:
        style_id = await db_manager.get_user_bot_style(user_id)
        if style_id != 'default':
            style_prompts = {
                'formal': "You must answer in a strictly formal and business-like manner.",
                'informal': "You should communicate in a friendly and informal way.",
                'concise': "Your answers must be as short and to the point as possible.",
                'detailed': "Provide detailed and comprehensive answers, explaining all aspects."
            }
            persona_prompt = style_prompts.get(style_id, "")

    if persona_prompt:
        system_prompt_parts.append(persona_prompt)

    return "\n".join(system_prompt_parts).strip()

async def generate_response(user_id: int, prompt: Union[str, List[Union[str, PIL.Image.Image, bytes]]], api_key: str, fernet_instance: Fernet) -> Tuple[str, List[Dict[str, str]]]:
    """
    Генерирует ответ от Gemini, динамически включая краткосрочную и долгосрочную память
    с учетом особенностей разных семейств моделей (Gemini vs Gemma).
    """
    active_dialog_id = await db_manager.get_active_dialog_id(user_id)
    if not active_dialog_id:
        gemini_logger.error(f"У пользователя {user_id} нет активного диалога для генерации ответа.")
        raise GeminiAPIError("Не найден активный диалог. Пожалуйста, перезапустите бота командой /start.", details={})

    # --- 1. Инициализация сервисов ---
    try:
        vector_store = VectorStoreManager(api_key=api_key)
    except ValueError as e:
        raise GeminiAPIError(str(e), details={"error": {"message": "API_KEY_INVALID"}})

    model_name = await db_manager.get_user_gemini_model(user_id) or DEFAULT_MODEL_ID
    
    # --- ВОЗВРАЩАЕМ ЛОГИКУ ДЛЯ GEMMA ---
    is_gemma_model = model_name.startswith('gemma')
    
    # Краткосрочная память (загружаем только для моделей, которые ее поддерживают)
    history = []
    if not is_gemma_model:
        history = await _get_dialog_chat_history(active_dialog_id, fernet_instance)
    
    model_meta = MODELS_METADATA.get(model_name, {})
    use_search = model_meta.get("supports_search", False)
    use_system_instruction = model_meta.get("supports_system_instruction", False)

    gemini_logger.info(f"Генерация: user={user_id}, model={model_name}, search={use_search}, system_instr={use_system_instruction}, stateless={is_gemma_model}", extra={'user_id': str(user_id)})

    # --- 2. Формирование промпта пользователя ---
    user_parts = []
    user_message_for_db = ""
    # Блок if/elif для обработки текста, фото и голоса остается таким же, как в оригинале
    if isinstance(prompt, str):
        user_parts.append({"text": prompt})
        user_message_for_db = prompt
    elif isinstance(prompt, list):
        text_part = ""
        media_type = None
        for item in prompt:
            if isinstance(item, str):
                text_part = item
            elif isinstance(item, PIL.Image.Image):
                media_type = "image"
                buffered = BytesIO()
                if item.mode == 'RGBA': item = item.convert('RGB')
                item.save(buffered, format="JPEG")
                img_str = base64.b64encode(buffered.getvalue()).decode('utf-8')
                user_parts.append({"inline_data": {"mime_type": "image/jpeg", "data": img_str}})
            elif isinstance(item, bytes):
                media_type = "audio"
                audio_str = base64.b64encode(item).decode('utf-8')
                user_parts.append({"inline_data": {"mime_type": "audio/ogg", "data": audio_str}})
        if text_part:
            user_parts.append({"text": text_part})
        if media_type == "image":
            user_message_for_db = f"[Изображение] {text_part}".strip()
        elif media_type == "audio":
            user_message_for_db = f"[Голосовое сообщение] {text_part}".strip()
        else:
            user_message_for_db = text_part
    
    # --- 3. Поиск и внедрение контекста из долговременной памяти ---
    long_term_memory_context = ""
    if user_message_for_db:
        relevant_chunks = await vector_store.search_relevant_chunks(active_dialog_id, user_message_for_db, n_results=3)
        if relevant_chunks:
            context_header = "ВАЖНО: Сначала ищи ответ в предоставленном ниже контексте из долговременной памяти. Используй интернет-поиск только если в этом контексте нет ответа. Контекст из памяти:\n---"
            formatted_chunks = "\n".join(f"- {chunk}" for chunk in relevant_chunks)
            long_term_memory_context = f"{context_header}\n{formatted_chunks}\n---\n"

    # --- 4. Сборка финального запроса к API ---
    request_contents = list(history)
    payload = {
        "generationConfig": GENERATION_CONFIG,
        "safetySettings": SAFETY_SETTINGS
    }

    if use_system_instruction:
        # Для Gemini Pro/Flash: контекст идет в system_instruction
        static_system_instruction = await _get_system_instruction_text(user_id, fernet_instance) or ""
        final_system_instruction = f"{long_term_memory_context}{static_system_instruction}".strip()
        if final_system_instruction:
            payload["system_instruction"] = { "parts": [{"text": final_system_instruction}] }
        request_contents.append({"role": "user", "parts": user_parts})
    else:
        # Для Gemma: контекст внедряется прямо в промпт пользователя
        if long_term_memory_context:
            user_parts.insert(0, {"text": long_term_memory_context})
        request_contents.append({"role": "user", "parts": user_parts})

    payload["contents"] = request_contents

    if use_search:
        payload.update(GOOGLE_SEARCH_TOOL)
    
    # Сохраняем сообщение пользователя в краткосрочную БД
    await db_manager.store_message(user_id, active_dialog_id, 'user', user_message_for_db, fernet_instance)
    
    url = f"{GEMINI_API_BASE_URL}/models/{model_name}:generateContent"
    
    try:
        response_json = await _make_gemini_request_async(api_key, url, payload)
        # ... остальная часть try-блока (обработка ответа) остается без изменений ...
        gemini_logger.debug(f"Сырой ответ от Gemini API для user_id {user_id}:\n{json.dumps(response_json, indent=2, ensure_ascii=False)}")
        if not response_json or "candidates" not in response_json:
            raise GeminiAPIError("Ответ API не содержит 'candidates'.", details=response_json)
        first_candidate = response_json["candidates"][0]
        if first_candidate.get("finishReason") == "SAFETY":
             raise GeminiAPIError("Ответ заблокирован настройками безопасности.", details={"finish_reason": "SAFETY"})
        response_text = "".join(part.get("text", "") for part in first_candidate["content"]["parts"]).strip()  
        sources = []
        metadata = first_candidate.get('groundingMetadata', {})
        if 'groundingAttributions' in metadata:
            for attr in metadata['groundingAttributions']:
                if 'web' in attr and attr['web'].get('uri') and attr['web'].get('title'):
                    sources.append({"uri": attr['web']['uri'], "title": attr['web']['title']})
        elif 'groundingChunks' in metadata:
            for chunk in metadata['groundingChunks']:
                if 'web' in chunk and chunk['web'].get('uri') and chunk['web'].get('title'):
                    source_item = {"uri": chunk['web']['uri'], "title": chunk['web']['title']}
                    if source_item not in sources:
                        sources.append(source_item)
        
        # --- ВОЗВРАЩАЕМ УСЛОВНОЕ ОБНОВЛЕНИЕ КЭША ---
        if not is_gemma_model:
            history.append({"role": "user", "parts": user_parts})
            history.append({"role": "model", "parts": [{"text": response_text}]})

        usage_metadata = response_json.get('usageMetadata', {})
        prompt_tokens = usage_metadata.get('promptTokenCount', 0)
        completion_tokens = usage_metadata.get('candidatesTokenCount', 0)
        total_tokens = usage_metadata.get('totalTokenCount', 0)

        await db_manager.store_message(
            user_id=user_id, dialog_id=active_dialog_id, role='bot',
            message_text=response_text, fernet_instance=fernet_instance,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens, total_tokens=total_tokens
        )
        
        # --- Сохранение в долговременную память (фоновое) ---
        if user_message_for_db and response_text:
            text_to_memorize = f"Вопрос пользователя: {user_message_for_db}\nОтвет ассистента: {response_text}"
            asyncio.create_task(
                vector_store.add_dialog_text(active_dialog_id, text_to_memorize)
            )

        return response_text, sources

    except GeminiAPIError:
        # --- ВОЗВРАЩАЕМ УСЛОВНОЕ УДАЛЕНИЕ ИЗ КЭША ---
        if history and not is_gemma_model: 
            history.pop()
        raise

async def generate_content_simple(api_key: str, prompt: str) -> str:
    """Генерирует ответ от Gemini без истории. Выбрасывает GeminiAPIError."""
    url = f"{GEMINI_API_BASE_URL}/models/{DEFAULT_MODEL_ID}:generateContent"
    payload = {"contents": [{"role": "user", "parts": [{"text": prompt}]}]}
    response_json = await _make_gemini_request_async(api_key, url, payload, 'POST')
    try:
        return response_json["candidates"][0]["content"]["parts"][0]["text"].strip()
    except (KeyError, IndexError) as e:
        raise GeminiAPIError(f"Ошибка чтения ответа от API: {e}", details={"error": {"message": "parsing_error"}})

async def validate_api_key(api_key: str) -> bool:
    """Проверяет валидность API-ключа."""
    url = f"{GEMINI_API_BASE_URL}/models/{DEFAULT_MODEL_ID}:countTokens"
    payload = {"contents": [{"parts": [{"text": "hello"}]}]}
    try:
        response = await _make_gemini_request_async(api_key, url, payload, 'POST')
        return response is not None and "totalTokens" in response
    except GeminiAPIError:
        return False

async def get_available_models(api_key: str) -> List[Dict[str, str]]:
    """Получает список доступных моделей Gemini с API. Выбрасывает GeminiAPIError."""
    url = f"{GEMINI_API_BASE_URL}/models"
    response_json = await _make_gemini_request_async(api_key, url, method='GET')
    available_models = []
    if not response_json or 'models' not in response_json:
        return []

    for model in response_json['models']:
        model_name = model.get('name', '').replace('models/', '')
        if 'generateContent' in model.get('supportedGenerationMethods', []) and \
           'embedding' not in model_name and 'aqa' not in model_name and 'text-embedding' not in model_name:
            available_models.append({
                "name": model_name,
                "display_name": model.get('displayName', model_name)
            })

    available_models.sort(key=lambda x: ('flash' not in x['name'], 'pro' not in x['name'], x['name']))
    return available_models