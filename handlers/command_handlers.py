# File: MyGemini_Zero/handlers/command_handlers.py

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
Обработчики для основных команд Telegram.

Этот модуль отвечает за "входные точки" для пользователя, такие как /start.
Он определяет начальное состояние пользователя (нужно ли создать пароль, разблокировать
сессию и т.д.) и передает управление в message_handlers для дальнейшей обработки.
"""
from telebot.async_telebot import AsyncTeleBot
from telebot import types

from config import settings
from . import telegram_helpers as tg_helpers
from utils import markup_helpers as mk
from utils import localization as loc
from utils import guide_manager
from config.settings import (
    STATE_WAITING_FOR_HISTORY_DATE,
    STATE_WAITING_FOR_API_KEY,
    TOKEN_PRICING,
    DEFAULT_MODEL_ID,
    STATE_WAITING_FOR_NEW_DIALOG_NAME, 
    STATE_WAITING_FOR_RENAME_DIALOG
)
from database import db_manager
from services import gemini_service
from features import personal_account
from logger_config import get_logger
from utils import text_helpers as th
from .decorators import session_required, subscription_required

logger = get_logger(__name__)

# --- Управляющие команды (не требуют активной сессии) ---

async def handle_start(message: types.Message, bot: AsyncTeleBot):
    """
    Обработчик команды /start. Главная точка входа в бота.

    Маршрутизирует пользователя в зависимости от его статуса в системе
    (новый пользователь, пользователь с установленным паролем,
    пользователь с заблокированной сессией).

    Args:
        message: Объект сообщения Telegram.
        bot: Экземпляр AsyncTeleBot.
    """
    user = message.from_user
    user_id = user.id
    logger.info(f"Команда /start от user_id: {user_id}", extra={'user_id': str(user_id)})

    await db_manager.add_or_update_user(user.id, user.username, user.first_name, user.last_name)
    lang_code = await db_manager.get_user_language(user_id)
    
    subscription = await db_manager.get_user_subscription_status(user_id)

    # Если у пользователя нет активной подписки, показываем "продающее" сообщение
    if subscription['status'] != 'active':
        plan = settings.SUBSCRIPTION_PLANS[0]
        markup = types.InlineKeyboardMarkup()
        sub_button = types.InlineKeyboardButton(
            text=loc.get_text('btn_subscribe', lang_code),
            callback_data=f"{settings.CALLBACK_SUBSCRIBE_PREFIX}{plan['id']}"
        )
        markup.add(sub_button)
        await bot.send_message(user_id, loc.get_text('welcome_new_user_subscribed', lang_code), reply_markup=markup, disable_web_page_preview=True)
        return

    # Если подписка есть, продолжаем стандартный ZK-onboarding
    await bot.delete_state(user_id, message.chat.id)

    if not await db_manager.is_master_password_set(user_id):
        await bot.set_state(user_id, settings.STATE_ZK_WAITING_FOR_PASSWORD_SETUP, message.chat.id)
        await bot.send_message(user_id, loc.get_text('zk_setup_prompt', lang_code), reply_markup=types.ReplyKeyboardRemove())
    else:
        if user_id in tg_helpers.user_session_keys:
            main_keyboard = mk.create_main_keyboard(lang_code, user_id)
            await bot.send_message(user_id, "С возвращением! Ваша сессия активна.", reply_markup=main_keyboard)
        else:
            await bot.set_state(user_id, settings.STATE_ZK_WAITING_FOR_PASSWORD_UNLOCK, message.chat.id)
            await bot.send_message(user_id, loc.get_text('zk_unlock_prompt', lang_code), reply_markup=types.ReplyKeyboardRemove())


async def handle_logout(message: types.Message, bot: AsyncTeleBot):
    """
    Обработчик команды /logout. Блокирует сессию пользователя.

    Удаляет ключ сессии из оперативной памяти, требуя повторного ввода пароля
    при следующем действии.

    Args:
        message: Объект сообщения Telegram.
        bot: Экземпляр AsyncTeleBot.
    """
    user_id = message.from_user.id
    if user_id in tg_helpers.user_session_keys:
        del tg_helpers.user_session_keys[user_id]
        logger.info(f"Сессия для пользователя {user_id} была завершена вручную.", extra={'user_id': str(user_id)})
        await bot.reply_to(message, "Ваша сессия заблокирована. Для продолжения используйте /start.", reply_markup=types.ReplyKeyboardRemove())
    else:
        await bot.reply_to(message, "Ваша сессия уже заблокирована.")


async def handle_cancel(message: types.Message, bot: AsyncTeleBot):
    """
    Обработчик команды /cancel. Сбрасывает любое текущее состояние.

    Args:
        message: Объект сообщения Telegram.
        bot: Экземпляр AsyncTeleBot.
    """
    user_id = message.from_user.id
    await bot.delete_state(user_id, message.chat.id)
    lang_code = await db_manager.get_user_language(user_id)
    main_keyboard = mk.create_main_keyboard(lang_code, user_id) if user_id in tg_helpers.user_session_keys else types.ReplyKeyboardRemove()
    await bot.send_message(message.chat.id, "Действие отменено.", reply_markup=main_keyboard)

@subscription_required
@session_required
async def handle_profile(message: types.Message, bot: AsyncTeleBot):
    """
    Обработчик команды /profile. Начинает процесс редактирования/просмотра профиля.

    Args:
        message: Объект сообщения Telegram.
        bot: Экземпляр AsyncTeleBot.
    """
    await personal_account.get_personal_account_info(message, bot)


# --- Команды, требующие активной сессии ---

@session_required
async def handle_help(message: types.Message, bot: AsyncTeleBot):
    """
    Обработчик команды /help. Отправляет краткую справку по командам.

    Args:
        message: Объект сообщения Telegram.
        bot: Экземпляр AsyncTeleBot.
    """
    user_id = message.from_user.id
    lang_code = await db_manager.get_user_language(user_id)
    help_text = loc.get_text('cmd_help_text', lang_code)
    main_keyboard = mk.create_main_keyboard(lang_code, user_id)
    await tg_helpers.send_long_message(bot, user_id, help_text, reply_markup=main_keyboard)
    if settings.DONATION_URL:
        support_markup = mk.create_support_button_markup(lang_code)
        if support_markup:
            await bot.send_message(user_id, loc.get_text('support_prompt', lang_code), reply_markup=support_markup)

@subscription_required
@session_required
async def handle_reset(message: types.Message, bot: AsyncTeleBot):
    """
    Обработчик команды /reset. Сбрасывает краткосрочную память (контекст).

    Args:
        message: Объект сообщения Telegram.
        bot: Экземпляр AsyncTeleBot.
    """
    user_id = message.from_user.id
    await bot.delete_state(user_id, message.chat.id)
    active_dialog_id = await db_manager.get_active_dialog_id(user_id)
    if active_dialog_id:
        gemini_service.reset_dialog_chat(active_dialog_id)

    lang_code = await db_manager.get_user_language(user_id)
    reset_text = loc.get_text('cmd_reset_success', lang_code)
    main_keyboard = mk.create_main_keyboard(lang_code, user_id)
    await bot.reply_to(message, reset_text, reply_markup=main_keyboard)

@subscription_required
@session_required
async def handle_set_api_key(message: types.Message, bot: AsyncTeleBot):
    """
    Обработчик команды /set_api_key. Начинает процесс установки API ключа.

    Args:
        message: Объект сообщения Telegram.
        bot: Экземпляр AsyncTeleBot.
    """
    user_id = message.from_user.id
    lang_code = await db_manager.get_user_language(user_id)
    text = loc.get_text('set_api_key_prompt', lang_code)
    await bot.set_state(user_id, STATE_WAITING_FOR_API_KEY, message.chat.id)
    await bot.reply_to(message, text, reply_markup=types.ReplyKeyboardRemove())

@subscription_required
@session_required
async def handle_history(message: types.Message, bot: AsyncTeleBot):
    """
    Обработчик команды /history. Отправляет календарь для просмотра истории.

    Args:
        message: Объект сообщения Telegram.
        bot: Экземпляр AsyncTeleBot.
    """
    user_id = message.from_user.id
    lang_code = await db_manager.get_user_language(user_id)
    calendar_markup = mk.create_calendar_keyboard()
    text = loc.get_text('history_prompt', lang_code)
    await bot.send_message(user_id, text, reply_markup=calendar_markup)
    await bot.set_state(user_id, STATE_WAITING_FOR_HISTORY_DATE, message.chat.id)

@subscription_required
@session_required
async def handle_settings(message: types.Message, bot: AsyncTeleBot):
    """
    Обработчик команды /settings. Открывает меню настроек.

    Args:
        message: Объект сообщения Telegram.
        bot: Экземпляр AsyncTeleBot.
    """
    user_id = message.from_user.id
    lang_code = await db_manager.get_user_language(user_id)
    settings_markup = await mk.create_settings_keyboard(user_id)
    await bot.send_message(user_id, loc.get_text('settings_title', lang_code), reply_markup=settings_markup)

@subscription_required
@session_required
async def handle_dialogs(message: types.Message, bot: AsyncTeleBot):
    """
    Обработчик команды /dialogs. Открывает меню управления диалогами.

    Args:
        message: Объект сообщения Telegram.
        bot: Экземпляр AsyncTeleBot.
    """
    user_id = message.from_user.id
    lang_code = await db_manager.get_user_language(user_id)
    text = f"{loc.get_text('dialogs_menu_title', lang_code)}\n\n{loc.get_text('dialogs_menu_desc', lang_code)}"
    dialogs_keyboard = await mk.create_dialogs_menu_keyboard(user_id)
    await bot.send_message(user_id, text, reply_markup=dialogs_keyboard)

@subscription_required
@session_required
async def handle_memorize_file(message: types.Message, bot: AsyncTeleBot):
    """
    Обработчик команды /memorize_file для загрузки документа в память.

    Args:
        message: Объект сообщения Telegram.
        bot: Экземпляр AsyncTeleBot.
    """
    user_id = message.from_user.id
    lang_code = await db_manager.get_user_language(user_id)
    
    dialog_info = await db_manager.get_user_context_info(user_id)
    dialog_name = dialog_info.get('dialog_name', 'N/A') if dialog_info else 'N/A'
    
    await bot.set_state(user_id, settings.STATE_WAITING_FOR_DOCUMENT, message.chat.id)
    
    prompt_text = loc.get_text('memory_prompt_file', lang_code).format(dialog_name=dialog_name)
    await bot.send_message(user_id, prompt_text, reply_markup=types.ReplyKeyboardRemove())

@subscription_required
@session_required
async def handle_translate(message: types.Message, bot: AsyncTeleBot):
    """
    Обработчик команды /translate. Открывает меню выбора языка для перевода.

    Args:
        message: Объект сообщения Telegram.
        bot: Экземпляр AsyncTeleBot.
    """
    user_id = message.from_user.id
    lang_code = await db_manager.get_user_language(user_id)
    text = loc.get_text('translate_prompt', lang_code)
    lang_markup = mk.create_language_selection_keyboard()
    await bot.send_message(user_id, text, reply_markup=lang_markup)

@subscription_required
@session_required
async def handle_personal_account_button(message: types.Message, bot: AsyncTeleBot):
    """
    Обработчик нажатия на кнопку 'Личный кабинет'.

    Args:
        message: Объект сообщения Telegram.
        bot: Экземпляр AsyncTeleBot.
    """
    user_id = message.from_user.id
    lang_code = await db_manager.get_user_language(user_id)
    fernet_instance = tg_helpers.user_session_keys.get(user_id)

    await tg_helpers.send_typing_action(bot, user_id)
    
    info_text = await personal_account.get_personal_account_info(user_id, fernet_instance)
    
    main_keyboard = mk.create_main_keyboard(lang_code, user_id)
    await tg_helpers.send_long_message(
        bot, user_id, info_text,
        reply_markup=main_keyboard
    )

@subscription_required
@session_required
async def handle_data_management(message: types.Message, bot: AsyncTeleBot):
    """
    Обработчик команд /mydata, /archive. Открывает меню управления данными.

    Args:
        message: Объект сообщения Telegram.
        bot: Экземпляр AsyncTeleBot.
    """
    user_id = message.from_user.id
    lang_code = await db_manager.get_user_language(user_id)

    text = loc.get_text('data_management_title', lang_code)
    markup = mk.create_data_management_keyboard(lang_code)

    await bot.send_message(user_id, text, reply_markup=markup)

@subscription_required
@session_required
async def handle_usage(message: types.Message, bot: AsyncTeleBot):
    """
    Обработчик команды /usage для отображения статистики расходов токенов.

    Args:
        message: Объект сообщения Telegram.
        bot: Экземпляр AsyncTeleBot.
    """
    user_id = message.from_user.id
    lang_code = await db_manager.get_user_language(user_id)
    fernet_instance = tg_helpers.user_session_keys.get(user_id)

    api_key = await db_manager.get_user_api_key(user_id, fernet_instance)
    if not api_key:
        await bot.reply_to(message, loc.get_text('api_key_needed_for_feature', lang_code))
        return

    usage_today = await db_manager.get_token_usage_by_period(user_id, 'today')
    usage_month = await db_manager.get_token_usage_by_period(user_id, 'month')

    user_model = await db_manager.get_user_gemini_model(user_id) or DEFAULT_MODEL_ID
    pricing = TOKEN_PRICING.get(user_model, TOKEN_PRICING['default'])

    def calculate_cost(usage_data):
        input_cost = (usage_data['prompt_tokens'] / 1_000_000) * pricing['input_usd_per_million']
        output_cost = (usage_data['completion_tokens'] / 1_000_000) * pricing['output_usd_per_million']
        return input_cost + output_cost

    cost_today = calculate_cost(usage_today)
    cost_month = calculate_cost(usage_month)
    
    cost_today_str = f"{cost_today:.4f}".replace('.', '\\.')
    cost_month_str = f"{cost_month:.4f}".replace('.', '\\.')
    
    title = th.escape_markdown(loc.get_text('usage_title', lang_code))
    today_header = th.escape_markdown(loc.get_text('usage_today_header', lang_code))
    month_header = th.escape_markdown(loc.get_text('usage_month_header', lang_code))
    prompt_tokens_text = th.escape_markdown(loc.get_text('usage_prompt_tokens', lang_code))
    completion_tokens_text = th.escape_markdown(loc.get_text('usage_completion_tokens', lang_code))
    total_tokens_text = th.escape_markdown(loc.get_text('usage_total_tokens', lang_code))
    estimated_cost_text = th.escape_markdown(loc.get_text('usage_estimated_cost', lang_code))
    no_data_text = th.escape_markdown(loc.get_text('usage_no_data', lang_code))
    cost_notice = th.escape_markdown(loc.get_text('usage_cost_notice', lang_code))

    report_text = f"*{title}*\n\n"
    report_text += f"*{today_header}*\n"
    if usage_today['total_tokens'] > 0:
        report_text += (
            f"`{prompt_tokens_text:<25}: {usage_today['prompt_tokens']:,}`\n"
            f"`{completion_tokens_text:<25}: {usage_today['completion_tokens']:,}`\n"
            f"`{total_tokens_text:<25}: {usage_today['total_tokens']:,}`\n"
            f"`{estimated_cost_text:<25}: ${cost_today_str}`\n\n"
        )
    else:
        report_text += f"_{no_data_text}_\n\n"

    report_text += f"*{month_header}*\n"
    if usage_month['total_tokens'] > 0:
        report_text += (
            f"`{prompt_tokens_text:<25}: {usage_month['prompt_tokens']:,}`\n"
            f"`{completion_tokens_text:<25}: {usage_month['completion_tokens']:,}`\n"
            f"`{total_tokens_text:<25}: {usage_month['total_tokens']:,}`\n"
            f"`{estimated_cost_text:<25}: ${cost_month_str}`"
        )
    else:
        report_text += f"_{no_data_text}_"
    
    report_text += f"\n{cost_notice}"
    
    await bot.send_message(user_id, report_text, parse_mode='MarkdownV2')

@session_required
async def handle_full_guide(message: types.Message, bot: AsyncTeleBot):
    """
    Обработчик команды /help_guide, отправляет полную справку.

    Args:
        message: Объект сообщения Telegram.
        bot: Экземпляр AsyncTeleBot.
    """
    user_id = message.from_user.id
    lang_code = await db_manager.get_user_language(user_id)
    await tg_helpers.send_typing_action(bot, user_id)
    guide_text = guide_manager.get_full_guide(lang_code)
    await tg_helpers.send_long_message(bot, user_id, guide_text)

@session_required
async def handle_api_key_info(message: types.Message, bot: AsyncTeleBot):
    """
    Обработчик команды /apikey_info, отправляет секцию про API ключ.

    Args:
        message: Объект сообщения Telegram.
        bot: Экземпляр AsyncTeleBot.
    """
    user_id = message.from_user.id
    lang_code = await db_manager.get_user_language(user_id)
    await tg_helpers.send_typing_action(bot, user_id)
    guide_text = guide_manager.get_guide_section('API_KEY', lang_code)
    await tg_helpers.send_long_message(bot, user_id, guide_text)

async def handle_subscription(message: types.Message, bot: AsyncTeleBot):
    """
    Обработчик команды /subscription. Показывает статус подписки.
    """
    user_id = message.from_user.id
    lang_code = await db_manager.get_user_language(user_id)
    subscription = await db_manager.get_user_subscription_status(user_id)
    
    status_map = {
        'active': loc.get_text('sub_status_active', lang_code),
        'expired': loc.get_text('sub_status_expired', lang_code),
        'none': loc.get_text('sub_status_none', lang_code)
    }
    
    status_text = status_map.get(subscription['status'], subscription['status'])
    
    if subscription['status'] == 'active' and subscription['end_date']:
        end_date_str = subscription['end_date'].strftime('%d.%m.%Y')
        text = (f"{loc.get_text('subscription_status_title', lang_code)}\n\n"
                f"**Статус:** {status_text}\n"
                f"**{loc.get_text('sub_ends_on', lang_code)}** {end_date_str}")
    else:
        plan = settings.SUBSCRIPTION_PLANS[0]
        markup = types.InlineKeyboardMarkup()
        sub_button = types.InlineKeyboardButton(
            text=loc.get_text('btn_subscribe', lang_code),
            callback_data=f"{settings.CALLBACK_SUBSCRIBE_PREFIX}{plan['id']}"
        )
        markup.add(sub_button)
        text = (f"{loc.get_text('subscription_status_title', lang_code)}\n\n"
                f"**Статус:** {status_text}\n\n"
                f"{loc.get_text('sub_no_active_sub', lang_code)}")
        await bot.send_message(user_id, text, reply_markup=markup)
        return

    await bot.send_message(user_id, text)

def register_command_handlers(bot: AsyncTeleBot):
    """Регистрирует все обработчики команд и кнопок-синонимов."""
    bot.register_message_handler(handle_start, commands=['start'], pass_bot=True)
    bot.register_message_handler(handle_logout, commands=['logout', 'lock'], pass_bot=True)
    bot.register_message_handler(handle_subscription, commands=['subscription'], pass_bot=True)
    bot.register_message_handler(handle_cancel, commands=['cancel'], pass_bot=True)
    bot.register_message_handler(handle_profile, commands=['profile'], pass_bot=True)

    bot.register_message_handler(handle_help, commands=['help'], pass_bot=True)
    bot.register_message_handler(handle_full_guide, commands=['help_guide', 'guide'], pass_bot=True)
    bot.register_message_handler(handle_api_key_info, commands=['apikey_info', 'key_info'], pass_bot=True)
    bot.register_message_handler(handle_reset, commands=['reset'], pass_bot=True)
    bot.register_message_handler(handle_set_api_key, commands=['set_api_key', 'setapikey'], pass_bot=True)
    bot.register_message_handler(handle_settings, commands=['settings'], pass_bot=True)
    bot.register_message_handler(handle_history, commands=['history'], pass_bot=True)
    bot.register_message_handler(handle_translate, commands=['translate'], pass_bot=True)
    bot.register_message_handler(handle_usage, commands=['usage'], pass_bot=True)
    bot.register_message_handler(handle_dialogs, commands=['dialogs'], pass_bot=True)
    bot.register_message_handler(handle_memorize_file, commands=['memorize', 'memorize_file'], pass_bot=True)
    bot.register_message_handler(handle_data_management, commands=['archive_memory', 'archive', 'mydata'], pass_bot=True)

    bot.register_message_handler(handle_dialogs,
                                 func=lambda msg: msg.text in [loc.get_text('btn_dialogs', 'ru'),
                                                               loc.get_text('btn_dialogs', 'en')], pass_bot=True)
    bot.register_message_handler(handle_translate,
                                 func=lambda msg: msg.text in [loc.get_text('btn_translate', 'ru'),
                                                               loc.get_text('btn_translate', 'en')], pass_bot=True)
    bot.register_message_handler(handle_history,
                                 func=lambda msg: msg.text in [loc.get_text('btn_history', 'ru'),
                                                               loc.get_text('btn_history', 'en')], pass_bot=True)
    bot.register_message_handler(handle_personal_account_button,
                                 func=lambda msg: msg.text in [loc.get_text('btn_account', 'ru'),
                                                               loc.get_text('btn_account', 'en')], pass_bot=True)
    bot.register_message_handler(handle_settings,
                                 func=lambda msg: msg.text in [loc.get_text('btn_settings', 'ru'),
                                                               loc.get_text('btn_settings', 'en')], pass_bot=True)
    bot.register_message_handler(handle_help,
                                 func=lambda msg: msg.text in [loc.get_text('btn_help', 'ru'),
                                                               loc.get_text('btn_help', 'en')], pass_bot=True)
    bot.register_message_handler(handle_reset,
                                 func=lambda msg: msg.text in [loc.get_text('btn_reset', 'ru'),
                                                               loc.get_text('btn_reset', 'en')], pass_bot=True)
    bot.register_message_handler(handle_usage,
                                 func=lambda msg: msg.text in [loc.get_text('btn_usage', 'ru'),
                                                               loc.get_text('btn_usage', 'en')], pass_bot=True)

    logger.info("Обработчики команд и кнопок-синонимов зарегистрированы (ZK Edition).")