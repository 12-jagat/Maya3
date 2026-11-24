"""
GGSIPU Official Notice Crawler Service.
Discovers pagination, extracts notice metadata, normalizes links, and prevents duplicates.
"""

import asyncio
from datetime import datetime, timezone
import hashlib
import re
from typing import Any, AsyncGenerator, Dict, List, Optional, Set, Tuple
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup
import httpx

from app.utils.logger import logger

# Official GGSIPU Initial Seed Sources
DEFAULT_GGSIPU_SOURCES = [
    "https://www.ipu.ac.in/notices.php",
    "https://www.ipu.ac.in/notices.php?limit=250",
    "https://examdept.ggsipu.ac.in/notices/",
    "https://www.ipu.ac.in/exam_notices.php",
    "https://www.ipu.ac.in/admissions.php",
    "https://www.ipu.ac.in/datesheet.php",
    "https://www.ipu.ac.in/results.php",
]

# Common date patterns in GGSIPU circulars (e.g. 23-11-2024, 23/11/2024, 23.11.2024)
DATE_REGEX = re.compile(r"\b(\d{1,2}[-/\.]\d{1,2}[-/\.]\d{2,4})\b")


class NoticeItem:
    """Standardized notice representation."""

    def __init__(
        self,
        title: str,
        source_url: str,
        pdf_url: Optional[str] = None,
        category: str = "General",
        published_date: Optional[str] = None,
        content: str = "",
    ):
        self.title = title.strip()
        self.source_url = source_url.strip()
        self.pdf_url = pdf_url.strip() if pdf_url else None
        self.category = category.strip()
        self.published_date = published_date.strip() if published_date else None
        self.content = content.strip()
        self.content_hash = self._compute_hash()

    def _compute_hash(self) -> str:
        raw = f"{self.title}|{self.pdf_url or ''}|{self.published_date or ''}|{self.content}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "source_url": self.source_url,
            "pdf_url": self.pdf_url,
            "category": self.category,
            "published_date": self.published_date,
            "content": self.content,
            "content_hash": self.content_hash,
            "processing_status": "pending",
        }


