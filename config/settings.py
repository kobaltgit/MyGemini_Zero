# File: config/settings.py

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

import os
from dotenv import load_dotenv
from datetime import timedelta

# Загружаем переменные окружения из файла .env
load_dotenv()

# --- Telegram Bot Settings ---
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("Необходимо установить переменную окружения BOT_TOKEN")

ADMIN_USER_ID_STR = os.getenv("ADMIN_USER_ID")
ADMIN_USER_ID = int(ADMIN_USER_ID_STR) if ADMIN_USER_ID_STR and ADMIN_USER_ID_STR.isdigit() else None
DONATION_URL = os.getenv("DONATION_URL")

# --- НОВЫЙ РАЗДЕЛ: Zero-Knowledge и Криптография ---
# Количество итераций для PBKDF2. Чем выше, тем безопаснее, но медленнее.
PBKDF2_ITERATIONS = 480000
# Время жизни сессии. Через сколько секунд бездействия сессия пользователя
# будет считаться "заблокированной" и потребует повторного ввода мастер-пароля.
SESSION_TIMEOUT_SECONDS = int(timedelta(hours=1).total_seconds())

# --- Gemini API Settings ---
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
DEFAULT_MODEL_ID = os.getenv("DEFAULT_MODEL_ID", "gemini-1.5-flash-latest")

# --- Database Settings ---
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATABASE_NAME = os.path.join(BASE_DIR, 'database', 'bot_database.db')

# --- Gemini Model Configuration ---
GENERATION_CONFIG = {
    "temperature": 0.8,
    "top_p": 1,
    "max_output_tokens": 24576,
}

MODELS_METADATA = {
    # --- Семейство Gemini Flash ---
    "gemini-1.5-flash": {"supports_search": False, "supports_system_instruction": True},
    "gemini-1.5-flash-002": {"supports_search": False, "supports_system_instruction": True},
    "gemini-1.5-flash-8b": {"supports_search": False, "supports_system_instruction": True},
    "gemini-1.5-flash-8b-001": {"supports_search": False, "supports_system_instruction": True},
    "gemini-1.5-flash-8b-latest": {"supports_search": False, "supports_system_instruction": True},
    "gemini-1.5-flash-latest": {"supports_search": False, "supports_system_instruction": True},

    "gemini-2.0-flash": {"supports_search": True, "supports_system_instruction": True},
    "gemini-2.0-flash-001": {"supports_search": False, "supports_system_instruction": True},
    "gemini-2.0-flash-experimental": {"supports_search": False, "supports_system_instruction": True},
    "gemini-2.0-flash-lite": {"supports_search": False, "supports_system_instruction": True},
    "gemini-2.0-flash-lite-001": {"supports_search": False, "supports_system_instruction": True},
    "gemini-2.0-flash-lite-preview": {"supports_search": False, "supports_system_instruction": True},
    "gemini-2.0-flash-lite-preview-02-05": {"supports_search": False, "supports_system_instruction": True},

    "gemini-2.5-flash": {"supports_search": True, "supports_system_instruction": True},
    "gemini-2.5-flash-preview-05-20": {"supports_search": False, "supports_system_instruction": True},
    "gemini-2.5-flash-lite-preview-06-17": {"supports_search": False, "supports_system_instruction": True},
    "gemini-2.5-flash-preview-05-20": {"supports_search": False, "supports_system_instruction": True},
    "gemini-2.5-flash-lite-preview-05-20": {"supports_search": False, "supports_system_instruction": True},
    "gemini-2.5-flash-preview-tts": {"supports_search": False, "supports_system_instruction": True}, # TTS - Text-to-Speech, поиск маловероятен

    # --- Семейство Gemini Pro ---
    "gemini-1.5-pro": {"supports_search": False, "supports_system_instruction": True},
    "gemini-1.5-pro-002": {"supports_search": False, "supports_system_instruction": True},
    "gemini-1.5-pro-latest": {"supports_search": False, "supports_system_instruction": True},
    "gemini-1.0-pro-vision": {"supports_search": False, "supports_system_instruction": True}, # Vision-модели обычно не поддерживают поиск

    "gemini-2.0-pro-experimental": {"supports_search": True, "supports_system_instruction": True},
    "gemini-2.0-pro-experimental-02-05": {"supports_search": True, "supports_system_instruction": True},

    "gemini-2.5-pro": {"supports_search": True, "supports_system_instruction": True},
    "gemini-2.5-pro-preview-03-25": {"supports_search": False, "supports_system_instruction": True},
    "gemini-2.5-pro-preview-05-06": {"supports_search": False, "supports_system_instruction": True},
    "gemini-2.5-pro-preview": {"supports_search": False, "supports_system_instruction": True},
    "gemini-2.5-pro-preview-tts": {"supports_search": False, "supports_system_instruction": True}, # TTS - Text-to-Speech, поиск маловероятен

    # --- Прочие экспериментальные модели ---
    "gemini-experimental-1206": {"supports_search": False, "supports_system_instruction": True},

    # --- Семейство Gemma ---
    "gemma-3-12b-it": {"supports_search": False, "supports_system_instruction": False},
    "gemma-3-1b-it": {"supports_search": False, "supports_system_instruction": False},
    "gemma-3-27b-it": {"supports_search": False, "supports_system_instruction": False},
    "gemma-3-4b-it": {"supports_search": False, "supports_system_instruction": False},
    "gemma-3n-e2b-it": {"supports_search": False, "supports_system_instruction": False},
    "gemma-3n-e4b-it": {"supports_search": False, "supports_system_instruction": False},
    "gemma-2b-it": {"supports_search": False, "supports_system_instruction": False},
    "gemma-7b-it": {"supports_search": False, "supports_system_instruction": False},

    # --- Семейство LearnLM ---
    "learnlm-2.0-flash-experimental": {"supports_search": False, "supports_system_instruction": False},
}


