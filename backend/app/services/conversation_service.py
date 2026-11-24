"""
Conversation and Message Management Service.
Coordinates thread persistence, message history retrieval, dynamic title generation,
and citation storage via Supabase PostgREST with resilient fallback.
"""

from datetime import datetime, timezone
import json
import logging
from typing import Any, Dict, List, Optional
import uuid
import httpx

from app.config import get_settings
from app.database.supabase_client import get_supabase_client
from app.schemas.chat import CitationItem, ConversationDetail, ConversationSummary

settings = get_settings()
logger = logging.getLogger("maya.conversation_service")


class ConversationService:
    """
    Manages student conversation threads, chat message history, and citations.
    Integrates with Supabase PostgreSQL and maintains resilient in-memory fallback.
    """

    def __init__(self):
        self.supabase = get_supabase_client()
        # In-memory storage for environments where Supabase tables are pending migration
        self._memory_conversations: Dict[str, Dict[str, Any]] = {}
        self._memory_messages: Dict[str, List[Dict[str, Any]]] = {}

    def _generate_title(self, first_message: str) -> str:
        """Derive a clean conversation title from the student's initial prompt."""
        clean = first_message.strip()
        if len(clean) <= 45:
            return clean
        truncated = clean[:42].rsplit(" ", 1)[0]
        return f"{truncated}..."

    async def get_or_create_conversation(
        self,
        conversation_id: Optional[str] = None,
        initial_prompt: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Fetch existing conversation or create a new thread with unique ID."""
        now = datetime.now(timezone.utc).isoformat()

        if conversation_id:
            # Check existing
            conv = await self.get_conversation(conversation_id)
            if conv:
                return conv

        # Create new conversation
        new_id = conversation_id or str(uuid.uuid4())
        title = self._generate_title(initial_prompt) if initial_prompt else "New Conversation"

        record = {
            "id": new_id,
            "title": title,
            "created_at": now,
            "updated_at": now,
        }

        # Cache locally
        self._memory_conversations[new_id] = record
        if new_id not in self._memory_messages:
            self._memory_messages[new_id] = []

        # Attempt Supabase insert
        if self.supabase.has_credentials:
            endpoint = f"{self.supabase.base_url}/rest/v1/conversations"
            headers = self.supabase._headers(return_representation=True)
            try:
                async with httpx.AsyncClient(timeout=8.0) as client:
                    res = await client.post(endpoint, json=record, headers=headers)
                    if res.status_code in (200, 201):
                        data = res.json()
                        if data and isinstance(data, list):
                            return data[0]
            except Exception as e:
                logger.warning(f"Supabase conversation insert fallback: {e}")

        return record

    async def get_conversation(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        """Fetch a single conversation metadata record."""
        # Check memory first
        if conversation_id in self._memory_conversations:
            return self._memory_conversations[conversation_id]

        if not self.supabase.has_credentials:
            return None

        endpoint = f"{self.supabase.base_url}/rest/v1/conversations"
        params = {"id": f"eq.{conversation_id}", "limit": "1"}
        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                res = await client.get(endpoint, params=params, headers=self.supabase._headers())
                if res.status_code == 200:
                    data = res.json()
                    if data:
                        self._memory_conversations[conversation_id] = data[0]
                        return data[0]
        except Exception as e:
            logger.warning(f"Error reading conversation from Supabase: {e}")

        return None

    async def list_conversations(self, limit: int = 25) -> List[ConversationSummary]:
        """List recent conversations sorted by latest update."""
        summaries: List[ConversationSummary] = []

        if self.supabase.has_credentials:
            endpoint = f"{self.supabase.base_url}/rest/v1/conversations"
            params = {"order": "updated_at.desc", "limit": str(limit)}
            try:
                async with httpx.AsyncClient(timeout=8.0) as client:
                    res = await client.get(endpoint, params=params, headers=self.supabase._headers())
                    if res.status_code == 200:
                        data = res.json()
                        for item in data:
                            cid = item["id"]
                            msg_count = len(self._memory_messages.get(cid, []))
                            summaries.append(
                                ConversationSummary(
                                    id=cid,
                                    title=item.get("title", "Conversation"),
                                    created_at=item.get("created_at", ""),
                                    updated_at=item.get("updated_at", ""),
                                    message_count=msg_count,
                                )
                            )
                        if summaries:
                            return summaries
            except Exception as e:
                logger.warning(f"Error listing conversations from Supabase: {e}")

        # Fallback to local memory store
        sorted_convs = sorted(
            self._memory_conversations.values(),
            key=lambda x: x.get("updated_at", ""),
            reverse=True,
        )
        for item in sorted_convs[:limit]:
            cid = item["id"]
            msg_count = len(self._memory_messages.get(cid, []))
            summaries.append(
                ConversationSummary(
                    id=cid,
                    title=item.get("title", "Conversation"),
                    created_at=item.get("created_at", ""),
                    updated_at=item.get("updated_at", ""),
                    message_count=msg_count,
                )
            )

        return summaries

    async def get_messages(self, conversation_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Fetch ordered messages for a conversation thread."""
        if self.supabase.has_credentials:
            endpoint = f"{self.supabase.base_url}/rest/v1/messages"
            params = {
                "conversation_id": f"eq.{conversation_id}",
                "order": "created_at.asc",
                "limit": str(limit),
            }
            try:
                async with httpx.AsyncClient(timeout=8.0) as client:
                    res = await client.get(endpoint, params=params, headers=self.supabase._headers())
                    if res.status_code == 200:
                        data = res.json()
                        if data and isinstance(data, list):
                            self._memory_messages[conversation_id] = data
                            return data
            except Exception as e:
                logger.warning(f"Error fetching messages from Supabase: {e}")

        # Memory store fallback
        msgs = self._memory_messages.get(conversation_id, [])
        return msgs[-limit:]

    async def add_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
        citations: Optional[List[Dict[str, Any]]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Record a chat message in the thread."""
        msg_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()

        msg_record = {
            "id": msg_id,
            "conversation_id": conversation_id,
            "role": role,
            "content": content,
            "citations": citations or [],
            "metadata": metadata or {},
            "created_at": now,
        }

        # Update local memory
        if conversation_id not in self._memory_messages:
            self._memory_messages[conversation_id] = []
        self._memory_messages[conversation_id].append(msg_record)

        # Update conversation updated_at
        if conversation_id in self._memory_conversations:
            self._memory_conversations[conversation_id]["updated_at"] = now

        # Persist to Supabase
        if self.supabase.has_credentials:
            endpoint = f"{self.supabase.base_url}/rest/v1/messages"
            headers = self.supabase._headers(return_representation=True)
            try:
                async with httpx.AsyncClient(timeout=8.0) as client:
                    await client.post(endpoint, json=msg_record, headers=headers)
            except Exception as e:
                logger.warning(f"Error saving message to Supabase: {e}")

        return msg_record

    async def delete_conversation(self, conversation_id: str) -> bool:
        """Delete conversation and all its messages."""
        self._memory_conversations.pop(conversation_id, None)
        self._memory_messages.pop(conversation_id, None)

        if self.supabase.has_credentials:
            endpoint = f"{self.supabase.base_url}/rest/v1/conversations"
            params = {"id": f"eq.{conversation_id}"}
            try:
                async with httpx.AsyncClient(timeout=8.0) as client:
                    res = await client.delete(endpoint, params=params, headers=self.supabase._headers())
                    return res.status_code in (200, 204, 404)
            except Exception as e:
                logger.warning(f"Error deleting conversation from Supabase: {e}")
                return True

        return True


# Singleton instance
_conversation_service: Optional[ConversationService] = None


def get_conversation_service() -> ConversationService:
    """Return singleton instance of ConversationService."""
    global _conversation_service
    if _conversation_service is None:
        _conversation_service = ConversationService()
    return _conversation_service
