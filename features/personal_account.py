# File: features/personal_account.py
from datetime import datetime
from typing import Optional, List, Dict, Any
from cryptography.fernet import Fernet

from database import db_manager
from config.settings import BOT_PERSONAS
from utils.analysis_helpers import extract_frequent_topics
from services.gemini_service import generate_content_simple
from logger_config import get_logger

logger = get_logger(__name__, user_id='System')

USER_TITLES: Dict[int, str] = {
    0: "Новичок / Newcomer", 100: "Активный пользователь / Active User", 500: "Ветеран чата / Chat Veteran",
    1000: "Мастер общения / Master of Conversation", 5000: "Легенда / Legend",
}

def _get_user_title(message_count: int) -> str:
    title: str = USER_TITLES[0]
    for messages, current_title in sorted(USER_TITLES.items(), reverse=True):
        if message_count >= messages:
            title = current_title
            break
    return title

def _get_days_since_start(first_interaction_date_str: Optional[str]) -> str:
    if not first_interaction_date_str:
        return "Неизвестно / Unknown"
    try:
        first_interaction_date = datetime.strptime(first_interaction_date_str, '%Y-%m-%d').date()
        days: int = (datetime.now().date() - first_interaction_date).days
        return str(max(0, days))
    except ValueError:
        return "Ошибка / Error"

async def _get_topic_description(user_id: int, api_key: str, active_dialog_id: int, fernet_instance: Fernet) -> str:
    try:
        conversation_history_raw = await db_manager.get_conversation_history(active_dialog_id, fernet_instance, limit=50)
        if not conversation_history_raw:
             return "Пока недостаточно данных для анализа в этом диалоге."

        frequent_topics = extract_frequent_topics(conversation_history_raw, top_n=7)
        if not frequent_topics:
            return "Пока недостаточно данных для анализа в этом диалоге."

        topics_str = ', '.join(frequent_topics)
        prompt = f"""Analyze the following keywords from a user's conversation with a chatbot: {topics_str}.
Briefly (in 1-2 sentences in Russian) describe the main topics the user discusses. Make the description generalized and positive.
Start the response with 'Чаще всего в этом диалоге вы обсуждаете' or a similar phrase."""

        ai_description = await generate_content_simple(api_key, prompt)
        return ai_description.strip() if ai_description else f"Ключевые слова: {topics_str}"

    except Exception as e:
        logger.exception(f"Ошибка при получении описания тем для user_id {user_id}: {e}", extra={'user_id': str(user_id)})
        return "Не удалось определить темы (ошибка)."

async def get_personal_account_info(user_id: int, fernet_instance: Optional[Fernet]) -> str:
    """Собирает и форматирует информацию для личного кабинета пользователя."""
    user_lang = await db_manager.get_user_language(user_id)
    persona_id = await db_manager.get_user_persona(user_id)
    first_interaction_date_str = await db_manager.get_first_interaction_date(user_id)
    active_dialog_id = await db_manager.get_active_dialog_id(user_id)
    conversation_count = await db_manager.get_total_user_message_count(user_id)

    title: str = _get_user_title(conversation_count)
    days_active: str = _get_days_since_start(first_interaction_date_str)

    persona_info = BOT_PERSONAS.get(persona_id, BOT_PERSONAS['default'])
    persona_name = persona_info.get(f"name_{user_lang}", persona_info['name_ru'])

    # Для отображения статуса используем проверку без расшифровки
    api_key_is_set = await db_manager.is_api_key_set(user_id)
    api_key_status = "✅ Установлен / Set" if api_key_is_set else "❌ Не установлен / Not Set"

    topics_description = "Для анализа тем разблокируйте сессию."
    if fernet_instance and active_dialog_id and api_key_is_set:
        # А для самого анализа расшифровываем ключ и историю
        decrypted_api_key = await db_manager.get_user_api_key(user_id, fernet_instance)
        if decrypted_api_key:
            topics_description = await _get_topic_description(user_id, decrypted_api_key, active_dialog_id, fernet_instance)
        else:
            topics_description = "Ошибка расшифровки API-ключа."
    elif not api_key_is_set:
        topics_description = "Для анализа нужен API ключ."

    info_text = f"""
👤 **Личный кабинет / My Account** 👤

🏆 **Звание / Title:** {title}
💬 **Всего сообщений (все диалоги):** {conversation_count}
🗓️ **Вы с нами (дней):** {days_active}

--- **Настройки / Settings** ---
🎭 **Текущая персона / Persona:** {persona_name}
🌐 **Язык / Language:** {"Русский" if user_lang == 'ru' else "English"}
🔑 **API Ключ / API Key:** {api_key_status}

--- **Анализ текущего диалога** ---
🗣️ {topics_description}
"""
    return "\n".join(line.strip() for line in info_text.strip().splitlines())