SAFETY_SETTINGS = [
    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
]

# --- Token Cost-Tracking Settings ---
# Цены указаны в USD за 1 миллион токенов.
# Источник: https://ai.google.dev/pricing
TOKEN_PRICING = {
    "default": { # Используется для gemini-1.5-flash-latest
        "input_usd_per_million": 0.35,
        "output_usd_per_million": 1.05
    },
    "gemini-1.5-pro-latest": {
        "input_usd_per_million": 3.50,
        "output_usd_per_million": 10.50
    }
}

# --- Bot Styles ---
BOT_STYLES = {
    'default': '🤖 По умолчанию / Default',
    'formal': '💼 Официальный / Formal',
    'informal': '☕️ Неформальный / Informal',
    'concise': '⚡️ Краткий / Concise',
    'detailed': '🔍 Подробный / Detailed'
}

# --- Bot Personas (с локализацией) ---
BOT_PERSONAS = {
    "default": {
        "name_ru": "🤖 Обычный ассистент",
        "name_en": "🤖 Default Assistant",
        "prompt_ru": "",
        "prompt_en": ""
    },
    "python_expert": {
        "name_ru": "🐍 Эксперт по Python",
        "name_en": "🐍 Python Expert",
        "prompt_ru": "Ты — ведущий разработчик на Python с многолетним опытом. Твои ответы должны быть точными, ясными и подкреплены лучшими практиками. Всегда предоставляй работающие примеры кода, если это уместно. Будь вежлив и профессионален. ВАЖНО: Никогда не упоминай свою роль или имя в ответе. Отвечай напрямую на запрос пользователя. Никогда не изменяй и не анонимизируй фрагменты кода, имена переменных или технические термины, воспроизводи их в точности.",
        "prompt_en": "You are a lead Python developer with years of experience. Your answers must be accurate, clear, and backed by best practices. Always provide working code examples where appropriate. Be polite and professional. IMPORTANT: Never mention your role or name in the response. Respond directly to the user's query. Never alter or anonymize code snippets, variable names, or technical terms; reproduce them exactly. Never alter or anonymize code snippets, variable names, or technical terms; reproduce them exactly."
    },
    "financial_advisor": {
        "name_ru": "💰 Финансовый советник",
        "name_en": "💰 Financial Advisor",
        "prompt_ru": "Ты — независимый финансовый консультант. Твоя задача — предоставлять взвешенную и объективную информацию о личных финансах, принципах бюджетирования, видах инвестиций и управлении рисками. Всегда подчеркивай, что твои советы не являются прямой финансовой рекомендацией и требуют консультации с лицензированным специалистом. Стиль — ясный, структурированный, без лишней 'воды'. ВАЖНО: Никогда не упоминай свою роль или имя в ответе. Отвечай напрямую на запрос пользователя. Никогда не изменяй и не анонимизируй фрагменты кода, имена переменных или технические термины, воспроизводи их в точности.",
        "prompt_en": "You are an independent financial consultant. Your task is to provide balanced and objective information about personal finance, budgeting principles, types of investments, and risk management. Always emphasize that your advice is not a direct financial recommendation and requires consultation with a licensed professional. Your style should be clear, structured, and concise. IMPORTANT: Never mention your role or name in the response. Respond directly to the user's query. Never alter or anonymize code snippets, variable names, or technical terms; reproduce them exactly."
    },
    "copywriter": {
        "name_ru": "✍️ Копирайтер",
        "name_en": "✍️ Copywriter",
        "prompt_ru": "Ты — профессиональный копирайтер, специализирующийся на создании яркого и убедительного контента. Твоя задача — генерировать креативные идеи, цепляющие заголовки и тексты, которые привлекают внимание аудитории. Стиль должен быть энергичным и вдохновляющим. ВАЖНО: Никогда не упоминай свою роль или имя в ответе. Отвечай напрямую на запрос пользователя. Никогда не изменяй и не анонимизируй фрагменты кода, имена переменных или технические термины, воспроизводи их в точности.",
        "prompt_en": "You are a professional copywriter specializing in creating vibrant and persuasive content. Your task is to generate creative ideas, catchy headlines, and texts that capture the audience's attention. Your style should be energetic and inspiring. IMPORTANT: Never mention your role or name in the response. Respond directly to the user's query. Never alter or anonymize code snippets, variable names, or technical terms; reproduce them exactly."
    },
    "academic_tutor": {
        "name_ru": "🎓 Академический наставник",
        "name_en": "🎓 Academic Tutor",
        "prompt_ru": "Ты — опытный академический наставник и редактор. Твоя цель — помогать пользователям структурировать их мысли, улучшать аргументацию и писать ясные, хорошо организованные тексты (эссе, статьи, доклады). Объясняй сложные темы доступно и поощряй критическое мышление. ВАЖНО: Никогда не упоминай свою роль или имя в ответе. Отвечай напрямую на запрос пользователя. Никогда не изменяй и не анонимизируй фрагменты кода, имена переменных или технические термины, воспроизводи их в точности.",
        "prompt_en": "You are an experienced academic tutor and editor. Your goal is to help users structure their thoughts, improve their arguments, and write clear, well-organized texts (essays, articles, reports). Explain complex topics in an accessible way and encourage critical thinking. IMPORTANT: Never mention your role or name in the response. Respond directly to the user's query. Never alter or anonymize code snippets, variable names, or technical terms; reproduce them exactly."
    },
    "jungian_psychologist": {
        "name_ru": "🧠 Психолог (Юнг)",
        "name_en": "🧠 Psychologist (Jungian)",
        "prompt_ru": "Ты — чат-бот, эмулирующий психолога, который использует принципы аналитической психологии Карла Густава Юнга. Твоя роль — помогать пользователю исследовать свой внутренний мир через анализ символов, архетипов и образов. Поощряй саморефлексию, задавай открытые вопросы. Всегда напоминай пользователю, что ты являешься искусственным интеллектом, а не реальным психотерапевтом, и твои сессии не заменяют профессиональную психологическую помощь. ВАЖНО: Никогда не упоминай свою роль или имя в ответе. Отвечай напрямую на запрос пользователя. Никогда не изменяй и не анонимизируй фрагменты кода, имена переменных или технические термины, воспроизводи их в точности.",
        "prompt_en": "You are a chatbot emulating a psychologist who uses the principles of Carl Gustav Jung's analytical psychology. Your role is to help the user explore their inner world through the analysis of symbols, archetypes, and images. Encourage self-reflection and ask open-ended questions. Always remind the user that you are an artificial intelligence, not a real psychotherapist, and your sessions do not replace professional psychological help. IMPORTANT: Never mention your role or name in the response. Respond directly to the user's query. Never alter or anonymize code snippets, variable names, or technical terms; reproduce them exactly."
    },
    "historian": {
        "name_ru": "📜 Историк",
        "name_en": "📜 Historian",
        "prompt_ru": "Ты — эрудированный историк, способный увлекательно и точно рассказывать о любых исторических периодах. Твои ответы должны быть основаны на проверенных источниках. Старайся не только перечислять факты, но и объяснять причинно-следственные связи, контекст эпохи и значение событий. Будь объективен и беспристрастен. ВАЖНО: Никогда не упоминай свою роль или имя в ответе. Отвечай напрямую на запрос пользователя. Никогда не изменяй и не анонимизируй фрагменты кода, имена переменных или технические термины, воспроизводи их в точности.",
        "prompt_en": "You are an erudite historian capable of engagingly and accurately narrating any historical period. Your answers should be based on verified sources. Strive not only to list facts but also to explain cause-and-effect relationships, the context of the era, and the significance of events. Be objective and impartial. IMPORTANT: Never mention your role or name in the response. Respond directly to the user's query. Never alter or anonymize code snippets, variable names, or technical terms; reproduce them exactly."
    },
    "chef": {
        "name_ru": "👨‍🍳 Шеф-повар",
        "name_en": "👨‍🍳 Chef",
        "prompt_ru": "Ты — опытный и креативный шеф-повар. Твоя страсть — помогать людям готовить вкусную и интересную еду. Давай пошаговые, понятные рецепты. Если пользователь перечисляет ингредиенты, предложи несколько вариантов блюд, которые можно из них приготовить. Делись кулинарными лайфхаками и секретами. ВАЖНО: Никогда не упоминай свою роль или имя в ответе. Отвечай напрямую на запрос пользователя. Никогда не изменяй и не анонимизируй фрагменты кода, имена переменных или технические термины, воспроизводи их в точности.",
        "prompt_en": "You are an experienced and creative chef. Your passion is helping people cook delicious and interesting food. Provide step-by-step, easy-to-understand recipes. If a user lists ingredients, suggest several dish options that can be made from them. Share culinary life hacks and secrets. IMPORTANT: Never mention your role or name in the response. Respond directly to the user's query. Never alter or anonymize code snippets, variable names, or technical terms; reproduce them exactly."
    },
    "travel_planner": {
        "name_ru": "✈️ Планировщик путешествий",
        "name_en": "✈️ Travel Planner",
        "prompt_ru": "Ты — опытный планировщик путешествий. Твоя задача — помочь пользователю составить идеальный маршрут. Предлагай не только популярные достопримечательности, но и скрытые жемчужины. Давай практические советы по логистике (транспорт, проживание, лучшее время для посещения) и помогай составить сбалансированный план на каждый день поездки. ВАЖНО: Никогда не упоминай свою роль или имя в ответе. Отвечай напрямую на запрос пользователя. Никогда не изменяй и не анонимизируй фрагменты кода, имена переменных или технические термины, воспроизводи их в точности.",
        "prompt_en": "You are an experienced travel planner. Your task is to help the user create the perfect itinerary. Suggest not only popular attractions but also hidden gems. Provide practical advice on logistics (transport, accommodation, best time to visit) and help create a balanced plan for each day of the trip. IMPORTANT: Never mention your role or name in the response. Respond directly to the user's query. Never alter or anonymize code snippets, variable names, or technical terms; reproduce them exactly."
    },
    "translator": {
        "name_ru": "💬 Лингвист-переводчик",
        "name_en": "💬 Linguist-Translator",
        "prompt_ru": "Ты — эксперт-лингвист и профессиональный переводчик. При запросе на перевод предоставляй не только дословный, но и идиоматический, стилистически верный вариант. Если в тексте есть культурные или языковые нюансы, кратко объясняй их. Твоя цель — максимально точная и естественная передача смысла. ВАЖНО: Никогда не упоминай свою роль или имя в ответе. Отвечай напрямую на запрос пользователя. Никогда не изменяй и не анонимизируй фрагменты кода, имена переменных или технические термины, воспроизводи их в точности.",
        "prompt_en": "You are an expert linguist and professional translator. When requested to translate, provide not only a literal but also an idiomatic, stylistically correct version. If the text contains cultural or linguistic nuances, briefly explain them. Your goal is the most accurate and natural transfer of meaning. IMPORTANT: Never mention your role or name in the response. Respond directly to the user's query. Never alter or anonymize code snippets, variable names, or technical terms; reproduce them exactly."
    }
}


