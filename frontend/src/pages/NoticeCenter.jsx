import React, { useEffect, useState, useRef } from 'react';
import Header from '../components/Header';
import CrawlControl from '../components/CrawlControl';
import CrawlProgress from '../components/CrawlProgress';
import IngestionControl from '../components/IngestionControl';
import SemanticSearchBox from '../components/SemanticSearchBox';
import NoticeFilters from '../components/NoticeFilters';
import NoticeList from '../components/NoticeList';
import {
  checkHealth,
  getNotices,
  startCrawl,
  getCrawlStatus,
  startIngestion,
  getIngestionStatus,
  getIngestionStats,
  retryNoticeIngestion,
} from '../services/api';
import { Bell, RefreshCw } from 'lucide-react';

export default function NoticeCenter() {
  const [healthStatus, setHealthStatus] = useState(null);
  const [isChecking, setIsChecking] = useState(true);

  // Crawler State
  const [isCrawling, setIsCrawling] = useState(false);
  const [activeJob, setActiveJob] = useState(null);

  // Ingestion State (Milestone 4: PyMuPDF + OCR + 8 Workers + Zilliz)
  const [isIngesting, setIsIngesting] = useState(false);
  const [activeIngestionJob, setActiveIngestionJob] = useState(null);
  const [ingestionStats, setIngestionStats] = useState(null);

  // Notices List State
  const [notices, setNotices] = useState([]);
  const [totalCount, setTotalCount] = useState(0);
  const [isLoadingNotices, setIsLoadingNotices] = useState(true);
  const [search, setSearch] = useState('');
  const [category, setCategory] = useState('');
  const [skip, setSkip] = useState(0);
  const limit = 18;

  const pollingRef = useRef(null);
  const ingestionPollingRef = useRef(null);

  // Check backend health and load initial stats
  useEffect(() => {
    let isMounted = true;
    checkHealth()
      .then((data) => {
        if (isMounted) {
          setHealthStatus(data);
          setIsChecking(false);
        }
      })
      .catch(() => {
        if (isMounted) {
          setHealthStatus(null);
          setIsChecking(false);
        }
      });

    loadIngestionStats();

    return () => {
      isMounted = false;
    };
  }, []);

  // Fetch ingestion statistics
  const loadIngestionStats = async () => {
    try {
      const stats = await getIngestionStats();
      setIngestionStats(stats);
    } catch (err) {
      console.error('Error loading ingestion stats:', err);
    }
  };

  // Fetch notices
  const loadNotices = async () => {
    setIsLoadingNotices(true);
    try {
      const data = await getNotices({ skip, limit, category, search });
      setNotices(data.items || []);
      setTotalCount(data.total || 0);
    } catch (err) {
      console.error('Error loading notices:', err);
    } finally {
      setIsLoadingNotices(false);
    }
  };

  useEffect(() => {
    loadNotices();
  }, [skip, category, search]);

  // Handle start crawl
  const handleStartCrawl = async () => {
    try {
      setIsCrawling(true);
      const job = await startCrawl({ max_pages_per_source: 20, download_pdfs: true });
      setActiveJob(job);
      startPolling(job.id);
    } catch (err) {
      console.error('Failed to trigger crawl:', err);
      setIsCrawling(false);
    }
  };

  // Poll crawl status
  const startPolling = (jobId) => {
    if (pollingRef.current) clearInterval(pollingRef.current);

    pollingRef.current = setInterval(async () => {
      try {
        const updated = await getCrawlStatus(jobId);
        setActiveJob(updated);

        if (updated.status === 'completed' || updated.status === 'failed' || updated.status === 'completed_with_warnings') {
          setIsCrawling(false);
          clearInterval(pollingRef.current);
          pollingRef.current = null;
          loadNotices();
          loadIngestionStats();
        }
      } catch (err) {
        console.error('Error polling crawl status:', err);
      }
    }, 2500);
  };

  // Handle start ingestion (Milestone 4)
  const handleStartIngestion = async (forceReprocess = false) => {
    try {
      setIsIngesting(true);
      const job = await startIngestion({ batch_size: 100, force_reprocess: forceReprocess });
      setActiveIngestionJob(job);
      startIngestionPolling(job.id);
    } catch (err) {
      console.error('Failed to trigger document ingestion:', err);
      setIsIngesting(false);
    }
  };

  // Poll ingestion status
  const startIngestionPolling = (jobId) => {
    if (ingestionPollingRef.current) clearInterval(ingestionPollingRef.current);

    ingestionPollingRef.current = setInterval(async () => {
      try {
        const updated = await getIngestionStatus(jobId);
        setActiveIngestionJob(updated);

        if (updated.status === 'completed' || updated.status === 'failed' || updated.status === 'completed_with_errors') {
          setIsIngesting(false);
          clearInterval(ingestionPollingRef.current);
          ingestionPollingRef.current = null;
          loadNotices();
          loadIngestionStats();
        }
      } catch (err) {
        console.error('Error polling ingestion status:', err);
      }
    }, 2500);
  };

  // Handle single notice retry
  const handleRetryNotice = async (noticeId) => {
    try {
      await retryNoticeIngestion(noticeId);
      loadNotices();
      loadIngestionStats();
    } catch (err) {
      console.error('Failed to retry notice:', err);
    }
  };

  // Cleanup polling on unmount
  useEffect(() => {
    return () => {
      if (pollingRef.current) clearInterval(pollingRef.current);
      if (ingestionPollingRef.current) clearInterval(ingestionPollingRef.current);
    };
  }, []);

  return (
    <div className="min-h-screen flex flex-col bg-warm-50">
      <Header
        isConnected={Boolean(healthStatus?.status === 'healthy')}
        isChecking={isChecking}
        appName={healthStatus?.application}
      />

      <main className="flex-1 max-w-6xl mx-auto w-full px-4 sm:px-6 py-8">
        {/* Page Title */}
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 mb-6">
          <div>
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-semibold bg-crimson-50 text-crimson-900 border border-crimson-200/60 mb-2">
              <Bell className="w-3.5 h-3.5" />
              <span>GGSIPU Official Circulars</span>
            </div>
            <h1 className="text-3xl font-bold text-charcoal-900 tracking-tight">
              University Notice Center
            </h1>
            <p className="text-sm text-charcoal-500 mt-1">
              Index and browse live notices from Guru Gobind Singh Indraprastha University official portals.
            </p>
          </div>

          <button
            type="button"
            onClick={loadNotices}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-semibold bg-white border border-warm-200 text-charcoal-700 hover:bg-warm-50 transition-colors shadow-subtle"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            <span>Refresh Notices</span>
          </button>
        </div>

        {/* Crawl Control Box */}
        <CrawlControl
          onStartCrawl={handleStartCrawl}
          isCrawling={isCrawling}
          activeJob={activeJob}
        />

        {/* Live Crawl Progress */}
        {activeJob && <CrawlProgress job={activeJob} />}

        {/* Milestone 4: Document Extraction, OCR & Vector Indexing Control */}
        <IngestionControl
          stats={ingestionStats}
          isProcessing={isIngesting}
          activeJob={activeIngestionJob}
          onStartProcessing={() => handleStartIngestion(false)}
          onRetryFailed={() => handleStartIngestion(true)}
        />

        {/* Milestone 4: Semantic Vector Search Testbed */}
        <SemanticSearchBox />

        {/* Notice Search & Category Filters */}
        <NoticeFilters
          search={search}
          onSearchChange={(val) => {
            setSearch(val);
            setSkip(0);
          }}
          category={category}
          onCategoryChange={(cat) => {
            setCategory(cat);
            setSkip(0);
          }}
          totalCount={totalCount}
        />

        {/* Paginated Notice Grid */}
        <NoticeList
          notices={notices}
          total={totalCount}
          skip={skip}
          limit={limit}
          onPageChange={(newSkip) => setSkip(newSkip)}
          isLoading={isLoadingNotices}
          onRetry={handleRetryNotice}
        />
      </main>

      <footer className="w-full border-t border-warm-200/80 py-6 text-center text-xs text-charcoal-400">
        <p>MAYA • GGSIPU Official Notice Crawler & Multimodal Processing Engine</p>
      </footer>
    </div>
  );
}
