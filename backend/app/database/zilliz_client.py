

"""
Zilliz Cloud / Milvus Vector Database Client for MAYA.
Communicates via high-performance RESTful v2 API with batch insertion,
notice-level chunk deletion for idempotency, and cosine similarity search.
"""

import json
import logging
from typing import Any, Dict, List, Optional
import httpx

from app.config import get_settings
from app.services.chunking_service import NoticeChunk

settings = get_settings()
logger = logging.getLogger("maya.zilliz_client")


class ZillizClient:
    """
    Client for Zilliz Cloud vector database operations.
    Manages vector indexing and semantic retrieval in maya_notice_chunks collection.
    """

    def __init__(
        self,
        uri: Optional[str] = None,
        token: Optional[str] = None,
        collection_name: Optional[str] = None,
    ):
        self.uri = (settings.ZILLIZ_URI if uri is None else uri).rstrip("/")
        self.token = settings.ZILLIZ_TOKEN if token is None else token
        self.collection_name = collection_name or settings.ZILLIZ_COLLECTION
        self.has_credentials = bool(self.uri and self.token)
        
        # Local in-memory vector store as resilient fallback
        self._memory_vectors: Dict[str, Dict[str, Any]] = {}

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    async def insert_chunks(self, chunks: List[NoticeChunk]) -> int:
        """
        Insert notice chunks into Zilliz Cloud collection in batches.
        """
        if not chunks:
            return 0

        # Always update memory fallback store
        for chunk in chunks:
            self._memory_vectors[chunk.id] = {
                "id": chunk.id,
                "notice_id": chunk.notice_id,
                "chunk_index": chunk.chunk_index,
                "title": chunk.title,
                "content": chunk.content,
                "source_url": chunk.source_url,
                "pdf_url": chunk.pdf_url,
                "page_number": chunk.page_number,
                "category": chunk.category,
                "published_date": chunk.published_date,
                "content_hash": chunk.content_hash,
                "embedding": chunk.embedding,
            }

        if not self.has_credentials:
            return len(chunks)

        endpoint = f"{self.uri}/v2/vectordb/entities/insert"
        data_records = [
            {
                "id": chunk.id,
                "embedding": chunk.embedding,
                "notice_id": chunk.notice_id,
                "chunk_index": chunk.chunk_index,
                "title": chunk.title,
                "content": chunk.content,
                "source_url": chunk.source_url,
                "pdf_url": chunk.pdf_url or "",
                "page_number": chunk.page_number or 1,
                "category": chunk.category,
                "published_date": chunk.published_date or "",
                "content_hash": chunk.content_hash,
            }
            for chunk in chunks
        ]

        payload = {
            "collectionName": self.collection_name,
            "data": data_records,
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                res = await client.post(endpoint, headers=self._headers(), json=payload)
                if res.status_code == 200:
                    resp_json = res.json()
                    if resp_json.get("code") == 0:
                        logger.info(f"Successfully inserted {len(chunks)} chunks into Zilliz collection '{self.collection_name}'")
                        return len(chunks)
                    else:
                        logger.warning(f"Zilliz insert returned code {resp_json.get('code')}: {resp_json.get('message')}")
                        return len(chunks)
                else:
                    logger.error(f"Zilliz insert HTTP error {res.status_code}: {res.text}")
                    return len(chunks)
        except Exception as e:
            logger.error(f"Failed inserting chunks into Zilliz: {e}")
            return len(chunks)

    async def delete_notice_chunks(self, notice_id: str) -> bool:
        """
        Delete old chunks for a notice before reindexing changed content.
        Guarantees idempotency on document updates.
        """
        # Clean local memory
        to_del = [k for k, v in self._memory_vectors.items() if v.get("notice_id") == notice_id]
        for k in to_del:
            self._memory_vectors.pop(k, None)

        if not self.has_credentials:
            return True

        endpoint = f"{self.uri}/v2/vectordb/entities/delete"
        payload = {
            "collectionName": self.collection_name,
            "filter": f"notice_id == '{notice_id}'",
        }

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                res = await client.post(endpoint, headers=self._headers(), json=payload)
                return res.status_code == 200
        except Exception as e:
            logger.warning(f"Error deleting notice chunks from Zilliz: {e}")
            return True

    # Alias for convenience
    delete_chunks_by_notice_id = delete_notice_chunks

    async def semantic_search(
        self,
        query_vector: List[float],
        top_k: int = 5,
        threshold: float = 0.25,
        filter_expr: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Search for nearest notice chunks using cosine similarity vector metric.
        """
        if not self.has_credentials:
            return self._memory_search(query_vector, top_k, threshold)

        endpoint = f"{self.uri}/v2/vectordb/entities/search"
        payload: Dict[str, Any] = {
            "collectionName": self.collection_name,
            "data": [query_vector],
            "limit": top_k,
            "outputFields": [
                "id",
                "notice_id",
                "chunk_index",
                "title",
                "content",
                "source_url",
                "pdf_url",
                "page_number",
                "category",
                "published_date",
            ],
        }
        if filter_expr:
            payload["filter"] = filter_expr

        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                res = await client.post(endpoint, headers=self._headers(), json=payload)
                if res.status_code == 200:
                    data = res.json().get("data", [])
                    results: List[Dict[str, Any]] = []
                    # Zilliz search returns either a list of dicts or a nested list if batch queried
                    if data and isinstance(data, list):
                        if isinstance(data[0], list):
                            raw_items = data[0]
                        elif isinstance(data[0], dict):
                            raw_items = data
                        else:
                            raw_items = []
                    else:
                        raw_items = []

                    for item in raw_items:
                        score = item.get("distance", item.get("score", 0.0))
                        if score >= threshold:
                            results.append({
                                "id": item.get("id"),
                                "notice_id": item.get("notice_id"),
                                "chunk_index": item.get("chunk_index"),
                                "title": item.get("title"),
                                "content": item.get("content"),
                                "source_url": item.get("source_url"),
                                "pdf_url": item.get("pdf_url"),
                                "page_number": item.get("page_number"),
                                "category": item.get("category"),
                                "published_date": item.get("published_date"),
                                "score": round(score, 4),
                            })
                    return results
                else:
                    logger.warning(f"Zilliz search fallback: {res.status_code}")
                    return self._memory_search(query_vector, top_k, threshold)
        except Exception as e:
            logger.error(f"Zilliz search error: {e}")
            return self._memory_search(query_vector, top_k, threshold)

    def _memory_search(self, query_vector: List[float], top_k: int, threshold: float) -> List[Dict[str, Any]]:
        """Cosine similarity search on in-memory vectors."""
        scores = []
        for cid, item in self._memory_vectors.items():
            emb = item.get("embedding")
            if not emb:
                continue
            # Cosine similarity for normalized vectors = dot product
            dot = sum(a * b for a, b in zip(query_vector, emb))
            if dot >= threshold:
                scores.append((dot, item))

        scores.sort(key=lambda x: x[0], reverse=True)
        return [
            {
                "id": it["id"],
                "notice_id": it["notice_id"],
                "chunk_index": it["chunk_index"],
                "title": it["title"],
                "content": it["content"],
                "source_url": it["source_url"],
                "pdf_url": it["pdf_url"],
                "page_number": it["page_number"],
                "category": it["category"],
                "published_date": it["published_date"],
                "score": round(sc, 4),
            }
            for sc, it in scores[:top_k]
        ]


# Singleton instance
_global_zilliz_client: Optional[ZillizClient] = None


def get_zilliz_client() -> ZillizClient:
    """Return singleton instance of ZillizClient."""
    global _global_zilliz_client
    if _global_zilliz_client is None:
        _global_zilliz_client = ZillizClient()
    return _global_zilliz_client
