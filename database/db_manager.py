# File: MyGemini_Zero/database/db_manager.py

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
Модуль для асинхронного управления реляционной базой данных SQLite.

Отвечает за все CRUD-операции с пользователями, диалогами и историей сообщений.
Ключевые особенности в архитектуре Zero-Knowledge:
- Хранит хеш мастер-пароля и соль пользователя, но никогда не сам пароль.
- Принимает готовый экземпляр Fernet для шифрования/дешифрования истории сообщений.
- Не имеет прямого доступа к расшифрованным данным, обеспечивая принцип "нулевого знания".
"""
import sqlite3
import asyncio
import datetime
import json
from typing import List, Tuple, Optional, Dict, Any
from services.vector_store_manager import VectorStoreManager
from cryptography.fernet import Fernet, InvalidToken

from logger_config import get_logger
from config.settings import DATABASE_NAME, DEFAULT_MODEL_ID
from utils import crypto_helpers
# from handlers import telegram_helpers as tg_helpers

db_logger = get_logger('database', user_id='System')
db_lock = asyncio.Lock()  # Используем asyncio.Lock для write-операций

# --- Внутренние функции подключения и выполнения ---

def _get_db_connection() -> sqlite3.Connection:
    """Устанавливает и настраивает соединение с базой данных SQLite."""
    try:
        conn = sqlite3.connect(DATABASE_NAME, check_same_thread=False, timeout=10.0,
                               detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.execute("PRAGMA journal_mode=WAL;")
        return conn
    except sqlite3.Error as e:
        db_logger.exception(f"Ошибка подключения к базе данных {DATABASE_NAME}: {e}")
        raise


def _execute_sync(query: str, params: tuple = (), fetch_one: bool = False, fetch_all: bool = False,
                  is_write_operation: bool = False) -> Optional[Any]:
    """(СИНХРОННАЯ) Выполняет SQL-запрос. Запускается в отдельном потоке."""
    conn = None
    result = None
    try:
        conn = _get_db_connection()
        if is_write_operation:
            conn.isolation_level = 'EXCLUSIVE'
            conn.execute('BEGIN EXCLUSIVE')

        cursor = conn.cursor()
        cursor.execute(query, params)

        if fetch_one:
            result = cursor.fetchone()
        elif fetch_all:
            result = cursor.fetchall()

        if is_write_operation:
            if query.strip().upper().startswith("INSERT"):
                result = cursor.lastrowid
            elif query.strip().upper().startswith(("UPDATE", "DELETE")):
                result = cursor.rowcount
            conn.commit()
        # Этот блок для простых агрегирующих запросов (возвращающих одно значение),
        # которые вызываются без fetch_one=True или fetch_all=True.
        elif not fetch_one and not fetch_all and ("count(" in query.lower() or "sum(" in query.lower()):
            aggregation_result = cursor.fetchone()
            # Возвращаем первое значение из кортежа или 0, если результат None
            result = aggregation_result[0] if aggregation_result and aggregation_result[0] is not None else 0

    except sqlite3.Error as e:
        db_logger.exception(f"Ошибка выполнения SQL: {query} | Params: {params} | Error: {e}")
        if conn and is_write_operation:
            conn.rollback()
        raise e
    finally:
        if conn:
            conn.close()
    return result

async def _execute_query(query: str, params: tuple = (), fetch_one: bool = False, fetch_all: bool = False,
                         is_write_operation: bool = False) -> Optional[Any]:
    """(АСИНХРОННАЯ) Выполняет SQL-запрос в отдельном потоке, чтобы не блокировать event loop."""
    try:
        if is_write_operation:
            async with db_lock:
                return await asyncio.to_thread(
                    _execute_sync, query, params, fetch_one, fetch_all, is_write_operation
                )
        else:
            return await asyncio.to_thread(
                _execute_sync, query, params, fetch_one, fetch_all, is_write_operation
            )
    except Exception as e:
        db_logger.error(f"Перехвачена ошибка из _execute_sync в _execute_query: {e}")
        if fetch_all: return []
        return None

# --- Инициализация и миграция БД ---

def setup_database_sync():
    """Синхронная функция для инициализации и миграции структуры базы данных."""
    conn = _get_db_connection()
    cursor = conn.cursor()
    try:
        # --- Таблица app_settings ---
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS app_settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        """)
        
        # --- Таблица users ---
        cursor.execute("PRAGMA table_info(users)")
        user_columns = {col['name'] for col in cursor.fetchall()}
        if not user_columns:
            db_logger.info("Таблица 'users' не найдена, создаем...")
            cursor.execute("""
            CREATE TABLE users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                language_code TEXT DEFAULT 'ru' NOT NULL,
                first_interaction_date TEXT,
                is_blocked INTEGER NOT NULL DEFAULT 0,
                active_dialog_id INTEGER REFERENCES dialogs(dialog_id) ON DELETE SET NULL,
                
                -- Поля из оригинального проекта
                bot_style TEXT DEFAULT 'default' NOT NULL,
                gemini_model TEXT,
                active_persona TEXT DEFAULT 'default' NOT NULL,
                
                -- Поля для Zero-Knowledge
                master_password_hash BLOB,
                encryption_salt BLOB,
                api_key BLOB,
                last_session_ts TEXT
            )""")
        else:
            # Логика миграции для добавления ВСЕХ недостающих колонок
            required_columns = {
                'bot_style': "TEXT DEFAULT 'default' NOT NULL",
                'gemini_model': 'TEXT',
                'active_persona': "TEXT DEFAULT 'default' NOT NULL",
                'master_password_hash': 'BLOB',
                'encryption_salt': 'BLOB',
                'api_key': 'BLOB',
                'last_session_ts': 'TEXT',
                'panic_password_hash': 'BLOB',
                'subscription_status': "TEXT DEFAULT 'none' NOT NULL", # 'none', 'active', 'expired'
                'subscription_end_date': 'TEXT'
            }
            missing_cols = required_columns.keys() - user_columns
            for col in missing_cols:
                col_type = required_columns[col]
                db_logger.info(f"Добавляем отсутствующий столбец '{col}' в 'users'...")
                cursor.execute(f"ALTER TABLE users ADD COLUMN {col} {col_type}")

        # --- Таблица dialogs ---
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS dialogs (
                dialog_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
            )""")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_dialogs_user ON dialogs (user_id)")

        # --- Таблица conversations ---
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                conversation_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                dialog_id INTEGER NOT NULL,
                timestamp TEXT NOT NULL,
                role TEXT NOT NULL CHECK(role IN ('user', 'bot')),
                message_text BLOB,
                prompt_tokens INTEGER NOT NULL DEFAULT 0,
                completion_tokens INTEGER NOT NULL DEFAULT 0,
                total_tokens INTEGER NOT NULL DEFAULT 0,
                FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
                FOREIGN KEY (dialog_id) REFERENCES dialogs(dialog_id) ON DELETE CASCADE
            )""")

        # --- Миграция для таблицы conversations ---
        cursor.execute("PRAGMA table_info(conversations)")
        conversation_columns = {col['name'] for col in cursor.fetchall()}

        if 'content_type' not in conversation_columns:
            db_logger.info("Добавляем отсутствующий столбец 'content_type' в 'conversations'...")
            cursor.execute("ALTER TABLE conversations ADD COLUMN content_type TEXT DEFAULT 'text' NOT NULL")

        conn.commit()
        db_logger.info("Проверка и настройка базы данных завершена.")
    except Exception as e:
        db_logger.exception(f"Критическая ошибка при настройке/миграции базы данных: {e}")
        if conn: conn.rollback()
        raise
    finally:
        if conn: conn.close()


