# File: MyGemini_Zero/utils/crypto_helpers.py

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
Модуль для реализации криптографических операций в рамках Zero-Knowledge архитектуры.

Этот модуль отвечает за:
1. Безопасное хеширование и проверку мастер-паролей пользователей с использованием bcrypt.
2. Генерацию уникальной криптографической "соли" для каждого пользователя.
3. Создание (деривацию) ключа шифрования на лету из мастер-пароля и соли пользователя
   с использованием стандарта PBKDF2-HMAC-SHA256. Этот ключ никогда не хранится на диске.
4. Шифрование и дешифрование данных (истории диалогов) с помощью сгенерированного ключа.
"""
import os
import base64
import bcrypt
from typing import Optional

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend

# Рекомендуется вынести в settings.py для легкой конфигурации
# Чем выше значение, тем сложнее брутфорс, но медленнее генерация ключа.
PBKDF2_ITERATIONS = 480000

# --- Функции для работы с мастер-паролем ---

def generate_salt() -> bytes:
    """
    Генерирует криптографически стойкую соль для хеширования пароля.

    Returns:
        bytes: 16-байтная случайная соль.
    """
    return os.urandom(16)


def hash_password(password: str) -> bytes:
    """
    Хеширует пароль с использованием bcrypt. Соль генерируется автоматически.

    Bcrypt является индустриальным стандартом для хеширования паролей, так как он
    включает соль в сам хеш и является вычислительно "медленным",
    что защищает от атак перебором.

    Args:
        password (str): Пароль пользователя в виде строки.

    Returns:
        bytes: Хеш пароля, готовый для сохранения в базу данных.
    """
    password_bytes = password.encode('utf-8')
    return bcrypt.hashpw(password_bytes, bcrypt.gensalt())


def verify_password(stored_hash: bytes, provided_password: str) -> bool:
    """
    Проверяет, соответствует ли предоставленный пароль сохраненному хешу.

    Args:
        stored_hash (bytes): Хеш, ранее сохраненный в базе данных.
        provided_password (str): Пароль, введенный пользователем для проверки.

    Returns:
        bool: True, если пароль верный, иначе False.
    """
    password_bytes = provided_password.encode('utf-8')
    return bcrypt.checkpw(password_bytes, stored_hash)


# --- Функции для генерации ключа шифрования и работы с данными ---

def derive_key(password: str, salt: bytes) -> bytes:
    """
    Создает (деривирует) ключ шифрования из пароля и соли с помощью PBKDF2.

    Это ядро Zero-Knowledge подхода. Мы не храним ключ, а каждый раз
    создаем его заново из пароля, который знает только пользователь.
    Это гарантирует, что без пароля данные расшифровать невозможно.

    Args:
        password (str): Мастер-пароль пользователя.
        salt (bytes): Уникальная соль пользователя, хранящаяся в БД.

    Returns:
        bytes: 32-байтный ключ шифрования, закодированный в URL-safe Base64.
    """
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=PBKDF2_ITERATIONS,
        backend=default_backend()
    )
    key = base64.urlsafe_b64encode(kdf.derive(password.encode('utf-8')))
    return key


def get_fernet_instance(password: str, salt: bytes) -> Fernet:
    """
    Создает и возвращает экземпляр Fernet для шифрования/дешифрования.

    Эта функция объединяет деривацию ключа и инициализацию объекта Fernet.
    Полученный экземпляр будет использоваться в течение всей активной сессии
    пользователя для работы с его зашифрованными данными.

    Args:
        password (str): Мастер-пароль пользователя.
        salt (bytes): Соль пользователя из БД.

    Returns:
        Fernet: Готовый к работе объект для шифрования.
    """
    derived_key = derive_key(password, salt)
    return Fernet(derived_key)


def encrypt_data(data: str, fernet_instance: Fernet) -> str:
    """
    Шифрует строковые данные с помощью предоставленного экземпляра Fernet.

    Args:
        data (str): Текст, который нужно зашифровать.
        fernet_instance (Fernet): Экземпляр Fernet, инициализированный
                                  ключом пользователя.

    Returns:
        str: Зашифрованная строка в формате base64.
    """
    encrypted_data = fernet_instance.encrypt(data.encode('utf-8'))
    return encrypted_data.decode('utf-8')


def decrypt_data(encrypted_data: str, fernet_instance: Fernet) -> Optional[str]:
    """
    Дешифрует строковые данные с помощью предоставленного экземпляра Fernet.

    Args:
        encrypted_data (str): Зашифрованный текст из БД.
        fernet_instance (Fernet): Экземпляр Fernet, инициализированный
                                  ключом пользователя.

    Returns:
        Optional[str]: Расшифрованная строка или None, если произошла ошибка
                       (например, был использован неверный ключ/пароль).
    """
    try:
        decrypted_data = fernet_instance.decrypt(encrypted_data.encode('utf-8'))
        return decrypted_data.decode('utf-8')
    except InvalidToken:
        # Эта ошибка возникает, если ключ (а значит, и пароль) неверный,
        # или если данные были повреждены.
        return None
    except Exception:
        # Логирование должно происходить в вызывающем коде.
        # Здесь мы просто возвращаем None при любой другой ошибке дешифровки.
        return None