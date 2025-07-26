# File: utils/markup_helpers.py

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

from telebot import types
import datetime
from typing import List, Optional, Dict, Any

from config import settings
from config.settings import (
    BOT_STYLES, CALLBACK_ADMIN_EXPORT_USERS, DONATION_URL, TRANSLATE_LANGUAGES, BOT_PERSONAS, ADMIN_USER_ID,
    CALLBACK_SETTINGS_STYLE_PREFIX, CALLBACK_IGNORE,
    CALLBACK_CALENDAR_DATE_PREFIX, CALLBACK_CALENDAR_MONTH_PREFIX,
    CALLBACK_REPORT_ERROR, CALLBACK_LANG_PREFIX,
    CALLBACK_SETTINGS_LANG_PREFIX, CALLBACK_SETTINGS_SET_API_KEY,
    CALLBACK_SETTINGS_CHOOSE_MODEL_MENU, CALLBACK_SETTINGS_MODEL_PREFIX, CALLBACK_SETTINGS_BACK_TO_MAIN,
    CALLBACK_SETTINGS_PERSONA_MENU, CALLBACK_SETTINGS_PERSONA_PREFIX,
    # Dialogs
    CALLBACK_DIALOGS_MENU, CALLBACK_DIALOG_SWITCH_PREFIX, CALLBACK_DIALOG_RENAME_PREFIX,
    CALLBACK_DIALOG_DELETE_PREFIX, CALLBACK_DIALOG_CREATE, CALLBACK_DIALOG_CONFIRM_DELETE_PREFIX,
    # Data Management (НОВЫЕ ИМПОРТЫ)
    CALLBACK_DATA_MANAGEMENT_MENU, CALLBACK_ARCHIVE_MEMORY_START,
    CALLBACK_CLEAR_DATA_START, CALLBACK_CLEAR_DATA_CONFIRM, CALLBACK_CLEAR_DATA_CANCEL,
    # Panic Password (НОВЫЕ ИМПОРТЫ)
    CALLBACK_PANIC_SETUP_YES, CALLBACK_PANIC_SETUP_NO,
    # Admin Panel
    CALLBACK_ADMIN_MAIN_MENU, CALLBACK_ADMIN_STATS_MENU, CALLBACK_ADMIN_COMMUNICATION_MENU,
    CALLBACK_ADMIN_USER_MANAGEMENT_MENU, CALLBACK_ADMIN_MAINTENANCE_MENU, CALLBACK_ADMIN_TOGGLE_MAINTENANCE,
    CALLBACK_ADMIN_BROADCAST, CALLBACK_ADMIN_CONFIRM_BROADCAST, CALLBACK_ADMIN_CANCEL_BROADCAST,
    CALLBACK_ADMIN_TOGGLE_BLOCK_PREFIX, CALLBACK_ADMIN_RESET_API_KEY_PREFIX,
    CALLBACK_ADMIN_EXTEND_SUB_PREFIX
)
from database import db_manager
from features.profile_manager import QUESTIONNAIRE
from logger_config import get_logger
from . import localization as loc

logger = get_logger('markup_helpers')


def create_main_keyboard(lang_code: str, user_id: int) -> types.ReplyKeyboardMarkup:
    """Создает основную клавиатуру с кнопками команд на основе языка и ID пользователя."""
    markup = types.ReplyKeyboardMarkup(row_width=3, resize_keyboard=True)

    buttons = [
        types.KeyboardButton(loc.get_text('btn_dialogs', lang_code)),
        types.KeyboardButton(loc.get_text('btn_account', lang_code)),
        types.KeyboardButton(loc.get_text('btn_usage', lang_code)),
        types.KeyboardButton(loc.get_text('btn_settings', lang_code)),
        types.KeyboardButton(loc.get_text('btn_translate', lang_code)),
        types.KeyboardButton(loc.get_text('btn_history', lang_code)),
        types.KeyboardButton(loc.get_text('btn_help', lang_code)),
        types.KeyboardButton(loc.get_text('btn_reset', lang_code)),
    ]

    if user_id == ADMIN_USER_ID:
        admin_button = types.KeyboardButton(loc.get_text('btn_admin_panel', lang_code))
        buttons.insert(0, admin_button)

    markup.add(*buttons)
    return markup


