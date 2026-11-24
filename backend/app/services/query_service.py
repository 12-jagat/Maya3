"""
Query Processing and Contextual Rewriting Service.
Validates student questions, detects follow-ups, and resolves ambiguous pronouns
against conversation history to create optimal standalone retrieval queries.
"""

import logging
import re
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("maya.query_service")

# Common follow-up reference patterns
FOLLOWUP_PRONOUNS = re.compile(
    r"\b(it|its|this|that|these|those|the same|that notice|the circular|the exam|the notification|the datesheet)\b",
    re.IGNORECASE,
)

FOLLOWUP_QUESTIONS = re.compile(
    r"^(what about|when was it|why|how come|explain it|tell me more|any changes|can you clarify|simpler language|in detail|what else|is there any)\b",
    re.IGNORECASE,
)


class QueryService:
    """
    Handles natural language query validation, contextual follow-up detection,
    and standalone query expansion for vector search.
    """

    @classmethod
    def clean_query(cls, raw_query: str) -> str:
        """Strip extraneous whitespace, control characters, and normalize question."""
        if not raw_query:
            return ""
        cleaned = re.sub(r"[\x00-\x1F\x7F]", "", raw_query)
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        return cleaned

    @classmethod
    def is_followup_query(cls, query: str, history: Optional[List[Dict[str, Any]]] = None) -> bool:
        """
        Determine if the user query is a follow-up depending on conversation context.
        """
        if not history or len(history) == 0:
            return False

        q = query.strip().lower()
        if len(q.split()) <= 4 and (FOLLOWUP_PRONOUNS.search(q) or FOLLOWUP_QUESTIONS.search(q)):
            return True
        if FOLLOWUP_QUESTIONS.search(q):
            return True
        if FOLLOWUP_PRONOUNS.search(q):
            return True

        return False

    @classmethod
    def reformulate_retrieval_query(
        cls,
        current_query: str,
        conversation_history: Optional[List[Dict[str, Any]]] = None,
    ) -> str:
        """
        Generate an expanded standalone retrieval query if the question is a follow-up.
        Strictly preserves the student's original query intent without fabricating topics.
        """
        clean_q = cls.clean_query(current_query)
        if not clean_q:
            return ""

        if not conversation_history or not cls.is_followup_query(clean_q, conversation_history):
            return clean_q

        # Extract recent user queries and assistant titles from history (up to last 3 exchanges)
        context_keywords: List[str] = []
        for msg in reversed(conversation_history[-4:]):
            content = msg.get("content", "")
            role = msg.get("role", "")

            # If previous assistant message had citations, grab notice titles
            if role == "assistant" and msg.get("citations"):
                for cit in msg.get("citations", []):
                    title = cit.get("title") or cit.get("notice_title")
                    if title and title not in context_keywords:
                        context_keywords.append(title)

            # If previous user query was substantial, extract key subject
            elif role == "user" and len(content.split()) >= 4:
                # Remove common query prefixes
                subj = re.sub(r"^(what is|when is|where is|how to|tell me about|explain)\s+", "", content, flags=re.I)
                subj = subj.strip("?. ")
                if subj and subj not in context_keywords:
                    context_keywords.append(subj)

        if not context_keywords:
            return clean_q

        # Combine dominant historical subject with current query focus
        primary_subject = context_keywords[0]
        # Avoid redundant duplication
        if primary_subject.lower() in clean_q.lower():
            return clean_q

        standalone_query = f"{primary_subject} {clean_q}"
        logger.info(f"Expanded follow-up query: '{clean_q}' -> '{standalone_query}'")
        return standalone_query


# Singleton instance
_query_service: Optional[QueryService] = None


def get_query_service() -> QueryService:
    """Return singleton instance of QueryService."""
    global _query_service
    if _query_service is None:
        _query_service = QueryService()
    return _query_service
