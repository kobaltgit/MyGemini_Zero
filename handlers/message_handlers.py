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
"""
import datetime
import PIL.Image
from io import BytesIO
import asyncio
from typing import Dict, List, Union
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
    STATE_ADMIN_WAITING_FOR_USER_ID_TO_REPLY, STATE_ADMIN_WAITING_FOR_REPLY_MESSAGE,
    STATE_ZK_WAITING_FOR_PANIC_SETUP, STATE_ZK_WAITING_FOR_PANIC_CONFIRM
)
from database import db_manager
from services import gemini_service
from services.gemini_service import GeminiAPIError
from services.vector_store_manager import VectorStoreManager
from features import profile_manager
from features.profile_manager import QUESTIONNAIRE, ask_question
from .decorators import admin_required
from handlers.callback_handlers import handle_callback_query


from logger_config import get_logger

logger = get_logger(__name__)
user_logger = get_logger('user_messages')

# --- Глобальные переменные для буферизации сообщений ---
# {user_id: [message_text_1, message_text_2]}
message_buffers: Dict[int, List[str]] = {}
# {user_id: asyncio.Task}
user_timers: Dict[int, asyncio.Task] = {}

# --- СПИСОК ВСЕХ КНОПОК ДЛЯ ИСКЛЮЧЕНИЯ ИЗ УНИВЕРСАЛЬНОГО ОБРАБОТЧИКА ---
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
# --- ВНУТРЕННИЕ ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ---
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

async def _handle_state_password_setup(message: types.Message, bot: AsyncTeleBot):
    """
    Обрабатывает ввод первого мастер-пароля при первичной настройке Zero-Knowledge.

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
    Обрабатывает подтверждение мастер-пароля, сохраняет его и запускает анкетирование.

    Args:
        message (types.Message): Объект сообщения Telegram, содержащий подтверждение пароля.
        bot (AsyncTeleBot): Экземпляр асинхронного Telegram-бота.
    """
    user_id = message.from_user.id
    lang_code = await db_manager.get_user_language(user_id)
    password_two = message.text.strip()
    await tg_helpers.delete_message_safe(bot, message.chat.id, message.message_id)

    async with bot.retrieve_data(user_id, message.chat.id) as data:
        password_one = data.get('password_one')

    if password_one == password_two:
        await db_manager.set_master_password(user_id, password_one)

        salt = await db_manager.get_user_salt(user_id)
        if salt:
            fernet_instance = crypto_helpers.get_fernet_instance(password_one, salt)
            tg_helpers.user_session_keys[user_id] = fernet_instance
            logger.info(f"Сессия для нового пользователя {user_id} создана после установки пароля.", extra={'user_id': str(user_id)})
        else:
            logger.error(f"Критическая ошибка: не удалось получить соль для user_id {user_id} после установки пароля.", extra={'user_id': str(user_id)})
            await bot.send_message(user_id, "Произошла критическая ошибка. Свяжитесь с администратором.")
            return

        await bot.delete_state(user_id, message.chat.id)
        await bot.send_message(user_id, loc.get_text('zk_setup_success', lang_code))

        # Сразу начинаем анкетирование после установки пароля
        await profile_manager.start_questionnaire(bot, message)
    else:
        await bot.set_state(user_id, settings.STATE_ZK_WAITING_FOR_PASSWORD_SETUP, message.chat.id)
        await bot.send_message(user_id, loc.get_text('zk_password_mismatch', lang_code))
        await bot.send_message(user_id, loc.get_text('zk_setup_prompt', lang_code))


async def _handle_state_password_unlock(message: types.Message, bot: AsyncTeleBot):
    """
    Обрабатывает ввод пароля для разблокировки сессии.

    Args:
        message (types.Message): Объект сообщения Telegram.
        bot (AsyncTeleBot): Экземпляр асинхронного Telegram-бота.
    """
    user_id = message.from_user.id
    lang_code = await db_manager.get_user_language(user_id)
    password = message.text.strip()
    await tg_helpers.delete_message_safe(bot, message.chat.id, message.message_id)
    
    pending_callback_data = None
    async with bot.retrieve_data(user_id, message.chat.id) as data:
        pending_callback_data = data.get('pending_callback_data')

    is_panic = await db_manager.verify_panic_password(user_id, password)
    if is_panic:
        logger.warning(f"!!! Сработал ПАРОЛЬ ПАНИКИ для пользователя {user_id} !!!", extra={'user_id': str(user_id)})
        salt = await db_manager.get_user_salt(user_id)
        fernet_instance_for_panic = crypto_helpers.get_fernet_instance(password, salt) if salt else None
        await db_manager.clear_user_content(user_id, fernet_instance_for_panic)

        await bot.delete_state(user_id, message.chat.id)
        main_keyboard = mk.create_main_keyboard(lang_code, user_id)
        await bot.send_message(user_id, loc.get_text('zk_unlock_success', lang_code), reply_markup=main_keyboard)
        return

    is_master = await db_manager.verify_master_password(user_id, password)
    if is_master:
        salt = await db_manager.get_user_salt(user_id)
        fernet_instance = crypto_helpers.get_fernet_instance(password, salt)
        tg_helpers.user_session_keys[user_id] = fernet_instance
        await db_manager.update_last_session_time(user_id)
        await bot.delete_state(user_id, message.chat.id)

        if pending_callback_data:
            logger.info(f"Сессия для {user_id} разблокирована. Выполняется отложенное действие: {pending_callback_data}", extra={'user_id': str(user_id)})
            fake_call = types.CallbackQuery(
                id=str(message.message_id),
                from_user=message.from_user,
                data=pending_callback_data,
                chat_instance=str(message.chat.id),
                json_string="",
                message=message
            )
            await handle_callback_query(fake_call, bot)
        else:
            main_keyboard = mk.create_main_keyboard(lang_code, user_id)
            await bot.send_message(user_id, loc.get_text('zk_unlock_success', lang_code), reply_markup=main_keyboard)
    else:
        await bot.send_message(user_id, loc.get_text('zk_unlock_fail', lang_code))


async def _handle_state_panic_password_setup(message: types.Message, bot: AsyncTeleBot):
    """
    Обрабатывает первый ввод пароля паники.

    Args:
        message (types.Message): Объект сообщения Telegram.
        bot (AsyncTeleBot): Экземпляр асинхронного Telegram-бота.
    """
    user_id = message.from_user.id
    password = message.text.strip()
    await tg_helpers.delete_message_safe(bot, message.chat.id, message.message_id)
    lang_code = await db_manager.get_user_language(user_id)

    is_master_match = await db_manager.verify_master_password(user_id, password)
    if is_master_match:
        await bot.reply_to(message, loc.get_text('panic_password_same_as_master', lang_code))
        return

    await bot.add_data(user_id, message.chat.id, panic_password_one=password)
    await bot.set_state(user_id, STATE_ZK_WAITING_FOR_PANIC_CONFIRM, message.chat.id)
    await bot.send_message(user_id, loc.get_text('panic_password_confirm_ask', lang_code))


async def _handle_state_panic_password_confirm(message: types.Message, bot: AsyncTeleBot):
    """
    Обрабатывает подтверждение пароля паники и переходит к установке API-ключа.

    Args:
        message (types.Message): Объект сообщения Telegram.
        bot (AsyncTeleBot): Экземпляр асинхронного Telegram-бота.
    """
    user_id = message.from_user.id
    lang_code = await db_manager.get_user_language(user_id)
    password_two = message.text.strip()
    await tg_helpers.delete_message_safe(bot, message.chat.id, message.message_id)

    async with bot.retrieve_data(user_id, message.chat.id) as data:
        password_one = data.get('panic_password_one')

    if password_one == password_two:
        await db_manager.set_panic_password(user_id, password_one)
        await bot.delete_state(user_id, message.chat.id)
        await bot.send_message(user_id, loc.get_text('panic_password_set_success', lang_code))
        
        # Переходим к установке API ключа
        await bot.set_state(user_id, settings.STATE_WAITING_FOR_API_KEY, message.chat.id)
        await bot.send_message(user_id, loc.get_text('set_api_key_prompt', lang_code))
    else:
        await bot.set_state(user_id, STATE_ZK_WAITING_FOR_PANIC_SETUP, message.chat.id)
        await bot.send_message(user_id, loc.get_text('panic_password_mismatch', lang_code))
        await bot.send_message(user_id, loc.get_text('panic_password_ask', lang_code))


async def _handle_state_profile_answer(message: types.Message, bot: AsyncTeleBot):
    """
    Обрабатывает текстовые ответы пользователя во время заполнения анкеты.

    Args:
        message (types.Message): Объект сообщения Telegram.
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
        
        current_profile[current_question_key] = answer
        
        next_question_key = QUESTIONNAIRE.get(current_question_key, {}).get('next')
        if next_question_key:
            data['current_question'] = next_question_key
            await ask_question(bot, user_id, next_question_key)
        else:
            # Анкета завершена, сохраняем профиль
            lang_code = await db_manager.get_user_language(user_id)
            fernet_instance = tg_helpers.user_session_keys.get(user_id)
            if fernet_instance:
                await db_manager.save_user_profile(user_id, current_profile, fernet_instance)
            else:
                logger.error(f"Не найдена сессия для сохранения профиля пользователя {user_id}", extra={'user_id': str(user_id)})
          
            logger.info(f"Анкета для пользователя {user_id} завершена. Профиль: {current_profile}", extra={'user_id': str(user_id)})
            await bot.send_message(user_id, loc.get_text('profile_end', lang_code))

            # Теперь предлагаем установить пароль паники
            panic_kbd = mk.create_panic_password_setup_keyboard(lang_code)
            await bot.send_message(user_id, loc.get_text('panic_password_prompt', lang_code), reply_markup=panic_kbd)
            
            # Сбрасываем состояние, чтобы пользователь мог нажать на inline-кнопки
            await bot.delete_state(user_id, message.chat.id)