async def create_dialogs_menu_keyboard(user_id: int) -> types.InlineKeyboardMarkup:
    """Создает клавиатуру для управления диалогами."""
    markup = types.InlineKeyboardMarkup(row_width=3)
    lang_code = await db_manager.get_user_language(user_id)
    dialogs = await db_manager.get_user_dialogs(user_id)
    active_dialog_id = await db_manager.get_active_dialog_id(user_id)

    for dialog in dialogs:
        is_active = dialog['dialog_id'] == active_dialog_id
        button_text = f"✅ {dialog['name']}" if is_active else dialog['name']
        callback_data = CALLBACK_IGNORE if is_active else f"{CALLBACK_DIALOG_SWITCH_PREFIX}{dialog['dialog_id']}"
        dialog_button = types.InlineKeyboardButton(button_text, callback_data=callback_data)
        rename_button = types.InlineKeyboardButton("✏️", callback_data=f"{CALLBACK_DIALOG_RENAME_PREFIX}{dialog['dialog_id']}")
        if not is_active:
            delete_button = types.InlineKeyboardButton("❌", callback_data=f"{CALLBACK_DIALOG_DELETE_PREFIX}{dialog['dialog_id']}")
            markup.row(dialog_button, rename_button, delete_button)
        else:
            markup.row(dialog_button, rename_button)

    markup.add(types.InlineKeyboardButton(
        "➕ " + loc.get_text('btn_create_dialog', lang_code),
        callback_data=CALLBACK_DIALOG_CREATE
    ))
    return markup

def create_confirm_delete_keyboard(dialog_id: int, lang_code: str) -> types.InlineKeyboardMarkup:
    """Создает клавиатуру для подтверждения удаления диалога."""
    markup = types.InlineKeyboardMarkup(row_width=2)
    confirm_button = types.InlineKeyboardButton(
        loc.get_text('btn_confirm_delete', lang_code),
        callback_data=f"{CALLBACK_DIALOG_CONFIRM_DELETE_PREFIX}{dialog_id}"
    )
    cancel_button = types.InlineKeyboardButton(
        loc.get_text('btn_cancel_delete', lang_code),
        callback_data=CALLBACK_DIALOGS_MENU
    )
    markup.add(confirm_button, cancel_button)
    return markup

def create_profile_view_keyboard(lang_code: str) -> types.InlineKeyboardMarkup:
    """Создает клавиатуру для режима просмотра профиля с одной кнопкой 'Редактировать'."""
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton(
        text=loc.get_text('btn_enter_edit_mode', lang_code),
        callback_data=settings.CALLBACK_PROFILE_SHOW_EDIT_OPTIONS
    ))
    return markup

def create_profile_edit_menu_keyboard(lang_code: str) -> types.InlineKeyboardMarkup:
    """Создает клавиатуру для режима редактирования профиля с кнопками для каждого поля."""
    markup = types.InlineKeyboardMarkup(row_width=2)
    buttons = []
    
    # QUESTIONNAIRE импортируется из profile_manager, убедитесь, что импорт есть вверху файла.
    # Если его нет, добавьте: from features.profile_manager import QUESTIONNAIRE
    for key in QUESTIONNAIRE.keys():
        field_name = loc.get_text(f'profile_label_{key}', lang_code)
        button_text = f"✏️ {field_name}"
        callback_data = f"{settings.CALLBACK_PROFILE_EDIT_PREFIX}{key}"
        buttons.append(types.InlineKeyboardButton(text=button_text, callback_data=callback_data))

    for i in range(0, len(buttons), 2):
        markup.add(*buttons[i:i + 2])
        
    markup.add(types.InlineKeyboardButton(
        text=loc.get_text('btn_back_to_profile_view', lang_code),
        callback_data=settings.CALLBACK_PROFILE_BACK_TO_VIEW
    ))
    return markup

def create_language_selection_keyboard() -> types.InlineKeyboardMarkup:
    """Создает inline-клавиатуру для выбора языка для ПЕРЕВОДА."""
    markup = types.InlineKeyboardMarkup(row_width=3)
    buttons = []
    sorted_languages = sorted(TRANSLATE_LANGUAGES.items(), key=lambda item: item[1])

    for lang_code, lang_name in sorted_languages:
        buttons.append(types.InlineKeyboardButton(lang_name, callback_data=f"{CALLBACK_LANG_PREFIX}{lang_code}"))

    for i in range(0, len(buttons), 3):
        markup.add(*buttons[i:i+3])
    return markup


