# MAYA: Multimodal AI-Powered University Assistant for GGSIPU

MAYA is an intelligent, multimodal university assistant tailored specifically for students and faculty of Guru Gobind Singh Indraprastha University (GGSIPU). It bridges the gap between scattered university notices and immediate student questions through official notice crawling, 8-process document extraction, dense vector indexing, verifiable citation generation, and conversational AI.

---

## 🏛️ Project Identity & Core Capabilities

- **Target Institution:** Guru Gobind Singh Indraprastha University (GGSIPU, Dwarka, New Delhi)
- **Official Portals:** `ipu.ac.in/notices.php`, examination portals, syllabus guidelines.
- **Key Capabilities:**
  - **Automated Ingestion:** Asynchronous crawler with SHA-256 deduplication and stage resumption.
  - **8-Process Document Extraction:** Dedicated `ProcessPoolExecutor(max_workers=8)` combining native PyMuPDF extraction with PaddleOCR fallback for scanned circulars.
  - **Dense Vector Search:** 384-dimensional dense embeddings (`sentence-transformers/all-MiniLM-L6-v2`) indexed in Zilliz Cloud with cosine metric.
  - **Conversational RAG:** Grounded question answering powered by Google Gemini with strict hallucination pruning and page-level citations.
  - **Multimodal AI:** Image notice cross-checking, user PDF/DOCX question-answering with session isolation, and audio lecture transcription.
  - **Accessible Voice:** Native browser Web Speech API for voice recognition (`en-IN`, `hi-IN`) and speech synthesis output.

---

## 🛠️ Technology Stack

| Layer | Technologies |
| :--- | :--- |
| **Frontend** | React 18, Vite, Tailwind CSS, Lucide React, Axios, React Router v6 |
| **Backend** | Python 3, FastAPI, Uvicorn, Pydantic v2 Settings, HTTPX |
| **AI & LLM** | Google Gemini API (`google-genai` SDK) |
| **Vector DB** | Zilliz Cloud / Milvus (Collection: `maya_notice_chunks`, 384 dimensions) |
| **Relational DB** | Supabase PostgreSQL (`notices`, `crawl_jobs`, `conversations`, `messages`) |
| **Embeddings** | `sentence-transformers/all-MiniLM-L6-v2` |
| **Document Processing** | PyMuPDF (`fitz`), PaddleOCR, `python-docx` |
| **Worker Architecture** | Python multiprocessing `spawn` context with exactly 8 PDF workers |
| **Voice Layer** | Browser Web Speech API (`SpeechRecognition` & `SpeechSynthesis`) |
| **Cloud Deployment** | Vercel (Frontend SPA) + Render (Backend Web Service) |

---

## 📁 Repository Structure

```
MAYA/
├── frontend/                     # React + Vite client
│   ├── public/                   # Static assets & icons
│   ├── src/
│   │   ├── components/           # UI components (Header, ChatWindow, VoiceInput, etc.)
│   │   ├── hooks/                # Speech recognition & synthesis hooks
│   │   ├── pages/                # Pages (WelcomePage, ChatPage, NoticeCenter, AboutPage)
│   │   ├── services/             # Axios API client (api.js)
│   │   ├── App.jsx               # Application routes
│   │   ├── index.css             # Tailwind CSS & global styles
│   │   └── main.jsx              # Vite entrypoint
│   ├── vercel.json               # Vercel SPA routing rewrites
│   ├── package.json
│   └── vite.config.js
├── backend/                      # FastAPI application
│   ├── app/
│   │   ├── api/                  # API routers (/health, /api/v1)
│   │   ├── database/             # Supabase & Zilliz clients
│   │   ├── models/               # Domain models
│   │   ├── schemas/              # Pydantic v2 schemas
│   │   ├── services/             # Core business logic (RAG, Gemini, Crawler, etc.)
│   │   ├── utils/                # Error handlers, loggers, text cleaners
│   │   ├── config.py             # Pydantic Settings management
│   │   └── main.py               # FastAPI application factory & lifespan
│   ├── scripts/                  # Migration SQL and manual verification scripts
│   ├── tests/                    # Automated pytest test suites (M4, M5, M6, M7)
│   ├── requirements.txt          # Python production dependencies
│   ├── run_server.py             # Production uvicorn server runner ($PORT / 0.0.0.0)
│   └── pytest.ini                # Pytest configuration
├── docs/                         # Engineering documentation & reports
│   ├── PROJECT_AUDIT.md          # Complete project audit & subsystem verification
│   ├── ARCHITECTURE.md           # System architecture & technical design
│   ├── TESTING.md                # Test execution commands & results (61 passing tests)
│   ├── DEPLOYMENT.md             # Cloud deployment instructions (Vercel + Render)
│   ├── PROJECT_REPORT.md         # Full academic engineering report
│   └── FINAL_STATUS.md           # Final feature status & classification
├── render.yaml                   # Render Blueprint infrastructure specification
├── .gitignore
└── README.md
```

---

## 🚀 Local Development Setup

### 1. Prerequisites
- Python 3.10+ (tested on Python 3.11, 3.12, 3.14)
- Node.js 18+ and npm
- Active credentials for Google Gemini API, Supabase PostgreSQL, and Zilliz Cloud (or run in resilient offline in-memory fallback mode)

### 2. Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows (PowerShell):
.\venv\Scripts\Activate.ps1   # or .\venv\bin\Activate.ps1
# Linux / macOS:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your credentials

# Run development server
python run_server.py
# (Or run directly via the virtualenv launcher: .\venv\bin\python.exe run_server.py)
```

Verify backend health at:
- Root Health: [http://localhost:8000/health](http://localhost:8000/health)
- Database Health: [http://localhost:8000/api/v1/health/database](http://localhost:8000/api/v1/health/database)
- Chat/RAG Health: [http://localhost:8000/api/v1/chat/health](http://localhost:8000/api/v1/chat/health)

### 3. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Configure environment
cp .env.example .env

# Run development server
npm run dev
```

Open the application in your browser: [http://localhost:5173](http://localhost:5173).

---

## 🧪 Automated Testing

Run the automated test suite covering all 61 tests across document processing, RAG, multimodal understanding, and system health:

```bash
cd backend
.\venv\bin\python.exe -m pytest tests/ -v
```

All 61 tests pass deterministically without paid API charges via unit mocks.

To test the frontend production build:

```bash
cd frontend
npm run build
```

---

## ☁️ Cloud Deployment

- **Backend (Render):** Deploy using `render.yaml` or connect repository to Render. Set Root Directory to `backend`, Build Command to `pip install -r requirements.txt`, and Start Command to `python run_server.py`.
- **Frontend (Vercel):** Deploy `frontend` directory as a Vite SPA. `frontend/vercel.json` provides route rewrites.
- Full details are provided in [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md).

---

## 🔒 Security & Privacy Guarantees

1. **Zero Credential Leakage:** All API keys, database connection strings, and vector tokens reside exclusively on the backend. No secrets are exposed to client JavaScript or documentation.
2. **Session-Level Document Isolation:** User-uploaded guidelines and fee receipts are strictly isolated to their active conversation thread and are never inserted into the public university Zilliz index.
3. **Factual Grounding:** Prompts enforce strict adherence to retrieved circulars. If no official evidence is present in university notices, MAYA explicitly returns an insufficient evidence notice instead of fabricating dates or fees.