async def set_user_api_key(user_id: int, api_key: str, fernet_instance: Fernet):
    """Шифрует и сохраняет API-ключ пользователя."""
    encrypted_key = crypto_helpers.encrypt_data(api_key, fernet_instance)
    query = "UPDATE users SET api_key = ? WHERE user_id = ?"
    await _execute_query(query, (encrypted_key, user_id), is_write_operation=True)
    db_logger.info(f"API-ключ для пользователя {user_id} был зашифрован и сохранен.")

async def get_user_api_key(user_id: int, fernet_instance: Fernet) -> Optional[str]:
    # ... (код без изменений)
    query = "SELECT api_key FROM users WHERE user_id = ?"
    result = await _execute_query(query, (user_id,), fetch_one=True)
    if result and result['api_key']:
        return crypto_helpers.decrypt_data(result['api_key'], fernet_instance)
    return None

async def is_api_key_set(user_id: int) -> bool:
    """Проверяет, установлен ли API-ключ, не расшифровывая его."""
    query = "SELECT api_key FROM users WHERE user_id = ?"
    result = await _execute_query(query, (user_id,), fetch_one=True)
    return result is not None and result['api_key'] is not None

async def setup_database():
    """Асинхронная обертка для запуска синхронной настройки БД в отдельном потоке."""
    await asyncio.to_thread(setup_database_sync)

# --- Управление пользователями и паролями (ZK) ---

