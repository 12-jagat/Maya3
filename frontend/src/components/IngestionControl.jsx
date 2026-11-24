import React from 'react';
import { Cpu, Play, RefreshCw, Loader2, Database, FileCheck, AlertTriangle, Layers } from 'lucide-react';

export default function IngestionControl({
  stats,
  isProcessing,
  activeJob,
  onStartProcessing,
  onRetryFailed,
}) {
  return (
    <div className="w-full bg-white rounded-2xl border border-warm-200/90 shadow-premium p-6 mb-8 transition-all">
      <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-6 pb-5 border-b border-warm-100">
        <div>
          <div className="flex items-center gap-2 mb-1.5">
            <Cpu className="w-4 h-4 text-crimson-800" />
            <h2 className="text-lg font-bold text-charcoal-900 tracking-tight">
              Document Extraction & Zilliz Vector Indexer
            </h2>
            <span className="text-xs font-semibold px-2 py-0.5 rounded bg-emerald-50 text-emerald-800 border border-emerald-200">
              8-Worker Pool Active
            </span>
          </div>
          <p className="text-sm text-charcoal-500 max-w-xl leading-relaxed">
            Extracts native text with PyMuPDF, executes OCR fallback for scanned circulars, cleans text, splits into 700-token chunks with 120-token overlap, and generates 384-dimensional dense vectors stored in Zilliz Cloud.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2.5 w-full sm:w-auto">
          <button
            type="button"
            onClick={onStartProcessing}
            disabled={isProcessing}
            className={`inline-flex items-center justify-center gap-2 px-5 py-2.5 rounded-xl font-semibold text-xs transition-all shadow-sm ${
              isProcessing
                ? 'bg-warm-200 text-charcoal-400 cursor-not-allowed'
                : 'bg-crimson-900 text-white hover:bg-crimson-950 active:scale-[0.98]'
            }`}
          >
            {isProcessing ? (
              <>
                <Loader2 className="w-3.5 h-3.5 animate-spin text-charcoal-500" />
                <span>Processing with 8 Workers...</span>
              </>
            ) : (
              <>
                <Play className="w-3.5 h-3.5 fill-current" />
                <span>Process Downloaded Documents</span>
              </>
            )}
          </button>

          <button
            type="button"
            onClick={onRetryFailed}
            disabled={isProcessing}
            className="inline-flex items-center justify-center gap-1.5 px-4 py-2.5 rounded-xl font-semibold text-xs border border-warm-200 bg-white text-charcoal-700 hover:bg-warm-50 disabled:opacity-50 transition-colors shadow-subtle"
          >
            <RefreshCw className="w-3.5 h-3.5 text-charcoal-500" />
            <span>Retry Failed</span>
          </button>
        </div>
      </div>

      {/* Real-time Statistics Tiles */}
      <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-8 gap-2.5 pt-5">
        <div className="p-3 rounded-xl bg-warm-50/70 border border-warm-200/60 text-center">
          <p className="text-[11px] text-charcoal-500 font-medium mb-0.5">Downloaded</p>
          <p className="text-lg font-bold text-charcoal-900">{stats?.downloaded || 0}</p>
        </div>

        <div className="p-3 rounded-xl bg-warm-50/70 border border-warm-200/60 text-center">
          <p className="text-[11px] text-charcoal-500 font-medium mb-0.5">Pending</p>
          <p className="text-lg font-bold text-amber-700">{stats?.pending || 0}</p>
        </div>

        <div className="p-3 rounded-xl bg-sky-50/70 border border-sky-200/60 text-center">
          <p className="text-[11px] text-sky-800 font-medium mb-0.5">Extracted</p>
          <p className="text-lg font-bold text-sky-900">{stats?.extracted || 0}</p>
        </div>

        <div className="p-3 rounded-xl bg-purple-50/70 border border-purple-200/60 text-center">
          <p className="text-[11px] text-purple-800 font-medium mb-0.5">OCR Pages</p>
          <p className="text-lg font-bold text-purple-900">{stats?.ocr_processed || 0}</p>
        </div>

        <div className="p-3 rounded-xl bg-emerald-50/70 border border-emerald-200/60 text-center">
          <p className="text-[11px] text-emerald-800 font-medium mb-0.5">Indexed Docs</p>
          <p className="text-lg font-bold text-emerald-900">{stats?.indexed || 0}</p>
        </div>

        <div className="p-3 rounded-xl bg-teal-50/70 border border-teal-200/60 text-center">
          <p className="text-[11px] text-teal-800 font-medium mb-0.5">Vector Chunks</p>
          <p className="text-lg font-bold text-teal-900">{stats?.total_indexed_chunks || 0}</p>
        </div>

        <div className="p-3 rounded-xl bg-rose-50/70 border border-rose-200/60 text-center">
          <p className="text-[11px] text-rose-800 font-medium mb-0.5">Failed</p>
          <p className="text-lg font-bold text-rose-900">{stats?.failed || 0}</p>
        </div>

        <div className="p-3 rounded-xl bg-warm-50/70 border border-warm-200/60 text-center">
          <p className="text-[11px] text-charcoal-500 font-medium mb-0.5">Worker Pool</p>
          <p className="text-xs font-bold text-crimson-900 mt-1 flex items-center justify-center gap-1">
            <Cpu className="w-3 h-3 text-crimson-800" />
            <span>8 Workers</span>
          </p>
        </div>
      </div>

      {/* Active Pipeline Progress */}
      {activeJob && isProcessing && (
        <div className="mt-4 p-3 rounded-xl bg-amber-50/70 border border-amber-200 text-xs text-amber-900 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Loader2 className="w-4 h-4 animate-spin text-amber-700" />
            <span className="font-semibold">Current Stage:</span>
            <span className="font-mono">{activeJob.current_stage}</span>
          </div>
          <span className="text-amber-800">
            Processed {activeJob.processed_documents || 0} / {activeJob.total_documents || 0} documents
          </span>
        </div>
      )}
    </div>
  );
}
