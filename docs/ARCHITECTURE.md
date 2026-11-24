# MAYA System Architecture & Technical Design

**Project:** MAYA — Multimodal AI-Powered University Assistant for GGSIPU  
**Milestone:** 7 (Final Architecture Documentation)

---

## 1. High-Level System Architecture

MAYA is built on a modern, decoupled full-stack architecture that combines asynchronous web APIs, multi-process document ingestion, hybrid vector retrieval, and multimodal generative AI:

```
+-------------------------------------------------------------------------+
|                         React 18 + Vite SPA                             |
|  - Matte Red / Charcoal / Warm Paper Theme                              |
|  - Dashboard: Live Health Metrics, Recent Threads, Latest Notices       |
|  - Conversational Interface: Markdown, Verifiable Citations, Drawer     |
|  - Multimodal Upload: Image Preview, PDF/DOCX Viewer, Audio Player       |
|  - Voice Layer: Web Speech STT (en-IN/hi-IN) + SpeechSynthesis TTS       |
+------------------------------------+------------------------------------+
                                     | Axios REST / SSE Streaming
                                     v
+-------------------------------------------------------------------------+
|                         FastAPI Core Backend                            |
|  - Centralized Exception Handlers (Validation, Base, Unhandled)         |
|  - Production CORS Middleware (Configurable Origins + Vercel Preview)   |
|  - Pydantic v2 Request & Response Validation                            |
|  - FileValidator (Magic Bytes, MIME, Extension, Size, Duration)        |
+----------+-------------------------+-------------------------+----------+
           |                         |                         |
           v                         v                         v
+-----------------------+ +-----------------------+ +---------------------+
| Crawler & Ingestion   | | Conversational RAG    | | Multimodal Services |
| - GGSIPUNoticeCrawler | | - RAGService          | | - ImageUnderstanding|
| - Async Downloader    | | - ContextBuilder      | | - DocUnderstanding  |
| - PDFWorkerPool (8)   | | - CitationVerifier    | | - AudioUnderstanding|
| - Chunking (700/120)  | | - GeminiService       | | - Private Isolation |
+----------+------------+ +----------+------------+ +----------+----------+
           |                         |                         |
           +-------------------------+-------------------------+
                                     |
                                     v
+-------------------------------------------------------------------------+
|                            Data & Cloud Tier                            |
|  - Supabase PostgreSQL: Notices, Crawl Jobs, Conversations, Messages     |
|  - Zilliz Cloud / Milvus: 384-dimensional dense vectors (all-MiniLM-L6) |
|  - Google Gemini API: Multimodal reasoning (gemini-2.5-flash)           |
+-------------------------------------------------------------------------+
```

---

## 2. Ingestion & Document Processing Architecture

### A. Strict 8-Process PDF Worker Architecture

To process university circulars (which can range from 1 to 100+ pages) without blocking the FastAPI async event loop, MAYA coordinates a dedicated `ProcessPoolExecutor` with **strictly 8 worker processes**:

- **Spawn Context:** Utilizes `multiprocessing.get_context("spawn")` for full cross-platform compatibility on Windows and Linux containers.
- **Security & Secret Isolation:** Child processes receive only primitive, serializable dictionaries (`file_path`, `doc_id`, `url`). Database connection strings, API tokens, and secrets are strictly excluded from child process memory.
- **Process-Local Engine Initializer:** Worker processes initialize local OCR engines on startup via `worker_init()`, avoiding repeated model loading during batch document processing.
- **Bounded Batches:** Documents are dispatched in bounded batches (default 10) to control peak memory consumption during high-throughput crawling.

### B. Extraction & OCR Fallback Flow

```
   [PDF Document]
         │
         ▼
   PyMuPDF Native Text Extraction
         │
         ├── Text length >= 40 chars/page? ──> (Native Text Preserved)
         │
         └── Text empty or scanned page?   ──> (PaddleOCR Fallback Triggered)
                                                         │
                                                         ▼
                                            (Extracted OCR Text Merged)
```

1. **Native PyMuPDF (`fitz`):** Extracts digital text, structural layout, and document metadata (creation date, title, author) at high speed.
2. **PaddleOCR Fallback:** Scanned or image-based pages (detected by zero native text or scanned page heuristics) are routed through PaddleOCR to extract text directly from high-resolution page pixmaps.
3. **DOCX Extractor:** Preserves headings, structured tables, and bold formatting from Microsoft Word syllabus documents using `python-docx`.

---

## 3. Vector Indexing & Chunking Pipeline

### A. Chunking Strategy
- **Chunk Size:** 700 target tokens.
- **Chunk Overlap:** 120 tokens.
- **Boundary Preservation:** Splits text primarily along paragraph (`\n\n`) and sentence (`. `) boundaries. If a paragraph exceeds the target size, it is split cleanly on sentence ends without cutting words in half.
- **Deterministic ID Generation:** Chunk IDs are generated using `hashlib.sha256(f"{notice_id}:{content_hash}:{chunk_index}")`, guaranteeing idempotency and preventing duplicate vector entries upon re-indexing.