async def add_or_update_user(user_id: int, username: Optional[str], first_name: Optional[str], last_name: Optional[str]) -> bool:
    """Добавляет нового пользователя или обновляет его данные. Создает диалог по умолчанию.

    Args:
        user_id: ID пользователя.
        username: Юзернейм пользователя.
        first_name: Имя пользователя.
        last_name: Фамилия пользователя.

    Returns:
        bool: True, если пользователь был новым, иначе False.
    """
    user_data = await _execute_query("SELECT user_id, active_dialog_id FROM users WHERE user_id = ?", (user_id,), fetch_one=True)
    is_new_user = False
    if not user_data:
        is_new_user = True
        db_logger.info(f"Добавляем нового пользователя {user_id} (@{username}).")
        today_date_str = datetime.date.today().strftime('%Y-%m-%d')
        query = "INSERT INTO users (user_id, username, first_name, last_name, first_interaction_date) VALUES (?, ?, ?, ?, ?)"
        params = (user_id, username, first_name, last_name, today_date_str)
        await _execute_query(query, params, is_write_operation=True)
        await create_dialog(user_id, "Основной диалог", set_active=True)
    else:
        query = "UPDATE users SET username = ?, first_name = ?, last_name = ? WHERE user_id = ?"
        params = (username, first_name, last_name, user_id)
        await _execute_query(query, params, is_write_operation=True)
        if not user_data['active_dialog_id']:
            db_logger.warning(f"У существующего пользователя {user_id} нет активного диалога. Создаем новый.")
            await create_dialog(user_id, "Основной диалог", set_active=True)
    return is_new_user

async def is_master_password_set(user_id: int) -> bool:
    """Проверяет, установил ли пользователь мастер-пароль."""
    query = "SELECT master_password_hash FROM users WHERE user_id = ?"
    result = await _execute_query(query, (user_id,), fetch_one=True)
    return result is not None and result['master_password_hash'] is not None


async def set_master_password(user_id: int, password: str):
    """Генерирует соль, хеширует пароль и сохраняет их для пользователя."""
    password_hash = crypto_helpers.hash_password(password)
    salt = crypto_helpers.generate_salt()
    query = "UPDATE users SET master_password_hash = ?, encryption_salt = ? WHERE user_id = ?"
    # ИСПРАВЛЕНИЕ: добавлен user_id в кортеж params
    params = (password_hash, salt, user_id)
    await _execute_query(query, params, is_write_operation=True)
    db_logger.info(f"Мастер-пароль и соль установлены для пользователя {user_id}.")


async def verify_master_password(user_id: int, provided_password: str) -> bool:
    """Проверяет предоставленный мастер-пароль."""
    query = "SELECT master_password_hash FROM users WHERE user_id = ?"
    result = await _execute_query(query, (user_id,), fetch_one=True)
    if not result or not result['master_password_hash']:
        return False
    stored_hash = result['master_password_hash']
    return crypto_helpers.verify_password(stored_hash, provided_password)


async def get_user_salt(user_id: int) -> Optional[bytes]:
    """Получает соль пользователя из БД для генерации ключа шифрования."""
    query = "SELECT encryption_salt FROM users WHERE user_id = ?"
    result = await _execute_query(query, (user_id,), fetch_one=True)
    return result['encryption_salt'] if result else None

# --- Управление сообщениями (с шифрованием) ---

async def store_message(user_id: int, dialog_id: int, role: str, message_text: str,
                        fernet_instance: Fernet, prompt_tokens: int = 0,
                        completion_tokens: int = 0, total_tokens: int = 0,
                        content_type: str = 'text'): # <--- ДОБАВЛЕН НОВЫЙ АРГУМЕНТ
    """
    Шифрует и сохраняет сообщение в базу данных.

    Args:
        user_id (int): ID пользователя.
        dialog_id (int): ID активного диалога.
        role (str): Роль отправителя ('user' или 'bot').
        message_text (str): Текст сообщения.
        fernet_instance (Fernet): Экземпляр Fernet, инициализированный ключом сессии.
        prompt_tokens (int): Количество токенов во входном запросе.
        completion_tokens (int): Количество токенов в сгенерированном ответе.
        total_tokens (int): Общее количество токенов.
        content_type (str): Тип содержимого сообщения (например, 'text', 'photo', 'voice', 'document').
    """
    if role not in ('user', 'bot'): return
    timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()

    encrypted_text = crypto_helpers.encrypt_data(message_text, fernet_instance)

    query = """
        INSERT INTO conversations 
        (user_id, dialog_id, timestamp, role, message_text, prompt_tokens, completion_tokens, total_tokens, content_type)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """
    params = (user_id, dialog_id, timestamp, role, encrypted_text, prompt_tokens, completion_tokens, total_tokens, content_type)
    await _execute_query(query, params, is_write_operation=True)



async def get_conversation_history(dialog_id: int, fernet_instance: Fernet, limit: int = 20) -> List[Dict[str, Any]]:
    """
    Получает и расшифровывает историю сообщений для конкретного диалога.

    Args:
        fernet_instance (Fernet): Экземпляр Fernet, инициализированный ключом сессии.
    
    Returns:
        Список словарей с расшифрованными сообщениями.
    """
    query = "SELECT role, message_text FROM conversations WHERE dialog_id = ? ORDER BY conversation_id DESC LIMIT ?"
    rows = await _execute_query(query, (dialog_id, limit), fetch_all=True)
    if not rows:
        return []

    decrypted_history = []
    for row in rows:
        decrypted_text = crypto_helpers.decrypt_data(row['message_text'], fernet_instance)
        if decrypted_text is None:
            db_logger.error(f"Не удалось расшифровать сообщение в dialog_id {dialog_id}. Возможно, неверный ключ сессии.")
            # Можно либо пропустить, либо добавить сообщение об ошибке
            decrypted_text = "[Ошибка расшифровки]"
        
        decrypted_history.append({'role': row['role'], 'message_text': decrypted_text})
    
    return list(reversed(decrypted_history))

