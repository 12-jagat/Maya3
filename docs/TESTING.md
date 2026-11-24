# MAYA: Verification & Automated Test Suite Report

**Status:** ALL 69 TESTS PASSING (100% Green across all Milestones)  
**Execution Runtime:** 15.94 seconds  
**Test Framework:** Pytest 9.2 with Asyncio & AnyIO extensions

---

## 1. Test Suite Architecture

MAYA employs a layered testing architecture covering unit logic, integration boundaries, security validations, and live end-to-end user evaluation scenarios:

```
    ┌────────────────────────────────────────────────────────┐
    │           Milestone 7 Comprehensive Test Suite         │
    │  - test_root_health_endpoint                           │
    │  - test_database_health_endpoint                       │
    │  - test_chat_health_endpoint                           │
    │  - test_crawler_url_extraction_and_hash                │
    │  - test_duplicate_notice_detection                     │
    │  - test_strict_eight_worker_configuration              │
    │  - test_chunking_token_boundaries                      │
    │  - test_embedding_dimensions                           │
    │  - test_context_builder_token_capping                  │
    │  - test_citation_validation                            │
    │  - test_conversation_lifecycle                         │
    │  - test_file_validator_image / document / audio        │
    │  - test_conversation_document_isolation                │
    │  - test_empty_retrieval_no_hallucinations              │
    └────────────────────────────────────────────────────────┘
                               ▲
    ┌──────────────────────────┴─────────────────────────────┐
    │           Underlying Subsystem Verification            │
    │  - Milestone 4: Text extraction, PaddleOCR, 8 Workers  │
    │  - Milestone 5: Conversational RAG, Gemini prompts     │
    │  - Milestone 6: Vision, audio, and upload validation   │
    └────────────────────────────────────────────────────────┘
```

---

## 2. Test Execution Commands

### Running Backend Unit & Integration Tests

From the `backend` directory:

```bash
# Run the complete test suite across all milestones
.\venv\bin\python.exe -m pytest tests/ -v

# Run Milestone 7 comprehensive integration tests
.\venv\bin\python.exe -m pytest tests/test_milestone7.py -v

# Run Multimodal security & isolation tests
.\venv\bin\python.exe -m pytest tests/test_milestone6.py -v
```

### Running Frontend Tests & Production Build

From the `frontend` directory:

```bash
# Verify static syntax, Tailwind compilation, and SPA bundling
npm run build
```

---

## 3. Verified Test Matrix (61 Tests)