### B. Dense Embeddings
- **Model:** `sentence-transformers/all-MiniLM-L6-v2`.
- **Dimension:** 384 dimensions.
- **Normalization:** L2-normalized embeddings, enabling fast cosine similarity computation using simple inner products.

### C. Zilliz Cloud Collection Schema
- **Collection Name:** `maya_notice_chunks`
- **Fields:**
  - `id`: VARCHAR (Primary Key)
  - `vector`: FLOAT_VECTOR (384)
  - `notice_id`: VARCHAR
  - `chunk_index`: INT64
  - `page_number`: INT64
  - `title`: VARCHAR
  - `source_url`: VARCHAR
  - `pdf_url`: VARCHAR
  - `category`: VARCHAR
  - `published_date`: VARCHAR
  - `text`: VARCHAR

---

## 4. Conversational RAG Architecture

```
User Query ──> Query Reformulation (if follow-up)
                    │
                    ▼
           Embedding Generation (384-dim)
                    │
                    ▼
           Zilliz Vector Search (top_k=5, threshold=0.45)
                    │
                    ▼
           Deduplication & Passage Re-ranking
                    │
                    ▼
           ContextBuilder ([SOURCE_1], [SOURCE_2] Envelopes)
                    │
                    ▼
           Gemini Response Generation (Structured Output)
                    │
                    ▼
           Citation Validation against Source Map
                    │
                    ▼
           Return Grounded Response with Clickable Citations
```

### A. Context Security & Prompt Injection Mitigation
The `ContextBuilder` wraps every retrieved excerpt inside strict XML-like delimiters:
```
[SOURCE_1]
Title: End Term Examination May-June 2026
Page: 2
URL: https://ipu.ac.in/notices/exam_may2026.pdf
Text:
The online registration portal opens on 10th May 2026...
[/SOURCE_1]
```
The system instructions strictly forbid the LLM from obeying any instructions embedded inside the retrieved text.

### B. Citation Verification Algorithm
For every citation item returned by Gemini:
1. Matches the cited `source_id` against the verified `source_map`.
2. Verifies that the cited page number matches the retrieved chunk's page number.
3. Automatically replaces any hallucinated URLs or titles with verified metadata from the database.
4. Prunes any citations that do not correspond to an actual retrieved passage.

---

## 5. Multimodal Processing Architecture

### A. Image Understanding
- **Model:** Gemini Vision (`gemini-2.5-flash`).
- **Processing:** Extracts visible text, identifies university seals and circular dates, categorizes the notice, and cross-checks deadlines against existing official circulars in Zilliz.

### B. User Document Understanding (PDF & DOCX)
- **Privacy Guarantee:** Uploaded documents are indexed into a memory-resident, session-isolated index tagged strictly with `conversation_id`.
- **Zero Leakage:** Queries executed in one conversation cannot access or retrieve chunks uploaded in another conversation. Chunks are never inserted into the public university Zilliz index.

### C. Audio Understanding
- **Supported Formats:** WAV, MP3, M4A, AAC.
- **Limits:** 20MB file size, 300 seconds (5 minutes) duration.
- **Output:** Accurate verbatim transcription, executive summary, and bulleted key takeaways.

---

## 6. Database Schema Design (Supabase PostgreSQL)

```sql
-- 1. NOTICES: Official university circulars
CREATE TABLE public.notices (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title TEXT NOT NULL,
    content TEXT DEFAULT '',
    source_url TEXT UNIQUE NOT NULL,
    pdf_url TEXT,
    category TEXT DEFAULT 'General',
    published_date TEXT,
    processing_status TEXT DEFAULT 'pending',
    content_hash TEXT,
    scraped_at TIMESTAMPTZ DEFAULT now(),
    indexed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- 2. CRAWL JOBS: Background crawl state & resumption
CREATE TABLE public.crawl_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    status TEXT NOT NULL DEFAULT 'pending',
    current_stage TEXT DEFAULT 'initializing',
    pages_discovered INT DEFAULT 0,
    pages_processed INT DEFAULT 0,
    notices_discovered INT DEFAULT 0,
    pdfs_downloaded INT DEFAULT 0,
    errors JSONB DEFAULT '[]'::jsonb,
    started_at TIMESTAMPTZ DEFAULT now(),
    completed_at TIMESTAMPTZ
);

-- 3. CONVERSATIONS & MESSAGES: Student chat threads
CREATE TABLE public.conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title TEXT NOT NULL DEFAULT 'New Conversation',
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE public.messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID REFERENCES public.conversations(id) ON DELETE CASCADE,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    citations JSONB DEFAULT '[]'::jsonb,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT now()
);
```
