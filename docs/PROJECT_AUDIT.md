# MAYA: Comprehensive Project Audit & Integration Health Report

**Generated:** November 2026  
**Project:** MAYA — Multimodal AI-Powered University Assistant for GGSIPU Students  
**Milestone:** 7 (Final Integration, Testing, UI Polish & Cloud Deployment)

---

## 1. System Architecture Overview

MAYA is a production-grade, multimodal university assistant tailored specifically to students and faculty of Guru Gobind Singh Indraprastha University (GGSIPU). The system ingests official university notices, circulars, syllabi, datesheets, and student ordinances from official domains (`ipu.ac.in`), processes them into high-dimensional vector embeddings, and delivers strictly grounded, conversational question-answering with verifiable citations. Additionally, it offers multimodal capabilities spanning voice interactions, vision extraction for notice photos, document QA for PDFs/DOCXs, and lecture audio transcription.

```
       +-------------------------------------------------------------+
       |               React + Vite Frontend (Tailwind CSS)           |
       |  - Landing / Dashboard with Live System Metrics & Notices   |
       |  - Interactive Chat Window with Citations & Source Drawer   |
       |  - Multimodal Upload Center (Image, PDF, DOCX, Audio)       |
       |  - Browser Voice STT (Web Speech) & TTS (SpeechSynthesis)   |
       |  - Notice Center (Crawl Control & Ingestion Dashboard)      |
       +------------------------------+------------------------------+
                                      | HTTP / REST / SSE
                                      v
       +-------------------------------------------------------------+
       |                   FastAPI Backend Core                      |
       |  - Async Lifespan & Centralized Exception Handling           |
       |  - Strict ProcessPoolExecutor with exactly 8 PDF Workers     |
       |  - Bounded Streaming Validation & Cryptographic Hashes      |
       |  - Session-level Isolation for User Uploads                 |
       +-------+--------------------+---------------------+----------+
               |                    |                     |
               v                    v                     v
     +-------------------+  +-------------------+  +-------------------+
     | Supabase Postgres |  | Zilliz Cloud RAG  |  |   Google Gemini   |
     | - notices         |  | - 384-dim dense   |  |   (gemini-2.5/3.5)|
     | - crawl_jobs      |  |   vector index    |  | - Grounded RAG    |
     | - conversations   |  | - all-MiniLM-L6-v2|  | - Vision analysis |
     | - messages        |  | - Cosine metric   |  | - Audio transcribe|
     +-------------------+  +-------------------+  +-------------------+
```

---

## 2. Implemented Features vs. Verification Matrix

Each module was audited for its actual execution path, runtime imports, and active handling:

