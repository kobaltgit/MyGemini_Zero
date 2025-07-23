import asyncio
import signal
import sys
import os
from telebot.async_telebot import AsyncTeleBot
from telebot.asyncio_storage import StateMemoryStorage

from logger_config import setup_logging, get_logger
from utils import guide_manager

setup_logging()
main_logger = get_logger(__name__)

guide_manager.load_guides()

try:
    from config import settings
    from database import db_manager
    # Импортируем новый модуль admin_handlers
    from handlers import command_handlers, callback_handlers, message_handlers, admin_handlers, telegram_helpers
    from services import gemini_service
except ImportError as e:
    main_logger.exception(f"Критическая ошибка: Не удалось импортировать необходимые модули: {e}", extra={'user_id': 'System'})
    sys.exit(1)
except Exception as e:
    main_logger.exception(f"Критическая ошибка при инициализации импортов: {e}", extra={'user_id': 'System'})
    sys.exit(1)

try:
    state_storage = StateMemoryStorage()
    bot = AsyncTeleBot(settings.BOT_TOKEN, state_storage=state_storage, parse_mode='Markdown')
    telegram_helpers.register_bot_instance(bot)
    main_logger.info("Экземпляр AsyncTeleBot создан.", extra={'user_id': 'System'})
except Exception as e:
    main_logger.exception(f"Критическая ошибка: Не удалось создать экземпляр бота: {e}", extra={'user_id': 'System'})
    sys.exit(1)


async def setup_db():
    """Асинхронная функция для настройки базы данных."""
    try:
        main_logger.info("Настройка базы данных...", extra={'user_id': 'System'})
        await db_manager.setup_database()
        main_logger.info("База данных успешно настроена.", extra={'user_id': 'System'})
    except Exception as e:
        main_logger.exception("Критическая ошибка: Не удалось настроить базу данных.", extra={'user_id': 'System'})
        sys.exit(1)

try:
    main_logger.info("Регистрация обработчиков...", extra={'user_id': 'System'})
    # Регистрируем админские обработчики
    admin_handlers.register_admin_handlers(bot)
    # Регистрируем остальные
    command_handlers.register_command_handlers(bot)
    callback_handlers.register_callback_handlers(bot)
    message_handlers.register_message_handlers(bot)
    main_logger.info("Обработчики успешно зарегистрированы.", extra={'user_id': 'System'})
except Exception as e:
    main_logger.exception("Критическая ошибка: Не удалось зарегистрировать обработчики.", extra={'user_id': 'System'})
    sys.exit(1)


async def run_bot_polling(bot_instance: AsyncTeleBot):
    """Запускает основной цикл опроса Telegram (polling)."""
    main_logger.info("Запуск бота (polling)...", extra={'user_id': 'System'})
    try:
        await bot_instance.polling(none_stop=True, interval=1)
    except asyncio.CancelledError:
        main_logger.info("Задача поллинга отменена (ожидаемо при завершении).", extra={'user_id': 'System'})
    except Exception as e:
         main_logger.exception("Критическая ошибка в цикле polling.", extra={'user_id': 'System'})
    finally:
        main_logger.info("Цикл polling завершен.", extra={'user_id': 'System'})

shutdown_event = asyncio.Event()

async def main():
    """Основная асинхронная функция, управляющая запуском и остановкой."""
    main_logger.info("Запуск основной асинхронной функции main().", extra={'user_id': 'System'})

    await setup_db()

    polling_task = asyncio.create_task(run_bot_polling(bot))
    await shutdown_event.wait()
    main_logger.warning("Начало процесса graceful shutdown...", extra={'user_id': 'System'})

    main_logger.info("Отмена задачи поллинга...", extra={'user_id': 'System'})
    polling_task.cancel()

    try:
        await polling_task
        main_logger.info("Задача поллинга успешно завершилась после отмены.", extra={'user_id': 'System'})
    except asyncio.CancelledError:
        main_logger.info("Поллинг был отменен (как и ожидалось).", extra={'user_id': 'System'})
    except Exception as e:
         main_logger.exception("Ошибка при ожидании завершения задачи поллинга.", extra={'user_id': 'System'})

    main_logger.info("Graceful shutdown завершен.", extra={'user_id': 'System'})


def handle_shutdown_signal(signum, frame):
    """Обработчик сигналов SIGINT и SIGTERM."""
    if not shutdown_event.is_set():
        main_logger.warning(f"Получен сигнал завершения ({signal.Signals(signum).name}). Инициирую graceful shutdown...", extra={'user_id': 'System'})
        shutdown_event.set()
    else:
        main_logger.warning("Повторный сигнал завершения получен. Процесс уже останавливается.", extra={'user_id': 'System'})

if __name__ == '__main__':
    main_logger.info(f"Запуск бота (PID: {os.getpid()})...", extra={'user_id': 'System'})

    signal.signal(signal.SIGINT, handle_shutdown_signal)
    signal.signal(signal.SIGTERM, handle_shutdown_signal)

    import logging
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        main_logger.info("Завершение работы по KeyboardInterrupt (до запуска main loop).", extra={'user_id': 'System'})
    except Exception as e:
        main_logger.exception("Необработанная критическая ошибка на верхнем уровне.", extra={'user_id': 'System'})
        sys.exit(1)
    finally:
        main_logger.info("Работа бота завершена.", extra={'user_id': 'System'})
        logging.shutdown()
        sys.exit(0)