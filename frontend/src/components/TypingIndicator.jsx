import React from 'react';
import { Sparkles } from 'lucide-react';

export default function TypingIndicator() {
  return (
    <div className="flex items-start gap-3 my-4 animate-in fade-in duration-300">
      <div className="w-8 h-8 rounded-full bg-crimson-900 text-white flex items-center justify-center flex-shrink-0 shadow-subtle">
        <Sparkles className="w-4 h-4 text-warm-100 animate-pulse" />
      </div>

      <div className="bg-white border border-warm-200/90 rounded-2xl rounded-tl-sm px-4 py-3 shadow-subtle">
        <div className="flex items-center gap-2">
          <span className="text-xs font-semibold text-charcoal-600">
            MAYA is reviewing official GGSIPU circulars
          </span>
          <div className="flex items-center gap-1 ml-1">
            <span className="w-1.5 h-1.5 rounded-full bg-crimson-800 animate-bounce [animation-delay:-0.3s]"></span>
            <span className="w-1.5 h-1.5 rounded-full bg-crimson-800 animate-bounce [animation-delay:-0.15s]"></span>
            <span className="w-1.5 h-1.5 rounded-full bg-crimson-800 animate-bounce"></span>
          </div>
        </div>
      </div>
    </div>
  );
}
