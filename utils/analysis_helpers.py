# --- START OF FILE utils/analysis_helpers.py ---

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

import re
from collections import Counter
from typing import List, Dict, Any

from logger_config import get_logger

logger = get_logger(__name__)

# Расширяем базовый набор стоп-слов
STOP_WORDS = set([
    'и', 'в', 'во', 'не', 'что', 'он', 'на', 'я', 'с', 'со', 'как', 'а', 'то',
    'все', 'она', 'так', 'его', 'но', 'да', 'ты', 'к', 'у', 'же', 'вы', 'за',
    'бы', 'по', 'только', 'ее', 'мне', 'было', 'вот', 'от', 'меня', 'еще', 'нет',
    'о', 'из', 'ему', 'теперь', 'когда', 'даже', 'ну', 'вдруг', 'ли', 'если',
    'уже', 'или', 'ни', 'быть', 'был', 'него', 'до', 'вас', 'нибудь', 'опять',
    'уж', 'вам', 'ведь', 'там', 'потом', 'себя', 'ничего', 'ей', 'может',
    'они', 'тут', 'где', 'есть', 'надо', 'ней', 'для', 'мы', 'тебя', 'их', 'чем',
    'была', 'сам', 'чтоб', 'без', 'будто', 'чего', 'раз', 'тоже', 'себе', 'под',
    'жи', 'будет', 'ж', 'тогда', 'кто', 'этот', 'того', 'потому', 'этого', 'какой',
    'совсем', 'ним', 'здесь', 'этом', 'один', 'почти', 'мой', 'тем', 'чтобы',
    'нее', 'сейчас', 'были', 'куда', 'зачем', 'всех', 'никогда', 'можно', 'при',
    'наконец', 'два', 'об', 'другой', 'хоть', 'после', 'над', 'больше', 'тот',
    'через', 'эти', 'нас', 'про', 'всего', 'них', 'какая', 'много', 'разве',
    'три', 'эту', 'моя', 'впрочем', 'хорошо', 'свою', 'этой', 'перед', 'иногда',
    'лучше', 'чуть', 'том', 'нельзя', 'такой', 'им', 'более', 'всегда', 'конечно',
    'изображение', 'картинка', 'опиши', 'подробно', 'изображено', 'справку', 'энциклопедическую', 'предоставь',
    'всю', 'между',
    # Специфичные для бота/общения слова
    'бот', 'gemini', 'чат', 'пожалуйста', 'спасибо', 'привет', 'здравствуй', 'пока',
    'вопрос', 'ответ', 'текст', 'сообщение', 'файл', 'картинка', 'изображение', 'ссылка',
    'перевести', 'перевод', 'язык', 'изложить', 'кратко', 'суть', 'тема',
    'план', 'доход', 'деньги', 'заработать', 'цель',
    'напоминание', 'напомнить', 'время', 'дата', 'установить',
    'история', 'диалог', 'посмотреть',
    'настройки', 'стиль', 'таймзона', 'пояс',
    'помощь', 'справка', 'умеешь', 'можешь', 'функции',
    'делать', 'сделать', 'хотеть', 'мочь', 'использовать', 'сказать', 'рассказать', 'дать',
    'который', 'какой', 'это', 'также'
])


def extract_frequent_topics(conversation_history: List[Dict[str, Any]], top_n: int = 7, min_word_length: int = 4) -> List[str]:
    """
    Извлекает наиболее частые ключевые слова (темы) из истории разговоров.

    Эта функция обрабатывает только сообщения пользователя, очищает их от
    стоп-слов и коротких слов, а затем возвращает N самых популярных слов.
    Важно: полный текст сообщений никогда не логируется для сохранения
    приватности.

    Args:
        conversation_history (List[Dict[str, Any]]): Список словарей,
            каждый из которых представляет сообщение. Ожидаются ключи
            'role' и 'message_text'.
        top_n (int): Количество наиболее частых тем для возврата.
        min_word_length (int): Минимальная длина слова для учета.

    Returns:
        List[str]: Список строк, представляющих наиболее частые темы.
    """
    if not conversation_history:
        logger.debug("История разговоров пуста, анализ тем невозможен.")
        return []

    # Собираем только сообщения пользователя ('user')
    user_messages_text = " ".join([
        item.get('message_text', '').lower()
        for item in conversation_history
        if item.get('role') == 'user' and item.get('message_text')
    ])

    if not user_messages_text:
        logger.debug("Сообщения пользователя в истории не найдены или пусты.")
        return []

    # Очистка текста: оставляем только кириллицу, латиницу и пробелы
    cleaned_text = re.sub(r'[^а-яёa-z\s]', '', user_messages_text)
    cleaned_text = re.sub(r'\s+', ' ', cleaned_text).strip()
    logger.debug(f"Длина очищенного текста для анализа тем: {len(cleaned_text)}")

    # Разбиваем на слова
    words = cleaned_text.split()
    logger.debug(f"Общее количество слов в тексте пользователя: {len(words)}")

    # Фильтруем слова: убираем стоп-слова и короткие слова
    filtered_words = [
        word for word in words
        if word not in STOP_WORDS and len(word) >= min_word_length
    ]
    logger.debug(f"Количество слов после фильтрации (удаление стоп-слов): {len(filtered_words)}")

    if not filtered_words:
        logger.debug("После фильтрации не осталось слов для анализа тем.")
        return []

    # Подсчитываем частоту слов
    word_counts = Counter(filtered_words)
    logger.debug(f"10 самых частых слов: {word_counts.most_common(10)}")

    # Получаем top_n наиболее частых слов
    top_topics = [word for word, count in word_counts.most_common(top_n)]
    logger.debug(f"Итоговые top-{top_n} тем: {top_topics}")

    return top_topics

# --- END OF FILE utils/analysis_helpers.py ---