async def create_settings_keyboard(user_id: int) -> types.InlineKeyboardMarkup:
    """Создает inline-клавиатуру настроек, включая стиль, язык и API ключ."""
    markup = types.InlineKeyboardMarkup(row_width=1)
    current_style = await db_manager.get_user_bot_style(user_id)
    current_lang = await db_manager.get_user_language(user_id)

    # --- Секция API и Модели ---
    markup.add(types.InlineKeyboardButton(loc.get_text('settings_api_key_section', current_lang), callback_data=CALLBACK_IGNORE))
    markup.add(types.InlineKeyboardButton(
        loc.get_text('settings_btn_set_api_key', current_lang),
        callback_data=CALLBACK_SETTINGS_SET_API_KEY
    ))
    markup.add(types.InlineKeyboardButton(loc.get_text('settings_model_section', current_lang), callback_data=CALLBACK_IGNORE))
    markup.add(types.InlineKeyboardButton(
        loc.get_text('settings_btn_choose_model', current_lang),
        callback_data=CALLBACK_SETTINGS_CHOOSE_MODEL_MENU
    ))

    # --- Секция Персонализации ---
    markup.add(types.InlineKeyboardButton(loc.get_text('settings_persona_section', current_lang), callback_data=CALLBACK_IGNORE))
    markup.add(types.InlineKeyboardButton(
        loc.get_text('settings_btn_choose_persona', current_lang),
        callback_data=CALLBACK_SETTINGS_PERSONA_MENU
    ))
    markup.add(types.InlineKeyboardButton(loc.get_text('settings_style_section', current_lang), callback_data=CALLBACK_IGNORE))
    style_buttons = []
    for style_code, style_name in BOT_STYLES.items():
        button_text = f"✅ {style_name}" if style_code == current_style else style_name
        style_buttons.append(types.InlineKeyboardButton(button_text, callback_data=f'{CALLBACK_SETTINGS_STYLE_PREFIX}{style_code}'))

    style_rows = [style_buttons[i:i + 2] for i in range(0, len(style_buttons), 2)]
    for row in style_rows:
        markup.add(*row)

    # --- Секция Языка и Данных (НОВОЕ) ---
    markup.add(types.InlineKeyboardButton("---", callback_data=CALLBACK_IGNORE))
    markup.add(types.InlineKeyboardButton(
        loc.get_text('settings_btn_data_management', current_lang),
        callback_data=CALLBACK_DATA_MANAGEMENT_MENU
    ))

    markup.add(types.InlineKeyboardButton(loc.get_text('settings_language_section', current_lang), callback_data=CALLBACK_IGNORE))
    lang_buttons = [
        types.InlineKeyboardButton(f"{'✅ ' if current_lang == 'ru' else ''}🇷🇺 Русский", callback_data=f"{CALLBACK_SETTINGS_LANG_PREFIX}ru"),
        types.InlineKeyboardButton(f"{'✅ ' if current_lang == 'en' else ''}🇺🇸 English", callback_data=f"{CALLBACK_SETTINGS_LANG_PREFIX}en")
    ]
    markup.add(*lang_buttons)

    # --- Секция поддержки ---
    if DONATION_URL:
        markup.add(types.InlineKeyboardButton(
            loc.get_text('btn_support', current_lang),
            url=DONATION_URL
        ))
    return markup


async def create_persona_selection_keyboard(user_id: int) -> types.InlineKeyboardMarkup:
    """Создает клавиатуру для выбора персоны."""
    markup = types.InlineKeyboardMarkup(row_width=2)
    lang_code = await db_manager.get_user_language(user_id)
    current_persona_id = await db_manager.get_user_persona(user_id)
    buttons = []
    for persona_id, persona_data in BOT_PERSONAS.items():
        persona_name = persona_data.get(f"name_{lang_code}", persona_data["name_ru"])
        button_text = f"✅ {persona_name}" if persona_id == current_persona_id else persona_name
        buttons.append(types.InlineKeyboardButton(
            text=button_text,
            callback_data=f"{CALLBACK_SETTINGS_PERSONA_PREFIX}{persona_id}"
        ))

    for i in range(0, len(buttons), 2):
        markup.add(*buttons[i:i + 2])

    markup.add(types.InlineKeyboardButton(
        loc.get_text('btn_back_to_settings', lang_code),
        callback_data=CALLBACK_SETTINGS_BACK_TO_MAIN
    ))
    return markup


