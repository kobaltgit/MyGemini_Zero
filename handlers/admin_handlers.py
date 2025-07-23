# File: handlers/admin_handlers.py
"""
Обработчики для админ-панели. Доступ к этим функциям строго ограничен.
Этот модуль отвечает за обработку команд (/admin, /reply) и callback-запросов (нажатий на кнопки).
Обработка сообщений в состояниях (ожидание ввода) вынесена в message_handlers.py.
"""
import asyncio
import csv
import io
from datetime import datetime
from telebot.async_telebot import AsyncTeleBot
from telebot import types
from telebot.apihelper import ApiException
import telegramify_markdown

from config.settings import (
    CALLBACK_ADMIN_MAIN_MENU, CALLBACK_ADMIN_TOGGLE_MAINTENANCE,
    CALLBACK_ADMIN_MAINTENANCE_MENU, CALLBACK_ADMIN_COMMUNICATION_MENU,
    CALLBACK_ADMIN_BROADCAST, STATE_ADMIN_WAITING_FOR_BROADCAST_MSG,
    CALLBACK_ADMIN_CONFIRM_BROADCAST, CALLBACK_ADMIN_CANCEL_BROADCAST,
    CALLBACK_ADMIN_REPLY_TO_USER, STATE_ADMIN_WAITING_FOR_USER_ID_TO_REPLY,
    CALLBACK_ADMIN_STATS_MENU, CALLBACK_ADMIN_USER_MANAGEMENT_MENU,
    STATE_ADMIN_WAITING_FOR_USER_ID_TO_MANAGE,
    CALLBACK_ADMIN_TOGGLE_BLOCK_PREFIX, CALLBACK_ADMIN_RESET_API_KEY_PREFIX,
    CALLBACK_ADMIN_EXPORT_USERS
)
from utils import markup_helpers as mk
from utils import localization as loc
from . import telegram_helpers as tg_helpers
from database import db_manager
from logger_config import get_logger
from .decorators import admin_required

logger = get_logger(__name__)

# --- Обработчики команд ---

@admin_required
async def handle_admin_command(message: types.Message, bot: AsyncTeleBot):
    """
    Обрабатывает команду /admin и нажатие на кнопку 'Админ-панель'.
    Выводит главное меню администратора.

    Args:
        message: Объект сообщения Telegram.
        bot: Экземпляр AsyncTeleBot.
    """
    user_id = message.from_user.id
    lang_code = await db_manager.get_user_language(user_id)

    admin_keyboard = await mk.create_admin_main_menu_keyboard(lang_code)
    await bot.send_message(
        user_id,
        text=loc.get_text('admin.panel_title', lang_code),
        reply_markup=admin_keyboard
    )

@admin_required
async def handle_reply_command(message: types.Message, bot: AsyncTeleBot):
    """
    Обрабатывает команду /reply <user_id> <text> для ответа пользователю.

    Args:
        message: Объект сообщения Telegram.
        bot: Экземпляр AsyncTeleBot.
    """
    admin_id = message.from_user.id
    lang_code = await db_manager.get_user_language(admin_id)
    parts = message.text.split(maxsplit=2)
    if len(parts) < 3:
        await bot.reply_to(message, "Использование: `/reply <user_id> <текст сообщения>`")
        return
    target_user_id_str, text_to_send = parts[1], parts[2]
    if not target_user_id_str.isdigit():
        await bot.reply_to(message, f"Ошибка: User ID '{target_user_id_str}' должен быть числом.")
        return
    target_user_id = int(target_user_id_str)
    if not await db_manager.get_user_info_for_admin(target_user_id):
        await bot.reply_to(message, loc.get_text('admin.user_not_found', lang_code).format(user_id=target_user_id))
        return
    
    target_lang_code = await db_manager.get_user_language(target_user_id)
    notification_text = loc.get_text('admin.reply_admin_notification', target_lang_code).format(text=text_to_send)
    try:
        await bot.send_message(target_user_id, telegramify_markdown.markdownify(notification_text), parse_mode='MarkdownV2')
        await bot.reply_to(message, loc.get_text('admin.reply_sent_success', lang_code).format(user_id=target_user_id))
        logger.info(f"Администратор {admin_id} отправил ответ пользователю {target_user_id}.")
    except ApiException as e:
        if "bot was blocked by the user" in e.description:
            await bot.reply_to(message, loc.get_text('admin.reply_sent_fail', lang_code))
        else:
            await bot.reply_to(message, f"Не удалось отправить сообщение: {e.description}")
        logger.error(f"Ошибка при отправке ответа от админа {admin_id} пользователю {target_user_id}: {e}")

