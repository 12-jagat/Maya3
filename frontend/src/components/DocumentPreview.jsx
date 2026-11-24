import React from 'react';
import { FileText, Download, ExternalLink } from 'lucide-react';

export default function DocumentPreview({ filename, pageCount, downloadUrl, sizeFormatted }) {
  const isPdf = (filename || '').toLowerCase().endsWith('.pdf');

  return (
    <div className="mt-2.5 flex items-center gap-3 p-3 rounded-xl border border-warm-200 bg-warm-50/70 max-w-sm shadow-subtle">
      <div className={`p-2.5 rounded-xl ${isPdf ? 'bg-rose-100 text-rose-800' : 'bg-blue-100 text-blue-800'}`}>
        <FileText className="w-5 h-5" />
      </div>

      <div className="flex-1 min-w-0">
        <div className="font-semibold text-xs text-charcoal-900 truncate" title={filename}>
          {filename || 'Uploaded Document'}
        </div>
        <div className="text-[11px] text-charcoal-500 flex items-center gap-2 mt-0.5">
          <span>{isPdf ? 'PDF Document' : 'Word Document'}</span>
          {pageCount && <span>• {pageCount} {pageCount === 1 ? 'page' : 'pages'}</span>}
          {sizeFormatted && <span>• {sizeFormatted}</span>}
        </div>
      </div>

      {downloadUrl && (
        <a
          href={downloadUrl}
          download={filename}
          target="_blank"
          rel="noopener noreferrer"
          title="Download uploaded document"
          className="p-2 rounded-lg text-charcoal-500 hover:text-crimson-800 hover:bg-warm-200 transition-colors"
        >
          <Download className="w-4 h-4" />
        </a>
      )}
    </div>
  );
}
