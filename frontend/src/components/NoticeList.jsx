import React from 'react';
import NoticeCard from './NoticeCard';
import { ChevronLeft, ChevronRight, Inbox } from 'lucide-react';

export default function NoticeList({
  notices,
  total,
  skip,
  limit,
  onPageChange,
  isLoading,
  onRetry,
}) {
  if (isLoading) {
    return (
      <div className="w-full py-16 text-center">
        <div className="inline-block w-8 h-8 border-2 border-crimson-800 border-t-transparent rounded-full animate-spin mb-3"></div>
        <p className="text-sm text-charcoal-500">Loading university circulars...</p>
      </div>
    );
  }

  if (!notices || notices.length === 0) {
    return (
      <div className="w-full bg-white rounded-2xl border border-warm-200/80 p-12 text-center my-6">
        <div className="w-12 h-12 rounded-2xl bg-warm-100 text-charcoal-400 flex items-center justify-center mx-auto mb-3">
          <Inbox className="w-6 h-6" />
        </div>
        <h4 className="text-base font-bold text-charcoal-800 mb-1">No University Notices Found</h4>
        <p className="text-sm text-charcoal-500 max-w-md mx-auto mb-4 leading-relaxed">
          No notices have been crawled yet or match your current search filters. Click "Crawl All Notices" above to index official GGSIPU circulars.
        </p>
      </div>
    );
  }

  const currentPage = Math.floor(skip / limit) + 1;
  const totalPages = Math.ceil(total / limit) || 1;

  return (
    <div>
      {/* Notice Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mb-8">
        {notices.map((notice) => (
          <NoticeCard
            key={notice.id || notice.source_url}
            notice={notice}
            onRetry={onRetry}
          />
        ))}
      </div>

      {/* Pagination Controls */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between border-t border-warm-200/80 pt-4">
          <p className="text-xs text-charcoal-500 font-medium">
            Showing <span className="font-semibold text-charcoal-800">{skip + 1}</span> to{' '}
            <span className="font-semibold text-charcoal-800">
              {Math.min(skip + limit, total)}
            </span>{' '}
            of <span className="font-semibold text-charcoal-800">{total}</span> circulars
          </p>

          <div className="flex items-center gap-2">
            <button
              type="button"
              disabled={skip === 0}
              onClick={() => onPageChange(Math.max(0, skip - limit))}
              className="p-2 rounded-lg border border-warm-200 bg-white text-charcoal-700 disabled:opacity-40 disabled:cursor-not-allowed hover:bg-warm-50 transition-colors"
            >
              <ChevronLeft className="w-4 h-4" />
            </button>
            <span className="text-xs font-semibold text-charcoal-700 px-2">
              Page {currentPage} of {totalPages}
            </span>
            <button
              type="button"
              disabled={skip + limit >= total}
              onClick={() => onPageChange(skip + limit)}
              className="p-2 rounded-lg border border-warm-200 bg-white text-charcoal-700 disabled:opacity-40 disabled:cursor-not-allowed hover:bg-warm-50 transition-colors"
            >
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
