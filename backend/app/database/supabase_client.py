"""
Supabase Database Client for MAYA.
Communicates via PostgREST with resilience and in-memory fallback.
"""

from datetime import datetime, timezone
import json
import json
from pathlib import Path
from typing import Any, Dict, List, Optional
import uuid
import httpx

from app.config import get_settings
from app.utils.logger import logger

settings = get_settings()


class SupabaseClient:
    """Asynchronous client for interacting with Supabase PostgREST tables."""

    def __init__(self):
        self.base_url = settings.clean_supabase_url
        self.api_key = settings.SUPABASE_KEY
        self.has_credentials = bool(self.base_url and self.api_key)
        
        # Local persistent fallback if tables have not been created yet in Supabase
        self._fallback_path = Path(settings.STORAGE_DIR) / "notices_fallback.json"
        self._memory_notices: Dict[str, Dict[str, Any]] = {}
        self._memory_jobs: Dict[str, Dict[str, Any]] = {}
        self._memory_events: List[Dict[str, Any]] = []
        self._load_fallback()

    def _load_fallback(self):
        """Load fallback records from local disk if present."""
        try:
            if self._fallback_path.exists():
                with open(self._fallback_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self._memory_notices = data.get("notices", {})
                    self._memory_jobs = data.get("jobs", {})
                    self._memory_events = data.get("events", [])
        except Exception as e:
            logger.warning(f"Failed to load fallback store: {e}")

    def _save_fallback(self):
        """Persist fallback records to local disk."""
        try:
            self._fallback_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self._fallback_path, "w", encoding="utf-8") as f:
                json.dump(
                    {
                        "notices": self._memory_notices,
                        "jobs": self._memory_jobs,
                        "events": self._memory_events,
                    },
                    f,
                    indent=2,
                    default=str,
                )
        except Exception as e:
            logger.warning(f"Failed to save fallback store: {e}")

    def _headers(self, return_representation: bool = True) -> Dict[str, str]:
        prefer = "return=representation" if return_representation else "return=minimal"
        return {
            "apikey": self.api_key,
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Prefer": prefer,
        }

    # =========================================================================
    # NOTICES OPERATIONS
    # =========================================================================

    async def get_notice_by_source_url(self, source_url: str) -> Optional[Dict[str, Any]]:
        """Fetch a single notice by unique source_url."""
        if not self.has_credentials:
            return self._memory_notices.get(source_url)

        endpoint = f"{self.base_url}/rest/v1/notices"
        params = {"source_url": f"eq.{source_url}", "limit": "1"}

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.get(endpoint, params=params, headers=self._headers())
                if res.status_code == 200:
                    data = res.json()
                    return data[0] if data else None
                elif res.status_code == 404:
                    return self._memory_notices.get(source_url)
                else:
                    logger.warning(f"Supabase get_notice error {res.status_code}: {res.text}")
                    return self._memory_notices.get(source_url)
        except Exception as e:
            logger.error(f"Error fetching notice from Supabase: {e}")
            return self._memory_notices.get(source_url)

    async def upsert_notice(self, notice: Dict[str, Any]) -> Dict[str, Any]:
        """
        Insert or update a notice idempotently based on source_url.
        Preserves existing indexed_at and processing_status if already processed.
        """
        source_url = notice["source_url"]
        now = datetime.now(timezone.utc).isoformat()
        
        if not notice.get("id"):
            notice["id"] = str(uuid.uuid4())
        notice["scraped_at"] = notice.get("scraped_at") or now
        notice["updated_at"] = now

        # Always update memory cache
        self._memory_notices[source_url] = notice
        self._save_fallback()

        if not self.has_credentials:
            return notice

        endpoint = f"{self.base_url}/rest/v1/notices"
        headers = self._headers(return_representation=True)
        headers["Prefer"] = "resolution=merge-duplicates,return=representation"

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.post(endpoint, json=notice, headers=headers)
                if res.status_code in (200, 201):
                    data = res.json()
                    return data[0] if data else notice
                else:
                    logger.warning(f"Supabase upsert_notice fallback {res.status_code}: {res.text}")
                    return notice
        except Exception as e:
            logger.error(f"Error upserting notice to Supabase: {e}")
            return notice

    async def update_notice_status(
        self, source_url: str, processing_status: str, content_hash: Optional[str] = None
    ) -> bool:
        """Update notice processing_status and optional content_hash."""
        update_data: Dict[str, Any] = {
            "processing_status": processing_status,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        if content_hash:
            update_data["content_hash"] = content_hash

        if source_url in self._memory_notices:
            self._memory_notices[source_url].update(update_data)
            self._save_fallback()

        if not self.has_credentials:
            return True

        endpoint = f"{self.base_url}/rest/v1/notices"
        params = {"source_url": f"eq.{source_url}"}

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.patch(endpoint, params=params, json=update_data, headers=self._headers())
                return res.status_code in (200, 204)
        except Exception as e:
            logger.error(f"Error updating notice status in Supabase: {e}")
            return True

    async def list_notices(
        self,
        skip: int = 0,
        limit: int = 20,
        category: Optional[str] = None,
        search: Optional[str] = None,
    ) -> Dict[str, Any]:
        """List notices with pagination, search, and category filtering."""
        if not self.has_credentials:
            items = list(self._memory_notices.values())
            if category:
                items = [n for n in items if n.get("category", "").lower() == category.lower()]
            if search:
                s = search.lower()
                items = [n for n in items if s in n.get("title", "").lower() or s in n.get("content", "").lower()]
            total = len(items)
            paginated = items[skip : skip + limit]
            return {"items": paginated, "total": total, "skip": skip, "limit": limit}

        endpoint = f"{self.base_url}/rest/v1/notices"
        params = {
            "select": "*",
            "order": "published_date.desc,created_at.desc",
            "offset": str(skip),
            "limit": str(limit),
        }
        if category:
            params["category"] = f"eq.{category}"
        if search:
            params["title"] = f"ilike.*{search}*"

        headers = self._headers()
        headers["Prefer"] = "count=exact"

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.get(endpoint, params=params, headers=headers)
                if res.status_code == 200:
                    data = res.json()
                    content_range = res.headers.get("content-range", "")
                    total = int(content_range.split("/")[-1]) if "/" in content_range and content_range.split("/")[-1].isdigit() else len(data)
                    return {"items": data, "total": total, "skip": skip, "limit": limit}
                else:
                    logger.warning(f"Supabase list_notices fallback {res.status_code}")
                    items = list(self._memory_notices.values())
                    return {"items": items[skip : skip + limit], "total": len(items), "skip": skip, "limit": limit}
        except Exception as e:
            logger.error(f"Error querying notices from Supabase: {e}")
            items = list(self._memory_notices.values())
            return {"items": items[skip : skip + limit], "total": len(items), "skip": skip, "limit": limit}

    # =========================================================================
    # CRAWL JOB OPERATIONS
    # =========================================================================

    async def create_crawl_job(self, job_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new crawl job record."""
        job_id = job_data.get("id") or str(uuid.uuid4())
        job_data["id"] = job_id
        job_data["created_at"] = datetime.now(timezone.utc).isoformat()
        job_data["started_at"] = job_data["created_at"]

        self._memory_jobs[job_id] = job_data
        self._save_fallback()

        if not self.has_credentials:
            return job_data

        endpoint = f"{self.base_url}/rest/v1/crawl_jobs"
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.post(endpoint, json=job_data, headers=self._headers())
                if res.status_code in (200, 201):
                    data = res.json()
                    return data[0] if data else job_data
                else:
                    return job_data
        except Exception as e:
            logger.error(f"Error creating crawl job in Supabase: {e}")
            return job_data

    async def update_crawl_job(self, job_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Update existing crawl job status and metrics."""
        if job_id in self._memory_jobs:
            self._memory_jobs[job_id].update(updates)
            self._save_fallback()
            current_job = self._memory_jobs[job_id]
        else:
            current_job = updates

        if not self.has_credentials:
            return current_job

        endpoint = f"{self.base_url}/rest/v1/crawl_jobs"
        params = {"id": f"eq.{job_id}"}

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.patch(endpoint, params=params, json=updates, headers=self._headers())
                if res.status_code in (200, 204):
                    return current_job
                return current_job
        except Exception as e:
            logger.error(f"Error updating crawl job in Supabase: {e}")
            return current_job

    async def get_crawl_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Fetch crawl job by ID."""
        if not self.has_credentials:
            return self._memory_jobs.get(job_id)

        endpoint = f"{self.base_url}/rest/v1/crawl_jobs"
        params = {"id": f"eq.{job_id}", "limit": "1"}

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.get(endpoint, params=params, headers=self._headers())
                if res.status_code == 200:
                    data = res.json()
                    return data[0] if data else self._memory_jobs.get(job_id)
                return self._memory_jobs.get(job_id)
        except Exception as e:
            logger.error(f"Error reading crawl job from Supabase: {e}")
            return self._memory_jobs.get(job_id)

    async def list_crawl_jobs(self, limit: int = 10) -> List[Dict[str, Any]]:
        """List recent crawl jobs."""
        if not self.has_credentials:
            jobs = list(self._memory_jobs.values())
            jobs.sort(key=lambda j: j.get("created_at", ""), reverse=True)
            return jobs[:limit]

        endpoint = f"{self.base_url}/rest/v1/crawl_jobs"
        params = {"select": "*", "order": "created_at.desc", "limit": str(limit)}

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.get(endpoint, params=params, headers=self._headers())
                if res.status_code == 200:
                    return res.json()
                return list(self._memory_jobs.values())[:limit]
        except Exception as e:
            logger.error(f"Error listing crawl jobs from Supabase: {e}")
            return list(self._memory_jobs.values())[:limit]

    async def add_crawl_event(self, job_id: str, stage: str, message: str, details: Optional[Dict[str, Any]] = None):
        """Append an event to crawl_job_events audit log."""
        event_entry = {
            "id": str(uuid.uuid4()),
            "job_id": job_id,
            "stage": stage,
            "message": message,
            "details": details or {},
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        self._memory_events.append(event_entry)

        if not self.has_credentials:
            return

        endpoint = f"{self.base_url}/rest/v1/crawl_job_events"
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                await client.post(endpoint, json=event_entry, headers=self._headers(return_representation=False))
        except Exception:
            pass


_supabase_client_instance: Optional[SupabaseClient] = None


def get_supabase_client() -> SupabaseClient:
    """Return singleton instance of SupabaseClient."""
    global _supabase_client_instance
    if _supabase_client_instance is None:
        _supabase_client_instance = SupabaseClient()
    return _supabase_client_instance
