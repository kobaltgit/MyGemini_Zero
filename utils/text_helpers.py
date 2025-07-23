# File: utils/text_helpers.py
import re
import string
from urllib.parse import urlparse
from logger_config import get_logger
from typing import List

# Максимальная длина сообщения Telegram (используется новой библиотекой, но оставим для справки)
TELEGRAM_MAX_MESSAGE_LENGTH = 4096

logger = get_logger('text_helpers')


def sanitize_text_for_telegram(text: str) -> str:
    """
    Очищает текст для безопасной отправки через Telegram (даже с parse_mode='None').
    Удаляет Markdown, символ '@', опасные символы и непечатаемые символы.
    """
    if not isinstance(text, str):
        return ""

    # 1. Удаляем Markdown
    text = remove_markdown(text)

    # 2. Заменяем символ '@'
    text = text.replace('@', '(at)')

    # 3. Удаляем опасные символы, которые Telegram может попытаться распарсить
    dangerous_symbols = ['`', '*', '_', '[', ']', '(', ')', '~', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    for symbol in dangerous_symbols:
        text = text.replace(symbol, '')

    # 4. Удаляем всё кроме допустимых символов
    allowed_chars = string.ascii_letters + string.digits + ' \t\n\r' + 'абвгдеёжзийклмнопрстуфхцчшщъыьэюяАБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ'
    text = ''.join(c for c in text if c in allowed_chars)

    # 5. Убираем повторяющиеся пробелы и переносы
    text = re.sub(r'\s{2,}', ' ', text)
    text = re.sub(r'\n{3,}', '\n\n', text)

    return text.strip()


def remove_markdown(text: str) -> str:
    """Удаляет основные Markdown v2 символы из текста."""
    if not text:
        return ""
    # Порядок важен: сначала удаляем экранирование, потом сами символы
    text = re.sub(r'\\([_*\[\]()~`>#+-=|{}.!])', r'\1', text) # Удаляем экранирование \
    # Удаление жирного (**text** или __text__)
    text = re.sub(r'\*([^*]+)\*', r'\1', text)  # *курсив/жирный*
    text = re.sub(r'_([^_]+)_', r'\1', text)  # _курсив/подчеркнутый_
    # Удаление зачеркнутого (~text~)
    text = re.sub(r'~([^~]+)~', r'\1', text)
    # Удаление спойлера (||text||)
    text = re.sub(r'\|\|([^|]+)\|\|', r'\1', text)
    # Удаление ссылок ([text](url)) -> text
    text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)
    # Удаление блоков кода (```lang\ncode``` или ```code```)
    text = re.sub(r'```(?:[a-zA-Z]+\n)?([\s\S]*?)```', r'\1', text) # Оставляем содержимое блока кода
    # Удаление встроенного кода (`code`) -> code
    text = re.sub(r'`([^`]+)`', r'\1', text)
    # Удаление элементов списка (* item, - item, + item, 1. item)
    text = re.sub(r'^[*\-]\s+', '', text, flags=re.MULTILINE)
    text = re.sub(r'^\d+[\.\)]\s+', '', text, flags=re.MULTILINE)
    # Удаление цитат (> quote)
    text = re.sub(r'^>\s?', '', text, flags=re.MULTILINE)
    # Замена множественных пробелов и очистка
    text = re.sub(r'\s{2,}', ' ', text)
    return text.strip()


def is_url(text: str) -> bool:
    """Проверяет, является ли строка валидным URL (простая проверка)."""
    if not text:
        return False
    # Упрощенная проверка: начинается с http:// или https:// и содержит точку после схемы
    if not (text.startswith('http://') or text.startswith('https://')):
        return False
    try:
        # Используем urlparse для базовой проверки структуры
        result = urlparse(text)
        # Проверяем наличие схемы и сетевой локации (домена)
        return bool(result.scheme and result.netloc and '.' in result.netloc)
    except ValueError: # urlparse может вызвать ValueError на очень странных строках
        return False

def escape_markdown(text: str, version: int = 2) -> str:
    """
    Экранирует специальные символы в тексте для безопасной отправки
    в Telegram с parse_mode='MarkdownV2'.
    """
    if not isinstance(text, str):
        return ""
    if version == 1:
        # Для старого Markdown, если понадобится
        escape_chars = r'_*`['
    elif version == 2:
        # Для MarkdownV2, который мы используем
        escape_chars = r'_*[]()~`>#+-=|{}.!'
    else:
        raise ValueError("Only Markdown versions 1 and 2 are supported.")

    # Экранируем только символы из списка
    return re.sub(f"([{re.escape(escape_chars)}])", r"\\\1", text)