def create_model_selection_keyboard(models: List[Dict[str, str]], current_model: Optional[str], lang_code: str) -> types.InlineKeyboardMarkup:
    """Создает клавиатуру для выбора модели Gemini."""
    markup = types.InlineKeyboardMarkup(row_width=1)
    for model in models:
        model_id = model['name']
        display_name = model['display_name']
        text = f"✅ {display_name}" if model_id == current_model else display_name
        markup.add(types.InlineKeyboardButton(
            text,
            callback_data=f"{CALLBACK_SETTINGS_MODEL_PREFIX}{model_id}"
        ))
    markup.add(types.InlineKeyboardButton(
        loc.get_text('btn_back_to_settings', lang_code),
        callback_data=CALLBACK_SETTINGS_BACK_TO_MAIN
    ))
    return markup


def create_calendar_keyboard(year: Optional[int] = None, month: Optional[int] = None) -> types.InlineKeyboardMarkup:
    """Создает inline-клавиатуру с календарем для выбора даты истории."""
    now = datetime.datetime.now()
    year = year or now.year
    month = month or now.month
    markup = types.InlineKeyboardMarkup(row_width=7)
    try:
        month_name = datetime.date(year, month, 1).strftime("%B %Y")
    except ValueError:
        year, month = now.year, now.month
        month_name = datetime.date(year, month, 1).strftime("%B %Y")
    markup.row(types.InlineKeyboardButton(month_name, callback_data=CALLBACK_IGNORE))
    days_of_week = ["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"]
    markup.row(*[types.InlineKeyboardButton(day, callback_data=CALLBACK_IGNORE) for day in days_of_week])
    try:
        first_day_of_month = datetime.date(year, month, 1)
        if month == 12:
            last_day_of_month_day = 31
        else:
            last_day_of_month_day = (datetime.date(year, month + 1, 1) - datetime.timedelta(days=1)).day
        row_buttons = [types.InlineKeyboardButton(" ", callback_data=CALLBACK_IGNORE)] * first_day_of_month.weekday()
        for day_num in range(1, last_day_of_month_day + 1):
            current_date = datetime.date(year, month, day_num)
            callback_value = f"{CALLBACK_CALENDAR_DATE_PREFIX}{current_date.strftime('%Y-%m-%d')}"
            row_buttons.append(types.InlineKeyboardButton(str(day_num), callback_data=callback_value))
            if len(row_buttons) == 7:
                markup.row(*row_buttons)
                row_buttons = []
        if row_buttons:
            row_buttons.extend([types.InlineKeyboardButton(" ", callback_data=CALLBACK_IGNORE)] * (7 - len(row_buttons)))
            markup.row(*row_buttons)
    except ValueError as date_err:
        logger.error(f"Ошибка генерации дней календаря для {year}-{month}: {date_err}")
    prev_month_date = first_day_of_month - datetime.timedelta(days=1)
    if month == 12:
        next_month_date = datetime.date(year + 1, 1, 1)
    else:
        next_month_date = datetime.date(year, month + 1, 1)
    nav_buttons = [
        types.InlineKeyboardButton("⬅️", callback_data=f"{CALLBACK_CALENDAR_MONTH_PREFIX}{prev_month_date.year}-{prev_month_date.month}"),
        types.InlineKeyboardButton(" ", callback_data=CALLBACK_IGNORE),
        types.InlineKeyboardButton("➡️", callback_data=f"{CALLBACK_CALENDAR_MONTH_PREFIX}{next_month_date.year}-{next_month_date.month}")
    ]
    markup.row(*nav_buttons)
    return markup


def create_error_report_button() -> types.InlineKeyboardMarkup:
    """Создает inline-клавиатуру с кнопкой 'Сообщить об ошибке'."""
    markup = types.InlineKeyboardMarkup()
    btn_report_error = types.InlineKeyboardButton('🆘 Сообщить об ошибке / Report Error', callback_data=CALLBACK_REPORT_ERROR)
    markup.add(btn_report_error)
    return markup

def create_support_button_markup(lang_code: str) -> Optional[types.InlineKeyboardMarkup]:
    """
    Создает inline-клавиатуру с кнопкой "Поддержать", если DONATION_URL настроен.
    """
    if not DONATION_URL:
        return None
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton(
        loc.get_text('btn_support', lang_code),
        url=DONATION_URL
    ))
    return markup

# --- Функции для админ-панели ---

