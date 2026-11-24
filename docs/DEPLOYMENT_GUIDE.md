# MAYA Cloud Deployment Guide (Vercel + Render)

MAYA is architected for cloud deployment using:
- **Frontend**: [Vercel](https://vercel.com) (React 18 + Vite + Tailwind CSS)
- **Backend**: [Render](https://render.com) (FastAPI + 8-Worker Multiprocessing + Uvicorn)
- **Database**: [Supabase](https://supabase.com) (PostgreSQL)
- **Vector DB**: [Zilliz Cloud](https://zilliz.com) (Milvus 384-dimensional dense vectors)
- **LLM**: [Google AI Studio](https://aistudio.google.com) (Gemini API with multi-model fallback)

---

## 1. Database Setup (Supabase)

1. Open your Supabase Project Dashboard: [https://supabase.com/dashboard](https://supabase.com/dashboard).
2. Go to **SQL Editor** in the left sidebar.
3. Open or copy the contents of `backend/scripts/migrate_supabase.sql`.
4. Click **Run**.
   - This creates `notices`, `crawl_jobs`, `crawl_job_events`, `conversations`, and `messages` tables with appropriate indexes and RLS policies.

---

## 2. Backend Deployment (Render)

### Option A: Using Blueprint (`render.yaml`)
1. Push your repository to GitHub.
2. In Render Dashboard, click **New +** -> **Blueprint**.
3. Select your repository. Render will automatically read `render.yaml`.
4. Fill in the secret environment variables when prompted.

### Option B: Manual Web Service
1. In Render Dashboard, click **New +** -> **Web Service**.
2. Connect your GitHub repository.
3. Configure the following fields:
   - **Name**: `maya-backend`
   - **Root Directory**: `backend`
   - **Environment**: `Python`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python run_server.py`
   - **Health Check Path**: `/health`
4. Add the following **Environment Variables**:

| Variable | Value | Description |
|---|---|---|
| `APP_ENV` | `production` | Production environment mode |
| `HOST` | `0.0.0.0` | Bind address |
| `PORT` | `10000` | Port assigned by Render |
| `PDF_WORKERS` | `8` | Strict 8-process worker pool |
| `OCR_ENABLED` | `true` | Enable OCR fallback |
| `GEMINI_API_KEY` | `your_gemini_api_key` | Google Gemini API key |
| `GEMINI_MODEL` | `gemini-3.1-flash-lite` | Primary production model |
| `SUPABASE_URL` | `https://your-project.supabase.co/rest/v1/` | Supabase URL |
| `SUPABASE_KEY` | `your_supabase_service_key` | Supabase API key |
| `ZILLIZ_URI` | `https://your-cluster.zillizcloud.com` | Zilliz Cloud endpoint |
| `ZILLIZ_TOKEN` | `your_zilliz_token` | Zilliz authentication token |
| `FRONTEND_URL` | `https://your-maya-app.vercel.app` | Allowed CORS origin |

5. Click **Create Web Service**. Wait for the build and deployment to complete.
6. Note your Render backend URL (e.g., `https://maya-backend.onrender.com`).

---

## 3. Frontend Deployment (Vercel)

1. Go to [Vercel Dashboard](https://vercel.com) and click **Add New...** -> **Project**.
2. Import your GitHub repository.
3. Configure project settings:
   - **Framework Preset**: `Vite`
   - **Root Directory**: Click *Edit* and select `frontend`.
   - **Build Command**: `npm run build`
   - **Output Directory**: `dist`
4. Expand **Environment Variables** and add:

| Key | Value |
|---|---|
| `VITE_API_URL` | `https://maya-backend.onrender.com` (Your Render backend URL without trailing slash) |

5. Click **Deploy**.
6. Once deployed, copy your production Vercel URL (e.g., `https://maya-ggsipu.vercel.app`).
7. Return to your Render backend dashboard -> **Environment** -> Update `FRONTEND_URL` to your Vercel URL so CORS allows all browser requests.

---

## 4. Verification Checklist

- [ ] Open `https://your-backend.onrender.com/health` -> returns `{"status":"healthy","application":"MAYA"}`
- [ ] Open your Vercel frontend -> Status badge in the header shows **Healthy** in green.
- [ ] Navigate to **Notice Center** -> Click **"Crawl All Notices"** to discover circulars and index them into Zilliz Cloud.
- [ ] Ask a question in **Chat** -> MAYA returns answers with verified university citations.
- [ ] Click the microphone or open **Voice Assistant Mode** -> Speak naturally to interact via turn-based voice.
