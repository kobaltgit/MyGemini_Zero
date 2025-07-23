# File: MyGemini_Zero/handlers/message_handlers.py
"""
Центральный модуль для обработки сообщений от пользователя.
Здесь реализована явная маршрутизация на основе состояний.
(ZK Edition - Corrected)
"""
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
from features import profile_manager
from features.profile_manager import QUESTIONNAIRE, ask_question
from .decorators import admin_required
from .admin_handlers import handle_admin_command
from .command_handlers import user_session_keys # <-- Импорт сессионного кэша

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
    """Оригинальная функция проверки доступа."""
    if await db_manager.is_user_blocked(user_id):
        await bot.send_message(user_id, loc.get_text('user_is_blocked', lang_code))
        return False

    maintenance_mode_str = await db_manager.get_app_setting('maintenance_mode')
    if maintenance_mode_str == 'true' and user_id != ADMIN_USER_ID:
        await bot.send_message(user_id, loc.get_text('maintenance_mode_on', lang_code))
        return False
    return True

async def _create_context_header(user_id: int, lang_code: str) -> str:
    """Оригинальная функция создания заголовка."""
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
    """Логика для состояния STATE_ZK_WAITING_FOR_PASSWORD_SETUP."""
    user_id = message.from_user.id
    password = message.text.strip()
    await bot.add_data(user_id, message.chat.id, password_one=password)
    await bot.set_state(user_id, settings.STATE_ZK_WAITING_FOR_PASSWORD_CONFIRM, message.chat.id)
    lang_code = await db_manager.get_user_language(user_id)
    await bot.send_message(user_id, loc.get_text('zk_warning', lang_code))


async def _handle_state_password_confirm(message: types.Message, bot: AsyncTeleBot):
    """
    Обрабатывает подтверждение мастер-пароля.

    Если пароли совпадают, сохраняет хеш и соль в БД, создает
    и сохраняет активную сессию (ключ шифрования), а затем
    запускает анкету для нового пользователя.
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
            user_session_keys[user_id] = fernet_instance
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
    """Логика для состояния STATE_ZK_WAITING_FOR_PASSWORD_UNLOCK."""
    user_id = message.from_user.id
    lang_code = await db_manager.get_user_language(user_id)
    password = message.text.strip()
    if await db_manager.verify_master_password(user_id, password):
        salt = await db_manager.get_user_salt(user_id)
        fernet_instance = crypto_helpers.get_fernet_instance(password, salt)
        user_session_keys[user_id] = fernet_instance
        await bot.delete_state(user_id, message.chat.id)
        main_keyboard = mk.create_main_keyboard(lang_code, user_id)
        await bot.send_message(user_id, loc.get_text('zk_unlock_success', lang_code), reply_markup=main_keyboard)
    else:
        await bot.send_message(user_id, loc.get_text('zk_unlock_fail', lang_code))

async def _handle_state_profile_answer(message: types.Message, bot: AsyncTeleBot):
    """Логика для состояния STATE_PROFILE_WAITING_FOR_ANSWER (текстовые ответы)."""
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
            fernet_instance = user_session_keys.get(user_id)
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
    # Эта функция остается без изменений
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
    # Эта функция остается без изменений
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
    # Эта функция остается без изменений
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
    # Эта функция остается без изменений
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
    """Логика для состояния STATE_WAITING_FOR_API_KEY (адаптированная под ZK)."""
    user_id = message.chat.id
    api_key_plain = message.text.strip()
    lang_code = await db_manager.get_user_language(user_id)
    
    fernet_instance = user_session_keys.get(user_id)
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
    """Логика для состояния STATE_WAITING_FOR_TRANSLATE_TEXT (адаптированная под ZK)."""
    user_id = message.chat.id
    text_to_translate = message.text
    lang_code = await db_manager.get_user_language(user_id)
    
    fernet_instance = user_session_keys.get(user_id)
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
    # Эта функция остается без изменений
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
    # Эта функция остается без изменений
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
    """Логика для состояния STATE_WAITING_FOR_FEEDBACK."""
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

# ===================================================================================
# --- ОБЩИЙ ОБРАБОТЧИК ДЛЯ СООБЩЕНИЙ БЕЗ СОСТОЯНИЯ (ИСПРАВЛЕННЫЙ) ---
# ===================================================================================

async def _handle_no_state_message(message: types.Message, bot: AsyncTeleBot):
    """Обрабатывает сообщения, когда пользователь не в состоянии, с проверкой ZK-сессии."""
    user_id = message.from_user.id
    lang_code = await db_manager.get_user_language(user_id)
    
    # --- ШАГ 1: ПРОВЕРКА АКТИВНОЙ СЕССИИ ---
    if user_id not in user_session_keys:
        await bot.reply_to(message, loc.get_text('zk_user_is_locked', lang_code))
        return
    fernet_instance = user_session_keys.get(user_id)
    
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
        # TODO: Изменить gemini_service.generate_response, чтобы она принимала fernet_instance
        response_text, sources = await gemini_service.generate_response(user_id, prompt, api_key, fernet_instance)
        
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
    Единый обработчик, который маршрутизирует все сообщения в единой логической цепочке.
    """
    user = message.from_user
    user_id = user.id

    user_logger.info(f"Получено сообщение ({message.content_type}) от user ID: {user_id}", extra={'user_id': str(user_id)})
    await db_manager.add_or_update_user(user.id, user.username, user.first_name, user.last_name)
    
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
    """Регистрирует единственный универсальный обработчик для всех сообщений."""
    bot.register_message_handler(
        universal_message_router,
        content_types=['text', 'photo', 'document', 'audio', 'video', 'sticker', 'voice', 'location', 'contact'],
        pass_bot=True
    )
    logger.info("Универсальный обработчик сообщений зарегистрирован.")