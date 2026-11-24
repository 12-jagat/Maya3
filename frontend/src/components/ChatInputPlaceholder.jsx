import React from 'react';
import { ArrowUp, Mic, Paperclip, Image as ImageIcon, FileText } from 'lucide-react';

export default function ChatInputPlaceholder() {
  return (
    <div className="w-full max-w-2xl mx-auto">
      <div className="bg-white rounded-2xl border border-warm-200/90 shadow-premium p-3 transition-all duration-200 focus-within:border-crimson-300 focus-within:ring-2 focus-within:ring-crimson-100">
        <textarea
          rows={3}
          disabled
          placeholder="Ask MAYA about official GGSIPU notices, exam schedules, or circulars..."
          className="w-full bg-transparent resize-none text-sm text-charcoal-900 placeholder:text-charcoal-400 focus:outline-none cursor-not-allowed px-1"
        />

        <div className="flex items-center justify-between pt-2 border-t border-warm-100 mt-1">
          {/* Multimodal action indicators (disabled placeholder for milestone 1) */}
          <div className="flex items-center gap-1.5 text-charcoal-400">
            <button
              type="button"
              disabled
              title="Upload PDF or Document (Milestone 2)"
              className="p-2 rounded-lg hover:bg-warm-100 text-charcoal-400 cursor-not-allowed transition-colors"
            >
              <Paperclip className="w-4 h-4" />
            </button>
            <button
              type="button"
              disabled
              title="Upload Image (Milestone 2)"
              className="p-2 rounded-lg hover:bg-warm-100 text-charcoal-400 cursor-not-allowed transition-colors"
            >
              <ImageIcon className="w-4 h-4" />
            </button>
            <button
              type="button"
              disabled
              title="Voice Input (Milestone 2)"
              className="p-2 rounded-lg hover:bg-warm-100 text-charcoal-400 cursor-not-allowed transition-colors"
            >
              <Mic className="w-4 h-4" />
            </button>
            <span className="text-xs text-charcoal-400 pl-1 font-medium hidden sm:inline">
              Multimodal inputs enabled in next milestone
            </span>
          </div>

          {/* Submit button indicator */}
          <button
            type="button"
            disabled
            className="w-9 h-9 rounded-xl bg-crimson-900 text-white flex items-center justify-center opacity-60 cursor-not-allowed shadow-sm transition-opacity"
          >
            <ArrowUp className="w-4 h-4" />
          </button>
        </div>
      </div>

      <div className="mt-2.5 text-center text-xs text-charcoal-400">
        Milestone 1 Architecture & Health Shell • Verified with GGSIPU official notice pipeline specifications
      </div>
    </div>
  );
}