async def get_conversation_history_by_date(dialog_id: int, selected_date: datetime.date, fernet_instance: Fernet) -> List[Dict[str, Any]]:
    """
    Получает и расшифровывает историю сообщений для конкретного диалога за указанную дату.

    Args:
        dialog_id: ID диалога.
        selected_date: Дата, за которую нужно получить историю.
        fernet_instance: Экземпляр Fernet для расшифровки.

    Returns:
        Список словарей с расшифрованными сообщениями, отсортированный по времени.
    """
    # Создаем временные рамки для запроса (от начала до конца указанного дня)
    start_of_day = datetime.datetime.combine(selected_date, datetime.time.min).replace(tzinfo=datetime.timezone.utc)
    end_of_day = datetime.datetime.combine(selected_date, datetime.time.max).replace(tzinfo=datetime.timezone.utc)
    
    # Конвертируем в ISO формат для сравнения с текстом в БД
    start_iso = start_of_day.isoformat()
    end_iso = end_of_day.isoformat()

    query = """
        SELECT role, message_text 
        FROM conversations 
        WHERE dialog_id = ? AND timestamp BETWEEN ? AND ?
        ORDER BY timestamp ASC
    """
    rows = await _execute_query(query, (dialog_id, start_iso, end_iso), fetch_all=True)
    if not rows:
        return []

    decrypted_history = []
    for row in rows:
        decrypted_text = crypto_helpers.decrypt_data(row['message_text'], fernet_instance)
        if decrypted_text is None:
            db_logger.error(f"Не удалось расшифровать сообщение в dialog_id {dialog_id}. Возможно, неверный ключ сессии.")
            decrypted_text = "[Ошибка расшифровки]"
        
        decrypted_history.append({'role': row['role'], 'message_text': decrypted_text})
    
    return decrypted_history


# =================================================================================
# === Остальные функции (метаданные), не требующие значительных изменений ===
# =================================================================================

async def create_dialog(user_id: int, name: str, set_active: bool = False) -> Optional[int]:
    """Создает новый диалог для пользователя и опционально делает его активным."""
    now_str = datetime.datetime.now(datetime.timezone.utc).isoformat()
    query = "INSERT INTO dialogs (user_id, name, created_at) VALUES (?, ?, ?)"
    new_dialog_id = await _execute_query(query, (user_id, name, now_str), is_write_operation=True)
    if new_dialog_id:
        if set_active:
            await set_active_dialog(user_id, new_dialog_id)
        db_logger.info(f"Для пользователя {user_id} создан новый диалог '{name}' (ID: {new_dialog_id}).")
        return int(new_dialog_id)
    return None

async def get_user_dialogs(user_id: int) -> List[Dict[str, Any]]:
    """Получает список всех диалогов пользователя."""
    query = "SELECT d.dialog_id, d.name, u.active_dialog_id FROM dialogs d JOIN users u ON d.user_id = u.user_id WHERE d.user_id = ? ORDER BY d.created_at DESC"
    rows = await _execute_query(query, (user_id,), fetch_all=True)
    return [dict(row) for row in rows] if rows else []

async def set_active_dialog(user_id: int, dialog_id: int):
    """Устанавливает активный диалог для пользователя."""
    query = "UPDATE users SET active_dialog_id = ? WHERE user_id = ?"
    await _execute_query(query, (dialog_id, user_id), is_write_operation=True)
    db_logger.info(f"Для пользователя {user_id} установлен активный диалог ID: {dialog_id}.")

async def rename_dialog(dialog_id: int, new_name: str):
    """Переименовывает диалог."""
    query = "UPDATE dialogs SET name = ? WHERE dialog_id = ?"
    await _execute_query(query, (new_name, dialog_id), is_write_operation=True)

async def delete_dialog(user_id: int, dialog_id_to_delete: int) -> Optional[str]:
    """Удаляет диалог и его историю."""
    other_dialogs = await _execute_query(
        "SELECT dialog_id FROM dialogs WHERE user_id = ? AND dialog_id != ? ORDER BY created_at DESC",
        (user_id, dialog_id_to_delete), fetch_all=True
    )
    if not other_dialogs:
        return None
    
    active_dialog_id = await get_active_dialog_id(user_id)
    if active_dialog_id == dialog_id_to_delete:
        await set_active_dialog(user_id, other_dialogs[0]['dialog_id'])

    dialog_info = await _execute_query("SELECT name FROM dialogs WHERE dialog_id = ?", (dialog_id_to_delete,), fetch_one=True)
    delete_query = "DELETE FROM dialogs WHERE dialog_id = ?"
    rows_affected = await _execute_query(delete_query, (dialog_id_to_delete,), is_write_operation=True)
    if rows_affected:
        db_logger.info(f"Диалог ID {dialog_id_to_delete} удален для пользователя {user_id}.")
        return dialog_info['name']
    return None

