import React from 'react';
import { X, ExternalLink, Download, FileText, CheckCircle2, BookOpen } from 'lucide-react';

export default function SourceDrawer({ isOpen, onClose, source }) {
  if (!isOpen || !source) return null;

  const {
    source_id,
    title,
    notice_id,
    source_url,
    pdf_url,
    page_number,
    relevant_excerpt,
  } = source;

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-charcoal-900/40 backdrop-blur-sm transition-opacity">
      <div className="w-full max-w-lg bg-white h-full shadow-2xl flex flex-col border-l border-warm-200 animate-in slide-in-from-right duration-200">
        {/* Header */}
        <div className="p-5 border-b border-warm-200 flex items-center justify-between bg-warm-50/70">
          <div className="flex items-center gap-2">
            <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-md text-xs font-bold bg-crimson-100 text-crimson-900 border border-crimson-200">
              <BookOpen className="w-3.5 h-3.5 text-crimson-800" />
              {source_id || 'SOURCE REFERENCE'}
            </span>
            <span className="text-xs font-semibold text-charcoal-500">
              Page {page_number || 1}
            </span>
          </div>

          <button
            type="button"
            onClick={onClose}
            className="p-1.5 rounded-lg text-charcoal-400 hover:text-charcoal-700 hover:bg-warm-100 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content Body */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          <div>
            <span className="text-[11px] font-bold tracking-wider text-charcoal-400 uppercase">
              Official Notice Title
            </span>
            <h3 className="text-base font-bold text-charcoal-900 mt-1 leading-snug">
              {title || 'Guru Gobind Singh Indraprastha University Notice'}
            </h3>
            {notice_id && (
              <p className="text-xs font-mono text-charcoal-400 mt-1">
                Notice Identifier: {notice_id}
              </p>
            )}
          </div>

          <div className="bg-warm-50 rounded-xl p-4 border border-warm-200/80">
            <div className="flex items-center gap-2 mb-2 text-emerald-800">
              <CheckCircle2 className="w-4 h-4 text-emerald-600" />
              <span className="text-xs font-bold uppercase tracking-wider">
                Retrieved Supporting Evidence
              </span>
            </div>
            <p className="text-sm text-charcoal-700 leading-relaxed whitespace-pre-wrap font-sans">
              {relevant_excerpt || 'Full text passage retrieved from official university document.'}
            </p>
          </div>

          <div>
            <span className="text-[11px] font-bold tracking-wider text-charcoal-400 uppercase mb-2 block">
              Official University Links
            </span>
            <div className="flex flex-col gap-2">
              {pdf_url && (
                <a
                  href={pdf_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center justify-between p-3 rounded-xl border border-warm-200 bg-white hover:bg-warm-50 text-charcoal-800 transition-colors"
                >
                  <div className="flex items-center gap-2.5">
                    <Download className="w-4 h-4 text-crimson-800" />
                    <span className="text-xs font-semibold">Download Original University PDF</span>
                  </div>
                  <ExternalLink className="w-3.5 h-3.5 text-charcoal-400" />
                </a>
              )}

              {source_url && (
                <a
                  href={source_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center justify-between p-3 rounded-xl border border-warm-200 bg-white hover:bg-warm-50 text-charcoal-800 transition-colors"
                >
                  <div className="flex items-center gap-2.5">
                    <FileText className="w-4 h-4 text-charcoal-600" />
                    <span className="text-xs font-semibold">Open Notice Listing on IPU.ac.in</span>
                  </div>
                  <ExternalLink className="w-3.5 h-3.5 text-charcoal-400" />
                </a>
              )}
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-warm-200 bg-warm-50/50 text-center">
          <p className="text-[11px] text-charcoal-400">
            Verified by MAYA Multimodal Document Engine • Guru Gobind Singh Indraprastha University
          </p>
        </div>
      </div>
    </div>
  );
}