@admin_required
async def _handle_state_admin_broadcast(message: types.Message, bot: AsyncTeleBot):
    """
    Обрабатывает ввод сообщения для рассылки.

    Args:
        message (types.Message): Объект сообщения Telegram.
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
    Обрабатывает ввод User ID для управления.

    Args:
        message (types.Message): Объект сообщения Telegram.
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
    Обрабатывает ввод User ID для ответа.

    Args:
        message (types.Message): Объект сообщения Telegram.
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
    Обрабатывает ввод сообщения для отправки пользователю.

    Args:
        message (types.Message): Объект сообщения Telegram.
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
    Обрабатывает ввод Google AI API ключа и завершает настройку.

    Args:
        message (types.Message): Объект сообщения Telegram.
        bot (AsyncTeleBot): Экземпляр асинхронного Telegram-бота.
    """
    user_id = message.chat.id
    api_key_plain = message.text.strip()
    lang_code = await db_manager.get_user_language(user_id)
    
    fernet_instance = tg_helpers.user_session_keys.get(user_id)
    if not fernet_instance:
        await bot.reply_to(message, "Критическая ошибка: сессия не найдена для шифрования ключа.")
        return
        
    await tg_helpers.delete_message_safe(bot, message.chat.id, message.message_id) # <-- ИЗМЕНЕНО
    
    status_msg = await bot.send_message(user_id, loc.get_text('api_key_verifying', lang_code))
    is_valid = await gemini_service.validate_api_key(api_key_plain)
    
    try:
        await bot.delete_message(user_id, status_msg.message_id)
    except Exception: pass
        
    if is_valid:
        await db_manager.set_user_api_key(user_id, api_key_plain, fernet_instance)
        await bot.delete_state(message.from_user.id, message.chat.id)
        
        main_keyboard = mk.create_main_keyboard(lang_code, user_id)
        await bot.send_message(user_id, loc.get_text('api_key_success', lang_code), reply_markup=main_keyboard)
    else:
        await bot.send_message(user_id, loc.get_text('api_key_invalid', lang_code))