| # | Subsystem / Feature | Implementation Location | Execution Path Verified | Status |
|---|---------------------|-------------------------|--------------------------|--------|
| **1** | **Authentication / Session** | `app/services/conversation_service.py` | Session-less UUID-based anonymous conversation threads (`conversation_id`). Enables frictionless student access without mandatory login gating while persisting threads in Supabase. | **Fully Implemented** |
| **2** | **University Notice Crawler** | `app/services/notice_crawler.py`<br>`app/services/crawl_manager.py` | Concurrent HTTP scraping (`ipu.ac.in/notices.php`), HTML table parsing, date normalization, relative URL resolution, SHA-256 content deduplication. | **Fully Implemented & Verified** |
| **3** | **PDF Download & Validation** | `app/services/document_downloader.py` | Asynchronous streaming download with semaphore limits (`PDF_DOWNLOAD_CONCURRENCY=10`), `%PDF-` magic-byte validation, and size capping (`PDF_MAX_SIZE_MB=30`). | **Fully Implemented & Verified** |
| **4** | **OCR Fallback** | `app/services/ocr_service.py` | PyMuPDF text check with automatic PaddleOCR fallback on scanned or image-based PDF circulars. | **Fully Implemented & Verified** |
| **5** | **8-Process PDF Worker Pool** | `app/services/pdf_worker_pool.py` | Long-lived `ProcessPoolExecutor` strictly locked to 8 worker processes (`PDF_WORKERS=8`) using top-level picklable functions without leaking DB/API handles. | **Fully Implemented & Verified** |
| **6** | **Chunking & MiniLM Embeddings** | `app/services/chunking_service.py`<br>`app/services/embedding_service.py` | 700-token chunks with 120-token overlap; 384-dimensional dense vectors generated via `sentence-transformers/all-MiniLM-L6-v2` with torch L2 normalization. | **Fully Implemented & Verified** |
| **7** | **Zilliz Cloud Vector Index** | `app/database/zilliz_client.py` | Vector search over collection `maya_notice_chunks` using COSINE distance, with resilient local in-memory vector fallback when offline. | **Fully Implemented & Verified** |
| **8** | **Gemini Conversational RAG** | `app/services/gemini_service.py`<br>`app/services/rag_service.py` | Strict RAG context synthesis using Google GenAI SDK (`google-genai`). Prompts enforce strict grounding to official notices and prohibit hallucinations. | **Fully Implemented & Verified** |
| **9** | **Conversation & Thread History** | `app/services/conversation_service.py` | Full persistence of conversations and chronological message threads in Supabase PostgreSQL tables `conversations` and `messages`. | **Fully Implemented & Verified** |
| **10** | **Citation Generation & Verification**| `app/services/rag_service.py` | Citations verified against retrieved text; source title, direct PDF URL, and page number embedded into responses. | **Fully Implemented & Verified** |
| **11** | **Image Notice Understanding** | `app/services/image_understanding.py` | Gemini Vision analysis of exam notices/circular photos with official circular cross-checking in Zilliz. | **Fully Implemented & Verified** |
| **12** | **PDF & DOCX Upload** | `app/services/document_understanding.py` | User uploaded PDF/DOCX parsing with conversation-level isolation guarantee (preventing data leakage into public knowledge base). | **Fully Implemented & Verified** |
| **13** | **Audio Understanding** | `app/services/audio_understanding.py` | Audio note upload (WAV/MP3/M4A), Gemini speech transcription, key takeaways extraction, and summary generation. | **Fully Implemented & Verified** |
| **14** | **Browser Voice Input & Output** | `frontend/src/hooks/useSpeechRecognition.js`<br>`frontend/src/hooks/useSpeechSynthesis.js` | Web Speech API for `en-IN` / `hi-IN` voice transcription, and SpeechSynthesis for speaking responses with active toggle controls. | **Fully Implemented & Verified** |
| **15** | **Notice Center & Ingestion UI** | `frontend/src/pages/NoticeCenter.jsx` | Filterable notice list, crawler trigger/resume controls, progress bars, and vector ingestion retry actions. | **Fully Implemented & Verified** |

---

## 3. Broken Integrations & Inconsistencies Discovered

During our audit, several critical edge cases and API contract discrepancies were identified:

1. **Multimodal Form Field Discrepancy:**
   - *Issue:* In `frontend/src/services/api.js`, `uploadImage`, `uploadDocument`, and `uploadAudio` appended `prompt` to `FormData`, whereas `backend/app/api/v1/multimodal.py` accepted `question: Optional[str] = Form(None)`.
   - *Impact:* The user's query prompt attached to file uploads was discarded on the backend, falling back to default questions.
   - *Fix:* Updated backend to accept both `question` and `prompt`, and updated frontend to supply both.

2. **Multimodal Assistant Response Schema Mismatch:**
   - *Issue:* In `frontend/src/pages/ChatPage.jsx`, assistant content was assigned via `res.result?.answer || res.message`, but `backend/app/schemas/multimodal.py` returns `MultimodalResponse` with `content` directly at the top level (`res.content`).
   - *Impact:* Uploading an image or document in ChatPage resulted in blank message content.
   - *Fix:* Updated `ChatPage.jsx` to map `res.content || res.result?.answer || res.message` and `res.citations || res.result?.citations`.

3. **Missing Dedicated Database Health Endpoint:**
   - *Issue:* Milestone 7 specification requires `GET /api/v1/health/database` in addition to `GET /health` and `GET /api/v1/chat/health`.
   - *Fix:* Added `GET /api/v1/health/database` to report Supabase and Zilliz connectivity, latency, and collection status without exposing secret tokens.

4. **Pytest-asyncio Transport Blocking in Tests:**
   - *Issue:* `test_document_downloader_validation_and_hash` utilized a synchronous mock transport handler with an asynchronous streaming client, causing coroutine stalls under strict event loops.
   - *Fix:* Added explicit `AsyncMockTransport` or mock responses in unit tests to ensure non-blocking execution across all test suites.

