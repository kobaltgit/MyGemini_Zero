# File: MyGemini_Zero/features/profile_manager.py

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

"""
Модуль для управления профилем пользователя (анкета-знакомство).
Отвечает за последовательное задавание вопросов и сбор ответов.
"""
from telebot.async_telebot import AsyncTeleBot
from telebot import types

from config import settings
from utils import localization as loc
from utils import markup_helpers as mk
from database import db_manager
from logger_config import get_logger

logger = get_logger(__name__)

 # --- ИСПРАВЛЕННАЯ СТРУКТУРА АНКЕТЫ ---
FIRST_QUESTION = 'role'

QUESTIONNAIRE = {
    'role':     {'type': 'text',   'next': 'industry'},
    'industry': {'type': 'text',   'next': 'projects'},
    'projects': {'type': 'text',   'next': 'stack'},
    'stack':    {'type': 'text',   'next': 'purpose'},
    'purpose':  {'type': 'choice', 'next': 'style'},
    'style':    {'type': 'choice', 'next': 'hobby'},
    'hobby':    {'type': 'text',   'next': 'rules'},
    'rules':    {'type': 'text',   'next': None}, # Последний вопрос
}
# --- КОНЕЦ ИСПРАВЛЕНИЯ ---


def _create_choice_keyboard(question_key: str, lang_code: str) -> types.InlineKeyboardMarkup:
    """Создает клавиатуру для вопросов с выбором ответа."""
    markup = types.InlineKeyboardMarkup(row_width=2)
    buttons = []
    if question_key == 'purpose':
        choices = {
            'work': loc.get_text('profile_btn_purpose_work', lang_code),
            'learn': loc.get_text('profile_btn_purpose_learn', lang_code),
            'creative': loc.get_text('profile_btn_purpose_creative', lang_code),
            'organize': loc.get_text('profile_btn_purpose_organize', lang_code),
        }
    elif question_key == 'style':
        choices = {
            'friendly': loc.get_text('profile_btn_style_friendly', lang_code),
            'formal': loc.get_text('profile_btn_style_formal', lang_code),
            'concise': loc.get_text('profile_btn_style_concise', lang_code),
            'detailed': loc.get_text('profile_btn_style_detailed', lang_code),
        }
    else:
        return None

    for key, text in choices.items():
        callback_data = f"{settings.CALLBACK_PROFILE_CHOICE}{question_key}:{key}"
        buttons.append(types.InlineKeyboardButton(text, callback_data=callback_data))

    # Располагаем кнопки по две в ряд
    for i in range(0, len(buttons), 2):
        markup.add(*buttons[i:i+2])
        
    return markup


async def ask_question(bot: AsyncTeleBot, user_id: int, question_key: str):
    """Отправляет пользователю вопрос из анкеты.

    Определяет текст вопроса и тип (текстовый или с выбором),
    создает соответствующую клавиатуру и отправляет сообщение.

    Args:
        bot: Экземпляр AsyncTeleBot.
        user_id: ID пользователя, которому задается вопрос.
        question_key: Ключ вопроса из словаря QUESTIONNAIRE (например, 'role').
    """
    lang_code = await db_manager.get_user_language(user_id)
    question_text = loc.get_text(f'profile_q_{question_key}', lang_code)
    question_info = QUESTIONNAIRE.get(question_key) or QUESTIONNAIRE.get(FIRST_QUESTION)

    markup = None
    if question_info.get('type') == 'choice':
        markup = _create_choice_keyboard(question_key, lang_code)

    await bot.send_message(user_id, question_text, reply_markup=markup)


async def start_questionnaire(bot: AsyncTeleBot, message: types.Message):
    """Начинает процесс заполнения анкеты для пользователя.

    Вызывается после успешной установки мастер-пароля. Устанавливает
    начальное состояние, инициализирует хранилище для ответов и задает
    первый вопрос анкеты.

    Args:
        bot: Экземпляр AsyncTeleBot.
        message: Объект сообщения Telegram, инициировавший команду.
    """
    user_id = message.from_user.id
    lang_code = await db_manager.get_user_language(user_id)

    # Устанавливаем состояние и сохраняем, что мы в процессе заполнения анкеты
    await bot.set_state(user_id, settings.STATE_PROFILE_WAITING_FOR_ANSWER, message.chat.id)
    
    # Сохраняем пустой профиль и текущий вопрос
    first_question_key = FIRST_QUESTION
    await bot.add_data(user_id, message.chat.id,
                       current_profile={},
                       current_question=first_question_key)
    
    await bot.send_message(user_id, loc.get_text('profile_start', lang_code))
    await ask_question(bot, user_id, first_question_key)