async def _handle_state_translate(message: types.Message, bot: AsyncTeleBot):
    """
    Обрабатывает ввод текста для перевода.

    Args:
        message (types.Message): Объект сообщения Telegram.
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

    Args:
        message (types.Message): Объект сообщения Telegram.
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

    Args:
        message (types.Message): Объект сообщения Telegram.
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
    Обрабатывает сообщение обратной связи.

    Args:
        message (types.Message): Объект сообщения Telegram.
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
                text=f"```{user_text}```"
            )
            await bot.send_message(ADMIN_USER_ID, telegramify_markdown.markdownify(admin_notification), parse_mode='MarkdownV2')
        except Exception as e:
            logger.error(f"Не удалось отправить уведомление о фидбэке администратору: {e}", extra={'user_id': 'System'})

async def _handle_state_document_memorize(message: types.Message, bot: AsyncTeleBot):
    """
    Обрабатывает загрузку файла для добавления в долговременную память.

    Args:
        message (types.Message): Объект сообщения Telegram.
        bot (AsyncTeleBot): Экземпляр асинхронного Telegram-бота.
    """
    user_id = message.from_user.id
    lang_code = await db_manager.get_user_language(user_id)
    main_keyboard = mk.create_main_keyboard(lang_code, user_id)

    if message.content_type != 'document':
        await bot.reply_to(message, loc.get_text('memory_file_error_type', lang_code), reply_markup=main_keyboard)
        await bot.delete_state(user_id, message.chat.id)
        return

    doc = message.document
    file_name = doc.file_name or "document"
    
    if not (file_name.lower().endswith('.txt') or file_name.lower().endswith('.md')):
        await bot.reply_to(message, loc.get_text('memory_file_error_type', lang_code), reply_markup=main_keyboard)
        await bot.delete_state(user_id, message.chat.id)
        return

    if doc.file_size > 1024 * 1024:
        await bot.reply_to(message, loc.get_text('memory_file_error_size', lang_code), reply_markup=main_keyboard)
        await bot.delete_state(user_id, message.chat.id)
        return

    status_msg = await bot.reply_to(message, loc.get_text('memory_file_processing', lang_code))

    try:
        file_info = await bot.get_file(doc.file_id)
        downloaded_file = await bot.download_file(file_info.file_path)
        
        try:
            file_content = downloaded_file.decode('utf-8')
        except UnicodeDecodeError:
            await bot.edit_message_text(loc.get_text('memory_file_error_read', lang_code), user_id, status_msg.message_id, reply_markup=main_keyboard)
            await bot.delete_state(user_id, message.chat.id)
            return

        fernet_instance = tg_helpers.user_session_keys.get(user_id)
        api_key = await db_manager.get_user_api_key(user_id, fernet_instance)
        active_dialog_id = await db_manager.get_active_dialog_id(user_id)

        if not all([fernet_instance, api_key, active_dialog_id]):
            raise ValueError("Сессия, API-ключ или активный диалог не найдены.")

        vector_store = VectorStoreManager(api_key=api_key)

        timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
        metadata = {
            "role": "user",
            "content_type": "document",
            "timestamp": timestamp,
            "user_id": user_id,
            "dialog_id": active_dialog_id
        }
        await vector_store.add_chunk(active_dialog_id, file_content, metadata)

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
        bot (AsyncTeleBot): Экземпляр асинхронного Telegram-бота.
    """
    user_id = message.from_user.id
    lang_code = await db_manager.get_user_language(user_id)
    
    # Сессия уже должна быть активна. Делаем проверку на всякий случай.
    if not await tg_helpers.check_session_and_prompt_for_unlock(bot, message):
        return

    main_keyboard = mk.create_main_keyboard(lang_code, user_id)

    try:
        days_to_archive = int(message.text.strip())
        if days_to_archive <= 0:
            raise ValueError("Период должен быть положительным числом.")
    except ValueError:
        await bot.reply_to(message, loc.get_text('memory_archiving_invalid_period', lang_code))
        return # Остаемся в том же состоянии, чтобы пользователь попробовал снова
        
    fernet_instance = tg_helpers.user_session_keys.get(user_id)
    api_key = await db_manager.get_user_api_key(user_id, fernet_instance)

    if not api_key:
        await bot.reply_to(message, loc.get_text('memory_archiving_error_api_key', lang_code), reply_markup=main_keyboard)
        await bot.delete_state(user_id, message.chat.id)
        return

    active_dialog_id = await db_manager.get_active_dialog_id(user_id)
    if not active_dialog_id:
        await bot.reply_to(message, "Ошибка: не найден активный диалог.", reply_markup=main_keyboard)
        await bot.delete_state(user_id, message.chat.id)
        return

    status_msg = await bot.reply_to(message, loc.get_text('memory_archiving_started', lang_code).format(days=days_to_archive))
    await bot.delete_state(user_id, message.chat.id)
    
    try:
        cutoff_date = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=days_to_archive)
        
        history_to_archive = await db_manager.get_history_for_archiving(active_dialog_id, cutoff_date, fernet_instance)

        if not history_to_archive:
            # ИЗМЕНЕНИЕ 1: Убираем reply_markup
            await bot.edit_message_text(
                loc.get_text('memory_archiving_no_old_messages', lang_code).format(days=days_to_archive),
                user_id, status_msg.message_id
            )
            return

        summary = await gemini_service.summarize_conversation_history(api_key, history_to_archive)
        
        if summary:
            vector_store = VectorStoreManager(api_key=api_key)
            start_date = datetime.datetime.fromisoformat(history_to_archive[0]['timestamp'])
            end_date = datetime.datetime.fromisoformat(history_to_archive[-1]['timestamp'])
            
            await vector_store.add_summary_chunk(active_dialog_id, user_id, summary, start_date, end_date)
            
            message_ids_to_delete = [msg['conversation_id'] for msg in history_to_archive]
            deleted_count = await db_manager.delete_messages_by_ids(message_ids_to_delete)
            
            # ИЗМЕНЕНИЕ 2: Убираем reply_markup
            await bot.edit_message_text(
                loc.get_text('memory_archiving_done', lang_code).format(summarized_periods=deleted_count),
                user_id, status_msg.message_id
            )
        else:
             # ИЗМЕНЕНИЕ 3: Убираем reply_markup
             await bot.edit_message_text(
                "Не удалось сгенерировать сводку для архивации.",
                user_id, status_msg.message_id
            )

    except Exception as e:
        logger.exception(f"Ошибка в процессе архивации памяти для user_id {user_id}: {e}", extra={'user_id': str(user_id)})
        # ИЗМЕНЕНИЕ 4: Убираем reply_markup
        await bot.edit_message_text(
            loc.get_text('memory_archiving_error', lang_code),
            user_id, status_msg.message_id
        )
    finally:
        # ИЗМЕНЕНИЕ 5: Отправляем новое сообщение, чтобы вернуть клавиатуру
        await bot.send_message(user_id, "Вы можете продолжать.", reply_markup=main_keyboard)