class GGSIPUNoticeCrawler:
    """
    Polite asynchronous crawler for official GGSIPU university portals.
    Discovers pagination dynamically, discovers documents, and extracts clean metadata.
    """

    def __init__(
        self,
        sources: Optional[List[str]] = None,
        delay_seconds: float = 0.3,
        max_retries: int = 3,
        timeout: float = 15.0,
    ):
        self.sources = sources or DEFAULT_GGSIPU_SOURCES
        self.delay_seconds = delay_seconds
        self.max_retries = max_retries
        self.timeout = timeout
        self.headers = {
            "User-Agent": "MAYA-UniversityAssistant/1.0 (+http://localhost:5173/about; academic student project)",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        }
        self.visited_urls: Set[str] = set()

    async def fetch_html(self, client: httpx.AsyncClient, url: str) -> Optional[str]:
        """Fetch page HTML with polite delays and bounded retries."""
        for attempt in range(1, self.max_retries + 1):
            try:
                await asyncio.sleep(self.delay_seconds)
                response = await client.get(url, headers=self.headers, timeout=self.timeout, follow_redirects=True)
                if response.status_code == 200:
                    return response.text
                elif response.status_code in (404, 410):
                    logger.warning(f"Notice page not found ({response.status_code}): {url}")
                    return None
                else:
                    logger.warning(f"Unexpected status {response.status_code} on {url} (attempt {attempt})")
            except (httpx.RequestError, httpx.TimeoutException) as exc:
                logger.warning(f"HTTP request error fetching {url} on attempt {attempt}: {exc}")
                if attempt == self.max_retries:
                    logger.error(f"Failed to fetch {url} after {self.max_retries} attempts.")
                    return None
                await asyncio.sleep(self.delay_seconds * (2**attempt))
        return None

    def extract_notices_from_html(self, html: str, page_url: str) -> List[NoticeItem]:
        """
        Parse HTML table and list structures to extract notices with PDFs and metadata.
        Handles various GGSIPU table layouts reliably without inventing metadata.
        """
        soup = BeautifulSoup(html, "html.parser")
        notices: List[NoticeItem] = []

        # Find all table rows
        rows = soup.find_all("tr")
        for row in rows:
            cells = row.find_all(["td", "th"])
            if not cells:
                continue

            # Look for anchor tag with link to PDF or notice detail
            links = row.find_all("a", href=True)
            if not links:
                continue

            for link in links:
                href = link["href"].strip()
                if not href or href.startswith("javascript:") or href.startswith("#"):
                    continue

                abs_link = urljoin(page_url, href)
                link_text = link.get_text(separator=" ", strip=True)

                # Row text context for date & category
                row_text = row.get_text(separator=" ", strip=True)

                # Determine notice title
                title = link_text if len(link_text) > 4 else row_text
                # Clean up title
                title = re.sub(r"\s+", " ", title).strip()
                if len(title) < 5:
                    continue

                # Extract date from cells or row text
                published_date = None
                date_match = DATE_REGEX.search(row_text)
                if date_match:
                    published_date = date_match.group(1)

                # Detect if the link itself is a document (PDF, DOCX)
                is_pdf = bool(
                    abs_link.lower().endswith(".pdf")
                    or ".pdf?" in abs_link.lower()
                    or "upload" in abs_link.lower()
                    or "pubinfo" in abs_link.lower()
                )

                pdf_url = abs_link if is_pdf else None
                source_url = abs_link

                # Categorize based on keywords in title or URL
                category = self._infer_category(title, page_url)

                notice = NoticeItem(
                    title=title,
                    source_url=source_url,
                    pdf_url=pdf_url,
                    category=category,
                    published_date=published_date,
                    content=row_text,
                )
                notices.append(notice)

        return notices

    def discover_pagination_links(self, html: str, current_url: str) -> List[str]:
        """
        Discover next page / pagination URLs dynamically.
        Never hardcodes total pages.
        """
        soup = BeautifulSoup(html, "html.parser")
        discovered: List[str] = []
        base_domain = urlparse(current_url).netloc

        for a in soup.find_all("a", href=True):
            href = a["href"].strip()
            if not href or href.startswith("javascript:") or href.startswith("#"):
                continue

            abs_url = urljoin(current_url, href)
            parsed = urlparse(abs_url)

            # Keep only links on the same host
            if parsed.netloc != base_domain:
                continue

            # Check for pagination patterns (page=, p=, offset=, or pagination containers)
            query = parsed.query.lower()
            text = a.get_text(strip=True).lower()
            parent_classes = " ".join(a.parent.get("class", [])).lower() if a.parent else ""

            is_pagination = (
                "page=" in query
                or "p=" in query
                or "offset=" in query
                or "limit=" in query
                or "pagination" in parent_classes
                or text in ("next", "»", ">", "next >", "next >>", "more")
                or (text.isdigit() and len(text) <= 3)
            )

            if is_pagination and abs_url not in self.visited_urls:
                discovered.append(abs_url)

        return discovered

    def _infer_category(self, title: str, source_url: str) -> str:
        """Categorize notices using academic keywords."""
        t = title.lower()
        if "exam" in t or "date sheet" in t or "datesheet" in t or "admit" in t or "examdept" in source_url:
            return "Examinations"
        if "admission" in t or "counselling" in t or "cutoff" in t or "seat" in t:
            return "Admissions"
        if "recruitment" in t or "vacancy" in t or "faculty" in t or "interview" in t:
            return "Recruitment"
        if "tender" in t or "quotation" in t or "eoi" in t:
            return "Tenders"
        if "result" in t or "grade" in t or "marks" in t:
            return "Results"
        if "circular" in t or "order" in t or "notification" in t:
            return "Academic Circulars"
        return "General"