5. **Missing Settings / About Screen:**
   - *Issue:* Frontend navigation lacked an explicit Settings/About page for voice compatibility, system parameters, and privacy guarantees.
   - *Fix:* Created `frontend/src/pages/AboutPage.jsx` and registered `/about` in `App.jsx`.

---

## 4. API Endpoints Catalog

### System & Health Endpoints
- `GET /health` — Application liveness and root health check.
- `GET /api/v1/status` — Subsystem readiness matrix.
- `GET /api/v1/health/database` — Supabase PostgreSQL & Zilliz vector store health.
- `GET /api/v1/chat/health` — Conversational RAG, Gemini model, and embedding model readiness.

### Conversational RAG Endpoints
- `POST /api/v1/chat/message` — Submit natural language query and receive grounded answer with citations.
- `GET /api/v1/chat/stream` — SSE token stream for progressive real-time answers.
- `GET /api/v1/chat/conversations` — Fetch recent conversation threads.
- `GET /api/v1/chat/conversations/{id}` — Fetch full ordered message history for a thread.
- `DELETE /api/v1/chat/conversations/{id}` — Delete a thread and all associated messages.

### Multimodal Endpoints
- `POST /api/v1/multimodal/image` — Upload image notice; perform vision extraction, analysis, and official cross-check.
- `POST /api/v1/multimodal/document` — Upload PDF/DOCX; extract, chunk, and answer queries in private scope.
- `POST /api/v1/multimodal/audio` — Upload WAV/MP3/M4A; transcribe speech and summarize key points.
- `GET /api/v1/multimodal/attachments/{conversation_id}/{filename}` — Serve uploaded user attachments with conversation scoping.

### Notice Crawler & Ingestion Endpoints
- `GET /api/v1/notices` — Paginated list of university notices with category and search filters.
- `GET /api/v1/notices/latest` — Quick access to latest official circulars.
- `GET /api/v1/notices/{id}` — Detailed notice record.
- `POST /api/v1/crawl/start` — Initiate crawl job across official GGSIPU portals.
- `GET /api/v1/crawl/status/{job_id}` — Real-time crawler job progress and stage metrics.
- `POST /api/v1/crawl/resume/{job_id}` — Resume interrupted crawl job.
- `GET /api/v1/crawl/history` — Historical crawl jobs.
- `POST /api/v1/ingestion/start` — Trigger PDF extraction, OCR, chunking, and Zilliz vector indexing.
- `GET /api/v1/ingestion/status/{job_id}` — Ingestion pipeline progress.
- `GET /api/v1/ingestion/statistics` — Summary of processed, failed, and pending documents.
- `POST /api/v1/ingestion/retry/{notice_id}` — Retry document processing for a failed circular.
- `POST /api/v1/search/semantic` — Direct vector similarity search over notice chunks.

---

## 5. Database Tables & Schemas

### Supabase PostgreSQL Tables
1. **`notices`**:
   - Primary key: `id` (UUID)
   - Unique: `source_url` (TEXT)
   - Fields: `title`, `content`, `pdf_url`, `category`, `published_date`, `processing_status`, `content_hash`, `scraped_at`, `indexed_at`, `created_at`, `updated_at`.
2. **`crawl_jobs`**:
   - Primary key: `id` (UUID)
   - Fields: `status`, `current_stage`, `current_source`, `pages_discovered`, `pages_processed`, `notices_discovered`, `new_notices`, `updated_notices`, `skipped_notices`, `pdfs_downloaded`, `pdfs_failed`, `last_processed_url`, `errors`, `started_at`, `completed_at`.
3. **`crawl_job_events`**:
   - Primary key: `id` (UUID), foreign key: `job_id` -> `crawl_jobs(id)`
   - Fields: `stage`, `message`, `details`, `created_at`.
4. **`conversations`**:
   - Primary key: `id` (UUID)
   - Fields: `title`, `created_at`, `updated_at`.
5. **`messages`**:
   - Primary key: `id` (UUID), foreign key: `conversation_id` -> `conversations(id)`
   - Fields: `role` ('user'/'assistant'/'system'), `content`, `citations` (JSONB), `metadata` (JSONB), `created_at`.

