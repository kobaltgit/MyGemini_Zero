# File: MyGemini_Zero/handlers/message_handlers.py

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
Центральный модуль для обработки сообщений от пользователя.
Здесь реализована явная маршрутизация на основе состояний.
(ZK Edition - Corrected)
"""
import datetime
import PIL.Image
from io import BytesIO
from typing import List, Union
from telebot.async_telebot import AsyncTeleBot
from telebot import types
import telegramify_markdown

from . import telegram_helpers as tg_helpers
from utils import markup_helpers as mk
from utils import localization as loc
from utils import text_helpers as th
from utils import crypto_helpers
from config import settings
from config.settings import (
   STATE_WAITING_FOR_TRANSLATE_TEXT, STATE_WAITING_FOR_API_KEY,
    STATE_WAITING_FOR_NEW_DIALOG_NAME, STATE_WAITING_FOR_RENAME_DIALOG,
    STATE_WAITING_FOR_FEEDBACK, DEFAULT_MODEL_ID, BOT_PERSONAS, ADMIN_USER_ID,
    STATE_ADMIN_WAITING_FOR_BROADCAST_MSG, STATE_ADMIN_WAITING_FOR_USER_ID_TO_MANAGE,
    STATE_ADMIN_WAITING_FOR_USER_ID_TO_REPLY, STATE_ADMIN_WAITING_FOR_REPLY_MESSAGE
)
from database import db_manager
from services import gemini_service
from services.gemini_service import GeminiAPIError
from services.vector_store_manager import VectorStoreManager
from features import profile_manager
from features.profile_manager import QUESTIONNAIRE, ask_question
from .decorators import admin_required
from .admin_handlers import handle_admin_command

from logger_config import get_logger

logger = get_logger(__name__)
user_logger = get_logger('user_messages')

# --- СПИСОК ВСЕХ КНОПОК ДЛЯ ИСКЛЮЧЕНИЯ ИЗ УНИВЕРСАЛЬНОГО ОБРАБОТЧИКА ---
# Собираем тексты всех кнопок на всех языках, чтобы роутер их игнорировал
BUTTON_KEYS = [
    'btn_dialogs', 'btn_account', 'btn_usage', 'btn_settings',
    'btn_translate', 'btn_history', 'btn_help', 'btn_reset', 'btn_admin_panel'
]
ALL_BUTTON_TEXTS = {
    text
    for lang in ['ru', 'en']
    for key in BUTTON_KEYS
    if (text := loc.get_text(key, lang)) != key
}

# ===================================================================================
# --- ВНУТРЕННИЕ ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ (ОРИГИНАЛ) ---
# ===================================================================================

async def _check_access(bot: AsyncTeleBot, user_id: int, lang_code: str) -> bool:
    """
    Проверяет, имеет ли пользователь доступ к боту (не заблокирован и не включен режим обслуживания).

    Args:
        bot (AsyncTeleBot): Экземпляр асинхронного Telegram-бота.
        user_id (int): ID пользователя для проверки.
        lang_code (str): Языковой код пользователя для локализации сообщений.

    Returns:
        bool: True, если пользователь имеет доступ, False в противном случае.
    """
    if await db_manager.is_user_blocked(user_id):
        await bot.send_message(user_id, loc.get_text('user_is_blocked', lang_code))
        return False

    maintenance_mode_str = await db_manager.get_app_setting('maintenance_mode')
    if maintenance_mode_str == 'true' and user_id != ADMIN_USER_ID:
        await bot.send_message(user_id, loc.get_text('maintenance_mode_on', lang_code))
        return False
    return True

async def _create_context_header(user_id: int, lang_code: str) -> str:
    """
    Формирует заголовок контекста для сообщения бота, включающий
    название активного диалога, активную персону и выбранную модель Gemini.

    Args:
        user_id (int): ID пользователя.
        lang_code (str): Языковой код пользователя для локализации имен персон.

    Returns:
        str: Отформатированная строка заголовка контекста.
    """
    context_info = await db_manager.get_user_context_info(user_id)
    if not context_info:
        return ""
    dialog_name = context_info.get('dialog_name', '..._')
    persona_id = context_info.get('active_persona', 'default')
    model_name = context_info.get('gemini_model') or DEFAULT_MODEL_ID
    persona_info = BOT_PERSONAS.get(persona_id, BOT_PERSONAS['default'])
    persona_name = persona_info.get(f"name_{lang_code}", persona_info.get('name_ru', '...'))
    header = (
        f"•  **Диалог:** `{dialog_name}`\n"
        f"•  **Персона:** `{persona_name}`\n"
        f"•  **Модель:** `{model_name}`\n"
        f"---"
    )
    return header

# ===================================================================================
# --- ОБРАБОТЧИКИ СОСТОЯНИЙ (STATE) ---
# ===================================================================================

# --- НОВЫЕ ОБРАБОТЧИКИ СОСТОЯНИЙ ДЛЯ ZERO-KNOWLEDGE ---
async def _handle_state_password_setup(message: types.Message, bot: AsyncTeleBot):
    """
    Обрабатывает ввод первого мастер-пароля при первичной настройке Zero-Knowledge.

    Сохраняет введенный пароль во временное хранилище состояния и переводит
    пользователя в состояние ожидания подтверждения пароля.

    Args:
        message (types.Message): Объект сообщения Telegram, содержащий введенный пароль.
        bot (AsyncTeleBot): Экземпляр асинхронного Telegram-бота.
    """
    user_id = message.from_user.id
    password = message.text.strip()
    await bot.add_data(user_id, message.chat.id, password_one=password)
    await bot.set_state(user_id, settings.STATE_ZK_WAITING_FOR_PASSWORD_CONFIRM, message.chat.id)
    lang_code = await db_manager.get_user_language(user_id)
    await bot.send_message(user_id, loc.get_text('zk_warning', lang_code))


async def _handle_state_password_confirm(message: types.Message, bot: AsyncTeleBot):
    """
    Обрабатывает подтверждение мастер-пароля.

    Сравнивает введенный пароль с ранее сохраненным. Если пароли совпадают,
    генерирует соль, хеширует пароль, сохраняет их в БД, создает экземпляр Fernet
    для сессии пользователя и запускает процесс заполнения анкеты профиля.
    В случае несовпадения паролей, просит пользователя начать процесс сначала.

    Args:
        message (types.Message): Объект сообщения Telegram, содержащий подтверждающий пароль.
        bot (AsyncTeleBot): Экземпляр асинхронного Telegram-бота.
    """
    user_id = message.from_user.id
    lang_code = await db_manager.get_user_language(user_id)
    password_two = message.text.strip()

    async with bot.retrieve_data(user_id, message.chat.id) as data:
        password_one = data.get('password_one')

    if password_one == password_two:
        # 1. Сохраняем хеш и соль в БД
        await db_manager.set_master_password(user_id, password_one)

        # 2. Создаем и сохраняем живую сессию (ключ шифрования)
        salt = await db_manager.get_user_salt(user_id)
        if salt:
            fernet_instance = crypto_helpers.get_fernet_instance(password_one, salt)
            tg_helpers.user_session_keys[user_id] = fernet_instance
            logger.info(f"Сессия для нового пользователя {user_id} создана и разблокирована после установки пароля.")
        else:
            logger.error(f"Критическая ошибка: не удалось получить соль для user_id {user_id} сразу после установки пароля.")
            await bot.send_message(user_id, "Произошла критическая ошибка. Свяжитесь с администратором.")
            return

        # 3. Удаляем состояние и начинаем анкету
        await bot.delete_state(user_id, message.chat.id)
        await bot.send_message(user_id, loc.get_text('zk_setup_success', lang_code))
        await profile_manager.start_questionnaire(bot, message)
    else:
        # Если пароли не совпали, начинаем процесс заново
        await bot.set_state(user_id, settings.STATE_ZK_WAITING_FOR_PASSWORD_SETUP, message.chat.id)
        await bot.send_message(user_id, loc.get_text('zk_password_mismatch', lang_code))
        await bot.send_message(user_id, loc.get_text('zk_setup_prompt', lang_code))


async def _handle_state_password_unlock(message: types.Message, bot: AsyncTeleBot):
    """
    Обрабатывает ввод мастер-пароля для разблокировки сессии пользователя.

    Проверяет введенный пароль. В случае успеха, извлекает соль из БД,
    создает и сохраняет экземпляр Fernet для текущей сессии пользователя,
    обновляет время последней активности и сбрасывает состояние.
    В случае неверного пароля, информирует пользователя.

    Args:
        message (types.Message): Объект сообщения Telegram, содержащий пароль для разблокировки.
        bot (AsyncTeleBot): Экземпляр асинхронного Telegram-бота.
    """
    user_id = message.from_user.id
    lang_code = await db_manager.get_user_language(user_id)
    password = message.text.strip()
    if await db_manager.verify_master_password(user_id, password):
        salt = await db_manager.get_user_salt(user_id)
        fernet_instance = crypto_helpers.get_fernet_instance(password, salt)
        tg_helpers.user_session_keys[user_id] = fernet_instance
        await db_manager.update_last_session_time(user_id)
        await bot.delete_state(user_id, message.chat.id)
        main_keyboard = mk.create_main_keyboard(lang_code, user_id)
        await bot.send_message(user_id, loc.get_text('zk_unlock_success', lang_code), reply_markup=main_keyboard)
    else:
        await bot.send_message(user_id, loc.get_text('zk_unlock_fail', lang_code))

async def _handle_state_profile_answer(message: types.Message, bot: AsyncTeleBot):
    """
    Обрабатывает текстовые ответы пользователя во время заполнения анкеты профиля.

    Сохраняет ответ в словарь `current_profile` в состоянии пользователя.
    Определяет следующий вопрос и задает его, или завершает анкету,
    сохраняя профиль в зашифрованном виде в БД.

    Args:
        message (types.Message): Объект сообщения Telegram, содержащий ответ пользователя.
        bot (AsyncTeleBot): Экземпляр асинхронного Telegram-бота.
    """
    user_id = message.from_user.id
    answer = message.text.strip()
    if answer.lower() == '/skip' or answer == '-':
        answer = "Пропущено"
    async with bot.retrieve_data(user_id, message.chat.id) as data:
        current_profile = data.get('current_profile', {})
        current_question_key = data.get('current_question')
        if not current_question_key:
            await bot.delete_state(user_id, message.chat.id)
            return
        # Сохраняем ответ
        current_profile[current_question_key] = answer
        
        # Определяем следующий вопрос
        next_question_key = QUESTIONNAIRE.get(current_question_key, {}).get('next')
        if next_question_key:
            # Обновляем состояние, чтобы бот знал, какой вопрос следующий
            data['current_question'] = next_question_key
            # Задаем следующий вопрос
            await ask_question(bot, user_id, next_question_key)
        else:
            # Анкета завершена
            lang_code = await db_manager.get_user_language(user_id)
            fernet_instance = tg_helpers.user_session_keys.get(user_id)
            if fernet_instance:
                await db_manager.save_user_profile(user_id, current_profile, fernet_instance)
            else:
                logger.error(f"Не найдена сессия для сохранения профиля пользователя {user_id}")
          
            logger.info(f"Анкета для пользователя {user_id} завершена. Профиль: {current_profile}")
            await bot.delete_state(user_id, message.chat.id)
            await bot.send_message(user_id, loc.get_text('profile_end', lang_code))

# --- ОРИГИНАЛЬНЫЕ ОБРАБОТЧИКИ СОСТОЯНИЙ (с минимальными адаптациями) ---

@admin_required
async def _handle_state_admin_broadcast(message: types.Message, bot: AsyncTeleBot):
    """
    Обрабатывает ввод сообщения для рассылки всем пользователям.

    Сохраняет текст сообщения в состояние администратора и запрашивает
    подтверждение перед отправкой рассылки.

    Args:
        message (types.Message): Объект сообщения Telegram, содержащий текст для рассылки.
        bot (AsyncTeleBot): Экземпляр асинхронного Telegram-бота.
    """
    user_id = message.from_user.id
    lang_code = await db_manager.get_user_language(user_id)
    await bot.add_data(user_id, user_id, broadcast_message=message.text)
    all_users_count = len(await db_manager.get_all_user_ids())
    confirmation_text = loc.get_text('admin.broadcast_confirm_prompt', lang_code).format(
        count=all_users_count, message_text=message.text
    )
    confirm_keyboard = mk.create_broadcast_confirmation_keyboard(lang_code)
    await bot.send_message(user_id, confirmation_text, reply_markup=confirm_keyboard)

@admin_required
async def _handle_state_admin_user_id_manage(message: types.Message, bot: AsyncTeleBot):
    """
    Обрабатывает ввод User ID для управления пользователем в админ-панели.

    После получения User ID, сбрасывает состояние администратора и отображает
    информацию о пользователе вместе с клавиатурой для управления им (блокировка,
    сброс API ключа).

    Args:
        message (types.Message): Объект сообщения Telegram, содержащий User ID.
        bot (AsyncTeleBot): Экземпляр асинхронного Telegram-бота.
    """
    admin_id = message.from_user.id
    lang_code = await db_manager.get_user_language(admin_id)
    if not message.text.isdigit():
        await bot.reply_to(message, "Ошибка: User ID должен быть числом.")
        return
    user_id_to_manage = int(message.text)
    await bot.delete_state(admin_id, admin_id)
    user_info_text = await tg_helpers.get_user_info_text(user_id_to_manage, lang_code)
    user_info = await db_manager.get_user_info_for_admin(user_id_to_manage)
    keyboard = mk.create_user_management_keyboard(user_id_to_manage, user_info['is_blocked'], lang_code) if user_info else None
    await bot.send_message(admin_id, user_info_text, reply_markup=keyboard, parse_mode="MarkdownV2")

@admin_required
async def _handle_state_user_id_for_reply(message: types.Message, bot: AsyncTeleBot):
    """
    Обрабатывает ввод User ID пользователя, которому администратор хочет ответить.

    Проверяет существование пользователя. Если пользователь найден, сохраняет
    его ID во временное хранилище состояния и переводит администратора в
    состояние ожидания сообщения для отправки.

    Args:
        message (types.Message): Объект сообщения Telegram, содержащий User ID.
        bot (AsyncTeleBot): Экземпляр асинхронного Telegram-бота.
    """
    admin_id = message.from_user.id
    lang_code = await db_manager.get_user_language(admin_id)
    if not message.text.isdigit():
        await bot.reply_to(message, "Ошибка: User ID должен быть числом.")
        return
    target_user_id = int(message.text)
    if not await db_manager.get_user_info_for_admin(target_user_id):
        await bot.reply_to(message, loc.get_text('admin.user_not_found', lang_code).format(user_id=target_user_id))
        await bot.delete_state(admin_id, admin_id)
        return
    await bot.add_data(admin_id, admin_id, target_user_id=target_user_id)
    await bot.set_state(admin_id, STATE_ADMIN_WAITING_FOR_REPLY_MESSAGE, admin_id)
    await bot.send_message(admin_id, loc.get_text('admin.reply_prompt_message', lang_code).format(user_id=target_user_id))

@admin_required
async def _handle_state_message_to_user(message: types.Message, bot: AsyncTeleBot):
    """
    Обрабатывает ввод сообщения от администратора для конкретного пользователя.

    Извлекает User ID из состояния и отправляет введенное сообщение целевому
    пользователю, после чего сбрасывает состояние администратора.

    Args:
        message (types.Message): Объект сообщения Telegram, содержащий текст для пользователя.
        bot (AsyncTeleBot): Экземпляр асинхронного Telegram-бота.
    """
    admin_id = message.from_user.id
    lang_code = await db_manager.get_user_language(admin_id)
    text_to_send = message.text
    async with bot.retrieve_data(admin_id, admin_id) as data:
        target_user_id = data.get('target_user_id')
    if not target_user_id:
        await bot.delete_state(admin_id, admin_id)
        return
    target_lang_code = await db_manager.get_user_language(target_user_id)
    notification_text = loc.get_text('admin.reply_admin_notification', target_lang_code).format(text=text_to_send)
    try:
        await bot.send_message(target_user_id, telegramify_markdown.markdownify(notification_text), parse_mode='MarkdownV2')
        await bot.send_message(admin_id, loc.get_text('admin.reply_sent_success', lang_code).format(user_id=target_user_id))
    except Exception as e:
        await bot.send_message(admin_id, loc.get_text('admin.reply_sent_fail', lang_code))
    finally:
        await bot.delete_state(admin_id, admin_id)

async def _handle_state_api_key(message: types.Message, bot: AsyncTeleBot):
    """
    Обрабатывает ввод Google AI API ключа от пользователя.

    Проверяет валидность ключа через Gemini API. Если ключ действителен,
    шифрует его с помощью сессионного ключа Fernet и сохраняет в БД,
    затем сбрасывает состояние. В противном случае информирует пользователя
    о недействительности ключа.

    Args:
        message (types.Message): Объект сообщения Telegram, содержащий API ключ.
        bot (AsyncTeleBot): Экземпляр асинхронного Telegram-бота.
    """
    user_id = message.chat.id
    api_key_plain = message.text.strip()
    lang_code = await db_manager.get_user_language(user_id)
    
    fernet_instance = tg_helpers.user_session_keys.get(user_id)
    if not fernet_instance:
        await bot.reply_to(message, "Критическая ошибка: сессия не найдена для шифрования ключа.")
        return
    try:
        await bot.delete_message(message.chat.id, message.message_id)
    except Exception: pass
    status_msg = await bot.send_message(user_id, loc.get_text('api_key_verifying', lang_code))
    is_valid = await gemini_service.validate_api_key(api_key_plain)
    try:
        await bot.delete_message(user_id, status_msg.message_id)
    except Exception: pass
    if is_valid:
        await db_manager.set_user_api_key(user_id, api_key_plain, fernet_instance)
        await bot.delete_state(message.from_user.id, message.chat.id)
        await bot.send_message(user_id, loc.get_text('api_key_success', lang_code))
    else:
        await bot.send_message(user_id, loc.get_text('api_key_invalid', lang_code))

async def _handle_state_translate(message: types.Message, bot: AsyncTeleBot):
    """
    Обрабатывает ввод текста для перевода.

    Извлекает целевой язык из состояния, получает API ключ пользователя (расшифровывая его),
    вызывает Gemini API для перевода и отправляет результат пользователю.
    В случае ошибки или отсутствия API ключа, уведомляет пользователя.

    Args:
        message (types.Message): Объект сообщения Telegram, содержащий текст для перевода.
        bot (AsyncTeleBot): Экземпляр асинхронного Telegram-бота.
    """
    user_id = message.chat.id
    text_to_translate = message.text
    lang_code = await db_manager.get_user_language(user_id)
    
    fernet_instance = tg_helpers.user_session_keys.get(user_id)
    if not fernet_instance:
        await bot.reply_to(message, "Критическая ошибка: сессия не найдена.")
        return

    api_key = await db_manager.get_user_api_key(user_id, fernet_instance)
    if not api_key:
        await bot.reply_to(message, loc.get_text('api_key_needed_for_feature', lang_code))
        await bot.delete_state(user_id, message.chat.id)
        return

    async with bot.retrieve_data(user_id, message.chat.id) as data:
        target_lang_code = data.get('target_lang')
    if not target_lang_code:
        await bot.reply_to(message, loc.get_text('translation_error_generic', lang_code))
        await bot.delete_state(user_id, message.chat.id)
        return

    await tg_helpers.send_typing_action(bot, user_id)
    try:
        translated_text = await gemini_service.generate_content_simple(api_key, f"Translate to {target_lang_code}: '{text_to_translate}'")
        if translated_text:
            await bot.reply_to(message, translated_text)
    except GeminiAPIError as e:
        user_friendly_error = loc.get_text(e.error_key, lang_code)
        await bot.reply_to(message, user_friendly_error)
    finally:
        await bot.delete_state(user_id, message.chat.id)

async def _handle_state_new_dialog_name(message: types.Message, bot: AsyncTeleBot):
    """
    Обрабатывает ввод нового названия для диалога.

    Создает новый диалог с указанным названием, делает его активным
    для пользователя и сбрасывает состояние.

    Args:
        message (types.Message): Объект сообщения Telegram, содержащий новое имя диалога.
        bot (AsyncTeleBot): Экземпляр асинхронного Telegram-бота.
    """
    user_id = message.chat.id
    lang_code = await db_manager.get_user_language(user_id)
    dialog_name = message.text.strip()
    if not dialog_name or len(dialog_name) > 50:
        await bot.reply_to(message, loc.get_text('dialog_name_invalid' if not dialog_name else 'dialog_name_too_long', lang_code))
        return
    await db_manager.create_dialog(user_id, dialog_name, set_active=True)
    await bot.delete_state(user_id, message.chat.id)
    await bot.send_message(user_id, loc.get_text('dialog_created_success', lang_code).format(name=dialog_name))
    dialog_keyboard = await mk.create_dialogs_menu_keyboard(user_id)
    await bot.send_message(user_id, f"{loc.get_text('dialogs_menu_title', lang_code)}\n\n{loc.get_text('dialogs_menu_desc', lang_code)}", reply_markup=dialog_keyboard)

async def _handle_state_rename_dialog(message: types.Message, bot: AsyncTeleBot):
    """
    Обрабатывает ввод нового названия для переименовываемого диалога.

    Переименовывает диалог в базе данных и сбрасывает состояние.

    Args:
        message (types.Message): Объект сообщения Telegram, содержащий новое имя диалога.
        bot (AsyncTeleBot): Экземпляр асинхронного Telegram-бота.
    """
    user_id = message.chat.id
    lang_code = await db_manager.get_user_language(user_id)
    new_name = message.text.strip()
    if not new_name or len(new_name) > 50:
        await bot.reply_to(message, loc.get_text('dialog_name_invalid' if not new_name else 'dialog_name_too_long', lang_code))
        return
    async with bot.retrieve_data(user_id, message.chat.id) as data:
        dialog_id_to_rename = data.get('dialog_id_to_rename')
    if dialog_id_to_rename:
        await db_manager.rename_dialog(dialog_id_to_rename, new_name)
        await bot.delete_state(user_id, message.chat.id)
        await bot.send_message(user_id, loc.get_text('dialog_renamed_success', lang_code).format(new_name=new_name))
        dialog_keyboard = await mk.create_dialogs_menu_keyboard(user_id)
        await bot.send_message(user_id, f"{loc.get_text('dialogs_menu_title', lang_code)}\n\n{loc.get_text('dialogs_menu_desc', lang_code)}", reply_markup=dialog_keyboard)

async def _handle_state_feedback(message: types.Message, bot: AsyncTeleBot):
    """
    Обрабатывает сообщение обратной связи от пользователя.

    Сбрасывает состояние пользователя, отправляет ему подтверждение
    и пересылает сообщение администратору (если ADMIN_USER_ID задан).

    Args:
        message (types.Message): Объект сообщения Telegram, содержащий обратную связь.
        bot (AsyncTeleBot): Экземпляр асинхронного Telegram-бота.
    """
    user_id = message.chat.id
    lang_code = await db_manager.get_user_language(user_id)

    await bot.delete_state(user_id, message.chat.id)
    await bot.send_message(user_id, loc.get_text('feedback_sent', lang_code))

    if ADMIN_USER_ID:
        try:
            username = message.from_user.username or "N/A"
            first_name = message.from_user.first_name or "N/A"
            user_text = message.text

            admin_notification = loc.get_text('feedback_admin_notification', 'ru').format(
                user_id=user_id,
                username=username,
                first_name=first_name,
                text=f"```{user_text}```" # Оборачиваем в блок кода
            )
            await bot.send_message(ADMIN_USER_ID, telegramify_markdown.markdownify(admin_notification), parse_mode='MarkdownV2')
        except Exception as e:
            logger.error(f"Не удалось отправить уведомление о фидбэке администратору: {e}", extra={'user_id': 'System'})

async def _handle_state_document_memorize(message: types.Message, bot: AsyncTeleBot):
    """
    Обрабатывает загрузку файла (документа) для добавления в долговременную память.

    Проверяет тип и размер файла, скачивает его, извлекает текст
    и добавляет его в векторное хранилище, связанное с активным диалогом пользователя.
    В случае успеха или неудачи уведомляет пользователя.

    Args:
        message (types.Message): Объект сообщения Telegram, содержащий загруженный документ.
        bot (AsyncTeleBot): Экземпляр асинхронного Telegram-бота.
    """
    user_id = message.from_user.id
    lang_code = await db_manager.get_user_language(user_id)
    main_keyboard = mk.create_main_keyboard(lang_code, user_id)

    # 1. Проверяем, что прислали именно документ
    if message.content_type != 'document':
        await bot.reply_to(message, loc.get_text('memory_file_error_type', lang_code), reply_markup=main_keyboard)
        await bot.delete_state(user_id, message.chat.id)
        return

    doc = message.document
    file_name = doc.file_name or "document"
    
    # 2. Проверяем расширение файла
    if not (file_name.lower().endswith('.txt') or file_name.lower().endswith('.md')):
        await bot.reply_to(message, loc.get_text('memory_file_error_type', lang_code), reply_markup=main_keyboard)
        await bot.delete_state(user_id, message.chat.id)
        return

    # 3. Проверяем размер файла (1 MB limit)
    if doc.file_size > 1024 * 1024:
        await bot.reply_to(message, loc.get_text('memory_file_error_size', lang_code), reply_markup=main_keyboard)
        await bot.delete_state(user_id, message.chat.id)
        return

    status_msg = await bot.reply_to(message, loc.get_text('memory_file_processing', lang_code))

    try:
        # 4. Скачиваем и читаем файл
        file_info = await bot.get_file(doc.file_id)
        downloaded_file = await bot.download_file(file_info.file_path)
        
        try:
            file_content = downloaded_file.decode('utf-8')
        except UnicodeDecodeError:
            await bot.edit_message_text(loc.get_text('memory_file_error_read', lang_code), user_id, status_msg.message_id, reply_markup=main_keyboard)
            await bot.delete_state(user_id, message.chat.id)
            return

        # 5. Интеграция с VectorStoreManager
        fernet_instance = tg_helpers.user_session_keys.get(user_id)
        api_key = await db_manager.get_user_api_key(user_id, fernet_instance)
        active_dialog_id = await db_manager.get_active_dialog_id(user_id)

        if not all([fernet_instance, api_key, active_dialog_id]):
            raise ValueError("Сессия, API-ключ или активный диалог не найдены.")

        vector_store = VectorStoreManager(api_key=api_key)

        # Формируем метаданные для документа
        timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
        metadata = {
            "role": "user",
            "content_type": "document",
            "timestamp": timestamp,
            "user_id": user_id,
            "dialog_id": active_dialog_id # Добавляем dialog_id для удобства фильтрации в будущем
        }
        await vector_store.add_chunk(active_dialog_id, file_content, metadata) # <-- Изменен вызов и добавлены метаданные

        # 6. Сообщаем об успехе
        dialog_info = await db_manager.get_user_context_info(user_id)
        dialog_name = dialog_info.get('dialog_name', 'текущего') if dialog_info else 'текущего'
        success_text = loc.get_text('memory_file_success', lang_code).format(file_name=file_name, dialog_name=dialog_name)
        await bot.edit_message_text(success_text, user_id, status_msg.message_id)

    except Exception as e:
        logger.exception(f"Ошибка при обработке файла для памяти: {e}", extra={'user_id': str(user_id)})
        await bot.edit_message_text(loc.get_text('memory_file_error_general', lang_code), user_id, status_msg.message_id)
    finally:
        await bot.delete_state(user_id, message.chat.id)
        await bot.send_message(user_id, "Можете продолжать общение.", reply_markup=main_keyboard)

async def _handle_state_archive_period(message: types.Message, bot: AsyncTeleBot):
    """
    Обрабатывает ввод периода для архивации старых сообщений.

    Валидирует введенное число дней, извлекает старые сообщения из базы данных,
    делит их на дневные периоды, суммаризирует каждый период с помощью Gemini,
    сохраняет сводки в векторную базу данных и удаляет старые детальные чанки.

    Args:
        message (types.Message): Объект сообщения Telegram, содержащий количество дней.
        bot (AsyncTeleBot): Экземпляр AsyncTeleBot.
    """
    user_id = message.from_user.id
    lang_code = await db_manager.get_user_language(user_id)
    main_keyboard = mk.create_main_keyboard(lang_code, user_id)

    try:
        days_to_archive = int(message.text.strip())
        if days_to_archive <= 0:
            raise ValueError("Period must be a positive number.")
    except ValueError:
        await bot.reply_to(message, loc.get_text('memory_archiving_invalid_period', lang_code))
        return

    fernet_instance = tg_helpers.user_session_keys.get(user_id)
    if not fernet_instance:
        await bot.reply_to(message, "Критическая ошибка: сессия не найдена для архивации.")
        return

    api_key = await db_manager.get_user_api_key(user_id, fernet_instance)
    if not api_key:
        await bot.reply_to(message, loc.get_text('memory_archiving_error_api_key', lang_code))
        await bot.delete_state(user_id, message.chat.id)
        return

    active_dialog_id = await db_manager.get_active_dialog_id(user_id)
    if not active_dialog_id:
        await bot.reply_to(message, loc.get_text('dialog_error_no_active', lang_code))
        await bot.delete_state(user_id, message.chat.id)
        return

    # Получаем всю историю сообщений для активного диалога (пока без ограничения по дате, будем фильтровать ниже)
    all_history = await db_manager.get_conversation_history(active_dialog_id, fernet_instance, limit=999999) 

    if not all_history:
        await bot.reply_to(message, loc.get_text('memory_archiving_no_old_messages', lang_code).format(days=days_to_archive))
        await bot.delete_state(user_id, message.chat.id)
        return

    # Группируем сообщения по дням
    messages_by_date = {}
    for msg in all_history:
        # timestamp в БД хранится в ISO формате. Преобразуем его в объект datetime.
        try:
            msg_dt = datetime.fromisoformat(msg['timestamp']).replace(tzinfo=None) # Убираем tzinfo для сравнения с datetime.now().date()
        except ValueError:
            logger.error(f"Некорректный формат timestamp в БД: {msg['timestamp']}", extra={'user_id': str(user_id)})
            continue # Пропускаем некорректные записи

        msg_date = msg_dt.date()
        messages_by_date.setdefault(msg_date, []).append(msg)

    # Определяем дату отсечения
    cutoff_date = datetime.now().date() - datetime.timedelta(days=days_to_archive)

    periods_to_summarize = []
    # Собираем периоды для суммаризации
    sorted_dates = sorted(messages_by_date.keys())

    current_period_messages = []
    current_period_start_date = None

    for date in sorted_dates:
        if date < cutoff_date:
            # Все сообщения до cutoff_date группируем в периоды для суммаризации
            if not current_period_start_date:
                current_period_start_date = date

            current_period_messages.extend(messages_by_date[date])

            # Если это последний день в списке или следующий день - это cutoff_date,
            # или если дата не является последовательной, закрываем период.
            if date == sorted_dates[-1] or (date + datetime.timedelta(days=1)) not in messages_by_date or \
               (date + datetime.timedelta(days=1)) >= cutoff_date:

                # Добавляем период для суммаризации, если в нем есть сообщения
                if current_period_messages:
                    # Сортируем сообщения в периоде по времени для корректной суммаризации
                    current_period_messages.sort(key=lambda x: datetime.fromisoformat(x['timestamp']).replace(tzinfo=None))
                    periods_to_summarize.append({
                        'messages': current_period_messages,
                        'start_date': current_period_start_date,
                        'end_date': date
                    })
                current_period_messages = []
                current_period_start_date = None
        else:
            # Сообщения после cutoff_date не архивируются
            break

    if not periods_to_summarize:
        await bot.reply_to(message, loc.get_text('memory_archiving_no_old_messages', lang_code).format(days=days_to_archive))
        await bot.delete_state(user_id, message.chat.id)
        return

    status_msg = await bot.reply_to(message, loc.get_text('memory_archiving_started', lang_code).format(days=days_to_archive))

    summarized_count = 0
    try:
        vector_store = VectorStoreManager(api_key=api_key)

        for period in periods_to_summarize:
            period_messages = period['messages']
            period_start_date = period['start_date']
            period_end_date = period['end_date']

            current_date_str = period_start_date.strftime('%d.%m.%Y')
            if period_start_date != period_end_date:
                current_date_str += f" - {period_end_date.strftime('%d.%m.%Y')}"

            await bot.edit_message_text(
                loc.get_text('memory_archiving_processing', lang_code).format(current_date_str=current_date_str),
                chat_id=user_id,
                message_id=status_msg.message_id
            )

            summary = await gemini_service.summarize_conversation_history(api_key, period_messages)

            if summary:
                # Добавляем сводку в векторную базу
                summary_metadata = {
                    "role": "system",
                    "content_type": "summary",
                    "timestamp": datetime.now(datetime.timezone.utc).isoformat(), # Время создания сводки
                    "user_id": user_id,
                    "dialog_id": active_dialog_id,
                    "period_start": period_start_date.isoformat(),
                    "period_end": period_end_date.isoformat()
                }
                await vector_store.add_chunk(active_dialog_id, summary, summary_metadata)

                # Удаляем детальные чанки за этот период
                # Важно: здесь мы удаляем чанки из векторной базы, а не из основной БД (SQLite).
                # Сообщения из SQLite остаются, но их детальные векторные представления удаляются.
                # Это компромисс, так как удалять из SQLite сложнее и потенциально опасно.
                # Наша "архивация" касается именно векторной памяти.

                # Удаляем из вектора все, что входило в этот период (по дате, не по 'summary')
                # Нужно получить все сообщения из SQLite за этот период и удалить их из вектора
                # Но мы уже "сжали" их, поэтому просто удалим все чанки, которые были ДО cutoff_date
                # Эта часть логики удаления будет выполняться один раз после всех суммаризаций

                summarized_count += 1
            else:
                logger.warning(f"Не удалось получить сводку для периода {current_date_str} в диалоге {active_dialog_id}.", extra={'user_id': str(user_id)})

        # После того, как все периоды были суммаризированы и добавлены, удаляем все старые ДЕТАЛЬНЫЕ чанки.
        # Это более безопасный подход, чем удаление из основной БД, так как ChromaDB
        # может быть перестроена, а оригинальные сообщения в SQLite останутся, если это потребуется для отладки.
        await vector_store.delete_chunks_by_dialog_and_timestamp(active_dialog_id, datetime.combine(cutoff_date, datetime.min.time()).replace(tzinfo=datetime.timezone.utc))

        await bot.edit_message_text(
            loc.get_text('memory_archiving_done', lang_code).format(summarized_periods=summarized_count),
            chat_id=user_id,
            message_id=status_msg.message_id,
            reply_markup=main_keyboard
        )

    except Exception as e:
        logger.exception(f"Ошибка в процессе архивации памяти для user_id {user_id}: {e}", extra={'user_id': str(user_id)})
        await bot.edit_message_text(
            loc.get_text('memory_archiving_error', lang_code),
            chat_id=user_id,
            message_id=status_msg.message_id,
            reply_markup=main_keyboard
        )
    finally:
        await bot.delete_state(user_id, message.chat.id)        

# ===================================================================================
# --- ОБЩИЙ ОБРАБОТЧИК ДЛЯ СООБЩЕНИЙ БЕЗ СОСТОЯНИЯ (ИСПРАВЛЕННЫЙ) ---
# ===================================================================================

async def _handle_no_state_message(message: types.Message, bot: AsyncTeleBot):
    """
    Обрабатывает входящие сообщения пользователя, когда нет активного состояния.

    Эта функция:
    1. Проверяет и при необходимости запрашивает разблокировку сессии Zero-Knowledge.
    2. Извлекает и расшифровывает API-ключ пользователя.
    3. Формирует промпт для Gemini, включая поддержку текстовых, фото и голосовых сообщений.
    4. Вызывает `gemini_service.generate_response` для получения ответа.
    5. Добавляет контекстный заголовок и отправляет сгенерированный ответ пользователю,
       обрабатывая возможные ошибки API.

    Args:
        message (types.Message): Объект входящего сообщения Telegram.
        bot (AsyncTeleBot): Экземпляр асинхронного Telegram-бота.
    """
    # --- ШАГ 1: ПРОВЕРКА АКТИВНОЙ СЕССИИ (ИСПРАВЛЕНА) ---
    # Вызываем централизованную функцию, которая сама обработает блокировку
    if not await tg_helpers.check_session_and_prompt_for_unlock(bot, message):
        return
        
    user_id = message.from_user.id
    lang_code = await db_manager.get_user_language(user_id)
    fernet_instance = tg_helpers.user_session_keys.get(user_id)
    
    content_type = message.content_type
    
    try:
        # --- ШАГ 2: ПОЛУЧЕНИЕ API-КЛЮЧА С РАСШИФРОВКОЙ ---
        api_key = await db_manager.get_user_api_key(user_id, fernet_instance)
        if not api_key:
            error_text_key = 'api_key_needed_for_chat' if content_type == 'text' else 'api_key_needed_for_vision'
            await bot.reply_to(message, loc.get_text(error_text_key, lang_code))
            return

        await tg_helpers.send_typing_action(bot, user_id)

        # --- ШАГ 3: ФОРМИРОВАНИЕ ПРОМПТА (ОРИГИНАЛЬНАЯ ЛОГИКА) ---
        prompt: Union[str, List[Union[str, PIL.Image.Image, bytes]]]
        if content_type == 'text':
            prompt = message.text
        elif content_type == 'photo':
            file_info = await bot.get_file(message.photo[-1].file_id)
            downloaded_bytes = await bot.download_file(file_info.file_path)
            image = PIL.Image.open(BytesIO(downloaded_bytes))
            prompt_text = message.caption or "Опиши это изображение."
            prompt = [prompt_text, image]
        elif content_type == 'voice':
             file_info = await bot.get_file(message.voice.file_id)
             downloaded_bytes = await bot.download_file(file_info.file_path)
             prompt_text = "Расшифруй это аудиосообщение и ответь на него."
             prompt = [prompt_text, downloaded_bytes]
        else:
            await bot.reply_to(message, loc.get_text('unsupported_content', lang_code))
            return

        # --- ШАГ 4: ВЫЗОВ GEMINI С ПЕРЕДАЧЕЙ КЛЮЧА СЕССИИ ---
        # Передаем content_type в generate_response
        response_text, sources = await gemini_service.generate_response(user_id, prompt, api_key, fernet_instance, content_type) # <-- Добавлен content_type
        
        # --- ШАГ 5: ОТПРАВКА ОТВЕТА (ОРИГИНАЛЬНАЯ ЛОГИКА) ---
        header = await _create_context_header(user_id, lang_code)
        if header:
            await bot.send_message(user_id, telegramify_markdown.markdownify(header), parse_mode='MarkdownV2')

        final_message_body = response_text
        if sources:
            sources_text = "\n\n---\n*Источники:*\n"
            for i, source in enumerate(sources, 1):
                title = th.escape_markdown(source['title'])
                url = source['uri']
                sources_text += f"{i}\\. [{title}]({url})\n"
            final_message_body += sources_text

        await tg_helpers.send_long_message(bot, user_id, final_message_body, disable_web_page_preview=True)

    except GeminiAPIError as e:
        user_model = await db_manager.get_user_gemini_model(user_id) or DEFAULT_MODEL_ID
        user_friendly_error = loc.get_text(e.error_key, lang_code).format(model_name=user_model)
        error_markup = mk.create_error_report_button()
        await tg_helpers.send_long_message(bot, user_id, user_friendly_error, reply_markup=error_markup)
        
    except Exception as e:
        await tg_helpers.send_error_reply(bot, message, f"Критическая ошибка в _handle_no_state_message: {e}")
        await bot.delete_state(user_id, message.chat.id)

# ===================================================================================
# --- ГЛАВНЫЙ ЕДИНЫЙ ОБРАБОТЧИК И РЕГИСТРАЦИЯ (ИСПРАВЛЕННЫЙ) ---
# ===================================================================================

async def universal_message_router(message: types.Message, bot: AsyncTeleBot):
    """
    Единый обработчик для всех входящих сообщений Telegram.

    Эта функция выполняет маршрутизацию сообщений на основе:
    1. Статуса блокировки пользователя и режима обслуживания.
    2. Текущего состояния пользователя (например, ожидание пароля, API ключа, ответа на анкету).
    3. Типа содержимого сообщения (текст, фото, документ, голос).

    Также она регистрирует новых пользователей и уведомляет администратора.

    Args:
        message (types.Message): Объект входящего сообщения Telegram.
        bot (AsyncTeleBot): Экземпляр асинхронного Telegram-бота.
    """
    user = message.from_user
    user_id = user.id

    user_logger.info(f"Получено сообщение ({message.content_type}) от user ID: {user_id}", extra={'user_id': str(user_id)})
    
    # Теперь функция возвращает флаг, был ли пользователь новым
    is_new = await db_manager.add_or_update_user(user_id, user.username, user.first_name, user.last_name)
    if is_new:
        # Уведомляем админа отсюда, а не из db_manager
        await tg_helpers.notify_admin_of_new_user(user_id, user.username, user.first_name, user.last_name)

    lang_code = await db_manager.get_user_language(user_id)
    if not await _check_access(bot, user_id, lang_code):
        return
    
    # --- НОВАЯ ПРОВЕРКА НА КНОПКИ ---
    # Если это текстовое сообщение, и оно совпадает с текстом одной из кнопок,
    # мы прекращаем выполнение этого обработчика. Это позволит сработать
    # правильному, более специфичному обработчику из command_handlers.py.
    if message.content_type == 'text' and message.text in ALL_BUTTON_TEXTS:
        logger.debug(f"Router: Сообщение '{message.text}' распознано как кнопка. Пропускаем.")
        return

    current_state = await bot.get_state(user_id, user_id)
    logger.debug(f"Router: User {user_id}, State: {current_state}, Content: {message.content_type}")

    # --- ЕДИНАЯ ЛОГИЧЕСКАЯ ЦЕПОЧКА ---
    if current_state == settings.STATE_ZK_WAITING_FOR_PASSWORD_SETUP:
        await _handle_state_password_setup(message, bot)
    
    elif current_state == settings.STATE_ZK_WAITING_FOR_PASSWORD_CONFIRM:
        await _handle_state_password_confirm(message, bot)
        
    elif current_state == settings.STATE_ZK_WAITING_FOR_PASSWORD_UNLOCK:
        await _handle_state_password_unlock(message, bot)

    elif current_state == settings.STATE_PROFILE_WAITING_FOR_ANSWER and message.content_type == 'text':
        await _handle_state_profile_answer(message, bot)

    elif current_state == STATE_ADMIN_WAITING_FOR_BROADCAST_MSG:
        await _handle_state_admin_broadcast(message, bot)
        
    elif current_state == STATE_ADMIN_WAITING_FOR_USER_ID_TO_MANAGE:
        await _handle_state_admin_user_id_manage(message, bot)
        
    elif current_state == STATE_ADMIN_WAITING_FOR_USER_ID_TO_REPLY:
        await _handle_state_user_id_for_reply(message, bot)
        
    elif current_state == STATE_ADMIN_WAITING_FOR_REPLY_MESSAGE:
        await _handle_state_message_to_user(message, bot)
        
    elif current_state == STATE_WAITING_FOR_API_KEY:
        await _handle_state_api_key(message, bot)
        
    elif current_state == STATE_WAITING_FOR_TRANSLATE_TEXT:
        await _handle_state_translate(message, bot)
        
    elif current_state == STATE_WAITING_FOR_NEW_DIALOG_NAME:
        await _handle_state_new_dialog_name(message, bot)
        
    elif current_state == STATE_WAITING_FOR_RENAME_DIALOG:
        await _handle_state_rename_dialog(message, bot)
        
    elif current_state == STATE_WAITING_FOR_FEEDBACK:
        await _handle_state_feedback(message, bot)

    elif current_state == settings.STATE_WAITING_FOR_ARCHIVE_PERIOD: # <-- НОВЫЙ ОБРАБОТЧИК СОСТОЯНИЯ
        await _handle_state_archive_period(message, bot)

    elif current_state == settings.STATE_WAITING_FOR_DOCUMENT:
        await _handle_state_document_memorize(message, bot)
        
    elif current_state is None:
        # Если состояний нет, обрабатываем как обычное сообщение
        if message.content_type in ['text', 'photo', 'voice']:
            await _handle_no_state_message(message, bot)
        else:
            await bot.reply_to(message, loc.get_text('unsupported_content', lang_code))
    
    else:
        # Если есть состояние, но тип контента не подходит (например, фото вместо текста)
        await bot.reply_to(message, loc.get_text('state_wrong_content_type', lang_code))


def register_message_handlers(bot: AsyncTeleBot):
    """
    Регистрирует единственный универсальный обработчик для всех типов входящих сообщений.

    Все сообщения будут направляться в `universal_message_router` для централизованной
    обработки и маршрутизации на основе текущего состояния пользователя и типа контента.

    Args:
        bot (AsyncTeleBot): Экземпляр асинхронного Telegram-бота.
    """
    bot.register_message_handler(
        universal_message_router,
        content_types=['text', 'photo', 'document', 'audio', 'video', 'sticker', 'voice', 'location', 'contact'],
        pass_bot=True
    )
    logger.info("Универсальный обработчик сообщений зарегистрирован.")