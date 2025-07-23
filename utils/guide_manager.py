# File: utils/guide_manager.py
import os
import re
from typing import Optional

from logger_config import get_logger

logger = get_logger(__name__)

# Путь к директории с файлами справки
GUIDE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'guides')

# Переменные для хранения загруженных текстов
_full_guide_ru: Optional[str] = None
_full_guide_en: Optional[str] = None # Задел на будущее для английской версии

def load_guides():
    """
    Загружает тексты справок из файлов в память при старте бота.
    Выбрасывает исключение, если основной файл справки не найден.
    """
    global _full_guide_ru, _full_guide_en
    
    # --- Загрузка русской версии ---
    ru_guide_path = os.path.join(GUIDE_DIR, 'full_guide_ru.md')
    try:
        if os.path.exists(ru_guide_path):
            with open(ru_guide_path, 'r', encoding='utf-8') as f:
                _full_guide_ru = f.read()
            logger.info(f"Справка на русском языке успешно загружена из {ru_guide_path}")
        else:
            logger.error(f"Файл справки на русском языке не найден: {ru_guide_path}")
            # Можно сделать это критической ошибкой, чтобы бот не стартовал
            # raise FileNotFoundError(f"Required guide file not found: {ru_guide_path}")
    except Exception as e:
        logger.exception(f"Ошибка при загрузке русской справки: {e}")
        raise

    # --- Загрузка английской версии ---
    en_guide_path = os.path.join(GUIDE_DIR, 'full_guide_en.md')
    try:
        if os.path.exists(en_guide_path):
            with open(en_guide_path, 'r', encoding='utf-8') as f:
                _full_guide_en = f.read()
            logger.info(f"Справка на английском языке успешно загружена из {en_guide_path}")
        else:
            logger.warning(f"Английская версия справки не найдена: {en_guide_path}. Будет использоваться русская версия по умолчанию.")
    except Exception as e:
        # Не выбрасываем исключение, чтобы бот мог работать хотя бы с русской версией
        logger.exception(f"Ошибка при загрузке английской справки: {e}")

def get_full_guide(lang: str = 'ru') -> str:
    """
    Возвращает полный текст справки для указанного языка.
    
    Args:
        lang (str): Код языка ('ru' или 'en').

    Returns:
        str: Полный текст справки или строка с сообщением об ошибке.
    """
    if lang == 'ru' and _full_guide_ru:
        return _full_guide_ru
    if lang == 'en' and _full_guide_en:
        return _full_guide_en
        
    return "К сожалению, текст справки для выбранного языка не найден."

def get_guide_section(section_name: str, lang: str = 'ru') -> str:
    """
    Извлекает конкретную секцию из полного текста справки.

    Args:
        section_name (str): Имя секции (например, 'API_KEY').
        lang (str): Код языка ('ru' или 'en').

    Returns:
        str: Текст указанной секции или сообщение об ошибке.
    """
    full_guide = get_full_guide(lang)
    if "не найден" in full_guide:
        return full_guide

    # Определяем теги для поиска в зависимости от языка
    tag_templates = {
        'ru': {'start': "НАЧАЛО РАЗДЕЛА", 'end': "КОНЕЦ РАЗДЕЛА"},
        'en': {'start': "START OF SECTION", 'end': "END OF SECTION"}
    }
    
    # Выбираем нужный язык, с фоллбэком на русский
    lang_tags = tag_templates.get(lang, tag_templates['ru'])
    start_tag = lang_tags['start']
    end_tag = lang_tags['end']

    # Собираем динамическое регулярное выражение
    pattern = re.compile(
        rf"# \[{re.escape(start_tag)}: {re.escape(section_name.upper())}\](.*?)# \[{re.escape(end_tag)}: {re.escape(section_name.upper())}\]",
        re.DOTALL
    )
    
    match = pattern.search(full_guide)
    
    if match:
        # match.group(1) возвращает текст между начальным и конечным тегами
        return match.group(1).strip()
    
    logger.warning(f"Секция '{section_name}' не найдена в справке для языка '{lang}'.")
    return f"Раздел справки '{section_name}' не найден."