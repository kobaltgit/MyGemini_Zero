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
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta

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

    async def add_chunk(self, dialog_id: int, text_content: str, metadata: Dict[str, Any]):
        """
        Добавляет текст (например, сообщение или сводку) в долговременную память,
        обогащая его метаданными.

        Текст сначала разбивается на чанки, затем для каждого чанка создается
        эмбеддинг, и он сохраняется в соответствующей коллекции диалога.

        Args:
            dialog_id (int): ID диалога, к которому относится текст.
            text_content (str): Текст для добавления в память.
            metadata (Dict[str, Any]): Словарь метаданных, например,
                                       {'role': 'user', 'content_type': 'text',
                                        'timestamp': 'ISO_STRING', 'user_id': user_id}.
        """
        if not text_content.strip():
            return

        logger.info(f"Добавление чанка в память для диалога {dialog_id}...")
        collection = self._get_or_create_collection(dialog_id)
        chunks = self.text_splitter.split_text(text_content)

        if not chunks:
            return

        # Создаем уникальные ID для каждого чанка
        ids = [f"{dialog_id}_{int(time.time())}_{i}" for i, _ in enumerate(chunks)]

        # Генерируем эмбеддинги для всех чанков одним запросом
        embeddings = await self.embedding_model.aembed_documents(chunks)

        # Дублируем метаданные для каждого чанка
        metadatas_list = [metadata] * len(chunks)

        # Добавляем чанки, их эмбеддинги и метаданные в коллекцию
        collection.add(
            embeddings=embeddings,
            documents=chunks,
            metadatas=metadatas_list, # <--- ИСПОЛЬЗУЕМ ПЕРЕДАННЫЕ МЕТАДАННЫЕ
            ids=ids
        )
        logger.info(f"Добавлено {len(chunks)} чанков в память для диалога {dialog_id}.")

    async def search_relevant_chunks(
        self, 
        dialog_id: int, 
        query_text: str, 
        n_results: int = 3, 
        metadata_filter: Optional[Dict[str, Any]] = None, 
        keyword_filter: Optional[Dict[str, Any]] = None
    ) -> List[str]:
        """
        Выполняет гибридный поиск по памяти диалога с фильтрацией.

        Args:
            dialog_id (int): ID диалога для поиска.
            query_text (str): Поисковый запрос (например, вопрос пользователя).
            n_results (int): Количество релевантных фрагментов для возврата.
            metadata_filter (Optional[Dict[str, Any]]): Фильтр по метаданным.
                Пример: `{"content_type": "document"}`
            keyword_filter (Optional[Dict[str, Any]]): Фильтр по содержимому текста.
                Пример: `{"$contains": "важное_слово"}`

        Returns:
            List[str]: Список наиболее релевантных текстовых фрагментов из памяти.
        """
        try:
            collection = self._get_or_create_collection(dialog_id)
            if collection.count() == 0:
                logger.debug(f"Поиск в диалоге {dialog_id} пропущен, т.к. память пуста.")
                return []

            # Создаем эмбеддинг для семантического поиска
            query_embedding = await self.embedding_model.aembed_query(query_text)

            # Выполняем поиск, используя семантику и фильтры
            results = collection.query(
                query_embeddings=[query_embedding],
                n_results=min(n_results, collection.count()),
                where=metadata_filter,
                where_document=keyword_filter
            )

            found_docs = results.get('documents', [[]])[0]
            logger.info(
                f"Найдено {len(found_docs)} релевантных чанков в диалоге {dialog_id} "
                f"с фильтрами: метаданные={metadata_filter}, ключевые слова={keyword_filter}."
            )
            return found_docs

        except Exception as e:
            logger.exception(f"Ошибка при поиске в векторной базе для диалога {dialog_id}: {e}")
            return []

    async def add_summary_chunk(self, dialog_id: int, user_id: int, summary_text: str, original_period_start: datetime, original_period_end: datetime):
        """
        Добавляет суммаризированный чанк в долговременную память.

        Эти чанки будут иметь специальный тип 'summary' и метаданные, указывающие
        период, который они охватывают.

        Args:
            dialog_id (int): ID диалога, к которому относится сводка.
            user_id (int): ID пользователя.
            summary_text (str): Текст сводки.
            original_period_start (datetime): Начало периода, который охватывает сводка.
            original_period_end (datetime): Конец периода, который охватывает сводка.
        """
        if not summary_text.strip():
            return

        logger.info(f"Добавление summary чанка для диалога {dialog_id}, охватывающего период с {original_period_start.isoformat()} по {original_period_end.isoformat()}...")
        collection = self._get_or_create_collection(dialog_id)

        # Создаем специальный ID для summary
        summary_id = f"summary_{dialog_id}_{int(time.time())}"

        # Генерируем эмбеддинг для сводки
        summary_embedding = await self.embedding_model.aembed_documents([summary_text])

        # Метаданные для summary чанка
        summary_metadata = {
            "type": "summary",
            "dialog_id": dialog_id,
            "user_id": user_id,
            "period_start": original_period_start.isoformat(),
            "period_end": original_period_end.isoformat(),
            "created_at": datetime.now(datetime.timezone.utc).isoformat()
        }

        collection.add(
            embeddings=summary_embedding,
            documents=[summary_text],
            metadatas=[summary_metadata],
            ids=[summary_id]
        )
        logger.info(f"Summary чанк для диалога {dialog_id} успешно добавлен.")

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

    async def delete_chunks_by_dialog_and_timestamp(self, dialog_id: int, cutoff_timestamp: datetime):
        """
        Удаляет все чанки из указанного диалога, которые были созданы до указанной временной метки.
        Исключает чанки типа 'summary', чтобы не удалять архивированные сводки.

        Args:
            dialog_id (int): ID диалога, из которого нужно удалить чанки.
            cutoff_timestamp (datetime): Временная метка, до которой чанки должны быть удалены.
        """
        collection_name = f"dialog_{dialog_id}"

        try:
            collection = self.client.get_collection(name=collection_name)

            # Удаляем чанки, где timestamp < cutoff_timestamp и тип не 'summary'
            # (предполагаем, что timestamp хранится в метаданных и является строкой ISO)
            results = collection.get(
                where={
                    "timestamp": {"$lt": cutoff_timestamp.isoformat()},
                    "type": {"$ne": "summary"}
                },
                # Здесь мы запрашиваем только ID, так как нам нужно удалить их
                # Примечание: ChromaDB пока не поддерживает прямое удаление по where_document
                # напрямую без предварительного получения ID.
                # Поэтому мы сначала получаем ID, а затем удаляем.
                # Это может быть неэффективно для очень больших коллекций.
            )

            ids_to_delete = results.get('ids', [])

            if ids_to_delete:
                collection.delete(ids=ids_to_delete)
                logger.info(f"Удалено {len(ids_to_delete)} старых чанков из диалога {dialog_id} до {cutoff_timestamp.isoformat()}.")
            else:
                logger.debug(f"Нет старых чанков для удаления в диалоге {dialog_id} до {cutoff_timestamp.isoformat()}.")

        except chromadb.errors.NotFoundError:
            logger.warning(f"Коллекция '{collection_name}' для диалога {dialog_id} не найдена. Нечего удалять.")
        except Exception as e:
            logger.exception(f"Ошибка при удалении старых чанков для диалога {dialog_id}: {e}")

    def delete_all_user_collections(self, dialog_ids: List[int]):
        """
        Удаляет все коллекции, связанные со списком ID диалогов.
        Вызывается при полной очистке данных пользователя.

        Args:
            dialog_ids (List[int]): Список идентификаторов диалогов для удаления.
        """
        if not dialog_ids:
            return

        logger.warning(f"Начато удаление всех коллекций для диалогов: {dialog_ids}.")
        for dialog_id in dialog_ids:
            collection_name = f"dialog_{dialog_id}"
            try:
                self.client.delete_collection(name=collection_name)
                logger.info(f"Векторная память (коллекция '{collection_name}') для диалога {dialog_id} успешно удалена.")
            except (ValueError, chromadb.errors.NotFoundError):
                logger.warning(f"Попытка удаления несуществующей векторной памяти (коллекции '{collection_name}').")
            except Exception as e:
                logger.exception(f"Ошибка при удалении векторной памяти для диалога {dialog_id}: {e}")        
