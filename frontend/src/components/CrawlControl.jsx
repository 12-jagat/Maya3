import React from 'react';
import { Play, Loader2, Sparkles, Database, CheckCircle2 } from 'lucide-react';

export default function CrawlControl({ onStartCrawl, isCrawling, activeJob }) {
  return (
    <div className="w-full bg-white rounded-2xl border border-warm-200/90 shadow-premium p-6 mb-8 transition-all">
      <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-6">
        <div>
          <div className="flex items-center gap-2 mb-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-crimson-800 animate-pulse"></span>
            <h2 className="text-lg font-bold text-charcoal-900 tracking-tight">
              GGSIPU One-Click Notice Crawler
            </h2>
            <span className="text-xs font-semibold px-2 py-0.5 rounded bg-crimson-100/80 text-crimson-900">
              8-Process Architecture
            </span>
          </div>
          <p className="text-sm text-charcoal-500 max-w-xl leading-relaxed">
            Automatically crawls official university circulars from <code className="font-mono text-xs text-charcoal-700 bg-warm-100 px-1.5 py-0.5 rounded">ipu.ac.in</code> and <code className="font-mono text-xs text-charcoal-700 bg-warm-100 px-1.5 py-0.5 rounded">examdept.ggsipu.ac.in</code>, discovers PDF attachments, avoids duplicates, and stores them in Supabase.
          </p>
        </div>

        <div className="flex items-center gap-3 w-full sm:w-auto">
          <button
            type="button"
            onClick={onStartCrawl}
            disabled={isCrawling}
            className={`w-full sm:w-auto inline-flex items-center justify-center gap-2.5 px-6 py-3 rounded-xl font-semibold text-sm transition-all duration-200 shadow-md ${
              isCrawling
                ? 'bg-warm-200 text-charcoal-400 cursor-not-allowed shadow-none'
                : 'bg-gradient-to-r from-crimson-800 to-crimson-950 text-white hover:opacity-95 hover:shadow-crimson-glow active:scale-[0.98]'
            }`}
          >
            {isCrawling ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin text-charcoal-500" />
                <span>Crawling in Progress...</span>
              </>
            ) : (
              <>
                <Play className="w-4 h-4 fill-current" />
                <span>Crawl All Notices</span>
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
