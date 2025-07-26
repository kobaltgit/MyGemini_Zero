# File: features/personal_account.py

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

from datetime import datetime
from typing import Optional, Dict
from cryptography.fernet import Fernet

from database import db_manager
from config.settings import BOT_PERSONAS
from utils.analysis_helpers import extract_frequent_topics
from services.gemini_service import generate_content_simple
from logger_config import get_logger
from features.profile_manager import QUESTIONNAIRE
from utils import localization as loc

logger = get_logger(__name__, user_id='System')

USER_TITLES: Dict[int, str] = {
    0: "Новичок / Newcomer", 100: "Активный пользователь / Active User", 500: "Ветеран чата / Chat Veteran",
    1000: "Мастер общения / Master of Conversation", 5000: "Легенда / Legend",
}

def _get_user_title(message_count: int) -> str:
    """Определяет звание пользователя по количеству сообщений."""
    if message_count is None:
        return USER_TITLES[0]
    title: str = USER_TITLES[0]
    for messages, current_title in sorted(USER_TITLES.items(), reverse=True):
        if message_count >= messages:
            title = current_title
            break
    return title

def _get_days_since_start(first_interaction_date_str: Optional[str]) -> str:
    """Вычисляет количество дней с момента регистрации."""
    if not first_interaction_date_str:
        return "Неизвестно / Unknown"
    try:
        first_interaction_date = datetime.strptime(first_interaction_date_str, '%Y-%m-%d').date()
        days: int = (datetime.now().date() - first_interaction_date).days
        return str(max(0, days))
    except ValueError:
        return "Ошибка / Error"

async def _get_topic_description(user_id: int, api_key: str, active_dialog_id: int, fernet_instance: Fernet) -> str:
    """Анализирует историю и генерирует описание тем диалога."""
    try:
        conversation_history_raw = await db_manager.get_conversation_history(active_dialog_id, fernet_instance, limit=50)
        if not conversation_history_raw:
             return "Пока недостаточно данных для анализа в этом диалоге."

        frequent_topics = extract_frequent_topics(conversation_history_raw, top_n=7)
        if not frequent_topics:
            return "Пока недостаточно данных для анализа в этом диалоге."

        topics_str = ', '.join(frequent_topics)
        prompt = f"""Analyze the following keywords from a user's conversation: {topics_str}.
Briefly (in 1-2 Russian sentences) describe the main topics. Make it generalized and positive.
Start with 'Чаще всего в этом диалоге вы обсуждаете' or similar."""

        ai_description = await generate_content_simple(api_key, prompt)
        return ai_description.strip() if ai_description else f"Ключевые слова: {topics_str}"

    except Exception as e:
        logger.exception(f"Ошибка при получении описания тем для user_id {user_id}: {e}", extra={'user_id': str(user_id)})
        return "Не удалось определить темы (ошибка)."

async def get_personal_account_info(user_id: int, fernet_instance: Fernet) -> str:
    """
    Собирает и форматирует ОБЪЕДИНЕННУЮ информацию для личного кабинета,
    включая статистику, настройки, анализ тем и данные анкеты.
    """
    lang_code = await db_manager.get_user_language(user_id)
    
    # --- Блок 1: Статистика Активности ---
    conversation_count = await db_manager.get_total_user_message_count(user_id)
    first_interaction_date_str = await db_manager.get_first_interaction_date(user_id)
    title: str = _get_user_title(conversation_count)
    days_active: str = _get_days_since_start(first_interaction_date_str)
    
    stats_lines = [
        f"🏆 **Звание / Title:** {title}",
        f"💬 **Всего сообщений:** {conversation_count}",
        f"🗓️ **Вы с нами (дней):** {days_active}",
    ]
    
    # --- Блок 2: Текущие Настройки ---
    persona_id = await db_manager.get_user_persona(user_id)
    persona_info = BOT_PERSONAS.get(persona_id, BOT_PERSONAS['default'])
    persona_name = persona_info.get(f"name_{lang_code}", persona_info['name_ru'])
    api_key_is_set = await db_manager.is_api_key_set(user_id)
    api_key_status = "✅ Установлен / Set" if api_key_is_set else "❌ Не установлен / Not Set"
    
    settings_lines = [
        f"🎭 **Текущая персона / Persona:** {persona_name}",
        f"🌐 **Язык / Language:** {'Русский' if lang_code == 'ru' else 'English'}",
        f"🔑 **API Ключ / API Key:** {api_key_status}",
    ]
    
    # --- Блок 3: Данные анкеты (профиля) ---
    profile_data = await db_manager.get_user_profile(user_id, fernet_instance)
    profile_lines = [f"*Профиль еще не заполнен.*"]
    if profile_data:
        profile_lines = []
        for key in QUESTIONNAIRE.keys():
            field_name = loc.get_text(f'profile_label_{key}', lang_code)
            answer = profile_data.get(key, "_- не указано -_")
            profile_lines.append(f"**{field_name}:** {answer}")
    
    # --- Блок 4: Анализ диалога ---
    active_dialog_id = await db_manager.get_active_dialog_id(user_id)
    topics_description = "Для анализа тем разблокируйте сессию и установите API-ключ."
    if active_dialog_id and api_key_is_set:
        decrypted_api_key = await db_manager.get_user_api_key(user_id, fernet_instance)
        if decrypted_api_key:
            topics_description = await _get_topic_description(user_id, decrypted_api_key, active_dialog_id, fernet_instance)
        else:
            topics_description = "Ошибка расшифровки API-ключа."
            
    # --- Финальная Сборка ---
    all_blocks = [
        f"**{loc.get_text('profile_stats_header', lang_code)}**",
        *stats_lines,
        "",
        f"**--- Настройки / Settings ---**",
        *settings_lines,
        "",
        f"**{loc.get_text('profile_answers_header', lang_code)}**",
        *profile_lines,
        "",
        f"**--- Анализ текущего диалога ---**",
        f"🗣️ {topics_description}"
    ]
    
    return "\n".join(all_blocks)