async def get_active_dialog_id(user_id: int) -> Optional[int]:
    """Получает ID активного диалога пользователя."""
    query = "SELECT active_dialog_id FROM users WHERE user_id = ?"
    result = await _execute_query(query, (user_id,), fetch_one=True)
    return result['active_dialog_id'] if result else None

async def get_total_user_message_count(user_id: int) -> int:
    """Получает общее количество сообщений пользователя во всех его диалогах."""
    query = "SELECT COUNT(*) FROM conversations WHERE user_id = ?"
    return await _execute_query(query, (user_id,))

async def set_user_language(user_id: int, lang_code: str):
    query = "UPDATE users SET language_code = ? WHERE user_id = ?"
    await _execute_query(query, (lang_code, user_id), is_write_operation=True)

async def get_user_language(user_id: int) -> str:
    query = "SELECT language_code FROM users WHERE user_id = ?"
    result = await _execute_query(query, (user_id,), fetch_one=True)
    return result['language_code'] if result and result['language_code'] else 'ru'

async def set_user_bot_style(user_id: int, style_code: str):
    """Устанавливает стиль общения бота для пользователя."""
    query = "UPDATE users SET bot_style = ? WHERE user_id = ?"
    await _execute_query(query, (style_code, user_id), is_write_operation=True)


async def get_user_bot_style(user_id: int) -> str:
    """Получает стиль общения бота для пользователя."""
    query = "SELECT bot_style FROM users WHERE user_id = ?"
    result = await _execute_query(query, (user_id,), fetch_one=True)
    return result['bot_style'] if result and result['bot_style'] else 'default'

async def set_user_gemini_model(user_id: int, model_name: str):
    query = "UPDATE users SET gemini_model = ? WHERE user_id = ?"
    await _execute_query(query, (model_name, user_id), is_write_operation=True)

async def get_user_gemini_model(user_id: int) -> Optional[str]:
    query = "SELECT gemini_model FROM users WHERE user_id = ?"
    result = await _execute_query(query, (user_id,), fetch_one=True)
    return result['gemini_model'] if result and result['gemini_model'] else None

async def set_user_persona(user_id: int, persona_id: str):
    query = "UPDATE users SET active_persona = ? WHERE user_id = ?"
    await _execute_query(query, (persona_id, user_id), is_write_operation=True)

async def get_user_persona(user_id: int) -> str:
    query = "SELECT active_persona FROM users WHERE user_id = ?"
    result = await _execute_query(query, (user_id,), fetch_one=True)
    return result['active_persona'] if result and result['active_persona'] else 'default'

async def get_first_interaction_date(user_id: int) -> Optional[str]:
    query = "SELECT first_interaction_date FROM users WHERE user_id = ?"
    result = await _execute_query(query, (user_id,), fetch_one=True)
    return result['first_interaction_date'] if result else None

async def get_token_usage_by_period(user_id: int, period: str) -> Dict[str, int]:
    """Получает статистику использования токенов по периоду.

    Использует явные диапазоны дат в формате ISO, что является более надежным
    методом, чем использование встроенных функций даты SQLite, особенно при
    работе с часовыми поясами.

    Args:
        user_id: ID пользователя, для которого запрашивается статистика.
        period: Период для расчета ('today' или 'month').

    Returns:
        Словарь с количеством prompt, completion и total токенов.
    """
    utc_now = datetime.datetime.now(datetime.timezone.utc)
    query: str
    params: tuple

    if period == 'today':
        start_of_day = utc_now.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day = start_of_day + datetime.timedelta(days=1)
        
        query = """
            SELECT SUM(prompt_tokens), SUM(completion_tokens), SUM(total_tokens) 
            FROM conversations 
            WHERE user_id = ? AND timestamp >= ? AND timestamp < ?
        """
        params = (user_id, start_of_day.isoformat(), end_of_day.isoformat())

    elif period == 'month':
        start_of_month = utc_now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        # Вычисляем первый день следующего месяца для корректного диапазона
        if start_of_month.month == 12:
            end_of_month = start_of_month.replace(year=start_of_month.year + 1, month=1)
        else:
            end_of_month = start_of_month.replace(month=start_of_month.month + 1)

        query = """
            SELECT SUM(prompt_tokens), SUM(completion_tokens), SUM(total_tokens) 
            FROM conversations 
            WHERE user_id = ? AND timestamp >= ? AND timestamp < ?
        """
        params = (user_id, start_of_month.isoformat(), end_of_month.isoformat())
        
    else:
        return {'prompt_tokens': 0, 'completion_tokens': 0, 'total_tokens': 0}

    result_row = await _execute_query(query, params, fetch_one=True)
    
    if result_row and result_row[0] is not None:
        return {
            'prompt_tokens': int(result_row[0]),
            'completion_tokens': int(result_row[1]),
            'total_tokens': int(result_row[2])
        }
    return {'prompt_tokens': 0, 'completion_tokens': 0, 'total_tokens': 0}