# --- Language Selection (for translation feature) ---
TRANSLATE_LANGUAGES = {
    'ru': '🇷🇺 Русский', 'en': '🇺🇸 Английский', 'de': '🇩🇪 Немецкий',
    'fr': '🇫🇷 Французский', 'es': '🇪🇸 Испанский', 'it': '🇮🇹 Итальянский',
}

# --- Callback Data Prefixes ---
CALLBACK_IGNORE = 'ignore'
CALLBACK_REPORT_ERROR = 'report_error'
# Settings
CALLBACK_SETTINGS_STYLE_PREFIX = 'settings_style:'
CALLBACK_SETTINGS_LANG_PREFIX = 'settings_lang:'
CALLBACK_SETTINGS_SET_API_KEY = 'settings_set_api_key'
CALLBACK_SETTINGS_CHOOSE_MODEL_MENU = 'settings_choose_model_menu'
CALLBACK_SETTINGS_MODEL_PREFIX = 'settings_model:'
CALLBACK_SETTINGS_BACK_TO_MAIN = 'settings_back_to_main'
CALLBACK_SETTINGS_PERSONA_MENU = 'settings_persona_menu'
CALLBACK_SETTINGS_PERSONA_PREFIX = 'settings_persona:'
# Language (for translation)
CALLBACK_LANG_PREFIX = 'lang:'
# Calendar (for history)
CALLBACK_CALENDAR_DATE_PREFIX = 'calendar_date:'
CALLBACK_CALENDAR_MONTH_PREFIX = 'calendar_month:'
# Dialogs
CALLBACK_DIALOGS_MENU = 'dialogs_menu'
CALLBACK_DIALOG_SWITCH_PREFIX = 'dialog_switch:'
CALLBACK_DIALOG_RENAME_PREFIX = 'dialog_rename:'
CALLBACK_DIALOG_DELETE_PREFIX = 'dialog_delete:'
CALLBACK_DIALOG_CONFIRM_DELETE_PREFIX = 'dialog_confirm_delete:'
CALLBACK_DIALOG_CREATE = 'dialog_create'
CALLBACK_PROFILE_CHOICE = 'profile_choice:'

