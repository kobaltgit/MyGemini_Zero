# File: logger_config.py
import logging
import logging.config
import yaml
import os
from logging import LoggerAdapter, LogRecord
from typing import MutableMapping, Any, Optional

# Определяем базовую директорию проекта (папка, где лежит main.py)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

LOG_CONFIG_FILE = os.path.join(BASE_DIR, "config", "logging.yaml")
LOG_DIR = os.path.join(BASE_DIR, "logs")


class UserIdContextFilter(logging.Filter):
    """
    Это фильтр, который гарантирует, что поле 'user_id' всегда будет
    присутствовать в записи лога перед ее передачей обработчику.
    """
    def filter(self, record: LogRecord) -> bool:
        if not hasattr(record, 'user_id'):
            # Если запись пришла извне (например, от библиотеки pyTelegramBotAPI)
            # и не имеет user_id, мы устанавливаем значение по умолчанию.
            record.user_id = 'System'
        return True


class UserIdAdapter(LoggerAdapter):
    """
    Адаптер, который мы используем в нашем коде для удобной передачи
    user_id в записи лога через параметр `extra`.
    """
    def process(self, msg: str, kwargs: MutableMapping[str, Any]) -> tuple[str, MutableMapping[str, Any]]:
        # Передаем user_id из 'extra' адаптера в 'extra' записи лога
        if 'user_id' not in kwargs.get('extra', {}):
            if 'extra' not in kwargs:
                kwargs['extra'] = {}
            kwargs['extra']['user_id'] = self.extra.get('user_id', 'System')
        return msg, kwargs


def setup_logging():
    """Настраивает логгер из YAML файла."""
    os.makedirs(LOG_DIR, exist_ok=True)

    if not os.path.exists(LOG_CONFIG_FILE):
        log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        logging.basicConfig(level=logging.INFO, format=log_format)
        logging.warning(
            f"Файл конфигурации логирования не найден: {LOG_CONFIG_FILE}. Используется базовая конфигурация.")
        return

    try:
        with open(LOG_CONFIG_FILE, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
            # Мы больше не используем setLoggerClass, это было ошибкой
            logging.config.dictConfig(config)
        print(f"Конфигурация логирования успешно загружена из {LOG_CONFIG_FILE}")
    except Exception as e:
        log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        logging.basicConfig(level=logging.ERROR, format=log_format)
        logging.exception(
            f"Ошибка при загрузке конфигурации логирования из {LOG_CONFIG_FILE}: {e}. Используется базовая конфигурация.")


def get_logger(name: str, user_id: Optional[str | int] = None) -> UserIdAdapter:
    """
    Возвращает стандартный логгер, обернутый в наш UserIdAdapter.
    """
    logger = logging.getLogger(name)
    user_id_str = str(user_id) if user_id is not None else 'System'

    # Просто создаем и возвращаем адаптер
    return UserIdAdapter(logger, {'user_id': user_id_str})