async def get_user_context_info(user_id: int) -> Optional[Dict[str, Any]]:
    """Получает единым запросом всю информацию для контекстного заголовка."""
    query = """
        SELECT
            d.name as dialog_name,
            u.gemini_model,
            u.active_persona
        FROM users u
        LEFT JOIN dialogs d ON u.active_dialog_id = d.dialog_id
        WHERE u.user_id = ?
    """
    result = await _execute_query(query, (user_id,), fetch_one=True)
    return dict(result) if result else None

async def update_last_session_time(user_id: int):
    """Обновляет временную метку последней активности пользователя."""
    now_str = datetime.datetime.now(datetime.timezone.utc).isoformat()
    query = "UPDATE users SET last_session_ts = ? WHERE user_id = ?"
    await _execute_query(query, (now_str, user_id), is_write_operation=True)

async def get_last_session_time(user_id: int) -> Optional[datetime.datetime]:
    """Получает время последней активности пользователя в виде объекта datetime."""
    query = "SELECT last_session_ts FROM users WHERE user_id = ?"
    result = await _execute_query(query, (user_id,), fetch_one=True)
    if result and result['last_session_ts']:
        try:
            return datetime.datetime.fromisoformat(result['last_session_ts'])
        except (ValueError, TypeError):
            return None
    return None

# --- Управление профилем пользователя (ZK) ---

async def save_user_profile(user_id: int, profile_data: Dict[str, Any], fernet_instance: Fernet):
    """Сериализует, шифрует и сохраняет профиль пользователя."""
    # Сериализуем словарь в строку JSON
    profile_str = json.dumps(profile_data, ensure_ascii=False)
    # Шифруем строку
    encrypted_profile = crypto_helpers.encrypt_data(profile_str, fernet_instance)
    
    now_str = datetime.datetime.now(datetime.timezone.utc).isoformat()
    
    query = """
        INSERT INTO user_profiles (user_id, profile_data, last_updated)
        VALUES (?, ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET
            profile_data = excluded.profile_data,
            last_updated = excluded.last_updated
    """
    await _execute_query(query, (user_id, encrypted_profile, now_str), is_write_operation=True)
    db_logger.info(f"Профиль для пользователя {user_id} был зашифрован и сохранен/обновлен.")


async def get_user_profile(user_id: int, fernet_instance: Fernet) -> Optional[Dict[str, Any]]:
    """Извлекает, расшифровывает и десериализует профиль пользователя."""
    query = "SELECT profile_data FROM user_profiles WHERE user_id = ?"
    result = await _execute_query(query, (user_id,), fetch_one=True)
    
    if result and result['profile_data']:
        decrypted_str = crypto_helpers.decrypt_data(result['profile_data'], fernet_instance)
        if decrypted_str:
            try:
                # Десериализуем строку JSON обратно в словарь
                return json.loads(decrypted_str)
            except json.JSONDecodeError:
                db_logger.error(f"Ошибка декодирования JSON профиля для пользователя {user_id}.")
                return None
    return None

async def get_history_for_archiving(dialog_id: int, cutoff_date: datetime.datetime, fernet_instance: Fernet) -> List[Dict[str, Any]]:
    """
    Получает сообщения из указанного диалога, которые старше cutoff_date.
    Возвращает расшифрованную историю, включая ID сообщений для последующего удаления.

    Args:
        dialog_id: ID диалога для поиска.
        cutoff_date: Временная метка. Все сообщения старше этой даты будут выбраны.
        fernet_instance: Экземпляр Fernet для расшифровки.

    Returns:
        Список словарей, где каждый словарь представляет старое сообщение.
    """
    query = """
        SELECT conversation_id, role, message_text, timestamp
        FROM conversations
        WHERE dialog_id = ? AND timestamp < ?
        ORDER BY timestamp ASC
    """
    params = (dialog_id, cutoff_date.isoformat())
    rows = await _execute_query(query, params, fetch_all=True)
    if not rows:
        return []

    decrypted_history = []
    for row in rows:
        decrypted_text = crypto_helpers.decrypt_data(row['message_text'], fernet_instance)
        if decrypted_text is not None:
            decrypted_history.append({
                'conversation_id': row['conversation_id'],
                'role': row['role'],
                'message_text': decrypted_text,
                'timestamp': row['timestamp']
            })
        else:
            db_logger.warning(f"Пропущено сообщение {row['conversation_id']} при архивации из-за ошибки расшифровки.")
            
    return decrypted_history