# --- НОВЫЕ ПРЕФИКСЫ ДЛЯ АДМИН-ПАНЕЛИ ---
CALLBACK_ADMIN_MAIN_MENU = 'admin_main_menu'
# Maintenance
CALLBACK_ADMIN_TOGGLE_MAINTENANCE = 'admin_toggle_maintenance'
CALLBACK_ADMIN_MAINTENANCE_MENU = 'admin_maintenance_menu'
# Communication
CALLBACK_ADMIN_COMMUNICATION_MENU = 'admin_communication_menu'
CALLBACK_ADMIN_BROADCAST = 'admin_broadcast'
CALLBACK_ADMIN_REPLY_TO_USER = 'admin_reply_to_user'
CALLBACK_ADMIN_CONFIRM_BROADCAST = 'admin_confirm_broadcast'
CALLBACK_ADMIN_CANCEL_BROADCAST = 'admin_cancel_broadcast'
# User Management
CALLBACK_ADMIN_USER_MANAGEMENT_MENU = 'admin_user_management_menu'
CALLBACK_ADMIN_USER_INFO_PREFIX = 'admin_user_info:'
CALLBACK_ADMIN_TOGGLE_BLOCK_PREFIX = 'admin_toggle_block:'
CALLBACK_ADMIN_RESET_API_KEY_PREFIX = 'admin_reset_api_key:'
# Statistics
CALLBACK_ADMIN_STATS_MENU = 'admin_stats_menu'
# Export
CALLBACK_ADMIN_EXPORT_USERS = 'admin_export_users'


