# File: utils/localization.py

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

from typing import Dict

# Словарь со всеми текстами. Ключ - язык, значение - словарь с текстами.
LOCALIZATION: Dict[str, Dict[str, str]] = {
    'ru': {

        # --- НОВЫЙ РАЗДЕЛ: Мета-инструкция для модели ---
        'bot_meta_instruction': "Ты — продвинутый ИИ-ассистент, интегрированный в Telegram-бота. Ты можешь получать от пользователя текст, изображения, голосовые сообщения и файлы (.txt, .md). Если пользователь говорит, что отправил файл, но ты его не видишь в текущем сообщении, это значит, что файл уже был обработан системой и добавлен в твою долговременную память. Никогда не отрицай свою способность получать файлы или изображения. Твои знания всегда актуальны, и ты можешь искать информацию в интернете.",

        # --- НОВЫЙ РАЗДЕЛ: Zero-Knowledge & Пароль ---
        'zk_setup_prompt': "🔐 **Создание хранилища**\n\nЗдравствуйте! Я ваш персональный ИИ-ассистент с приватной памятью. Для защиты ваших данных, пожалуйста, создайте **мастер-пароль**. Он будет ключом ко всей вашей истории.",
        'zk_warning': "🔐 **ОЧЕНЬ ВАЖНО: Прочтите перед подтверждением**\n\nВы ввели свой мастер-пароль. Прежде чем мы его сохраним, вы должны понять главный принцип безопасности этого бота.\n\n❗️ **Если вы забудете этот пароль, восстановить доступ к вашим данным будет НЕВОЗМОЖНО.**\n\nВсе ваши диалоги и заметки будут утеряны навсегда. У нас нет и не будет функции \"Сбросить пароль\".\n\n---\n\n*Почему так? (Это не ошибка, а гарантия вашей приватности)*\n\nПредставьте, что ваш пароль — это единственный существующий ключ от вашего личного цифрового сейфа.\n1. Мы не храним ваш пароль, а только его зашифрованный \"отпечаток\" (хеш).\n2. Ключ для расшифровки данных создается на лету из вашего пароля и исчезает после окончания сессии.\n3. Нет пароля = Нет ключа.\n\nЭто осознанный компромисс: **максимальная приватность в обмен на вашу личную ответственность за сохранность пароля.**\n\nПожалуйста, запишите ваш пароль и храните его в надежном месте. Для подтверждения, что вы прочитали и поняли это предупреждение, **введите ваш мастер-пароль еще раз.**",
        'zk_confirm_prompt': "Отлично. А теперь, для подтверждения, введите этот же пароль еще раз.",
        'zk_password_mismatch': "❌ Пароли не совпадают. Пожалуйста, попробуйте создать пароль заново.",
        'zk_setup_success': "✅ Пароль успешно установлен! Ваше зашифрованное хранилище создано.",
        'zk_unlock_prompt': "🔐 **Сессия заблокирована**\n\nДля продолжения работы, пожалуйста, введите ваш мастер-пароль, чтобы разблокировать доступ к вашей памяти.",
        'zk_unlock_fail': "❌ Неверный пароль. Попробуйте еще раз.",
        'zk_unlock_success': "✅ Память успешно разблокирована!",
        'zk_user_is_locked': "Ваша сессия заблокирована. Пожалуйста, введите мастер-пароль для продолжения.",

        # --- НОВЫЙ РАЗДЕЛ: Анкета профиля ---
        'profile_start': "👋 **Давайте познакомимся!**\n\nЯ ваш персональный ИИ-ассистент. Чтобы наше общение было максимально продуктивным, я могу запомнить ключевую информацию о вас. Это как ввести в курс дел нового сотрудника.\n\n🔒 *Напоминаю: вся эта информация будет зашифрована вашим мастер-паролем и сохранится в вашей персональной памяти.*\n\nВы можете пропустить любой вопрос, просто отправив «-» или команду `/skip`.",
        'profile_q_role': "**1/8. Ваша роль или профессия?**\n*Например: разработчик, менеджер проектов, студент, предприниматель.*",
        'profile_q_industry': "**2/8. Ваша сфера деятельности или индустрия?**\n*Например: IT, финансы, образование, ритейл.*",
        'profile_q_projects': "**3/8. Над какими ключевыми проектами или задачами вы сейчас работаете?**\n*Опишите 1-3 главных направления. Например: \"Запускаю новый сайт\", \"Пишу диссертацию\", \"Разрабатываю мобильное приложение\".*",
        'profile_q_stack': "**4/8. Какие технологии, инструменты или методологии вы чаще всего используете?**\n*Например: Python, Figma, Agile, Notion.*",
        'profile_q_purpose': "**5/8. Для чего, в первую очередь, вы планируете меня использовать?**",
        'profile_q_style': "**6/8. Какой стиль общения вы предпочитаете?**",
        'profile_q_hobby': "**7/8. Чем вы увлекаетесь в свободное время? Какие у вас хобби?**\n*Например: шахматы, путешествия, научная фантастика.*",
        'profile_q_rules': "**8/8. Есть ли темы, которые мне следует избегать, или \"золотое правило\", которое я всегда должен соблюдать?**\n*Например: \"Никогда не давать финансовых советов\", \"Всегда предлагать несколько вариантов\".*",
        'profile_end': "✅ **Отлично, настройка завершена!**\n\nЯ сохранил эту информацию в вашу персональную память. Вы всегда можете просмотреть и изменить этот профиль с помощью команды `/profile`.\n\n**Давайте попробуем! Задайте мне любой вопрос.**",
        
        # --- НОВЫЙ РАЗДЕЛ: Кнопки для анкеты ---
        'profile_btn_purpose_work': "Помощь в работе",
        'profile_btn_purpose_learn': "Обучение",
        'profile_btn_purpose_creative': "Творчество и идеи",
        'profile_btn_purpose_organize': "Организация информации",
        'profile_btn_style_friendly': "Дружелюбный",
        'profile_btn_style_formal': "Деловой и формальный",
        'profile_btn_style_concise': "Краткий, по существу",
        'profile_btn_style_detailed': "Подробный, с деталями",    

        # --- Приветствие и Помощь ---
        'welcome': "👋 Привет, *{name}*! Я твой личный ассистент на базе Gemini.\n\n"
           "Для начала работы мне понадобится твой Google AI API ключ. "
           "Если ты не знаешь, что это и как его получить, воспользуйся новой подробной командой: /apikey_info\n\n"
           "✅ После установки ключа через /set_api_key ты сможешь полноценно общаться со мной.\n\n"
           "Используй /help_guide, чтобы увидеть полный список моих возможностей.",
        'cmd_help_text': "🆘 *Краткая справка по командам*\n\n"
                 "*/start* - Перезапустить бота.\n"
                 "*/reset* - Сбросить контекст текущего диалога.\n"
                 "*/set_api_key* - Установить или обновить API ключ.\n"
                 "*/settings* - Открыть меню настроек.\n"
                 "*/dialogs* - Управление диалогами.\n"
                 "*/history* - Посмотреть историю сообщений.\n"
                 "*/usage* - Статистика расходов токенов.\n\n"
                 "➡️ Используй /help_guide для получения **полного руководства** по всем функциям.\n"
                 "🔑 Используй /apikey_info для получения инструкции по **созданию API ключа**.",
        # --- Настройки ---
        'settings_title': "⚙️ *Настройки бота*",
        'settings_style_section': "--- Стиль общения бота ---",
        'settings_language_section': "--- Язык интерфейса ---",
        'settings_api_key_section': "--- Управление API ключом ---",
        'settings_btn_set_api_key': "🔑 Установить/обновить API ключ",
        'settings_model_section': "--- Нейросетевая модель ---",
        'settings_btn_choose_model': "🧠 Выбрать модель",
        'settings_persona_section': "--- Роль ассистента (Персона) ---",
        'settings_btn_choose_persona': "🎭 Выбрать персону",
        'style_changed_notice': "Стиль общения изменен. Контекст диалога сброшен.",
        'persona_changed_notice': "✅ Персона изменена на *{persona_name}*. Контекст диалога сброшен.",
        # --- Выбор модели ---
        'model_selection_title': "🧠 *Выбор модели Gemini*",
        'model_selection_loading': "⏳ Загружаю список доступных моделей...",
        'model_selection_error': "❌ Не удалось загрузить список моделей. Проверьте ваш API ключ или попробуйте позже.",
        'model_changed_notice': "✅ Модель изменена на *{model_name}*. Контекст диалога сброшен.",
        'btn_back_to_settings': "⬅️ Назад в настройки",
        # --- Выбор персоны ---
        'persona_selection_title': "🎭 *Выбор персоны ассистента*",
        'persona_selection_desc': "Выберите роль, которую бот будет отыгрывать. Это изменит его стиль общения и экспертизу. Текущие *стили* (краткий, подробный и т.д.) будут игнорироваться.",
        # --- Управление диалогами ---
        'dialogs_menu_title': "🗂️ *Управление диалогами*",
        'dialogs_menu_desc': "Здесь вы можете создавать новые диалоги, переключаться между ними, переименовывать и удалять. Активный диалог отмечен ✅.",
        'btn_create_dialog': "➕ Создать новый",
        'btn_rename_dialog': "✏️ Переименовать",
        'btn_delete_dialog': "❌ Удалить",
        'btn_back_to_main_menu': "⬅️ Главное меню",
        'dialog_enter_new_name_prompt': "Введите название для нового диалога:",
        'dialog_created_success': "✅ Диалог *{name}* создан и установлен как активный. Контекст сброшен.",
        'dialog_switched_success': "✅ Активный диалог изменен на *{name}*. Контекст восстановлен.",
        'dialog_deleted_success': "🗑️ Диалог *{name}* удален. Активным установлен другой диалог.",
        'dialog_deleted_last_success': "🗑️ Диалог *{name}* удален. Создан новый 'Основной диалог' и сделан активным.",
        'dialog_enter_rename_prompt': "Введите новое название для диалога *{name}*:",
        'dialog_renamed_success': "✅ Диалог переименован в *{new_name}*.",
        'dialog_delete_confirmation': "Вы уверены, что хотите удалить диалог *{name}*? Это действие необратимо.",
        'btn_confirm_delete': "Да, удалить",
        'btn_cancel_delete': "Нет, отмена",
        'dialog_name_too_long': "Название диалога слишком длинное. Пожалуйста, введите название до 50 символов.",
        'dialog_name_invalid': "Название диалога не может быть пустым.",
        'dialog_error_delete_active': "Нельзя удалить активный диалог. Сначала переключитесь на другой.",
        # --- Команды и Состояния ---
        'cmd_reset_success': "✅ Контекст текущего диалога сброшен.",
        # --- НОВЫЙ РАЗДЕЛ: Долговременная память ---
        'memory_prompt_file': "📄 **Запомнить документ**\n\nОтправьте мне файл в формате `.txt` или `.md`, и я добавлю его содержимое в долговременную память **текущего диалога** (`{dialog_name}`).\n\nМаксимальный размер файла: 1 МБ.",
        'memory_file_processing': "⏳ Обрабатываю и запоминаю файл...",
        'memory_file_success': "✅ Файл `{file_name}` успешно добавлен в память диалога `{dialog_name}`.",
        'memory_file_error_type': "❌ Неверный формат. Пожалуйста, отправьте файл `.txt` или `.md`.",
        'memory_file_error_size': "❌ Файл слишком большой. Максимальный размер — 1 МБ.",
        'memory_file_error_read': "❌ Не удалось прочитать содержимое файла. Убедитесь, что он в кодировке UTF-8.",
        'memory_file_error_general': "❌ Произошла ошибка при обработке файла.",

        'set_api_key_prompt': "Пожалуйста, отправьте ваш Google AI API ключ. Сообщение с ключом будет удалено.",
        'history_prompt': "🗓️ Пожалуйста, выберите дату для просмотра истории текущего диалога:",
        'translate_prompt': "Выберите язык, на который нужно перевести текст:",
        'language_selected_notice': "Язык выбран: {lang_name}.",
        'send_text_to_translate_prompt': "Теперь отправьте мне текст, который нужно перевести на {lang_name}.",
        # --- Обработка API ключа ---
        'api_key_verifying': "Проверяю ключ...",
        'api_key_success': "✅ Ключ успешно установлен и зашифрован! Теперь вы можете общаться со мной.",
        'api_key_invalid': "❌ Этот ключ недействителен. Пожалуйста, проверьте его и попробуйте снова.",
        'api_key_needed_for_chat': "Для общения со мной нужен API ключ. Пожалуйста, установите его с помощью команды /set_api_key.",
        'api_key_needed_for_vision': "Для анализа изображений нужен API ключ. Пожалуйста, установите его с помощью команды /set_api_key.",
        'api_key_needed_for_feature': "Для использования этой функции нужен API ключ. Пожалуйста, установите его через /set_api_key.",
        # --- История ---
        'history_loading': "Загружаю историю...",
        'history_for_date': "История за",
        'history_role_user': "Вы",
        'history_role_bot': "Бот",
        'history_no_messages': "В этот день в данном диалоге сообщений не найдено.",
        'history_date_error': "Произошла ошибка при обработке даты. Попробуйте еще раз.",
        # --- Статистика расходов ---
        'usage_title': "📊 Статистика расходов токенов",
        'usage_today_header': "За сегодня:",
        'usage_month_header': "За текущий месяц:",
        'usage_prompt_tokens': "📥 Входящие (prompt)",
        'usage_completion_tokens': "📤 Исходящие (completion)",
        'usage_total_tokens': "∑ Всего",
        'usage_estimated_cost': "💰 Примерная стоимость",
        'usage_no_data': "Нет данных для отображения.",
        'usage_cost_notice': "\n Стоимость является приблизительной и рассчитывается на основе текущей модели и публичных тарифов Google. ",
        # --- Обратная связь ---
        'feedback_prompt': "Пожалуйста, скопируйте текст ошибки и вставьте в сообщение, опишите проблему или ваше предложение. Это сообщение будет отправлено администратору.",
        'feedback_sent': "✅ Спасибо! Ваше сообщение отправлено администратору.",

        'feedback_admin_notification': "⚠️ *Новое сообщение от пользователя\\!*\n\n*От:* `{user_id}` \\(@{username}\\)\n*Имя:* {first_name}\n\n*Сообщение:*\n{text}\n\n*Для ответа используйте команду:* `/reply {user_id}`",

        # --- Поддержка ---
        'support_prompt': "Если вам нравится бот и вы хотите поддержать его развитие, вы можете сделать небольшой донат:",
        # --- Ошибки ---
        'unsupported_content': "Я пока не умею обрабатывать такой тип контента.",
        'state_wrong_content_type': "Пожалуйста, отправьте текст для завершения текущего действия или нажмите /reset.",
        'translation_error_generic': "Не удалось выполнить перевод. Попробуйте еще раз.",
        # --- Ошибки Gemini API (понятные пользователю) ---
        'gemini_error_timeout': "⏳ *Сервер не ответил вовремя.*\nЭто может быть связано с большой нагрузкой на API Google или временными проблемами с сетью. Пожалуйста, повторите ваш запрос через несколько минут.",
        'gemini_error_api_key_invalid': "🚫 *Ошибка: Неверный API-ключ.*\nПожалуйста, проверьте правильность вашего ключа и установите его заново с помощью /set_api_key.",
        'gemini_error_api_key_invalid': "🚫 *Ошибка: Неверный API-ключ.*\nПожалуйста, проверьте правильность вашего ключа и установите его заново с помощью /set_api_key.",
        'gemini_error_permission_denied': "🚫 *Ошибка: Доступ запрещен.*\nУбедитесь, что ваш API-ключ активирован и имеет необходимые разрешения в Google AI Studio.",
        'gemini_error_quota_exceeded': "⏳ *Ошибка: Превышена квота.*\nВы исчерпали лимит запросов к API. Попробуйте позже или проверьте лимиты в вашей учетной записи Google.",
        'gemini_error_safety': "censored:censored_black_rectangle: *Ответ заблокирован.*\nСгенерированный ответ был заблокирован настройками безопасности Google. Попробуйте переформулировать запрос.",
        'gemini_error_unavailable': "🛠️ *Сервис временно недоступен.*\nСерверы Google могут быть перегружены. Пожалуйста, повторите попытку через несколько минут.",
        'gemini_error_invalid_argument': "🤔 *Ошибка: Некорректный запрос.*\nВозможно, вы пытаетесь отправить контент, который не поддерживается выбранной моделью (например, видео).",
        'gemini_error_unknown': "🤯 *Произошла неизвестная ошибка при обращении к API.*\nПожалуйста, попробуйте еще раз. Если ошибка повторяется, свяжитесь с администратором.",
        'user_is_blocked': "❌ Вы были заблокированы администратором.",
        'maintenance_mode_on': "🛠️ Бот временно находится на техническом обслуживании. Пожалуйста, попробуйте позже.",
        # --- Кнопки ---
        'btn_dialogs': "🗂️ Диалоги",
        'btn_translate': "🇷🇺 Перевести",
        'btn_history': "📜 История",
        'btn_account': "👤 Личный кабинет",
        'btn_settings': "⚙️ Настройки",
        'btn_help': "❓ Помощь",
        'btn_reset': "🔄 Сброс",
        'btn_usage': "📊 Расходы",
        'btn_admin_panel': "👑 Админ-панель",
        'btn_support': "❤️ Поддержать автора",
        # --- Секция админа ---
        'admin': {
            'panel_title': "👑 *Админ-панель*",
            'not_admin': "❌ У вас нет прав для выполнения этой команды.",
            # Меню
            'btn_stats': "📊 Статистика",
            'btn_communication': "📬 Коммуникация",
            'btn_user_management': "👤 Управление пользователями",
            'btn_maintenance': "🛠️ Режим обслуживания",
            'btn_export_users': "📥 Выгрузить пользователей",
            'btn_back_to_admin_menu': "⬅️ Назад в админ-панель",
            # Режим обслуживания
            'maintenance_menu_title': "🛠️ *Режим обслуживания*",
            'maintenance_status_on': "🟢 *Статус:* ВКЛЮЧЕН",
            'maintenance_status_off': "🔴 *Статус:* ВЫКЛЮЧЕН",
            'btn_maintenance_enable': "Включить",
            'btn_maintenance_disable': "Выключить",
            'maintenance_enabled_msg': "✅ Режим обслуживания ВКЛЮЧЕН. Только администратор может использовать бота.",
            'maintenance_disabled_msg': "✅ Режим обслуживания ВЫКЛЮЧЕН. Бот доступен всем пользователям.",
            # Статистика
            'stats_title': "📊 *Глобальная статистика бота*",
            'stats_total_users': "👥 Всего пользователей:",
            'stats_active_users': "🏃 Активных за 7 дней:",
            'stats_new_users': "🌱 Новых за 7 дней:",
            'stats_blocked_users': "🚫 Заблокированных:",
            # Управление пользователями
            'user_management_title': "👤 *Управление пользователями*",
            'user_management_prompt': "Введите User ID для получения информации:",
            'user_info_title': "ℹ️ *Информация о пользователе*",
            'user_info_id': "ID:",
            'user_info_lang': "Язык:",
            'user_info_reg_date': "Дата регистрации:",
            'user_info_messages': "Сообщений:",
            'user_info_status': "Статус:",
            'user_status_active': "Активен",
            'user_status_blocked': "Заблокирован",
            'btn_block_user': "🚫 Заблокировать",
            'btn_unblock_user': "✅ Разблокировать",
            'btn_reset_user_api_key': "🔑 Сбросить API ключ",
            'user_not_found': "❌ Пользователь с ID `{user_id}` не найден.",
            'user_blocked_success': "✅ Пользователь `{user_id}` заблокирован.",
            'user_unblocked_success': "✅ Пользователь `{user_id}` разблокирован.",
            'user_api_key_reset_success': "✅ API ключ для пользователя `{user_id}` сброшен.",
            # Коммуникация
            'communication_title': "📬 *Коммуникация*",
            'btn_broadcast': "📢 Рассылка всем",
            'btn_reply_to_user': "✉️ Ответить пользователю",
            'reply_prompt_user_id': "Введите User ID пользователя, которому вы хотите отправить сообщение:",
            'reply_prompt_message': "Теперь введите сообщение для пользователя `{user_id}`:",
            'broadcast_prompt': "Отправьте сообщение, которое будет разослано всем пользователям. Для отмены введите /cancel.",
            'broadcast_confirm_prompt': "Вы собираетесь отправить следующее сообщение `{count}` пользователям. Вы уверены?\n\n---\n{message_text}\n---",
            'btn_confirm_broadcast': "Да, отправить",
            'btn_cancel_broadcast': "Отмена",
            'broadcast_started': "✅ Рассылка начата...",
            'broadcast_cancelled': "❌ Рассылка отменена.",
            'broadcast_finished': "✅ Рассылка завершена. Отправлено: {sent}. Не удалось: {failed}.",
            'reply_to_user_prompt': "Ответить пользователю `{user_id}`:",
            'reply_sent_success': "✅ Сообщение отправлено пользователю `{user_id}`.",
            'reply_sent_fail': "❌ Не удалось отправить сообщение. Возможно, пользователь заблокировал бота.",
            'reply_admin_notification': "✉️ *Сообщение от администратора:*\n\n`{text}`"
        }
    },
    'en': {

        # --- NEW SECTION: Bot Meta-Instruction ---
        'bot_meta_instruction': "You are an advanced AI assistant integrated into a Telegram bot. You can receive text, images, voice messages, and files (.txt, .md) from the user. If the user mentions sending a file that you don't see in the current message, it means the file has already been processed by the system and added to your long-term memory. Never deny your ability to receive files or images. Your knowledge is always up-to-date, and you can search the internet.",

        # --- NEW SECTION: Zero-Knowledge & Password ---
        'zk_setup_prompt': "🔐 **Create Your Vault**\n\nHello! I am your personal AI assistant with a private memory. To protect your data, please create a **master password**. It will be the key to all your history.",
        'zk_warning': "🔐 **VERY IMPORTANT: Read Before Confirming**\n\nYou have entered your master password. Before we save it, you must understand the core security principle of this bot.\n\n❗️ **If you forget this password, it will be IMPOSSIBLE to recover your data.**\n\nAll your dialogues and notes will be lost forever. We do not have and will not have a \"Reset Password\" feature.\n\n---\n\n*Why? (This is not a bug, but a guarantee of your privacy)*\n\nImagine your password is the only existing key to your personal digital vault.\n1. We do not store your password, only its encrypted \"fingerprint\" (hash).\n2. The decryption key is generated on-the-fly from your password and disappears after the session ends.\n3. No password = No key.\n\nThis is a deliberate trade-off: **maximum privacy in exchange for your personal responsibility for the password.**\n\nPlease write down your password and keep it in a safe place. To confirm that you have read and understood this warning, **please enter your master password again.**",
        'zk_confirm_prompt': "Great. Now, for confirmation, please enter the same password again.",
        'zk_password_mismatch': "❌ The passwords do not match. Please try creating a password again.",
        'zk_setup_success': "✅ Password successfully set! Your encrypted vault has been created.",
        'zk_unlock_prompt': "🔐 **Session Locked**\n\nTo continue, please enter your master password to unlock your memory.",
        'zk_unlock_fail': "❌ Incorrect password. Please try again.",
        'zk_unlock_success': "✅ Memory successfully unlocked!",
        'zk_user_is_locked': "Your session is locked. Please enter your master password to continue.",
        
        # --- NEW SECTION: Profile Questionnaire ---
        'profile_start': "👋 **Let's get acquainted!**\n\nI am your personal AI assistant. To make our communication as productive as possible, I can remember key information about you. It's like briefing a new employee.\n\n🔒 *Reminder: All this information will be encrypted with your master password and stored in your personal memory.*\n\nYou can skip any question by simply sending \"-\" or the `/skip` command.",
        'profile_q_role': "**1/8. What is your role or profession?**\n*E.g., developer, project manager, student, entrepreneur.*",
        'profile_q_industry': "**2/8. What is your field or industry?**\n*E.g., IT, finance, education, retail.*",
        'profile_q_projects': "**3/8. What key projects or tasks are you currently working on?**\n*Describe 1-3 main areas. E.g., \"Launching a new website,\" \"Writing a dissertation,\" \"Developing a mobile app.\"*",
        'profile_q_stack': "**4/8. What technologies, tools, or methodologies do you use most often?**\n*E.g., Python, Figma, Agile, Notion.*",
        'profile_q_purpose': "**5/8. What do you primarily plan to use me for?**",
        'profile_q_style': "**6/8. What communication style do you prefer?**",
        'profile_q_hobby': "**7/8. What are your hobbies or interests in your free time?**\n*E.g., chess, traveling, science fiction.*",
        'profile_q_rules': "**8/8. Are there any topics I should avoid, or a \"golden rule\" I should always follow?**\n*E.g., \"Never give financial advice,\" \"Always offer several options.\"*",
        'profile_end': "✅ **Great, setup is complete!**\n\nI have saved this information to your personal memory. You can always view and change this profile using the `/profile` command.\n\n**Let's give it a try! Ask me any question.**",
        
        # --- NEW SECTION: Buttons for questionnaire ---
        'profile_btn_purpose_work': "Help with work",
        'profile_btn_purpose_learn': "Learning",
        'profile_btn_purpose_creative': "Creativity & ideas",
        'profile_btn_purpose_organize': "Organizing information",
        'profile_btn_style_friendly': "Friendly",
        'profile_btn_style_formal': "Business & Formal",
        'profile_btn_style_concise': "Concise & to the point",
        'profile_btn_style_detailed': "Detailed & in-depth",

        # --- Welcome and Help ---
        'welcome': "👋 Hi, *{name}*! I'm your personal assistant powered by Gemini.\n\n"
           "To get started, I'll need your Google AI API key. "
           "If you don't know what it is or how to get it, use the new detailed command: /apikey_info\n\n"
           "✅ After setting the key via /set_api_key, you'll be able to chat with me.\n\n"
           "Use /help_guide to see a full list of my features.",
        'cmd_help_text': "🆘 *Quick Command Reference*\n\n"
                 "*/start* - Restart the bot.\n"
                 "*/reset* - Clear the current dialog context.\n"
                 "*/set_api_key* - Set or update your API key.\n"
                 "*/settings* - Open the settings menu.\n"
                 "*/dialogs* - Manage your dialogs.\n"
                 "*/history* - View message history.\n"
                 "*/usage* - Token usage statistics.\n\n"
                 "➡️ Use /help_guide for the **full user manual**.\n"
                 "🔑 Use /apikey_info for instructions on **creating an API key**.",
        # --- Settings ---
        'settings_title': "⚙️ *Bot Settings*",
        'settings_style_section': "--- Bot Communication Style ---",
        'settings_language_section': "--- Interface Language ---",
        'settings_api_key_section': "--- API Key Management ---",
        'settings_btn_set_api_key': "🔑 Set/Update API Key",
        'settings_model_section': "--- Neural Network Model ---",
        'settings_btn_choose_model': "🧠 Choose Model",
        'settings_persona_section': "--- Assistant's Role (Persona) ---",
        'settings_btn_choose_persona': "🎭 Choose Persona",
        'style_changed_notice': "Communication style changed. The conversation context has been reset.",
        'persona_changed_notice': "✅ Persona changed to *{persona_name}*. The conversation context has been reset.",
        # --- Model Selection ---
        'model_selection_title': "🧠 *Gemini Model Selection*",
        'model_selection_loading': "⏳ Loading list of available models...",
        'model_selection_error': "❌ Could not load the model list. Please check your API key or try again later.",
        'model_changed_notice': "✅ Model changed to *{model_name}*. The conversation context has been reset.",
        'btn_back_to_settings': "⬅️ Back to Settings",
        # --- Persona Selection ---
        'persona_selection_title': "🎭 *Assistant Persona Selection*",
        'persona_selection_desc': "Choose a role for the bot to play. This will change its communication style and expertise. Current *styles* (concise, detailed, etc.) will be ignored.",
        # --- Dialog Management ---
        'dialogs_menu_title': "🗂️ *Dialog Management*",
        'dialogs_menu_desc': "Here you can create new dialogs, switch between them, rename, and delete. The active dialog is marked with ✅.",
        'btn_create_dialog': "➕ Create New",
        'btn_rename_dialog': "✏️ Rename",
        'btn_delete_dialog': "❌ Delete",
        'btn_back_to_main_menu': "⬅️ Main Menu",
        'dialog_enter_new_name_prompt': "Enter a name for the new dialog:",
        'dialog_created_success': "✅ Dialog *{name}* created and set as active. Context has been reset.",
        'dialog_switched_success': "✅ Active dialog changed to *{name}*. Context has been restored.",
        'dialog_deleted_success': "🗑️ Dialog *{name}* has been deleted. Another dialog has been set as active.",
        'dialog_deleted_last_success': "🗑️ Dialog *{name}* has been deleted. A new 'General Chat' has been created and made active.",
        'dialog_enter_rename_prompt': "Enter a new name for the dialog *{name}*:",
        'dialog_renamed_success': "✅ Dialog renamed to *{new_name}*.",
        'dialog_delete_confirmation': "Are you sure you want to delete the dialog *{name}*? This action cannot be undone.",
        'btn_confirm_delete': "Yes, delete",
        'btn_cancel_delete': "No, cancel",
        'dialog_name_too_long': "The dialog name is too long. Please enter a name up to 50 characters.",
        'dialog_name_invalid': "The dialog name cannot be empty.",
        'dialog_error_delete_active': "You cannot delete the active dialog. Switch to another one first.",
        # --- Commands and States ---
        'cmd_reset_success': "✅ The context of the current dialog has been reset.",
        # --- NEW SECTION: Long-term Memory ---
        'memory_prompt_file': "📄 **Memorize Document**\n\nPlease send a `.txt` or `.md` file, and I will add its content to the long-term memory of the **current dialog** (`{dialog_name}`).\n\nMaximum file size: 1 MB.",
        'memory_file_processing': "⏳ Processing and memorizing the file...",
        'memory_file_success': "✅ File `{file_name}` has been successfully added to the memory of dialog `{dialog_name}`.",
        'memory_file_error_type': "❌ Invalid format. Please send a `.txt` or `.md` file.",
        'memory_file_error_size': "❌ The file is too large. The maximum size is 1 MB.",
        'memory_file_error_read': "❌ Could not read the file's content. Please ensure it is UTF-8 encoded.",
        'memory_file_error_general': "❌ An error occurred while processing the file.",

        'set_api_key_prompt': "Please send your Google AI API key. The message with the key will be deleted.",
        'history_prompt': "🗓️ Please select a date to view the history of the current dialog:",
        'translate_prompt': "Select the language to translate the text into:",
        'language_selected_notice': "Language selected: {lang_name}.",
        'send_text_to_translate_prompt': "Now send me the text to be translated into {lang_name}.",
        # --- API Key Handling ---
        'api_key_verifying': "Verifying key...",
        'api_key_success': "✅ Key successfully set and encrypted! You can now chat with me.",
        'api_key_invalid': "❌ This key is invalid. Please check it and try again.",
        'api_key_needed_for_chat': "To chat with me, an API key is required. Please set it using the /set_api_key command.",
        'api_key_needed_for_vision': "To analyze images, an API key is required. Please set it using the /set_api_key command.",
        'api_key_needed_for_feature': "To use this feature, an API key is required. Please set it via /set_api_key.",
        # --- History ---
        'history_loading': "Loading history...",
        'history_for_date': "History for",
        'history_role_user': "You",
        'history_role_bot': "Bot",
        'history_no_messages': "No messages found on this day in this dialog.",
        'history_date_error': "An error occurred while processing the date. Please try again.",
        # --- Usage Statistics ---
        'usage_title': "📊 *Token Usage Statistics*",
        'usage_today_header': "*For Today:*",
        'usage_month_header': "*For Current Month:*",
        'usage_prompt_tokens': "📥 Input (prompt)",
        'usage_completion_tokens': "📤 Output (completion)",
        'usage_total_tokens': "∑ Total",
        'usage_estimated_cost': "💰 Estimated Cost",
        'usage_no_data': "No data to display.",
        'usage_cost_notice': "\n_The cost is an estimate based on the current model and public Google tariffs._",
        # --- Feedback ---
        'feedback_prompt': "Please copy the error text and paste it into the message, then describe the problem or your suggestion. This message will be sent to the administrator.",
        'feedback_sent': "✅ Thank you! Your message has been sent to the administrator.",

        'feedback_admin_notification': "⚠️ *New message from a user\\!*\n\n*From:* `{user_id}` \\(@{username}\\)\n*Name:* {first_name}\n\n*Message:*\n{text}\n\n*To reply, use the command:* `/reply {user_id}`",
        
        # --- Support ---
        'support_prompt': "If you like the bot and wish to support its development, you can make a small donation:",
        # --- Errors ---
        'unsupported_content': "I don't know how to handle this type of content yet.",
        'state_wrong_content_type': "Please send text to complete the current action, or press /reset.",
        'translation_error_generic': "Failed to perform translation. Please try again.",
        # --- Gemini API Errors (User-Friendly) ---
        'gemini_error_timeout': "⏳ *Server did not respond in time.*\nThis might be due to a high load on the Google API or temporary network issues. Please try your request again in a few minutes.",
        'gemini_error_api_key_invalid': "🚫 *Error: Invalid API Key.*\nPlease check your key and set it again using /set_api_key.",
        'gemini_error_api_key_invalid': "🚫 *Error: Invalid API Key.*\nPlease check your key and set it again using /set_api_key.",
        'gemini_error_permission_denied': "🚫 *Error: Permission Denied.*\nEnsure your API key is activated and has permissions in Google AI Studio.",
        'gemini_error_quota_exceeded': "⏳ *Error: Quota Exceeded.*\nYou have exhausted your API request limit. Try again later or check your Google account limits.",
        'gemini_error_safety': "censored:censored_black_rectangle: *Response Blocked.*\nThe generated response was blocked by Google's safety settings. Try rephrasing your request.",
        'gemini_error_unavailable': "🛠️ *Service Temporarily Unavailable.*\nGoogle's servers might be overloaded. Please try again in a few minutes.",
        'gemini_error_invalid_argument': "🤔 *Error: Invalid Request.*\nYou might be trying to send content not supported by the model (e.g., a video).",
        'gemini_error_unknown': "🤯 *An unknown API error occurred.*\nPlease try again. If the error persists, contact the administrator.",
        'user_is_blocked': "❌ You have been blocked by the administrator.",
        'maintenance_mode_on': "🛠️ The bot is temporarily in maintenance mode. Please try again later.",
        # --- Buttons ---
        'btn_dialogs': "🗂️ Dialogs",
        'btn_translate': "🇬🇧 Translate",
        'btn_history': "📜 History",
        'btn_account': "👤 My Account",
        'btn_settings': "⚙️ Settings",
        'btn_help': "❓ Help",
        'btn_reset': "🔄 Reset",
        'btn_usage': "📊 Usage",
        'btn_admin_panel': "👑 Admin Panel",
        'btn_support': "❤️ Support the Author",
        # --- Admin Section ---
        'admin': {
            'panel_title': "👑 *Admin Panel*",
            'not_admin': "❌ You do not have permission to execute this command.",
            # Menu
            'btn_stats': "📊 Statistics",
            'btn_communication': "📬 Communication",
            'btn_user_management': "👤 User Management",
            'btn_maintenance': "🛠️ Maintenance Mode",
            'btn_export_users': "📥 Export Users",
            'btn_back_to_admin_menu': "⬅️ Back to Admin Panel",
            # Maintenance Mode
            'maintenance_menu_title': "🛠️ *Maintenance Mode*",
            'maintenance_status_on': "🟢 *Status:* ENABLED",
            'maintenance_status_off': "🔴 *Status:* DISABLED",
            'btn_maintenance_enable': "Enable",
            'btn_maintenance_disable': "Disable",
            'maintenance_enabled_msg': "✅ Maintenance mode is ENABLED. Only the admin can use the bot.",
            'maintenance_disabled_msg': "✅ Maintenance mode is DISABLED. The bot is available to all users.",
            # Statistics
            'stats_title': "📊 *Global Bot Statistics*",
            'stats_total_users': "👥 Total users:",
            'stats_active_users': "🏃 Active in last 7 days:",
            'stats_new_users': "🌱 New in last 7 days:",
            'stats_blocked_users': "🚫 Blocked users:",
            # User Management
            'user_management_title': "👤 *User Management*",
            'user_management_prompt': "Enter User ID for details:",
            'user_info_title': "ℹ️ *User Information*",
            'user_info_id': "ID:",
            'user_info_lang': "Language:",
            'user_info_reg_date': "Registration Date:",
            'user_info_messages': "Messages:",
            'user_info_status': "Status:",
            'user_status_active': "Active",
            'user_status_blocked': "Blocked",
            'btn_block_user': "🚫 Block",
            'btn_unblock_user': "✅ Unblock",
            'btn_reset_user_api_key': "🔑 Reset API Key",
            'user_not_found': "❌ User with ID `{user_id}` not found.",
            'user_blocked_success': "✅ User `{user_id}` has been blocked.",
            'user_unblocked_success': "✅ User `{user_id}` has been unblocked.",
            'user_api_key_reset_success': "✅ API key for user `{user_id}` has been reset.",
            # Communication
            'communication_title': "📬 *Communication*",
            'btn_broadcast': "📢 Broadcast to all",
            'btn_reply_to_user': "✉️ Reply to User",
            'reply_prompt_user_id': "Enter the User ID of the user you want to message:",
            'reply_prompt_message': "Now enter the message for user `{user_id}`:",
            'broadcast_prompt': "Send the message to be broadcast to all users. To cancel, type /cancel.",
            'broadcast_confirm_prompt': "You are about to send the following message to `{count}` users. Are you sure?\n\n---\n{message_text}\n---",
            'btn_confirm_broadcast': "Yes, send",
            'btn_cancel_broadcast': "Cancel",
            'broadcast_started': "✅ Broadcast initiated...",
            'broadcast_cancelled': "❌ Broadcast cancelled.",
            'broadcast_finished': "✅ Broadcast finished. Sent: {sent}. Failed: {failed}.",
            'reply_to_user_prompt': "Reply to user `{user_id}`:",
            'reply_sent_success': "✅ Message sent to user `{user_id}`.",
            'reply_sent_fail': "❌ Failed to send message. The user may have blocked the bot.",
            'reply_admin_notification': "✉️ *Message from the administrator:*\n\n`{text}`"
        }
    }
}

DEFAULT_LANG = 'ru'


def get_text(key: str, lang_code: str) -> str:
    """
    Возвращает текст по ключу для указанного языка.
    Если ключ или язык не найден, возвращает ключ в виде строки.
    Поддерживает вложенные ключи (например, 'admin.panel_title').
    """
    lang_dict = LOCALIZATION.get(lang_code)
    if lang_dict is None:
        lang_dict = LOCALIZATION.get(DEFAULT_LANG, {})
    
    # Обработка вложенных ключей
    keys = key.split('.')
    value = lang_dict
    try:
        for k in keys:
            value = value[k]
        if isinstance(value, str):
            return value
        else:
            # Если по ключу лежит словарь, а не строка
            return key
    except KeyError:
        # Пытаемся найти в словаре по умолчанию
        default_dict = LOCALIZATION.get(DEFAULT_LANG, {})
        value = default_dict
        try:
            for k in keys:
                value = value[k]
            if isinstance(value, str):
                return value
        except (KeyError, TypeError):
            return key # Возвращаем сам ключ, если ничего не найдено
    except TypeError:
        # Если пытаемся получить ключ от не-словаря
        return key

    return key