async def delete_messages_by_ids(message_ids: List[int]) -> int:
    """
    Удаляет сообщения из таблицы conversations по списку их ID.

    Args:
        message_ids: Список ID сообщений, которые нужно удалить.

    Returns:
        Количество удаленных строк.
    """
    if not message_ids:
        return 0
    
    placeholders = ', '.join(['?'] * len(message_ids))
    query = f"DELETE FROM conversations WHERE conversation_id IN ({placeholders})"
    
    rows_affected = await _execute_query(query, tuple(message_ids), is_write_operation=True)
    
    if rows_affected is not None:
        db_logger.info(f"Удалено {rows_affected} сообщений в процессе архивации.")
        return rows_affected
    return 0

# --- НОВЫЕ ФУНКЦИИ ДЛЯ АДМИН-ПАНЕЛИ ---

async def set_app_setting(key: str, value: str):
    """Устанавливает или обновляет глобальную настройку приложения."""
    query = "INSERT INTO app_settings (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value"
    await _execute_query(query, (key, value), is_write_operation=True)
    db_logger.info(f"Глобальная настройка '{key}' установлена в значение '{value}'.")

async def get_app_setting(key: str) -> Optional[str]:
    """Получает значение глобальной настройки приложения."""
    query = "SELECT value FROM app_settings WHERE key = ?"
    result = await _execute_query(query, (key,), fetch_one=True)
    return result['value'] if result else None

async def is_user_blocked(user_id: int) -> bool:
    """Проверяет, заблокирован ли пользователь."""
    query = "SELECT is_blocked FROM users WHERE user_id = ?"
    result = await _execute_query(query, (user_id,), fetch_one=True)
    return result['is_blocked'] == 1 if result else False

async def block_user(user_id: int):
    """Блокирует пользователя."""
    await _execute_query("UPDATE users SET is_blocked = 1 WHERE user_id = ?", (user_id,), is_write_operation=True)
    db_logger.info(f"Пользователь {user_id} заблокирован.")

async def unblock_user(user_id: int):
    """Разблокирует пользователя."""
    await _execute_query("UPDATE users SET is_blocked = 0 WHERE user_id = ?", (user_id,), is_write_operation=True)
    db_logger.info(f"Пользователь {user_id} разблокирован.")

async def get_all_user_ids() -> List[int]:
    """Возвращает список ID всех пользователей."""
    rows = await _execute_query("SELECT user_id FROM users", fetch_all=True)
    return [row['user_id'] for row in rows] if rows else []

async def get_total_users_count() -> int:
    """Возвращает общее количество пользователей."""
    count = await _execute_query("SELECT COUNT(*) FROM users")
    return count if count is not None else 0

async def get_blocked_users_count() -> int:
    """Возвращает количество заблокированных пользователей."""
    count = await _execute_query("SELECT COUNT(*) FROM users WHERE is_blocked = 1")
    return count if count is not None else 0

async def get_active_users_count(days: int = 7) -> int:
    """Возвращает количество пользователей, отправлявших сообщения за последние N дней."""
    start_date = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=days)
    query = "SELECT COUNT(DISTINCT user_id) FROM conversations WHERE timestamp >= ?"
    count = await _execute_query(query, (start_date.isoformat(),))
    return count if count is not None else 0

async def get_new_users_count(days: int = 7) -> int:
    """Возвращает количество новых пользователей за последние N дней."""
    start_date = datetime.date.today() - datetime.timedelta(days=days)
    query = "SELECT COUNT(*) FROM users WHERE first_interaction_date >= ?"
    count = await _execute_query(query, (start_date.strftime('%Y-%m-%d'),))
    return count if count is not None else 0

async def get_user_info_for_admin(user_id: int) -> Optional[Dict[str, Any]]:
    """Собирает подробную информацию о пользователе для админ-панели."""
    query = """
        SELECT
            u.user_id,
            u.username,
            u.first_name,
            u.last_name,
            u.language_code,
            u.first_interaction_date,
            u.is_blocked,
            (SELECT COUNT(*) FROM conversations WHERE user_id = u.user_id) as message_count
        FROM users u
        WHERE u.user_id = ?
    """
    row = await _execute_query(query, (user_id,), fetch_one=True)
    # Также обновляем информацию о пользователе при просмотре
    if row:
        user_info = dict(row)
        # Добавляем обновление имени пользователя при его просмотре админом
        # Это необязательно, но может быть полезно
        # await add_or_update_user(user_id, user_info.get('username'), user_info.get('first_name'), user_info.get('last_name'))
        return user_info
    return None