# ===================================================================================
# --- ОБЩИЙ ОБРАБОТЧИК ДЛЯ СООБЩЕНИЙ БЕЗ СОСТОЯНИЯ ---
# ===================================================================================

async def _process_and_send_response(bot: AsyncTeleBot, message: types.Message, prompt: Union[str, List[Union[str, PIL.Image.Image, bytes]]], content_type: str):
    """
    Финальный этап обработки: отправляет запрос к Gemini и посылает ответ.

    Эта функция вызывается либо немедленно для нетекстовых сообщений, либо
    по истечении таймера для объединенных текстовых сообщений.

    Args:
        bot (AsyncTeleBot): Экземпляр бота.
        message (types.Message): Оригинальный объект сообщения для получения
            контекста (user_id, chat_id).
        prompt (Union[str, List[Union[str, PIL.Image.Image, bytes]]]):
            Сформированный промпт (текст или список с медиа).
        content_type (str): Тип контента ('text', 'photo', 'voice').
    """
    user_id = message.from_user.id
    lang_code = await db_manager.get_user_language(user_id)
    fernet_instance = tg_helpers.user_session_keys.get(user_id)
    
    try:
        api_key = await db_manager.get_user_api_key(user_id, fernet_instance)
        if not api_key:
            error_text_key = 'api_key_needed_for_chat' if content_type == 'text' else 'api_key_needed_for_vision'
            await bot.reply_to(message, loc.get_text(error_text_key, lang_code))
            return

        await tg_helpers.send_typing_action(bot, user_id)
        
        response_text, sources = await gemini_service.generate_response(user_id, prompt, api_key, fernet_instance, content_type)
        
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
        await tg_helpers.send_error_reply(bot, message, f"Критическая ошибка в _process_and_send_response: {e}")
        await bot.delete_state(user_id, message.chat.id)


