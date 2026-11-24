import React, { useState } from 'react';
import { Search, Sparkles, FileText, ExternalLink, Download, AlertCircle, ArrowRight } from 'lucide-react';
import { semanticSearch } from '../services/api';

const SAMPLE_QUERIES = [
  'When is the last date for examination form submission?',
  'Spot counselling notification for B.Tech admissions',
  'Inter-college sports meet and annual events',
  'Fee refund rules and guidelines',
];

export default function SemanticSearchBox() {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState([]);
  const [isSearching, setIsSearching] = useState(false);
  const [hasSearched, setHasSearched] = useState(false);
  const [error, setError] = useState(null);

  const handleSearch = async (searchQuery) => {
    const q = searchQuery !== undefined ? searchQuery : query;
    if (!q || q.trim().length < 2) return;

    setIsSearching(true);
    setError(null);
    setHasSearched(true);

    try {
      const data = await semanticSearch({ query: q, top_k: 5, threshold: 0.1 });
      setResults(data.results || []);
    } catch (err) {
      console.error('Semantic search error:', err);
      setError('Failed to perform semantic search. Please ensure documents have been indexed.');
      setResults([]);
    } finally {
      setIsSearching(false);
    }
  };

  return (
    <div className="w-full bg-white rounded-2xl border border-warm-200/90 shadow-premium p-6 mb-8">
      {/* Title */}
      <div className="flex items-center gap-2 mb-2">
        <Sparkles className="w-4 h-4 text-crimson-800" />
        <h2 className="text-lg font-bold text-charcoal-900 tracking-tight">
          Semantic Vector Search (Zilliz Cloud)
        </h2>
        <span className="text-xs font-semibold px-2 py-0.5 rounded bg-crimson-100/70 text-crimson-900 font-mono">
          all-MiniLM-L6-v2 (384-d)
        </span>
      </div>
      <p className="text-sm text-charcoal-500 mb-4 leading-relaxed">
        Test natural language questions against official GGSIPU circular text chunks indexed in the vector database.
      </p>

      {/* Search Input Bar */}
      <form
        onSubmit={(e) => {
          e.preventDefault();
          handleSearch();
        }}
        className="flex items-center gap-2 mb-3"
      >
        <div className="relative flex-1">
          <Search className="w-4 h-4 text-charcoal-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Ask a question in natural language (e.g. When is the exam form deadline?)..."
            className="w-full pl-10 pr-4 py-3 rounded-xl border border-warm-200 text-sm text-charcoal-900 placeholder:text-charcoal-400 focus:outline-none focus:border-crimson-400 focus:ring-2 focus:ring-crimson-100 transition-all bg-warm-50/50"
          />
        </div>
        <button
          type="submit"
          disabled={isSearching || !query.trim()}
          className="px-6 py-3 rounded-xl font-semibold text-xs bg-crimson-900 text-white hover:bg-crimson-950 disabled:opacity-50 transition-colors shadow-sm whitespace-nowrap"
        >
          {isSearching ? 'Searching...' : 'Vector Search'}
        </button>
      </form>

      {/* Sample Question Chips */}
      <div className="flex flex-wrap items-center gap-1.5 mb-5 text-xs text-charcoal-500">
        <span className="font-semibold text-charcoal-400 mr-1">Try questions:</span>
        {SAMPLE_QUERIES.map((sample, idx) => (
          <button
            key={idx}
            type="button"
            onClick={() => {
              setQuery(sample);
              handleSearch(sample);
            }}
            className="px-2.5 py-1 rounded-lg bg-warm-100/70 hover:bg-crimson-50 hover:text-crimson-900 transition-colors text-charcoal-600 text-[11px]"
          >
            {sample}
          </button>
        ))}
      </div>

      {/* Error state */}
      {error && (
        <div className="p-3 rounded-xl bg-rose-50 border border-rose-200 text-xs text-rose-800 flex items-center gap-2 mb-4">
          <AlertCircle className="w-4 h-4 text-rose-600 flex-shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Search Results Display */}
      {hasSearched && (
        <div className="mt-4 pt-4 border-t border-warm-100">
          <div className="flex items-center justify-between mb-3 text-xs text-charcoal-500">
            <span className="font-semibold text-charcoal-800">
              Matched {results.length} Relevant Chunk{results.length === 1 ? '' : 's'}
            </span>
            <span className="text-charcoal-400 font-mono">Cosine Metric</span>
          </div>

          {results.length === 0 ? (
            <div className="p-6 text-center rounded-xl bg-warm-50 text-xs text-charcoal-500">
              No relevant chunks found above similarity threshold. Try adjusting the query or click "Process Downloaded Documents" above to index more circulars.
            </div>
          ) : (
            <div className="space-y-3">
              {results.map((item, index) => (
                <div
                  key={item.id || index}
                  className="p-4 rounded-xl border border-warm-200/90 hover:border-crimson-300 bg-warm-50/40 hover:bg-white transition-all shadow-subtle"
                >
                  <div className="flex items-center justify-between gap-2 mb-1.5">
                    <span className="text-xs font-bold text-charcoal-900 truncate">
                      {item.title}
                    </span>
                    <span className="text-[11px] font-semibold px-2 py-0.5 rounded bg-emerald-50 text-emerald-800 border border-emerald-200 whitespace-nowrap">
                      Score: {(item.score * 100).toFixed(1)}%
                    </span>
                  </div>

                  <p className="text-xs text-charcoal-700 leading-relaxed font-sans line-clamp-3 mb-2 bg-white/60 p-2.5 rounded-lg border border-warm-100">
                    "{item.content}"
                  </p>

                  <div className="flex items-center justify-between text-[11px] text-charcoal-400 pt-1">
                    <div className="flex items-center gap-3">
                      {item.page_number && (
                        <span>Page {item.page_number}</span>
                      )}
                      {item.category && (
                        <span className="text-charcoal-600 font-medium">{item.category}</span>
                      )}
                    </div>

                    <div className="flex items-center gap-2">
                      {item.pdf_url && (
                        <a
                          href={item.pdf_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="inline-flex items-center gap-1 text-crimson-900 font-semibold hover:underline"
                        >
                          <span>Official PDF</span>
                          <ExternalLink className="w-3 h-3" />
                        </a>
                      )}
                      <a
                        href={item.source_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-charcoal-500 hover:text-charcoal-900"
                        title="View Notice Page"
                      >
                        <ExternalLink className="w-3 h-3" />
                      </a>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