# --- Обработчики Callback-запросов ---

@admin_required
async def handle_admin_main_menu(call: types.CallbackQuery, bot: AsyncTeleBot):
    """
    Возвращает в главное меню админ-панели по нажатию кнопки.

    Args:
        call: Объект CallbackQuery Telegram.
        bot: Экземпляр AsyncTeleBot.
    """
    user_id = call.from_user.id
    lang_code = await db_manager.get_user_language(user_id)
    admin_keyboard = await mk.create_admin_main_menu_keyboard(lang_code)
    await tg_helpers.edit_message_text_safe(
        bot,
        chat_id=user_id,
        message_id=call.message.message_id,
        text=loc.get_text('admin.panel_title', lang_code),
        reply_markup=admin_keyboard
    )
    await bot.answer_callback_query(call.id)

# --- Блок режима обслуживания ---

@admin_required
async def handle_maintenance_menu(call: types.CallbackQuery, bot: AsyncTeleBot):
    """
    Показывает меню управления режимом обслуживания.

    Args:
        call: Объект CallbackQuery Telegram.
        bot: Экземпляр AsyncTeleBot.
    """
    user_id = call.from_user.id
    lang_code = await db_manager.get_user_language(user_id)
    maintenance_keyboard = await mk.create_maintenance_menu_keyboard(lang_code)
    await tg_helpers.edit_message_text_safe(
        bot,
        chat_id=user_id,
        message_id=call.message.message_id,
        text=loc.get_text('admin.maintenance_menu_title', lang_code),
        reply_markup=maintenance_keyboard
    )
    await bot.answer_callback_query(call.id)

@admin_required
async def handle_toggle_maintenance(call: types.CallbackQuery, bot: AsyncTeleBot):
    """
    Включает или выключает режим обслуживания.

    Args:
        call: Объект CallbackQuery Telegram.
        bot: Экземпляр AsyncTeleBot.
    """
    action = call.data.split(':')[1]
    user_id = call.from_user.id
    lang_code = await db_manager.get_user_language(user_id)
    if action == 'on':
        await db_manager.set_app_setting('maintenance_mode', 'true')
        answer_text = loc.get_text('admin.maintenance_enabled_msg', lang_code)
        logger.warning("Активирован режим технического обслуживания.", extra={'user_id': str(user_id)})
    else:
        await db_manager.set_app_setting('maintenance_mode', 'false')
        answer_text = loc.get_text('admin.maintenance_disabled_msg', lang_code)
        logger.info("Режим технического обслуживания отключен.", extra={'user_id': str(user_id)})
    maintenance_keyboard = await mk.create_maintenance_menu_keyboard(lang_code)
    await bot.edit_message_reply_markup(
        chat_id=user_id,
        message_id=call.message.message_id,
        reply_markup=maintenance_keyboard
    )
    await bot.answer_callback_query(call.id, text=answer_text, show_alert=True)

# --- Блок коммуникации ---

@admin_required
async def handle_communication_menu(call: types.CallbackQuery, bot: AsyncTeleBot):
    """
    Показывает меню коммуникации (рассылка, ответы).

    Args:
        call: Объект CallbackQuery Telegram.
        bot: Экземпляр AsyncTeleBot.
    """
    user_id = call.from_user.id
    lang_code = await db_manager.get_user_language(user_id)
    comm_keyboard = await mk.create_communication_menu_keyboard(lang_code)
    await tg_helpers.edit_message_text_safe(
        bot,
        chat_id=user_id,
        message_id=call.message.message_id,
        text=loc.get_text('admin.communication_title', lang_code),
        reply_markup=comm_keyboard
    )
    await bot.answer_callback_query(call.id)

@admin_required
async def handle_broadcast_start(call: types.CallbackQuery, bot: AsyncTeleBot):
    """
    Начинает процесс создания рассылки, переводя админа в состояние ожидания сообщения.

    Args:
        call: Объект CallbackQuery Telegram.
        bot: Экземпляр AsyncTeleBot.
    """
    user_id = call.from_user.id
    lang_code = await db_manager.get_user_language(user_id)
    await bot.set_state(user_id, STATE_ADMIN_WAITING_FOR_BROADCAST_MSG, user_id)
    await tg_helpers.edit_message_text_safe(
        bot,
        chat_id=user_id,
        message_id=call.message.message_id,
        text=loc.get_text('admin.broadcast_prompt', lang_code),
        reply_markup=None
    )
    await bot.answer_callback_query(call.id)