async def _process_buffered_messages_task(bot: AsyncTeleBot, message: types.Message):
    """
    Задача-таймер, которая ждет, объединяет сообщения и запускает их обработку.

    Args:
        bot (AsyncTeleBot): Экземпляр бота.
        message (types.Message): Последний объект сообщения, который триггернул
            эту задачу. Нужен для передачи контекста.
    """
    user_id = message.from_user.id
    try:
        await asyncio.sleep(settings.MESSAGE_BUFFER_TIMEOUT)
        
        # Получаем и объединяем сообщения
        buffered_parts = message_buffers.get(user_id, [])
        if not buffered_parts:
            return
            
        combined_text = "\n".join(buffered_parts)
        logger.info(f"Таймер для user_id {user_id} сработал. Отправка объединенного сообщения: '{combined_text[:100]}...'", extra={'user_id': str(user_id)})
        
        # Очищаем буфер и таймер ПЕРЕД отправкой
        if user_id in message_buffers:
            del message_buffers[user_id]
        if user_id in user_timers:
            del user_timers[user_id]
            
        # Запускаем обработку
        await _process_and_send_response(bot, message, combined_text, 'text')
        
    except asyncio.CancelledError:
        logger.debug(f"Таймер для user_id {user_id} отменен (получено новое сообщение).", extra={'user_id': str(user_id)})
    except Exception as e:
        logger.exception(f"Ошибка в задаче обработки буфера для user_id {user_id}: {e}", extra={'user_id': str(user_id)})
        # Очистка в случае сбоя
        if user_id in message_buffers:
            del message_buffers[user_id]
        if user_id in user_timers:
            del user_timers[user_id]


