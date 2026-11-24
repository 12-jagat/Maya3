-- ====================================================================
-- MAYA: Supabase Database Schema Migration
-- Multimodal AI-Powered University Assistant for GGSIPU
-- ====================================================================

-- 1. NOTICES TABLE
CREATE TABLE IF NOT EXISTS public.notices (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title TEXT NOT NULL,
    content TEXT DEFAULT '',
    source_url TEXT UNIQUE NOT NULL,
    pdf_url TEXT,
    category TEXT DEFAULT 'General',
    published_date TEXT,
    processing_status TEXT DEFAULT 'pending', -- 'pending', 'downloaded', 'processed', 'failed'
    content_hash TEXT,
    scraped_at TIMESTAMPTZ DEFAULT now(),
    indexed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- Indexes for high-performance notice filtering and search
CREATE INDEX IF NOT EXISTS idx_notices_source_url ON public.notices (source_url);
CREATE INDEX IF NOT EXISTS idx_notices_published_date ON public.notices (published_date DESC);
CREATE INDEX IF NOT EXISTS idx_notices_category ON public.notices (category);
CREATE INDEX IF NOT EXISTS idx_notices_processing_status ON public.notices (processing_status);

-- 2. CRAWL JOBS TABLE
CREATE TABLE IF NOT EXISTS public.crawl_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    status TEXT NOT NULL DEFAULT 'pending', -- 'pending', 'running', 'completed', 'failed', 'resumed'
    current_stage TEXT DEFAULT 'initializing', -- 'discovering_pages', 'extracting_notices', 'downloading_pdfs', 'processing_documents', 'completed'
    current_source TEXT,
    pages_discovered INT DEFAULT 0,
    pages_processed INT DEFAULT 0,
    notices_discovered INT DEFAULT 0,
    new_notices INT DEFAULT 0,
    updated_notices INT DEFAULT 0,
    skipped_notices INT DEFAULT 0,
    pdfs_downloaded INT DEFAULT 0,
    pdfs_failed INT DEFAULT 0,
    last_processed_url TEXT,
    errors JSONB DEFAULT '[]'::jsonb,
    started_at TIMESTAMPTZ DEFAULT now(),
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_crawl_jobs_status ON public.crawl_jobs (status);
CREATE INDEX IF NOT EXISTS idx_crawl_jobs_created_at ON public.crawl_jobs (created_at DESC);

-- 3. CRAWL JOB EVENTS (AUDIT TRAIL)
CREATE TABLE IF NOT EXISTS public.crawl_job_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id UUID REFERENCES public.crawl_jobs(id) ON DELETE CASCADE,
    stage TEXT NOT NULL,
    message TEXT NOT NULL,
    details JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_crawl_job_events_job_id ON public.crawl_job_events (job_id);

-- Enable Row Level Security (RLS) with full backend service access
ALTER TABLE public.notices ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.crawl_jobs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.crawl_job_events ENABLE ROW LEVEL SECURITY;

-- Allow public read & service role all
CREATE POLICY "Allow public read notices" ON public.notices FOR SELECT USING (true);
CREATE POLICY "Allow service all notices" ON public.notices USING (true) WITH CHECK (true);

CREATE POLICY "Allow public read crawl_jobs" ON public.crawl_jobs FOR SELECT USING (true);
CREATE POLICY "Allow service all crawl_jobs" ON public.crawl_jobs USING (true) WITH CHECK (true);

CREATE POLICY "Allow service all crawl_job_events" ON public.crawl_job_events USING (true) WITH CHECK (true);

-- ====================================================================
-- 4. CONVERSATIONS & MESSAGES (MILESTONE 5)
-- ====================================================================

CREATE TABLE IF NOT EXISTS public.conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title TEXT NOT NULL DEFAULT 'New Conversation',
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID REFERENCES public.conversations(id) ON DELETE CASCADE,
    role TEXT NOT NULL, -- 'user', 'assistant', 'system'
    content TEXT NOT NULL,
    citations JSONB DEFAULT '[]'::jsonb,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_messages_conversation_id ON public.messages (conversation_id);
CREATE INDEX IF NOT EXISTS idx_messages_created_at ON public.messages (created_at ASC);

ALTER TABLE public.conversations ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.messages ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Allow all conversations" ON public.conversations USING (true) WITH CHECK (true);
CREATE POLICY "Allow all messages" ON public.messages USING (true) WITH CHECK (true);