# --- НОВАЯ ФУНКЦИЯ ДЛЯ ЭКСПОРТА ---
async def get_all_users_for_export() -> List[Dict[str, Any]]:
    """Извлекает всех пользователей со всеми необходимыми полями для экспорта в CSV."""
    query = """
        SELECT
            user_id,
            username,
            first_name,
            last_name,
            language_code,
            first_interaction_date,
            is_blocked
        FROM users
        ORDER BY user_id ASC
    """
    rows = await _execute_query(query, fetch_all=True)
    return [dict(row) for row in rows] if rows else []

async def set_panic_password(user_id: int, password: str):
    """Генерирует хеш для пароля паники и сохраняет его для пользователя."""
    password_hash = crypto_helpers.hash_password(password)
    query = "UPDATE users SET panic_password_hash = ? WHERE user_id = ?"
    params = (password_hash, user_id)
    await _execute_query(query, params, is_write_operation=True)
    db_logger.info(f"Пароль паники установлен для пользователя {user_id}.")


async def verify_panic_password(user_id: int, provided_password: str) -> bool:
    """Проверяет предоставленный пароль паники."""
    query = "SELECT panic_password_hash FROM users WHERE user_id = ?"
    result = await _execute_query(query, (user_id,), fetch_one=True)
    if not result or not result['panic_password_hash']:
        return False
    stored_hash = result['panic_password_hash']
    # Также проверяем, что он не совпадает с основным паролем, на всякий случай
    is_panic_match = crypto_helpers.verify_password(stored_hash, provided_password)
    if is_panic_match:
        is_master_match = await verify_master_password(user_id, provided_password)
        return not is_master_match
    return False


async def clear_user_content(user_id: int, fernet_instance: Fernet):
    """
    Удаляет весь контент пользователя (диалоги, сообщения), но сохраняет
    самого пользователя, его пароли, профиль и API-ключ.
    Сначала удаляет векторную память, затем данные из SQLite.
    После удаления создает один новый "Основной диалог".

    Args:
        user_id (int): ID пользователя для очистки.
        fernet_instance (Fernet): Ключ сессии для доступа к API-ключу Google.
    """
    db_logger.warning(f"Начата полная очистка контента для пользователя {user_id}.")

    # 1. Получаем список ID всех диалогов пользователя ПЕРЕД их удалением
    dialogs_to_delete = await get_user_dialogs(user_id)
    dialog_ids = [d['dialog_id'] for d in dialogs_to_delete]

    # 2. Удаляем коллекции из векторной базы
    # Для этого нужен API-ключ, который тоже зашифрован
    api_key = await get_user_api_key(user_id, fernet_instance)
    if api_key and dialog_ids:
        try:
            vector_store = VectorStoreManager(api_key=api_key)
            vector_store.delete_all_user_collections(dialog_ids)
        except Exception as e:
            db_logger.exception(f"Не удалось полностью очистить векторную память для user_id {user_id}: {e}")
            # Не прерываем процесс, очистка основной БД важнее

    # 3. Удаляем все диалоги из SQLite (каскадное удаление удалит и все сообщения)
    delete_dialogs_query = "DELETE FROM dialogs WHERE user_id = ?"
    await _execute_query(delete_dialogs_query, (user_id,), is_write_operation=True)
    db_logger.info(f"Все диалоги и сообщения для user_id {user_id} удалены из SQLite.")

    # 4. Создаем новый диалог по умолчанию
    await create_dialog(user_id, "Основной диалог", set_active=True)
    db_logger.info(f"Создан новый основной диалог для user_id {user_id} после очистки.")

async def get_user_subscription_status(user_id: int) -> Dict[str, Any]:
    """
    Получает статус и дату окончания подписки пользователя.
    Автоматически обновляет статус на 'expired', если дата прошла.
    """
    query = "SELECT subscription_status, subscription_end_date FROM users WHERE user_id = ?"
    result = await _execute_query(query, (user_id,), fetch_one=True)

    if not result or not result['subscription_status']:
        return {"status": "none", "end_date": None}

    status = result['subscription_status']
    end_date_str = result['subscription_end_date']
    end_date = None

    if end_date_str:
        end_date = datetime.datetime.fromisoformat(end_date_str).date()
        if status == 'active' and end_date < datetime.date.today():
            status = 'expired'
            # Обновляем статус в базе данных асинхронно
            asyncio.create_task(
                update_user_subscription(user_id, 'expired', end_date.isoformat())
            )

    return {"status": status, "end_date": end_date}


async def update_user_subscription(user_id: int, status: str, end_date_iso: str):
    """Обновляет статус и дату окончания подписки пользователя."""
    query = "UPDATE users SET subscription_status = ?, subscription_end_date = ? WHERE user_id = ?"
    await _execute_query(query, (status, end_date_iso, user_id), is_write_operation=True)
    db_logger.info(f"Статус подписки для пользователя {user_id} обновлен на '{status}' до {end_date_iso}.")