### Zilliz Cloud Vector Collection
- **Collection Name**: `maya_notice_chunks`
- **Vector Dimension**: 384 (`all-MiniLM-L6-v2`)
- **Metric**: `COSINE`
- **Fields**: `id` (VARCHAR PK), `vector` (FLOAT_VECTOR[384]), `notice_id`, `chunk_index`, `page_number`, `title`, `source_url`, `pdf_url`, `category`, `published_date`, `text`.

---

## 6. Environment Variables Audit

All sensitive keys are strictly confined to the backend `.env`. The frontend strictly consumes `VITE_API_URL`.

| Environment Variable | Service | Default / Value | Description |
|----------------------|---------|-----------------|-------------|
| `APP_NAME` | Backend | `MAYA` | Application identifier |
| `APP_ENV` | Backend | `production` / `development` | Deployment environment |
| `PORT` | Backend | `8000` | Dynamic port binding |
| `HOST` | Backend | `0.0.0.0` | Public interface binding |
| `FRONTEND_URL` | Backend | `http://localhost:5173` | Allowed CORS origins (comma-separated for multi-origin) |
| `GEMINI_API_KEY` | Backend | *(Secret)* | Google Gemini API Key |
| `GEMINI_MODEL` | Backend | `gemini-2.5-flash` | Gemini model variant |
| `SUPABASE_URL` | Backend | `https://*.supabase.co` | Supabase Project URL |
| `SUPABASE_KEY` | Backend | *(Secret)* | Supabase Service/Anon Key |
| `ZILLIZ_URI` | Backend | `https://*.zillizcloud.com` | Zilliz Cloud endpoint |
| `ZILLIZ_TOKEN` | Backend | *(Secret)* | Zilliz API token |
| `EMBEDDING_MODEL` | Backend | `sentence-transformers/all-MiniLM-L6-v2` | Dense sentence embedding model |
| `PDF_WORKERS` | Backend | `8` | Exactly 8 worker processes |
| `PDF_DOWNLOAD_CONCURRENCY` | Backend | `10` | Max concurrent PDF downloads |
| `PDF_MAX_SIZE_MB` | Backend | `30` | Max PDF download size limit |
| `OCR_ENABLED` | Backend | `true` | Enable OCR fallback |
| `EMBEDDING_BATCH_SIZE` | Backend | `64` | Embedding batch processing size |
| `CHUNK_SIZE` | Backend | `700` | Chunk size (target tokens) |
| `CHUNK_OVERLAP` | Backend | `120` | Chunk overlap (tokens) |
| `RAG_TOP_K` | Backend | `5` | Retrieved chunks per query |
| `RAG_SIMILARITY_THRESHOLD`| Backend | `0.45` | Cosine similarity threshold |
| `MAX_IMAGE_SIZE_MB` | Backend | `10` | Max image upload limit |
| `MAX_DOCUMENT_SIZE_MB` | Backend | `30` | Max PDF/DOCX upload limit |
| `MAX_AUDIO_SIZE_MB` | Backend | `20` | Max audio upload limit |
| `MAX_AUDIO_DURATION_SECONDS` | Backend | `300` | Max audio duration limit |
| `VITE_API_URL` | Frontend | `http://localhost:8000` | Base backend API endpoint URL |

---

## 7. Known Limitations

1. **SpeechRecognition Browser Compatibility**:
   - The Web Speech API for voice STT is natively supported in Chromium browsers (Chrome, Edge, Brave) and Safari. Firefox does not implement the SpeechRecognition API; MAYA detects this and displays a graceful fallback message.
2. **Offline Mode Fallbacks**:
   - If Supabase or Zilliz Cloud credentials are not configured, MAYA falls back to safe in-memory caching and vector simulation without crashing the server.
3. **Public Knowledge Privacy**:
   - User-uploaded documents (e.g. personal fee receipts or draft guidelines) are tagged with `conversation_id` and strictly isolated to that active thread. They are never ingested into the public university Zilliz index.

---

## 8. Deployment Readiness Assessment

- **Backend (Render / Containerized Linux)**: **READY**
  - Bound to `0.0.0.0` with `$PORT` support.
  - Multi-process worker pool (`ProcessPoolExecutor`) handles Linux/macOS `fork` as well as Windows `spawn`.
  - Memory-safe bounded batching prevents OOM during PDF extraction.
- **Frontend (Vercel / Cloudflare Pages)**: **READY**
  - Pure static SPA built with Vite.
  - Clean API abstraction via `VITE_API_URL`.
  - Client-side routing supported via SPA rewrite configuration.
