# MAYA: Cloud Deployment & Infrastructure Guide

**Target Cloud Architecture:**
- **Frontend:** Vercel (Single Page React / Vite App)
- **Backend:** Render (Python Web Service / Docker container)
- **Database:** Supabase PostgreSQL (PostgREST API)
- **Vector Store:** Zilliz Cloud / Milvus (384-dimensional dense vectors)
- **LLM & Vision:** Google Gemini API (`google-genai` SDK)

---

## 1. Environment Variables Reference

Configure these environment variables in your deployment environments. **Never store real credentials in Git or frontend source code.**

### Backend Environment Variables (`backend/.env` or Render Dashboard)

| Key | Example / Recommended Value | Description |
|-----|-----------------------------|-------------|
| `APP_NAME` | `MAYA` | Service name identifier |
| `APP_ENV` | `production` | Deployment mode (`production` disables interactive API docs) |
| `PORT` | `10000` | Injected dynamically by Render ($PORT) |
| `HOST` | `0.0.0.0` | Network binding interface |
| `FRONTEND_URL` | `https://your-app.vercel.app` | Allowed CORS origins (comma-separated for multi-domain) |
| `GEMINI_API_KEY` | *(Secret Google AI Studio Key)* | Google Gemini API key |
| `GEMINI_MODEL` | `gemini-2.5-flash` or `gemini-3.5-flash` | Gemini model name |
| `SUPABASE_URL` | `https://xxxx.supabase.co` | Supabase Project URL |
| `SUPABASE_KEY` | *(Secret Supabase Service Key)* | Service role key for PostgREST database operations |
| `ZILLIZ_URI` | `https://in03-xxxx.serverless.gcp-us-west1.zillizcloud.com` | Zilliz Cloud endpoint |
| `ZILLIZ_TOKEN` | *(Secret Zilliz API Key)* | Zilliz Cloud authentication token |
| `ZILLIZ_COLLECTION` | `maya_notice_chunks` | Collection name storing 384-dim notice embeddings |
| `EMBEDDING_MODEL` | `sentence-transformers/all-MiniLM-L6-v2` | Dense sentence embedding model |
| `EMBEDDING_BATCH_SIZE` | `64` | Ingestion batch size for embedding model |
| `CHUNK_SIZE` | `700` | Target token chunk size |
| `CHUNK_OVERLAP` | `120` | Token overlap between adjacent chunks |
| `PDF_WORKERS` | `8` | Exactly 8 worker processes for multi-process extraction |
| `PDF_DOWNLOAD_CONCURRENCY` | `10` | Max concurrent async PDF downloads |
| `PDF_MAX_SIZE_MB` | `30` | Maximum PDF size limit in MB |
| `OCR_ENABLED` | `true` | Enable PaddleOCR fallback on scanned notices |
| `RAG_TOP_K` | `5` | Retrieved chunks per user query |
| `RAG_SIMILARITY_THRESHOLD` | `0.45` | Cosine similarity cutoff for vector retrieval |
| `MAX_IMAGE_SIZE_MB` | `10` | Maximum upload limit for image notices |
| `MAX_DOCUMENT_SIZE_MB` | `30` | Maximum upload limit for PDFs/DOCXs |
| `MAX_AUDIO_SIZE_MB` | `20` | Maximum upload limit for audio recordings |
| `MAX_AUDIO_DURATION_SECONDS` | `300` | Maximum audio duration limit (5 minutes) |

### Frontend Environment Variables (`frontend/.env` or Vercel Dashboard)

| Key | Example Value | Description |
|-----|---------------|-------------|
| `VITE_API_URL` | `https://maya-backend.onrender.com` | Public base URL of the deployed FastAPI backend |

---

## 2. Supabase PostgreSQL Setup

1. Create a project at [supabase.com](https://supabase.com).
2. Open the **SQL Editor** tab.
3. Paste and execute the contents of `backend/scripts/migrate_supabase.sql`.
4. This creates:
   - `public.notices` (official university circulars & metadata)
   - `public.crawl_jobs` (crawler job states and progress tracking)
   - `public.crawl_job_events` (audit log for document downloads)
   - `public.conversations` (chat threads)
   - `public.messages` (user and assistant messages with citation envelopes)
5. Copy your **Project URL** and **Service Role API Key** from **Project Settings > API**.

---

## 3. Zilliz Cloud / Milvus Setup

1. Create a serverless cluster at [zilliz.com](https://zilliz.com).
2. Copy the **Cluster Endpoint** and **API Key**.
3. The MAYA backend automatically initializes the collection `maya_notice_chunks` with 384 dimensions and COSINE metric upon startup if it does not already exist.

---

## 4. Render Deployment (Backend)

1. Connect your GitHub repository to Render.
2. Choose **New Web Service**.
3. Configure the service settings:
   - **Environment:** `Python 3`
   - **Root Directory:** `backend`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `python run_server.py`
4. In the **Environment Variables** section, add the required backend variables from Section 1.
5. In Render, set the Health Check Path to:
   ```
   /health
   ```
6. Deploy the service. Verify deployment by accessing:
   ```
   https://<your-service>.onrender.com/health
   https://<your-service>.onrender.com/api/v1/health/database
   https://<your-service>.onrender.com/api/v1/chat/health
   ```

---

## 5. Vercel Deployment (Frontend)

1. Connect your repository to Vercel.
2. Select the `frontend` folder as the **Root Directory**.
3. Vercel automatically detects the Vite build preset:
   - **Framework Preset:** `Vite`
   - **Build Command:** `npm run build`
   - **Output Directory:** `dist`
4. In **Environment Variables**, add:
   ```
   VITE_API_URL = https://<your-render-service>.onrender.com
   ```
5. The `frontend/vercel.json` file automatically handles SPA route fallbacks so direct navigation to `/chat`, `/notices`, and `/about` functions cleanly.
6. Deploy.

---

## 6. Troubleshooting Common Deployment Issues

| Problem | Root Cause | Solution |
|---------|------------|----------|
| **CORS Error in Browser** | `FRONTEND_URL` on Render does not match Vercel origin. | Add your exact Vercel domain (e.g. `https://maya-app.vercel.app`) to `FRONTEND_URL`. MAYA automatically supports any `*.vercel.app` preview branch. |
| **PDF Processing OOM on Render Free Tier** | Free tier memory limit (512MB) exceeded during OCR. | Set `OCR_ENABLED=false` on memory-constrained nodes or upgrade to a 2GB+ standard instance. Native PyMuPDF text extraction remains active and fast. |
| **Voice STT Not Available** | Browser lacks Web Speech API. | Web Speech STT requires a Chromium browser (Chrome, Edge, Brave) or Safari. Firefox users receive a graceful fallback. |
| **Zilliz Connection Refused** | Incorrect region or cluster URL. | Verify `ZILLIZ_URI` starts with `https://` and includes the full hostname from your Zilliz Cloud dashboard. |
