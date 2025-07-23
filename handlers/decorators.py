# File: handlers/decorators.py
"""
Модуль для хранения декораторов, используемых в обработчиках.
"""
from functools import wraps
from telebot.async_telebot import AsyncTeleBot
from telebot import types

from config.settings import ADMIN_USER_ID
from database import db_manager
from utils import localization as loc
from logger_config import get_logger

logger = get_logger(__name__)


def admin_required(func):
    """
    Декоратор для проверки, является ли пользователь администратором.
    """
    @wraps(func)
    async def wrapper(message_or_call: types.Message | types.CallbackQuery, *args, **kwargs):
        user_id = message_or_call.from_user.id
        if user_id != ADMIN_USER_ID:
            lang_code = await db_manager.get_user_language(user_id)
            error_text = loc.get_text('admin.not_admin', lang_code)
            
            # Нам нужен экземпляр бота для ответа
            bot = None
            if args and isinstance(args[0], AsyncTeleBot):
                bot = args[0]
            elif 'bot' in kwargs:
                bot = kwargs['bot']
            
            if bot:
                if isinstance(message_or_call, types.Message):
                    await bot.reply_to(message_or_call, error_text)
                elif isinstance(message_or_call, types.CallbackQuery):
                    await bot.answer_callback_query(message_or_call.id, text=error_text, show_alert=True)
            
            logger.warning(f"Попытка несанкционированного доступа к админ-функции от user_id: {user_id}")
            return
        return await func(message_or_call, *args, **kwargs)
    return wrapper