@admin_required
async def handle_broadcast_cancel(call: types.CallbackQuery, bot: AsyncTeleBot):
    """
    Отменяет рассылку на этапе подтверждения.

    Args:
        call: Объект CallbackQuery Telegram.
        bot: Экземпляр AsyncTeleBot.
    """
    user_id = call.from_user.id
    lang_code = await db_manager.get_user_language(user_id)
    await bot.delete_state(user_id, user_id)
    await tg_helpers.edit_message_text_safe(
        bot,
        chat_id=user_id,
        message_id=call.message.message_id,
        text=loc.get_text('admin.broadcast_cancelled', lang_code),
        reply_markup=None
    )
    await bot.answer_callback_query(call.id)

async def _run_broadcast(bot: AsyncTeleBot, admin_id: int, message_text: str, lang_code: str):
    """
    (Внутренняя функция) Асинхронно выполняет саму рассылку в фоновом режиме.

    Args:
        bot: Экземпляр AsyncTeleBot.
        admin_id: ID администратора для отправки отчета.
        message_text: Текст для рассылки.
        lang_code: Языковой код администратора.
    """
    all_user_ids = await db_manager.get_all_user_ids()
    sent_count = 0
    failed_count = 0
    formatted_message = telegramify_markdown.markdownify(message_text)
    for user_id in all_user_ids:
        try:
            await bot.send_message(user_id, formatted_message, parse_mode='MarkdownV2', disable_web_page_preview=True)
            sent_count += 1
        except Exception as e:
            logger.warning(f"Не удалось отправить рассылку пользователю {user_id}: {e}", extra={'user_id': str(user_id)})
            failed_count += 1
        await asyncio.sleep(0.1) # Задержка для избежания флуд-лимитов Telegram
    result_text = loc.get_text('admin.broadcast_finished', lang_code).format(sent=sent_count, failed=failed_count)
    await bot.send_message(admin_id, result_text)

@admin_required
async def handle_broadcast_confirm(call: types.CallbackQuery, bot: AsyncTeleBot):
    """
    Запускает рассылку после подтверждения админом.

    Args:
        call: Объект CallbackQuery Telegram.
        bot: Экземпляр AsyncTeleBot.
    """
    admin_id = call.from_user.id
    lang_code = await db_manager.get_user_language(admin_id)
    async with bot.retrieve_data(admin_id, admin_id) as data:
        message_text = data.get('broadcast_message')
    if not message_text:
        await bot.answer_callback_query(call.id, "Ошибка: текст для рассылки не найден.", show_alert=True)
        return
    await bot.delete_state(admin_id, admin_id)
    await tg_helpers.edit_message_text_safe(
        bot,
        chat_id=admin_id,
        message_id=call.message.message_id,
        text=loc.get_text('admin.broadcast_started', lang_code),
        reply_markup=None
    )
    asyncio.create_task(_run_broadcast(bot, admin_id, message_text, lang_code))
    await bot.answer_callback_query(call.id)

# --- Блок статистики ---
@admin_required
async def handle_stats_menu(call: types.CallbackQuery, bot: AsyncTeleBot):
    """
    Показывает меню глобальной статистики бота.

    Args:
        call: Объект CallbackQuery Telegram.
        bot: Экземпляр AsyncTeleBot.
    """
    user_id = call.from_user.id
    lang_code = await db_manager.get_user_language(user_id)

    total_users = await db_manager.get_total_users_count()
    active_users = await db_manager.get_active_users_count(days=7)
    new_users = await db_manager.get_new_users_count(days=7)
    blocked_users = await db_manager.get_blocked_users_count()

    stats_text = (f"{loc.get_text('admin.stats_title', lang_code)}\n\n"
                  f"{loc.get_text('admin.stats_total_users', lang_code)} `{total_users}`\n"
                  f"{loc.get_text('admin.stats_active_users', lang_code)} `{active_users}`\n"
                  f"{loc.get_text('admin.stats_new_users', lang_code)} `{new_users}`\n"
                  f"{loc.get_text('admin.stats_blocked_users', lang_code)} `{blocked_users}`")

    back_keyboard = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton(
        loc.get_text('admin.btn_back_to_admin_menu', lang_code),
        callback_data=CALLBACK_ADMIN_MAIN_MENU
    ))

    await tg_helpers.edit_message_text_safe(
        bot,
        chat_id=user_id,
        message_id=call.message.message_id,
        text=stats_text,
        reply_markup=back_keyboard,
        parse_mode="MarkdownV2"
    )
    await bot.answer_callback_query(call.id)

