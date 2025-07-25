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

import asyncio
import signal
import sys
import os
from datetime import datetime, timedelta
from telebot.async_telebot import AsyncTeleBot
from telebot import types
from telebot.asyncio_storage import StateMemoryStorage

from logger_config import setup_logging, get_logger
from utils import guide_manager
from utils import localization as loc

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

async def pre_checkout_callback(pre_checkout_query: types.PreCheckoutQuery, bot: AsyncTeleBot):
    """
    Отвечает на запрос pre-checkout. Обязательный шаг для подтверждения платежа.
    """
    lang_code = await db_manager.get_user_language(pre_checkout_query.from_user.id)
    try:
        # Здесь можно добавить любую логику проверки (например, доступность товара)
        # Для подписки просто подтверждаем.
        await bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)
    except Exception as e:
        main_logger.error(f"Ошибка в pre_checkout_callback: {e}", extra={'user_id': str(pre_checkout_query.from_user.id)})
        await bot.answer_pre_checkout_query(
            pre_checkout_query.id,
            ok=False,
            error_message=loc.get_text('payment_pre_checkout_error', lang_code)
        )

async def successful_payment_callback(message: types.Message, bot: AsyncTeleBot):
    """
    Обрабатывает уведомление об успешной оплате.
    """
    user_id = message.from_user.id
    lang_code = await db_manager.get_user_language(user_id)
    
    payload = message.successful_payment.invoice_payload
    plan = next((p for p in settings.SUBSCRIPTION_PLANS if p['id'] == payload), None)

    if plan:
        end_date = datetime.now() + timedelta(days=plan['duration_days'])
        await db_manager.update_user_subscription(user_id, 'active', end_date.isoformat())
        
        main_logger.info(f"Пользователь {user_id} успешно оплатил подписку '{plan['id']}'.", extra={'user_id': str(user_id)})
        
        # Отправляем подтверждение и призываем к следующему шагу - /start
        await bot.send_message(user_id, loc.get_text('payment_successful', lang_code))
    else:
        main_logger.error(f"Получен успешный платеж по неизвестному payload: {payload}", extra={'user_id': str(user_id)})


async def check_subscriptions(bot: AsyncTeleBot):
    """
    Фоновая задача для проверки истекающих подписок и отправки уведомлений.
    Запускается раз в сутки.
    """
    while True:
        main_logger.info("Запущена фоновая проверка истекающих подписок...", extra={'user_id': 'System'})
        # Здесь будет логика проверки и отправки уведомлений
        # В данном примере она не реализована, чтобы не усложнять.
        # Для полноценной реализации потребуется добавить функции в db_manager
        # для получения пользователей, у которых подписка истекает через N дней.
        
        # Пауза на 24 часа
        await asyncio.sleep(24 * 60 * 60)

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
    # Регистрируем обработчики платежей
    bot.register_pre_checkout_query_handler(
        func=lambda query: True,
        callback=pre_checkout_callback,
        pass_bot=True
    )
    bot.register_message_handler(
        content_types=['successful_payment'],
        callback=successful_payment_callback,
        pass_bot=True
    )
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
    subscription_check_task = asyncio.create_task(check_subscriptions(bot))

    await shutdown_event.wait()
    main_logger.warning("Начало процесса graceful shutdown...", extra={'user_id': 'System'})

    main_logger.info("Отмена задачи поллинга...", extra={'user_id': 'System'})
    polling_task.cancel()
    subscription_check_task.cancel()

    try:
        await asyncio.gather(polling_task, subscription_check_task)
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