async def _handle_no_state_message(message: types.Message, bot: AsyncTeleBot):
    """
    Обрабатывает входящие сообщения, когда нет активного состояния.
    Управляет буферизацией для текстовых сообщений.

    Args:
        message (types.Message): Объект входящего сообщения Telegram.
        bot (AsyncTeleBot): Экземпляр асинхронного Telegram-бота.
    """
    if not await tg_helpers.check_session_and_prompt_for_unlock(bot, message):
        return
        
    user_id = message.from_user.id
    content_type = message.content_type

    # --- ЛОГИКА БУФЕРИЗАЦИИ ---
    if content_type == 'text':
        # 1. Если для пользователя уже есть таймер, отменяем его
        if user_id in user_timers:
            user_timers[user_id].cancel()
        
        # 2. Добавляем текст нового сообщения в буфер
        if user_id not in message_buffers:
            message_buffers[user_id] = []
        message_buffers[user_id].append(message.text)
        
        # 3. Запускаем новый таймер
        task = asyncio.create_task(_process_buffered_messages_task(bot, message))
        user_timers[user_id] = task
        return

    # --- ОБРАБОТКА НЕ-ТЕКСТОВЫХ СООБЩЕНИЙ (сразу, без буфера) ---
    prompt: Union[str, List[Union[str, PIL.Image.Image, bytes]]]
    if content_type == 'photo':
        file_info = await bot.get_file(message.photo[-1].file_id)
        downloaded_bytes = await bot.download_file(file_info.file_path)
        image = PIL.Image.open(BytesIO(downloaded_bytes))
        prompt_text = message.caption or "Опиши это изображение."
        prompt = [prompt_text, image]
        await _process_and_send_response(bot, message, prompt, content_type)
    elif content_type == 'voice':
        file_info = await bot.get_file(message.voice.file_id)
        downloaded_bytes = await bot.download_file(file_info.file_path)
        prompt_text = "Расшифруй это аудиосообщение и ответь на него."
        prompt = [prompt_text, downloaded_bytes]
        await _process_and_send_response(bot, message, prompt, content_type)
    else:
        lang_code = await db_manager.get_user_language(user_id)
        await bot.reply_to(message, loc.get_text('unsupported_content', lang_code))

# ===================================================================================
# --- ГЛАВНЫЙ ЕДИНЫЙ ОБРАБОТЧИК И РЕГИСТРАЦИЯ ---
# ===================================================================================