# --- Блок управления пользователями ---

@admin_required
async def handle_user_management_menu(call: types.CallbackQuery, bot: AsyncTeleBot):
    """
    Начинает процесс управления пользователем, запрашивая ID.

    Args:
        call: Объект CallbackQuery Telegram.
        bot: Экземпляр AsyncTeleBot.
    """
    user_id = call.from_user.id
    lang_code = await db_manager.get_user_language(user_id)
    await bot.set_state(user_id, STATE_ADMIN_WAITING_FOR_USER_ID_TO_MANAGE, user_id)
    await tg_helpers.edit_message_text_safe(
        bot,
        chat_id=user_id,
        message_id=call.message.message_id,
        text=loc.get_text('admin.user_management_prompt', lang_code),
        reply_markup=None
    )
    await bot.answer_callback_query(call.id)

@admin_required
async def handle_toggle_block_user(call: types.CallbackQuery, bot: AsyncTeleBot):
    """
    Блокирует или разблокирует пользователя по нажатию кнопки.

    Args:
        call: Объект CallbackQuery Telegram.
        bot: Экземпляр AsyncTeleBot.
    """
    admin_id = call.from_user.id
    lang_code = await db_manager.get_user_language(admin_id)
    user_id_to_toggle = int(call.data.split(':')[1])

    user_info = await db_manager.get_user_info_for_admin(user_id_to_toggle)
    if not user_info:
        await bot.answer_callback_query(call.id, "Пользователь не найден.", show_alert=True)
        return

    if user_info['is_blocked']:
        await db_manager.unblock_user(user_id_to_toggle)
        alert_text = loc.get_text('admin.user_unblocked_success', lang_code).format(user_id=user_id_to_toggle)
    else:
        await db_manager.block_user(user_id_to_toggle)
        alert_text = loc.get_text('admin.user_blocked_success', lang_code).format(user_id=user_id_to_toggle)

    new_user_info_text = await tg_helpers.get_user_info_text(user_id_to_toggle, lang_code)
    new_user_info = await db_manager.get_user_info_for_admin(user_id_to_toggle)
    new_keyboard = mk.create_user_management_keyboard(user_id_to_toggle, new_user_info['is_blocked'], lang_code)

    await tg_helpers.edit_message_text_safe(
        bot,
        chat_id=admin_id,
        message_id=call.message.message_id,
        text=new_user_info_text,
        reply_markup=new_keyboard,
        parse_mode="MarkdownV2"
    )
    await bot.answer_callback_query(call.id, alert_text)

@admin_required
async def handle_reset_api_key(call: types.CallbackQuery, bot: AsyncTeleBot):
    """
    Сбрасывает API-ключ пользователя по нажатию кнопки.

    Args:
        call: Объект CallbackQuery Telegram.
        bot: Экземпляр AsyncTeleBot.
    """
    admin_id = call.from_user.id
    lang_code = await db_manager.get_user_language(admin_id)
    user_id_to_reset = int(call.data.split(':')[1])

    await db_manager.set_user_api_key(user_id_to_reset, None)
    alert_text = loc.get_text('admin.user_api_key_reset_success', lang_code).format(user_id=user_id_to_reset)
    await bot.answer_callback_query(call.id, alert_text, show_alert=True)

# --- Блок экспорта ---
@admin_required
async def handle_export_users(call: types.CallbackQuery, bot: AsyncTeleBot):
    """
    Обрабатывает запрос на выгрузку пользователей в CSV.

    Args:
        call: Объект CallbackQuery Telegram.
        bot: Экземпляр AsyncTeleBot.
    """
    admin_id = call.from_user.id
    await bot.answer_callback_query(call.id)
    status_msg = await bot.send_message(admin_id, "⏳ Готовлю файл для выгрузки...")

    try:
        users_data = await db_manager.get_all_users_for_export()
        if not users_data:
            await bot.edit_message_text("Нет пользователей для экспорта.", admin_id, status_msg.message_id)
            return

        output = io.StringIO()
        output.write('\ufeff')
        writer = csv.writer(output, delimiter=';', quotechar='"', quoting=csv.QUOTE_MINIMAL)
        headers = ["user_id", "username", "first_name", "last_name", "language_code", "first_interaction_date", "is_blocked"]
        writer.writerow(headers)

        for user in users_data:
            writer.writerow([
                user.get("user_id"), user.get("username", ""), user.get("first_name", ""),
                user.get("last_name", ""), user.get("language_code", ""),
                user.get("first_interaction_date", ""), "Yes" if user.get("is_blocked") else "No"
            ])

        output.seek(0)
        file_data = output.getvalue().encode('utf-8')
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
        file_name = f"users_export_{timestamp}.csv"
        input_file = types.InputFile(io.BytesIO(file_data)) 

        await bot.send_document(
            admin_id,
            input_file,
            visible_file_name=file_name,
            caption="✅ Выгрузка данных пользователей завершена."
        )
        await bot.delete_message(admin_id, status_msg.message_id)

    except Exception as e:
        logger.exception(f"Ошибка при экспорте пользователей: {e}", extra={'user_id': str(admin_id)})
        await bot.edit_message_text("❌ Произошла ошибка при создании файла.", admin_id, status_msg.message_id)