async def create_admin_main_menu_keyboard(lang_code: str) -> types.InlineKeyboardMarkup:
    """Создает главное меню админ-панели."""
    markup = types.InlineKeyboardMarkup(row_width=2)
    stats_btn = types.InlineKeyboardButton(
        loc.get_text('admin.btn_stats', lang_code),
        callback_data=CALLBACK_ADMIN_STATS_MENU
    )
    comm_btn = types.InlineKeyboardButton(
        loc.get_text('admin.btn_communication', lang_code),
        callback_data=CALLBACK_ADMIN_COMMUNICATION_MENU
    )
    user_mgmt_btn = types.InlineKeyboardButton(
        loc.get_text('admin.btn_user_management', lang_code),
        callback_data=CALLBACK_ADMIN_USER_MANAGEMENT_MENU
    )
    maintenance_btn = types.InlineKeyboardButton(
        loc.get_text('admin.btn_maintenance', lang_code),
        callback_data=CALLBACK_ADMIN_MAINTENANCE_MENU
    )
    # Новая кнопка экспорта
    export_btn = types.InlineKeyboardButton(
        loc.get_text('admin.btn_export_users', lang_code),
        callback_data=CALLBACK_ADMIN_EXPORT_USERS # Используем новую константу
    )
    markup.add(stats_btn, comm_btn)
    markup.add(user_mgmt_btn, maintenance_btn)
    markup.add(export_btn)
    return markup


async def create_maintenance_menu_keyboard(lang_code: str) -> types.InlineKeyboardMarkup:
    """Создает клавиатуру для управления режимом обслуживания."""
    markup = types.InlineKeyboardMarkup(row_width=1)
    maintenance_mode_str = await db_manager.get_app_setting('maintenance_mode')
    is_on = maintenance_mode_str == 'true'

    status_text = loc.get_text('admin.maintenance_status_on', lang_code) if is_on else loc.get_text('admin.maintenance_status_off', lang_code)
    markup.add(types.InlineKeyboardButton(status_text, callback_data=CALLBACK_IGNORE))

    if is_on:
        toggle_btn = types.InlineKeyboardButton(
            loc.get_text('admin.btn_maintenance_disable', lang_code),
            callback_data=f"{CALLBACK_ADMIN_TOGGLE_MAINTENANCE}:off"
        )
    else:
        toggle_btn = types.InlineKeyboardButton(
            loc.get_text('admin.btn_maintenance_enable', lang_code),
            callback_data=f"{CALLBACK_ADMIN_TOGGLE_MAINTENANCE}:on"
        )
    markup.add(toggle_btn)

    markup.add(types.InlineKeyboardButton(
        loc.get_text('admin.btn_back_to_admin_menu', lang_code),
        callback_data=CALLBACK_ADMIN_MAIN_MENU
    ))
    return markup


async def create_communication_menu_keyboard(lang_code: str) -> types.InlineKeyboardMarkup:
    """Создает меню для раздела 'Коммуникация'."""
    markup = types.InlineKeyboardMarkup(row_width=1)
    broadcast_btn = types.InlineKeyboardButton(
        loc.get_text('admin.btn_broadcast', lang_code),
        callback_data=CALLBACK_ADMIN_BROADCAST
    )
    reply_btn = types.InlineKeyboardButton(
        loc.get_text('admin.btn_reply_to_user', lang_code),
        callback_data='admin_reply_to_user' # Используем callback из settings.py
    )
    back_btn = types.InlineKeyboardButton(
        loc.get_text('admin.btn_back_to_admin_menu', lang_code),
        callback_data=CALLBACK_ADMIN_MAIN_MENU
    )
    markup.add(broadcast_btn, reply_btn, back_btn)
    return markup

def create_broadcast_confirmation_keyboard(lang_code: str) -> types.InlineKeyboardMarkup:
    """Создает клавиатуру для подтверждения рассылки."""
    markup = types.InlineKeyboardMarkup(row_width=2)
    confirm_btn = types.InlineKeyboardButton(
        loc.get_text('admin.btn_confirm_broadcast', lang_code),
        callback_data=CALLBACK_ADMIN_CONFIRM_BROADCAST
    )
    cancel_btn = types.InlineKeyboardButton(
        loc.get_text('admin.btn_cancel_broadcast', lang_code),
        callback_data=CALLBACK_ADMIN_CANCEL_BROADCAST
    )
    markup.add(confirm_btn, cancel_btn)
    return markup