async def universal_message_router(message: types.Message, bot: AsyncTeleBot):
    """
    Единый обработчик для всех входящих сообщений Telegram.

    Args:
        message (types.Message): Объект входящего сообщения Telegram.
        bot (AsyncTeleBot): Экземпляр асинхронного Telegram-бота.
    """
    user = message.from_user
    user_id = user.id
    chat_id = message.chat.id

    user_logger.info(f"Получено сообщение ({message.content_type}) от user ID: {user_id}", extra={'user_id': str(user_id)})
    
    is_new = await db_manager.add_or_update_user(user_id, user.username, user.first_name, user.last_name)
    if is_new:
        await tg_helpers.notify_admin_of_new_user(user_id, user.username, user.first_name, user.last_name)

    lang_code = await db_manager.get_user_language(user_id)
    if not await _check_access(bot, user_id, lang_code):
        return
    
    # --- НАЧАЛО НОВОГО БЛОКА ПРОВЕРКИ ПОДПИСКИ ---
    # Проверяем подписку для всех сообщений, которые не являются кнопками-командами
    if message.text not in ALL_BUTTON_TEXTS:
        subscription = await db_manager.get_user_subscription_status(user_id)
        if subscription['status'] != 'active':
            # Используем ту же логику, что и в декораторе
            plan = settings.SUBSCRIPTION_PLANS[0]
            markup = types.InlineKeyboardMarkup()
            sub_button = types.InlineKeyboardButton(
                text=loc.get_text('btn_subscribe', lang_code),
                callback_data=f"{settings.CALLBACK_SUBSCRIBE_PREFIX}{plan['id']}"
            )
            markup.add(sub_button)
            await bot.reply_to(message, loc.get_text('subscription_needed', lang_code), reply_markup=markup)
            return
    # --- КОНЕЦ НОВОГО БЛОКА ---
    
    if message.content_type == 'text' and message.text in ALL_BUTTON_TEXTS:
        logger.debug(f"Router: Сообщение '{message.text}' распознано как кнопка. Пропускаем.")
        return

    current_state = await bot.get_state(user_id, chat_id)
    logger.debug(f"Router: User {user_id}, Chat {chat_id}, State: {current_state}, Content: {message.content_type}")

    state_handlers = {
        settings.STATE_ZK_WAITING_FOR_PASSWORD_SETUP: _handle_state_password_setup,
        settings.STATE_ZK_WAITING_FOR_PASSWORD_CONFIRM: _handle_state_password_confirm,
        settings.STATE_ZK_WAITING_FOR_PASSWORD_UNLOCK: _handle_state_password_unlock,
        settings.STATE_PROFILE_WAITING_FOR_ANSWER: _handle_state_profile_answer,
        STATE_ZK_WAITING_FOR_PANIC_SETUP: _handle_state_panic_password_setup,
        STATE_ZK_WAITING_FOR_PANIC_CONFIRM: _handle_state_panic_password_confirm,
        STATE_ADMIN_WAITING_FOR_BROADCAST_MSG: _handle_state_admin_broadcast,
        STATE_ADMIN_WAITING_FOR_USER_ID_TO_MANAGE: _handle_state_admin_user_id_manage,
        STATE_ADMIN_WAITING_FOR_USER_ID_TO_REPLY: _handle_state_user_id_for_reply,
        STATE_ADMIN_WAITING_FOR_REPLY_MESSAGE: _handle_state_message_to_user,
        STATE_WAITING_FOR_API_KEY: _handle_state_api_key,
        STATE_WAITING_FOR_TRANSLATE_TEXT: _handle_state_translate,
        STATE_WAITING_FOR_NEW_DIALOG_NAME: _handle_state_new_dialog_name,
        STATE_WAITING_FOR_RENAME_DIALOG: _handle_state_rename_dialog,
        STATE_WAITING_FOR_FEEDBACK: _handle_state_feedback,
        settings.STATE_WAITING_FOR_ARCHIVE_PERIOD: _handle_state_archive_period,
        settings.STATE_WAITING_FOR_DOCUMENT: _handle_state_document_memorize,
    }

    handler = state_handlers.get(current_state)

    if handler:
        if handler in [_handle_state_profile_answer] and message.content_type != 'text':
             await bot.reply_to(message, loc.get_text('state_wrong_content_type', lang_code))
             return
        await handler(message, bot)
    elif current_state is None:
        # --- ИЗМЕНЕНИЕ: Вся логика (буферизация и обработка) теперь внутри _handle_no_state_message ---
        await _handle_no_state_message(message, bot)
    else:
        await bot.reply_to(message, loc.get_text('state_wrong_content_type', lang_code))


def register_message_handlers(bot: AsyncTeleBot):
    """
    Регистрирует единственный универсальный обработчик для всех типов сообщений.

    Args:
        bot (AsyncTeleBot): Экземпляр асинхронного Telegram-бота.
    """
    bot.register_message_handler(
        universal_message_router,
        content_types=['text', 'photo', 'document', 'audio', 'video', 'sticker', 'voice', 'location', 'contact'],
        pass_bot=True
    )
    logger.info("Универсальный обработчик сообщений зарегистрирован.")