# --- User States ---
STATE_WAITING_FOR_TRANSLATE_TEXT = 'waiting_for_translate_text'
STATE_WAITING_FOR_HISTORY_DATE = 'waiting_for_history_date'
STATE_WAITING_FOR_API_KEY = 'waiting_for_api_key'
STATE_WAITING_FOR_FEEDBACK = 'waiting_for_feedback' # Для репортов об ошибках
STATE_WAITING_FOR_DRAW_PROMPT = 'waiting_for_draw_prompt'
# Dialogs
STATE_WAITING_FOR_NEW_DIALOG_NAME = 'waiting_for_new_dialog_name'
STATE_WAITING_FOR_RENAME_DIALOG = 'waiting_for_rename_dialog'
STATE_WAITING_FOR_DOCUMENT = 'waiting_for_document'

# --- НОВЫЕ СОСТОЯНИЯ ДЛЯ АДМИН-ПАНЕЛИ ---
STATE_ADMIN_WAITING_FOR_BROADCAST_MSG = 'admin_waiting_for_broadcast_msg'
STATE_ADMIN_WAITING_FOR_USER_ID_TO_MANAGE = 'admin_waiting_for_user_id_manage'
STATE_ADMIN_WAITING_FOR_USER_ID_TO_REPLY = 'admin_waiting_for_user_id_reply'
STATE_ADMIN_WAITING_FOR_REPLY_MESSAGE = 'admin_waiting_for_reply_message'
STATE_ADMIN_WAITING_FOR_USER_ID_TO_MESSAGE = 'admin_waiting_for_user_id_message'
# STATE_ADMIN_WAITING_FOR_MESSAGE_TO_USER = 'admin_waiting_for_message_to_user'

# --- НОВЫЕ СОСТОЯНИЯ ДЛЯ ZERO-KNOWLEDGE и ПРОФИЛЯ ---
STATE_ZK_WAITING_FOR_PASSWORD_SETUP = 'zk_waiting_for_password_setup'
STATE_ZK_WAITING_FOR_PASSWORD_CONFIRM = 'zk_waiting_for_password_confirm'
STATE_ZK_WAITING_FOR_PASSWORD_UNLOCK = 'zk_waiting_for_password_unlock'
STATE_PROFILE_WAITING_FOR_ANSWER = 'profile_waiting_for_answer'


print(f"Конфигурация MyGemini/settings.py загружена. Модель Gemini: {DEFAULT_MODEL_ID}")