def create_user_management_keyboard(user_to_manage_id: int, is_blocked: bool, lang_code: str) -> types.InlineKeyboardMarkup:
    """Создает клавиатуру для управления конкретным пользователем."""
    markup = types.InlineKeyboardMarkup(row_width=1)
    
    # Кнопка блокировки/разблокировки
    if is_blocked:
        block_text = loc.get_text('admin.btn_unblock_user', lang_code)
        block_callback = f"{CALLBACK_ADMIN_TOGGLE_BLOCK_PREFIX}{user_to_manage_id}"
    else:
        block_text = loc.get_text('admin.btn_block_user', lang_code)
        block_callback = f"{CALLBACK_ADMIN_TOGGLE_BLOCK_PREFIX}{user_to_manage_id}"
    block_btn = types.InlineKeyboardButton(block_text, callback_data=block_callback)
    
    # Кнопка сброса API ключа
    reset_key_btn = types.InlineKeyboardButton(
        loc.get_text('admin.btn_reset_user_api_key', lang_code),
        callback_data=f"{CALLBACK_ADMIN_RESET_API_KEY_PREFIX}{user_to_manage_id}"
    )

    # --- НОВАЯ КНОПКА: Продление подписки ---
    extend_sub_btn = types.InlineKeyboardButton(
        loc.get_text('admin.btn_extend_subscription', lang_code),
        callback_data=f"{CALLBACK_ADMIN_EXTEND_SUB_PREFIX}{user_to_manage_id}"
    )
    
    # Кнопка назад
    back_btn = types.InlineKeyboardButton(
        loc.get_text('admin.btn_back_to_admin_menu', lang_code),
        callback_data=CALLBACK_ADMIN_MAIN_MENU
    )
    
    markup.add(block_btn, reset_key_btn, extend_sub_btn, back_btn)
    return markup

def create_extend_subscription_keyboard(user_id: int, lang_code: str) -> types.InlineKeyboardMarkup:
    """Создает клавиатуру для выбора срока продления подписки."""
    markup = types.InlineKeyboardMarkup(row_width=1)
    
    days_options = [30, 90, 365]
    for days in days_options:
        button_text = loc.get_text(f'admin.btn_days_{days}', lang_code)
        callback_data = f"{settings.CALLBACK_ADMIN_EXTEND_SUB_DAYS_PREFIX}{user_id}:{days}"
        markup.add(types.InlineKeyboardButton(text=button_text, callback_data=callback_data))
        
    # Добавляем кнопку "Назад" к информации о пользователе
    # Это создаст ощущение "вложенного" меню
    markup.add(types.InlineKeyboardButton(
        "⬅️ " + loc.get_text('admin.user_info_title', lang_code),
        callback_data=f"admin_back_to_user_info:{user_id}"
    ))
    return markup

def create_panic_password_setup_keyboard(lang_code: str) -> types.InlineKeyboardMarkup:
    """Создает клавиатуру для предложения установить пароль паники."""
    markup = types.InlineKeyboardMarkup(row_width=2)
    yes_btn = types.InlineKeyboardButton("✅ " + loc.get_text('btn_confirm_delete', lang_code).split(',')[0], callback_data=CALLBACK_PANIC_SETUP_YES)
    no_btn = types.InlineKeyboardButton("❌ " + loc.get_text('btn_cancel_delete', lang_code).split(',')[1].strip(), callback_data=CALLBACK_PANIC_SETUP_NO)
    markup.add(yes_btn, no_btn)
    return markup


def create_data_management_keyboard(lang_code: str) -> types.InlineKeyboardMarkup:
    """Создает клавиатуру для меню 'Управление данными'."""
    markup = types.InlineKeyboardMarkup(row_width=1)
    archive_btn = types.InlineKeyboardButton(
        loc.get_text('btn_archive_memory', lang_code),
        callback_data=CALLBACK_ARCHIVE_MEMORY_START
    )
    clear_btn = types.InlineKeyboardButton(
        loc.get_text('btn_clear_data', lang_code),
        callback_data=CALLBACK_CLEAR_DATA_START
    )
    back_btn = types.InlineKeyboardButton(
        loc.get_text('btn_back_to_settings', lang_code),
        callback_data=CALLBACK_SETTINGS_BACK_TO_MAIN
    )
    markup.add(archive_btn, clear_btn, back_btn)
    return markup


def create_confirm_clear_data_keyboard(lang_code: str) -> types.InlineKeyboardMarkup:
    """Создает клавиатуру для подтверждения полной очистки данных."""
    markup = types.InlineKeyboardMarkup(row_width=2)
    confirm_btn = types.InlineKeyboardButton(
        loc.get_text('btn_confirm_clear', lang_code),
        callback_data=CALLBACK_CLEAR_DATA_CONFIRM
    )
    cancel_btn = types.InlineKeyboardButton(
        loc.get_text('btn_cancel_clear', lang_code),
        callback_data=CALLBACK_CLEAR_DATA_CANCEL
    )
    markup.add(confirm_btn, cancel_btn)
    return markup