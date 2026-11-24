import React from 'react';
import { Plus, MessageSquare, Trash2, ChevronLeft, ShieldCheck, ExternalLink } from 'lucide-react';
import { Link } from 'react-router-dom';

export default function ConversationSidebar({
  conversations,
  activeId,
  onSelectConversation,
  onNewConversation,
  onDeleteConversation,
  isOpen,
  onToggleOpen,
}) {
  return (
    <aside
      className={`${
        isOpen ? 'w-72' : 'w-0 -ml-72 md:w-20 md:ml-0'
      } flex-shrink-0 bg-warm-100/90 border-r border-warm-200/80 flex flex-col h-full transition-all duration-300 overflow-hidden select-none z-30`}
    >
      {/* Top Brand / New Chat */}
      <div className="p-4 border-b border-warm-200/70">
        <button
          type="button"
          onClick={onNewConversation}
          className="w-full flex items-center justify-center gap-2 px-3.5 py-2.5 rounded-xl bg-crimson-900 text-white font-semibold text-xs shadow-sm hover:bg-crimson-950 active:scale-[0.98] transition-all"
        >
          <Plus className="w-4 h-4" />
          {isOpen && <span>New Conversation</span>}
        </button>
      </div>

      {/* Conversations List */}
      <div className="flex-1 overflow-y-auto p-3 space-y-1.5">
        {isOpen && (
          <div className="px-2 py-1 text-[11px] font-bold text-charcoal-400 uppercase tracking-wider">
            Recent Threads
          </div>
        )}

        {conversations.length === 0 ? (
          isOpen && (
            <div className="px-3 py-6 text-center text-xs text-charcoal-400">
              No previous threads. Ask a question to begin.
            </div>
          )
        ) : (
          conversations.map((c) => {
            const isActive = c.id === activeId;
            return (
              <div
                key={c.id}
                onClick={() => onSelectConversation(c.id)}
                className={`group flex items-center justify-between px-3 py-2.5 rounded-xl text-xs font-medium cursor-pointer transition-all ${
                  isActive
                    ? 'bg-white text-crimson-950 font-bold shadow-subtle border border-warm-200/90'
                    : 'text-charcoal-600 hover:bg-warm-200/60 hover:text-charcoal-900'
                }`}
              >
                <div className="flex items-center gap-2.5 min-w-0">
                  <MessageSquare
                    className={`w-3.5 h-3.5 flex-shrink-0 ${
                      isActive ? 'text-crimson-800' : 'text-charcoal-400'
                    }`}
                  />
                  {isOpen && (
                    <span className="truncate max-w-[150px]">
                      {c.title || 'Conversation'}
                    </span>
                  )}
                </div>

                {isOpen && (
                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation();
                      onDeleteConversation(c.id);
                    }}
                    title="Delete Thread"
                    className="opacity-0 group-hover:opacity-100 p-1 text-charcoal-400 hover:text-crimson-700 transition-all"
                  >
                    <Trash2 className="w-3 h-3" />
                  </button>
                )}
              </div>
            );
          })
        )}
      </div>

      {/* Footer Navigation Link */}
      <div className="p-3 border-t border-warm-200/70 bg-warm-50/50">
        <Link
          to="/notices"
          className="flex items-center justify-between p-2 rounded-xl text-xs font-semibold text-charcoal-700 hover:text-crimson-900 hover:bg-white transition-colors"
        >
          <div className="flex items-center gap-2">
            <ShieldCheck className="w-4 h-4 text-crimson-800" />
            {isOpen && <span>Notice Center</span>}
          </div>
          {isOpen && <ExternalLink className="w-3 h-3 text-charcoal-400" />}
        </Link>
      </div>
    </aside>
  );
}
