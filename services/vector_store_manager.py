# File: services/vector_store_manager.py

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
Сервис для управления долговременной памятью на основе векторной базы данных ChromaDB.

Этот модуль отвечает за:
1. Создание и управление постоянным хранилищем векторов (эмбеддингов).
2. Преобразование текста в векторы с помощью модели Google Generative AI.
3. Добавление текста (истории диалогов, документов) в память.
4. Выполнение семантического поиска для извлечения релевантного контекста.
5. Очистку памяти при удалении диалогов.
"""
import os
import time
from typing import List, Optional

import chromadb
from chromadb.config import Settings # <-- НОВЫЙ ИМПОРТ
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings

from config.settings import BASE_DIR
from logger_config import get_logger

logger = get_logger('vector_store')

# Директория для хранения файлов векторной базы данных
VECTOR_STORE_PATH = os.path.join(BASE_DIR, "vector_store")
os.makedirs(VECTOR_STORE_PATH, exist_ok=True)


class VectorStoreManager:
    """
    Управляет операциями с векторной базой данных ChromaDB для обеспечения
    долговременной памяти для каждого диалога пользователя.
    """

    def __init__(self, api_key: str):
        """
        Инициализирует менеджер векторного хранилища.

        Args:
            api_key (str): API-ключ Google, необходимый для модели эмбеддингов.

        Raises:
            ValueError: Если API-ключ не предоставлен.
        """
        if not api_key:
            raise ValueError("API-ключ Google необходим для инициализации модели эмбеддингов.")

        # --- ИЗМЕНЕНИЕ 1: Отключаем телеметрию ---
        # 1. Инициализируем клиент ChromaDB для постоянного хранения
        self.client = chromadb.PersistentClient(
            path=VECTOR_STORE_PATH,
            settings=Settings(anonymized_telemetry=False) # <-- ДОБАВЛЕНА ЭТА СТРОКА
        )

        # 2. Инициализируем модель для создания эмбеддингов
        self.embedding_model = GoogleGenerativeAIEmbeddings(
            model="models/text-embedding-004",  # Одна из самых эффективных моделей Google для этого
            google_api_key=api_key
        )

        # 3. Инициализируем сплиттер для разбивки текста на чанки
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=500,  # Оптимальный размер чанка для хороших эмбеддингов
            chunk_overlap=50,
            length_function=len,
        )
        logger.debug("VectorStoreManager инициализирован.")

    def _get_or_create_collection(self, dialog_id: int) -> chromadb.Collection:
        """
        Получает или создает коллекцию в ChromaDB для указанного диалога.
        Каждый диалог хранится в отдельной коллекции для изоляции данных.

        Args:
            dialog_id (int): Уникальный идентификатор диалога.

        Returns:
            chromadb.Collection: Объект коллекции ChromaDB.
        """
        collection_name = f"dialog_{dialog_id}"
        # get_or_create_collection является потокобезопасной
        collection = self.client.get_or_create_collection(
            name=collection_name,
            # Важно указать, что мы используем внешнюю модель для эмбеддингов
            # embedding_function=self.embedding_model не работает напрямую,
            # поэтому мы будем создавать эмбеддинги вручную.
        )
        return collection

    async def add_dialog_text(self, dialog_id: int, text: str):
        """
        Добавляет текст (например, сообщение из диалога) в долговременную память.

        Текст сначала разбивается на чанки, затем для каждого чанка создается
        эмбеддинг, и он сохраняется в соответствующей коллекции диалога.

        Args:
            dialog_id (int): ID диалога, к которому относится текст.
            text (str): Текст для добавления в память.
        """
        if not text.strip():
            return

        logger.info(f"Добавление текста в память для диалога {dialog_id}...")
        collection = self._get_or_create_collection(dialog_id)
        chunks = self.text_splitter.split_text(text)

        if not chunks:
            return

        # Создаем уникальные ID для каждого чанка
        ids = [f"{dialog_id}_{int(time.time())}_{i}" for i, _ in enumerate(chunks)]

        # Генерируем эмбеддинги для всех чанков одним запросом
        embeddings = await self.embedding_model.aembed_documents(chunks)

        # Добавляем чанки, их эмбеддинги и метаданные в коллекцию
        collection.add(
            embeddings=embeddings,
            documents=chunks,
            metadatas=[{"source": "dialog_history"}] * len(chunks),
            ids=ids
        )
        logger.info(f"Добавлено {len(chunks)} чанков в память для диалога {dialog_id}.")

    async def search_relevant_chunks(self, dialog_id: int, query_text: str, n_results: int = 3) -> List[str]:
        """
        Выполняет семантический поиск по памяти диалога.

        Args:
            dialog_id (int): ID диалога для поиска.
            query_text (str): Поисковый запрос (например, вопрос пользователя).
            n_results (int): Количество релевантных фрагментов для возврата.

        Returns:
            List[str]: Список наиболее релевантных текстовых фрагментов из памяти.
        """
        try:
            collection = self._get_or_create_collection(dialog_id)
            if collection.count() == 0:
                logger.debug(f"Поиск в диалоге {dialog_id} пропущен, т.к. память пуста.")
                return []
            
            # Создаем эмбеддинг для поискового запроса
            query_embedding = await self.embedding_model.aembed_query(query_text)

            # Выполняем поиск
            results = collection.query(
                query_embeddings=[query_embedding],
                n_results=min(n_results, collection.count()) # Убедимся, что не запрашиваем больше, чем есть
            )
            
            found_docs = results.get('documents', [[]])[0]
            logger.info(f"Найдено {len(found_docs)} релевантных чанков в памяти для диалога {dialog_id}.")
            return found_docs

        except Exception as e:
            logger.exception(f"Ошибка при поиске в векторной базе для диалога {dialog_id}: {e}")
            return []

    def delete_dialog_memory(self, dialog_id: int):
        """
        Полностью удаляет всю память, связанную с указанным диалогом.

        Args:
            dialog_id (int): ID диалога, память которого нужно очистить.
        """
        collection_name = f"dialog_{dialog_id}"
        try:
            self.client.delete_collection(name=collection_name)
            logger.info(f"Память (коллекция '{collection_name}') для диалога {dialog_id} успешно удалена.")
        # --- ИЗМЕНЕНИЕ 2: Улучшаем обработку ошибки ---
        except (ValueError, chromadb.errors.NotFoundError):
            logger.warning(f"Попытка удаления несуществующей памяти (коллекции '{collection_name}') для диалога {dialog_id}. Это нормальная ситуация.")
        except Exception as e:
            logger.exception(f"Ошибка при удалении памяти для диалога {dialog_id}: {e}")