import React from 'react';
import { Search, Filter, SortDesc } from 'lucide-react';

const CATEGORIES = [
  'All',
  'Examinations',
  'Admissions',
  'Academic Circulars',
  'Results',
  'Recruitment',
  'Tenders',
  'General',
];

export default function NoticeFilters({
  search,
  onSearchChange,
  category,
  onCategoryChange,
  totalCount,
}) {
  return (
    <div className="w-full bg-white rounded-2xl border border-warm-200/90 shadow-subtle p-5 mb-6">
      <div className="flex flex-col md:flex-row items-stretch md:items-center justify-between gap-4">
        {/* Search input */}
        <div className="relative flex-1">
          <Search className="w-4 h-4 text-charcoal-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            value={search}
            onChange={(e) => onSearchChange(e.target.value)}
            placeholder="Search circulars, exam notices, date sheets, or keywords..."
            className="w-full pl-10 pr-4 py-2.5 rounded-xl border border-warm-200 text-sm text-charcoal-900 placeholder:text-charcoal-400 focus:outline-none focus:border-crimson-400 focus:ring-2 focus:ring-crimson-100 transition-all bg-warm-50/50"
          />
        </div>

        {/* Count display */}
        <div className="text-xs text-charcoal-500 font-medium px-2 flex items-center gap-1.5 self-center">
          <span className="font-semibold text-charcoal-800">{totalCount}</span>
          <span>circulars indexed</span>
        </div>
      </div>

      {/* Category Pills */}
      <div className="flex items-center gap-1.5 overflow-x-auto pt-4 mt-3 border-t border-warm-100 no-scrollbar">
        <span className="text-xs font-semibold text-charcoal-400 mr-1 flex items-center gap-1">
          <Filter className="w-3 h-3" />
          <span>Category:</span>
        </span>
        {CATEGORIES.map((cat) => {
          const isActive = (cat === 'All' && !category) || category === cat;
          return (
            <button
              key={cat}
              type="button"
              onClick={() => onCategoryChange(cat === 'All' ? '' : cat)}
              className={`px-3 py-1 rounded-lg text-xs font-medium whitespace-nowrap transition-colors ${
                isActive
                  ? 'bg-crimson-900 text-white shadow-sm'
                  : 'bg-warm-100/70 text-charcoal-600 hover:bg-warm-200/60'
              }`}
            >
              {cat}
            </button>
          );
        })}
      </div>
    </div>
  );
}
