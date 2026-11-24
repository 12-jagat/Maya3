import React from 'react';
import { Calendar, FileText, ExternalLink, ShieldCheck, Download, RefreshCw, CheckCircle2, AlertCircle, Cpu } from 'lucide-react';

const STATUS_CONFIG = {
  indexed: { label: 'Indexed in Zilliz', bg: 'bg-emerald-50', text: 'text-emerald-800', border: 'border-emerald-200' },
  extracted: { label: 'Text Extracted', bg: 'bg-sky-50', text: 'text-sky-800', border: 'border-sky-200' },
  downloaded: { label: 'PDF Downloaded', bg: 'bg-indigo-50', text: 'text-indigo-800', border: 'border-indigo-200' },
  chunking: { label: 'Chunking...', bg: 'bg-amber-50', text: 'text-amber-800', border: 'border-amber-200' },
  embedding: { label: 'Embedding (384-d)...', bg: 'bg-purple-50', text: 'text-purple-800', border: 'border-purple-200' },
  indexing: { label: 'Writing to Vector DB...', bg: 'bg-teal-50', text: 'text-teal-800', border: 'border-teal-200' },
  failed: { label: 'Extraction Failed', bg: 'bg-rose-50', text: 'text-rose-800', border: 'border-rose-200' },
  pending: { label: 'Pending Processing', bg: 'bg-warm-100', text: 'text-charcoal-600', border: 'border-warm-200' },
};

export default function NoticeCard({ notice, onRetry }) {
  const isPdf = Boolean(notice.pdf_url);
  const statusKey = notice.processing_status || 'pending';
  const statusCfg = STATUS_CONFIG[statusKey] || STATUS_CONFIG.pending;

  return (
    <div className="group bg-white rounded-xl border border-warm-200/90 hover:border-crimson-300 p-5 shadow-subtle hover:shadow-premium transition-all duration-200 flex flex-col justify-between">
      <div>
        {/* Category & Date */}
        <div className="flex items-center justify-between gap-2 mb-3">
          <span className="text-xs font-semibold px-2.5 py-0.5 rounded-full bg-crimson-50 text-crimson-900 border border-crimson-100">
            {notice.category || 'General'}
          </span>

          <div className="flex items-center gap-2">
            {notice.published_date && (
              <span className="inline-flex items-center gap-1 text-xs text-charcoal-500 font-medium">
                <Calendar className="w-3 h-3 text-charcoal-400" />
                <span>{notice.published_date}</span>
              </span>
            )}
          </div>
        </div>

        {/* Title */}
        <h3 className="font-semibold text-base text-charcoal-900 group-hover:text-crimson-950 transition-colors leading-snug mb-3 line-clamp-3">
          {notice.title}
        </h3>

        {/* Processing State Badge */}
        <div className="mb-3">
          <span
            className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-md text-[11px] font-semibold border ${statusCfg.bg} ${statusCfg.text} ${statusCfg.border}`}
          >
            {statusKey === 'indexed' && <CheckCircle2 className="w-3 h-3 text-emerald-600" />}
            {statusKey === 'failed' && <AlertCircle className="w-3 h-3 text-rose-600" />}
            {statusKey === 'extracted' && <Cpu className="w-3 h-3 text-sky-600" />}
            <span>{statusCfg.label}</span>
          </span>
        </div>
      </div>

      {/* Footer Actions */}
      <div className="pt-3 border-t border-warm-100 flex items-center justify-between text-xs text-charcoal-500 mt-2">
        <div className="flex items-center gap-2">
          {isPdf ? (
            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-emerald-50 text-emerald-700 font-medium border border-emerald-200/50">
              <FileText className="w-3 h-3" />
              <span>Official PDF</span>
            </span>
          ) : (
            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-warm-100 text-charcoal-500 font-medium">
              <span>Web Notice</span>
            </span>
          )}

          {statusKey === 'failed' && onRetry && (
            <button
              type="button"
              onClick={() => onRetry(notice.id || notice.source_url)}
              className="inline-flex items-center gap-1 text-[11px] text-rose-700 hover:underline font-semibold ml-1"
            >
              <RefreshCw className="w-3 h-3" />
              <span>Retry</span>
            </button>
          )}
        </div>

        <div className="flex items-center gap-2">
          {isPdf && (
            <a
              href={notice.pdf_url}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg text-crimson-900 hover:bg-crimson-50 font-medium transition-colors"
              title="Open Official PDF Document"
            >
              <span>View PDF</span>
              <Download className="w-3 h-3" />
            </a>
          )}
          <a
            href={notice.source_url}
            target="_blank"
            rel="noopener noreferrer"
            className="p-1 rounded-lg text-charcoal-400 hover:text-charcoal-800 hover:bg-warm-100 transition-colors"
            title="Open Original Source Page"
          >
            <ExternalLink className="w-3.5 h-3.5" />
          </a>
        </div>
      </div>
    </div>
  );
}
