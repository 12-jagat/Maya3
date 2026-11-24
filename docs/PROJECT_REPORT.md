# MAYA: Multimodal AI-Powered University Assistant for GGSIPU
## Comprehensive Engineering Milestone Report

---

### Abstract

Navigating official circulars, examination date sheets, admission guidelines, and academic regulations at large collegiate universities presents substantial friction for students and faculty. Guru Gobind Singh Indraprastha University (GGSIPU) publishes hundreds of circulars annually across fragmented departmental portals in scanned or image-heavy PDF formats. Traditional keyword searches frequently fail to extract relevant guidelines or miss critical amendments.

**MAYA** is an end-to-end, multimodal, retrieval-augmented intelligence system built specifically to address these challenges. Integrating asynchronous web crawling, an 8-process document extraction architecture, dense vector semantic search using `sentence-transformers/all-MiniLM-L6-v2`, and conversational generation through Google Gemini, MAYA delivers verified answers grounded in official documentation with exact citations. Furthermore, MAYA expands accessibility through voice interactions (STT/TTS), image notice analysis, user document QA, and lecture audio transcription, all within a privacy-preserving and session-isolated boundary.

---

### 1. Problem Statement

1. **Information Fragmentation:** GGSIPU notices are dispersed across multiple departmental pages (`ipu.ac.in/notices.php`, examination portals, affiliated colleges).
2. **Scanned & Unsearchable Documents:** A significant portion of urgent notices are scanned physical documents or image circulars lacking selectable text.
3. **Hallucination Risk:** Generic commercial LLMs frequently hallucinate deadlines, examination fees, and eligibility criteria, leading to catastrophic misinformation for students.
4. **Accessibility Barriers:** Students on mobile devices or with visual/auditory impairments lack intuitive ways to query circulars via speech or listen to spoken summaries.

---

### 2. Project Objectives

- Implement an autonomous, idempotent crawler to discover and mirror official GGSIPU circulars.
- Build an asynchronous PDF and document processing pipeline leveraging native PyMuPDF and OCR fallback across exactly 8 isolated worker processes.
- Index document passages into a high-dimensional vector database (Zilliz Cloud) using 384-dimensional dense representations.
- Develop a conversational RAG system powered by Gemini that enforces strict factual grounding, prunes hallucinations, and cites exact page numbers.
- Provide multimodal interaction capabilities: image notice verification, private PDF/DOCX querying, and audio note transcription.
- Implement accessible voice input (speech-to-text) and speech output (text-to-speech) through native browser Web APIs.
- Deliver a responsive, minimal, university-branded user interface with full conversation thread persistence in Supabase PostgreSQL.

---

### 3. Existing System Limitations vs. Proposed MAYA System

| Feature | Legacy University Portals / Chatbots | MAYA University Assistant |
|---------|--------------------------------------|---------------------------|
| **Search Mechanism** | Exact keyword substring search on titles only | Dense semantic vector search over document contents |
| **Document Formats** | PDFs cannot be searched internally if scanned | Dual extraction: native digital text + PaddleOCR fallback |
| **Response Accuracy** | Static links or generic AI hallucinations | Strictly grounded RAG answers with clickable page citations |
| **Multimodal Inputs** | Plain text only | Voice STT/TTS, image notices, PDFs, DOCXs, and audio notes |
| **Document Privacy** | No user upload capability | Session-isolated uploads guaranteed never to leak to public DB |
| **Worker Architecture** | Single-threaded synchronous bottleneck | Dedicated 8-process `ProcessPoolExecutor` with bounded batches |

---

### 4. Implementation Details

#### A. Document Extraction & OCR Pipeline
- The extraction engine detects whether a PDF page contains digital text (threshold $\ge 40$ characters).
- Digital pages are extracted via PyMuPDF in milliseconds. Scanned pages trigger PaddleOCR to render and read text.
- Worker processes run under Python's `spawn` context with zero database or API credential sharing.

#### B. Chunking & Embedding Generation
- Text is partitioned into 700-token chunks with 120-token overlap, preserving paragraph boundaries.
- Passages are vectorized into 384-dimensional dense vectors using `sentence-transformers/all-MiniLM-L6-v2` with L2 unit normalization.
- Chunk IDs are computed deterministically via cryptographic hashing to prevent duplicate vector entries.

#### C. Gemini Conversational RAG
- User queries are analyzed to detect follow-up prompts and reformulated using recent conversation turns.
- Candidate passages are retrieved from Zilliz Cloud using cosine similarity ($threshold \ge 0.45$).
- Prompts are constructed with structured `[SOURCE_X]` envelopes.
- Generated citations are validated against retrieved passages, ensuring zero hallucinated references reach the student.

#### D. Voice & Multimodal Interface
- Web Speech API enables speech recognition for Indian English (`en-IN`) and Hindi (`hi-IN`).
- Browser SpeechSynthesis provides vocal responses with stop and replay controls.
- File uploads are validated via binary magic numbers (e.g. `%PDF-`, `\x89PNG`, `RIFF WAVE`) before storage.

---

### 5. Database Schema & Architecture

- **`notices`:** Stores title, source URL, PDF URL, category, published date, content hash, and indexing status.
- **`crawl_jobs` & `crawl_job_events`:** State machine managing asynchronous crawler execution and stage resumption.
- **`conversations` & `messages`:** Persists multi-turn chat threads, assistant answers, and citation metadata envelopes.
- **`maya_notice_chunks` (Zilliz Cloud):** 384-dimensional vector collection storing dense embeddings with cosine indexing.

---

### 6. Verification & Testing Results

- **Automated Test Suite:** 61 automated tests across 4 test suites (`test_milestone4.py`, `test_milestone5.py`, `test_milestone6.py`, `test_milestone7.py`) passed cleanly in 13.08 seconds with 100% pass rate.
- **Security & Validation:** Verified magic byte spoof detection, path traversal sanitization, and session isolation.
- **Frontend Production Build:** Vite build succeeded in 5.86s, generating zero runtime bundle errors.
- **Dependency Health:** Live endpoints (`/health`, `/api/v1/health/database`, `/api/v1/chat/health`) verified with active Supabase, Zilliz, and Gemini connections.

---

### 7. Known Limitations & Future Scope

1. **Speech Recognition Support:** Voice STT relies on the Web Speech API, currently native to Chromium-based browsers (Chrome, Edge, Brave) and Safari. Future iterations could add backend Whisper speech transcription for Firefox users.
2. **Multi-Campus Crawling:** Currently targets primary university portals (`ipu.ac.in`). Future versions can expand crawling to individual affiliated college websites.
3. **Real-Time Duplex Audio:** Future milestones can integrate Gemini Live API for real-time bidirectional audio streaming when low-latency WebRTC infrastructure is deployed.

---

### 8. Conclusion

MAYA Milestone 7 delivers a unified, production-ready university assistant. By combining resilient multi-process document extraction, dense vector retrieval, Gemini-powered synthesis with verifiable citations, and multimodal interaction, MAYA sets a high standard for academic artificial intelligence assistants.
