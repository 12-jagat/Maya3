import React from 'react';
import { FileText, ExternalLink, Download, BookOpen } from 'lucide-react';

export default function CitationCard({ citation, onSelectSource }) {
  if (!citation) return null;

  const {
    source_id,
    title,
    source_url,
    pdf_url,
    page_number,
    relevant_excerpt,
  } = citation;

  return (
    <div className="group relative flex flex-col justify-between p-3.5 bg-warm-50/80 hover:bg-white rounded-xl border border-warm-200/90 hover:border-crimson-300 transition-all shadow-subtle hover:shadow-card text-left">
      <div>
        <div className="flex items-center justify-between gap-2 mb-1.5">
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-bold bg-crimson-100/70 text-crimson-900 border border-crimson-200/50">
            <BookOpen className="w-3 h-3 text-crimson-800" />
            {source_id || 'SOURCE'}
          </span>

          {page_number && (
            <span className="text-[10px] font-semibold text-charcoal-500 bg-white px-2 py-0.5 rounded-full border border-warm-200">
              Page {page_number}
            </span>
          )}
        </div>

        <h4 className="text-xs font-bold text-charcoal-900 line-clamp-2 mb-1 group-hover:text-crimson-900 transition-colors">
          {title || 'Official University Circular'}
        </h4>

        {relevant_excerpt && (
          <p className="text-[11px] text-charcoal-600 line-clamp-2 leading-relaxed italic mb-2">
            "{relevant_excerpt}"
          </p>
        )}
      </div>

      <div className="flex items-center justify-between gap-2 pt-2 border-t border-warm-200/60 mt-1">
        {onSelectSource && (
          <button
            type="button"
            onClick={() => onSelectSource(citation)}
            className="text-[11px] font-semibold text-crimson-900 hover:underline"
          >
            Read Excerpt
          </button>
        )}

        <div className="flex items-center gap-1.5 ml-auto">
          {pdf_url && (
            <a
              href={pdf_url}
              target="_blank"
              rel="noopener noreferrer"
              title="Open Official PDF"
              className="inline-flex items-center gap-1 px-2 py-1 rounded text-[10px] font-semibold bg-white border border-warm-200 text-charcoal-700 hover:text-crimson-900 hover:bg-warm-50 transition-colors"
            >
              <Download className="w-2.5 h-2.5 text-crimson-800" />
              <span>PDF</span>
            </a>
          )}

          {source_url && (
            <a
              href={source_url}
              target="_blank"
              rel="noopener noreferrer"
              title="Open University Portal Page"
              className="inline-flex items-center gap-1 px-2 py-1 rounded text-[10px] font-semibold bg-white border border-warm-200 text-charcoal-700 hover:text-crimson-900 hover:bg-warm-50 transition-colors"
            >
              <ExternalLink className="w-2.5 h-2.5" />
              <span>Portal</span>
            </a>
          )}
        </div>
      </div>
    </div>
  );
}