@admin_required
async def handle_reply_to_user_start(call: types.CallbackQuery, bot: AsyncTeleBot):
    """
    Начинает процесс отправки сообщения конкретному пользователю.
    Запрашивает у админа User ID.
    """
    admin_id = call.from_user.id
    lang_code = await db_manager.get_user_language(admin_id)

    await bot.set_state(admin_id, STATE_ADMIN_WAITING_FOR_USER_ID_TO_REPLY, admin_id)
    
    await tg_helpers.edit_message_text_safe(
        bot,
        chat_id=admin_id,
        message_id=call.message.message_id,
        text=loc.get_text('admin.reply_prompt_user_id', lang_code),
        reply_markup=None
    )
    await bot.answer_callback_query(call.id)

def register_admin_handlers(bot: AsyncTeleBot):
    """
    Регистрирует все обработчики для админ-панели (команды и callback-и).
    """
    # --- Команды ---
    bot.register_message_handler(handle_admin_command, commands=['admin'], pass_bot=True)
    bot.register_message_handler(handle_reply_command, commands=['reply'], pass_bot=True)
    
    # --- Текстовая кнопка ---
    bot.register_message_handler(
        handle_admin_command,
        func=lambda msg: msg.text in [loc.get_text('btn_admin_panel', 'ru'), loc.get_text('btn_admin_panel', 'en')],
        pass_bot=True
    )

    # --- Callback-запросы ---
    # Меню
    bot.register_callback_query_handler(handle_admin_main_menu, func=lambda call: call.data == CALLBACK_ADMIN_MAIN_MENU, pass_bot=True)
    bot.register_callback_query_handler(handle_communication_menu, func=lambda call: call.data == CALLBACK_ADMIN_COMMUNICATION_MENU, pass_bot=True)
    bot.register_callback_query_handler(handle_maintenance_menu, func=lambda call: call.data == CALLBACK_ADMIN_MAINTENANCE_MENU, pass_bot=True)
    bot.register_callback_query_handler(handle_stats_menu, func=lambda call: call.data == CALLBACK_ADMIN_STATS_MENU, pass_bot=True)
    bot.register_callback_query_handler(handle_user_management_menu, func=lambda call: call.data == CALLBACK_ADMIN_USER_MANAGEMENT_MENU, pass_bot=True)
    bot.register_callback_query_handler(handle_export_users, func=lambda call: call.data == CALLBACK_ADMIN_EXPORT_USERS, pass_bot=True)

    # Действия
    bot.register_callback_query_handler(handle_toggle_maintenance, func=lambda call: call.data.startswith(CALLBACK_ADMIN_TOGGLE_MAINTENANCE), pass_bot=True)
    bot.register_callback_query_handler(handle_broadcast_start, func=lambda call: call.data == CALLBACK_ADMIN_BROADCAST, pass_bot=True)
    bot.register_callback_query_handler(handle_reply_to_user_start, func=lambda call: call.data == CALLBACK_ADMIN_REPLY_TO_USER, pass_bot=True)
    bot.register_callback_query_handler(handle_broadcast_confirm, func=lambda call: call.data == CALLBACK_ADMIN_CONFIRM_BROADCAST, pass_bot=True)
    bot.register_callback_query_handler(handle_broadcast_cancel, func=lambda call: call.data == CALLBACK_ADMIN_CANCEL_BROADCAST, pass_bot=True)
    bot.register_callback_query_handler(handle_toggle_block_user, func=lambda call: call.data.startswith(CALLBACK_ADMIN_TOGGLE_BLOCK_PREFIX), pass_bot=True)
    bot.register_callback_query_handler(handle_reset_api_key, func=lambda call: call.data.startswith(CALLBACK_ADMIN_RESET_API_KEY_PREFIX), pass_bot=True)

    logger.info("Обработчики команд и callback'ов админ-панели зарегистрированы.")