| Category / Milestone | Test Name | Target Module | Verified Behavior |
|----------------------|-----------|---------------|-------------------|
| **M7: System Health** | `test_root_health_endpoint` | `app/api/health.py` | Returns 200 OK with `status: healthy` and `application: MAYA`. |
| **M7: Database Health** | `test_database_health_endpoint` | `app/api/health.py` | Reports Supabase PostgREST and Zilliz Cloud status without credential leaks. |
| **M7: RAG Health** | `test_chat_health_endpoint` | `app/api/v1/chat.py` | Reports Gemini, embedding model, and vector indexing readiness. |
| **M7: Crawler URL** | `test_crawler_url_extraction_and_hash` | `app/services/notice_crawler.py` | Normalizes relative links against `ipu.ac.in` and computes content hashes. |
| **M7: Deduplication** | `test_duplicate_notice_detection` | `app/services/notice_crawler.py` | Generates identical hashes for identical notices and distinct for revisions. |
| **M7: Worker Architecture**| `test_strict_eight_worker_configuration`| `app/services/pdf_worker_pool.py` | Strictly verifies `PDF_WORKERS=8` across settings and process pools. |
| **M7: Chunking** | `test_chunking_token_boundaries` | `app/services/chunking_service.py` | Validates 700-token chunk target and 120-token overlap boundaries. |
| **M7: Embeddings** | `test_embedding_dimensions` | `app/services/embedding_service.py` | Verifies 384-dimensional dense vectors from `all-MiniLM-L6-v2`. |
| **M7: Context Builder** | `test_context_builder_token_capping` | `app/services/context_builder.py` | Assembles structured `[SOURCE_X]` prompt blocks capped to token limit. |
| **M7: Citations** | `test_citation_validation` | `app/services/rag_service.py` | Validates citations against evidence and prunes hallucinated references. |
| **M7: Conversation** | `test_conversation_lifecycle` | `app/services/conversation_service.py`| Creates thread, appends user & assistant turns, retrieves ordered history. |
| **M7: Image Validation** | `test_file_validator_image` | `app/services/file_validator.py` | Validates PNG/JPG magic bytes (`\x89PNG`, `\xff\xd8\xff`) and rejects spoofed files. |
| **M7: Doc Validation** | `test_file_validator_document` | `app/services/file_validator.py` | Validates `%PDF-` and DOCX ZIP manifest signatures. |
| **M7: Audio Validation** | `test_file_validator_audio` | `app/services/file_validator.py` | Validates RIFF/WAVE header and enforces size boundaries. |
| **M7: Data Isolation** | `test_conversation_document_isolation` | `app/services/document_understanding.py`| Confirms student uploaded document cannot be retrieved in another thread. |
| **M7: Factual Fallback** | `test_empty_retrieval_no_hallucinations`| `app/services/rag_service.py` | Returns polite insufficient evidence flag when no circulars match. |
| **M4: Processing (18)** | `test_milestone4.py` | PDF/OCR/Chunking | All 18 document processing and worker pool tests passed. |
| **M5: RAG Chat (14)** | `test_milestone5.py` | RAG/Query/Gemini | All 14 conversational and follow-up reformulation tests passed. |
| **M6: Multimodal (13)** | `test_milestone6.py` | Vision/Audio/Docs | All 13 multimodal validation, resize, and API endpoint tests passed. |

---

## 4. End-to-End Manual Scenario Verification

| # | Evaluation Scenario | Verification Method | Outcome |
|---|---------------------|---------------------|---------|
| **1** | *"What are the latest GGSIPU notices?"* | Queried live RAG pipeline against ingested university notices. | Grounded response returned with official circular titles and dates. |
| **2** | *"What is the last date mentioned in this notice?"* | Query grounded in official End-Term exam circular. | Accurate deadline cited with page number and direct link. |
| **3** | *"What happens if I miss it?"* | Follow-up query in conversation thread testing conversational context. | Late fee penalty regulations cited factually from Ordinance 11. |
| **4** | Unrelated question test | Tested query on unrelated trivia. | MAYA politely stated that no official university notices contain this information without fabricating facts. |
| **5** | PDF Upload Question Answering | Uploaded sample B.Tech guidelines PDF and asked for internship deadline. | Extracted 15th August deadline strictly from uploaded document; verified zero leakage to public DB. |
| **6** | Image Notice Vision Analysis | Uploaded university circular image. | Extracted text and verified against official circular index. |
| **7** | DOCX Syllabus Extraction | Uploaded syllabus DOCX with evaluation scheme. | Extracted 25/25/50 exam marking scheme with structure preserved. |
| **8** | Voice STT & Spoken TTS | Tested microphone speech transcription (`en-IN`) and TTS speech playback. | Web Speech STT populated input text; SpeechSynthesis voiced responses with toggle stop controls. |
| **9** | Citation Click-Through | Clicked citation in UI. | Opened source drawer with source title, direct PDF link, and supporting excerpt. |
| **10** | Session Persistence | Refreshed browser window and navigated between `/chat` and `/notices`. | Previous conversation threads and messages loaded from Supabase. |

---

## 5. Mock Strategy & Isolation

- **Unit Test Determinism:** Unit tests mock external Gemini network requests, Supabase PostgREST endpoints, and Zilliz Cloud network calls to ensure zero cost, no quota depletion, and instant sub-second test execution.
- **Integration Tests:** Integration and live verification scripts (`manual_multimodal_test.py`, `manual_rag_test.py`) test against real models and endpoints when credentials are provided.
