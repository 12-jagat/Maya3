"""
RAG Document Retrieval Service.
Generates 384-dimensional local query embeddings, queries Zilliz Cloud collection,
applies cosine similarity filtering, deduplicates overlapping passages,
and applies lightweight lexical re-ranking.
"""

import logging
import re
from typing import Any, Dict, List, Optional

from app.config import get_settings
from app.database.zilliz_client import get_zilliz_client
from app.services.embedding_service import get_embedding_service

settings = get_settings()
logger = logging.getLogger("maya.retrieval_service")


class RetrievedChunk:
    """Passage retrieved from vector storage with metadata and similarity score."""

    def __init__(
        self,
        id: str,
        notice_id: str,
        title: str,
        content: str,
        source_url: str,
        pdf_url: Optional[str] = None,
        page_number: Optional[int] = 1,
        category: Optional[str] = "General",
        published_date: Optional[str] = None,
        score: float = 0.0,
    ):
        self.id = id
        self.notice_id = notice_id
        self.title = title
        self.content = content
        self.source_url = source_url
        self.pdf_url = pdf_url
        self.page_number = page_number or 1
        self.category = category or "General"
        self.published_date = published_date
        self.score = score

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "notice_id": self.notice_id,
            "title": self.title,
            "content": self.content,
            "source_url": self.source_url,
            "pdf_url": self.pdf_url,
            "page_number": self.page_number,
            "category": self.category,
            "published_date": self.published_date,
            "score": round(self.score, 4),
        }


class RetrievalService:
    """
    Coordinates semantic vector retrieval against the official GGSIPU circular collection in Zilliz.
    """

    def __init__(
        self,
        top_k: Optional[int] = None,
        similarity_threshold: Optional[float] = None,
    ):
        self.top_k = top_k or settings.RAG_TOP_K
        self.similarity_threshold = similarity_threshold or settings.RAG_SIMILARITY_THRESHOLD
        self.embedding_service = get_embedding_service()
        self.zilliz_client = get_zilliz_client()

    async def retrieve_relevant_chunks(
        self,
        query: str,
        top_k: Optional[int] = None,
        threshold: Optional[float] = None,
        category_filter: Optional[str] = None,
    ) -> List[RetrievedChunk]:
        """
        Execute dense vector retrieval with local MiniLM embeddings.
        Applies deduplication and lexical re-ranking.
        """
        clean_q = query.strip()
        if not clean_q:
            return []

        limit = top_k or self.top_k
        min_threshold = threshold if threshold is not None else self.similarity_threshold

        try:
            # 1. Generate 384-d dense vector locally
            query_vector = self.embedding_service.generate_query_embedding(clean_q)

            # 2. Query Zilliz Cloud (fetch candidate pool of limit * 2 to allow hybrid rerank)
            candidate_limit = max(limit * 2, 8)
            filter_expr = f"category == '{category_filter}'" if category_filter else None

            raw_results = await self.zilliz_client.semantic_search(
                query_vector=query_vector,
                top_k=candidate_limit,
                threshold=0.0,  # Fetch candidates, then apply calibrated threshold
                filter_expr=filter_expr,
            )

            if not raw_results:
                logger.info(f"No vector matches found for query: '{clean_q}'")
                return []

            # 3. Convert to structured chunks & deduplicate
            seen_hashes = set()
            unique_chunks: List[RetrievedChunk] = []

            for r in raw_results:
                content = r.get("content", "").strip()
                if not content:
                    continue

                # Near-duplicate hash check (first 60 chars of content)
                content_key = re.sub(r"\W+", "", content[:60].lower())
                if content_key in seen_hashes:
                    continue
                seen_hashes.add(content_key)

                raw_score = float(r.get("score", 0.0))

                chunk = RetrievedChunk(
                    id=r.get("id", ""),
                    notice_id=r.get("notice_id", ""),
                    title=r.get("title") or "Official University Circular",
                    content=content,
                    source_url=r.get("source_url", ""),
                    pdf_url=r.get("pdf_url"),
                    page_number=r.get("page_number", 1),
                    category=r.get("category", "General"),
                    published_date=r.get("published_date"),
                    score=raw_score,
                )
                unique_chunks.append(chunk)

            # 4. Optional hybrid re-ranking: boost score with exact keyword matches
            query_terms = set(re.findall(r"\w{3,}", clean_q.lower()))
            for chk in unique_chunks:
                content_lower = chk.content.lower()
                title_lower = chk.title.lower()
                matches = sum(1 for term in query_terms if term in content_lower or term in title_lower)
                # Small lexical boost (up to +0.05)
                lexical_boost = min(matches * 0.015, 0.05)
                chk.score += lexical_boost

            # 5. Filter by threshold (or relax if all scores are low)
            filtered = [c for c in unique_chunks if c.score >= min_threshold]

            # If strict threshold excluded everything, fall back to top candidates above a baseline
            if not filtered and unique_chunks:
                baseline = max(min_threshold * 0.25, 0.05)
                filtered = [c for c in unique_chunks if c.score >= baseline]

            # Sort descending by score
            filtered.sort(key=lambda x: x.score, reverse=True)
            final_selection = filtered[:limit]

            logger.info(
                f"Retrieved {len(final_selection)} chunks for query '{clean_q}' (threshold={min_threshold})."
            )
            return final_selection

        except Exception as e:
            logger.error(f"Error during document retrieval: {e}")
            return []


# Singleton instance
_retrieval_service: Optional[RetrievalService] = None


def get_retrieval_service() -> RetrievalService:
    """Return singleton instance of RetrievalService."""
    global _retrieval_service
    if _retrieval_service is None:
        _retrieval_service = RetrievalService()
    return _retrieval_service
