import React from 'react';
import { Activity, FileText, CheckCircle, AlertTriangle, Layers, ArrowRight, Cpu } from 'lucide-react';

const STAGE_LABELS = {
  initializing: 'Initializing crawl job...',
  discovering_pages: 'Discovering pagination & circulars...',
  extracting_notices: 'Extracting metadata & deduplicating...',
  downloading_pdfs: 'Concurrently downloading PDFs (10x)...',
  processing_documents: 'Processing documents with 8 worker processes...',
  completed: 'Crawl completed successfully',
  completed_with_warnings: 'Crawl completed with minor warnings',
  failed: 'Crawl failed',
  resumed: 'Resuming previous crawl job...',
};

export default function CrawlProgress({ job }) {
  if (!job) return null;

  const isRunning = job.status === 'running';
  const stageLabel = STAGE_LABELS[job.current_stage] || job.current_stage || 'Processing...';

  return (
    <div className="w-full bg-white rounded-2xl border border-warm-200/90 shadow-premium p-6 mb-8 transition-all">
      {/* Header and status */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 pb-4 border-b border-warm-100">
        <div>
          <div className="flex items-center gap-2.5">
            <span className={`w-2.5 h-2.5 rounded-full ${isRunning ? 'bg-amber-500 animate-ping' : 'bg-emerald-500'}`}></span>
            <span className="text-xs font-mono uppercase tracking-wider font-semibold text-charcoal-400">
              Job ID: {job.id.slice(0, 8)}...
            </span>
            <span
              className={`text-xs px-2.5 py-0.5 rounded-full font-medium ${
                job.status === 'completed'
                  ? 'bg-emerald-50 text-emerald-800 border border-emerald-200'
                  : isRunning
                  ? 'bg-amber-50 text-amber-800 border border-amber-200 animate-pulse'
                  : 'bg-rose-50 text-rose-800 border border-rose-200'
              }`}
            >
              {job.status.toUpperCase()}
            </span>
          </div>
          <p className="text-sm font-medium text-charcoal-800 mt-1 flex items-center gap-2">
            <Activity className="w-4 h-4 text-crimson-800" />
            <span>{stageLabel}</span>
          </p>
        </div>

        {job.current_source && (
          <div className="text-xs text-charcoal-500 bg-warm-50 px-3 py-1.5 rounded-lg border border-warm-200/60 max-w-sm truncate">
            <span className="font-semibold text-charcoal-700">Source: </span>
            <span className="font-mono">{job.current_source}</span>
          </div>
        )}
      </div>

      {/* Metrics Grid */}
      <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-6 gap-3 pt-5">
        <div className="p-3 rounded-xl bg-warm-50/70 border border-warm-200/60 text-center">
          <p className="text-xs text-charcoal-500 font-medium mb-1">Pages Crawled</p>
          <p className="text-xl font-bold text-charcoal-900">{job.pages_processed || 0}</p>
        </div>

        <div className="p-3 rounded-xl bg-warm-50/70 border border-warm-200/60 text-center">
          <p className="text-xs text-charcoal-500 font-medium mb-1">Notices Found</p>
          <p className="text-xl font-bold text-charcoal-900">{job.notices_discovered || 0}</p>
        </div>

        <div className="p-3 rounded-xl bg-emerald-50/70 border border-emerald-200/50 text-center">
          <p className="text-xs text-emerald-800 font-medium mb-1">New Notices</p>
          <p className="text-xl font-bold text-emerald-900">+{job.new_notices || 0}</p>
        </div>

        <div className="p-3 rounded-xl bg-warm-50/70 border border-warm-200/60 text-center">
          <p className="text-xs text-charcoal-500 font-medium mb-1">Unchanged</p>
          <p className="text-xl font-bold text-charcoal-600">{job.skipped_notices || 0}</p>
        </div>

        <div className="p-3 rounded-xl bg-crimson-50/60 border border-crimson-200/50 text-center">
          <p className="text-xs text-crimson-900 font-medium mb-1">PDFs Ingested</p>
          <p className="text-xl font-bold text-crimson-950">{job.pdfs_downloaded || 0}</p>
        </div>

        <div className="p-3 rounded-xl bg-warm-50/70 border border-warm-200/60 text-center">
          <p className="text-xs text-charcoal-500 font-medium mb-1">Worker Pool</p>
          <p className="text-sm font-bold text-charcoal-800 flex items-center justify-center gap-1 mt-1">
            <Cpu className="w-3.5 h-3.5 text-crimson-800" />
            <span>8 Processes</span>
          </p>
        </div>
      </div>

      {/* Warnings or errors */}
      {job.errors && job.errors.length > 0 && (
        <div className="mt-4 p-3 rounded-xl bg-amber-50/80 border border-amber-200/80 text-xs text-amber-900">
          <div className="flex items-center gap-1.5 font-semibold mb-1">
            <AlertTriangle className="w-4 h-4 text-amber-600" />
            <span>Notice Warnings ({job.errors.length}):</span>
          </div>
          <ul className="list-disc list-inside space-y-0.5 text-amber-800">
            {job.errors.slice(0, 3).map((err, i) => (
              <li key={i} className="truncate">{err}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
