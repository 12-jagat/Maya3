import React from 'react';
import { ArrowRight, HelpCircle } from 'lucide-react';

const DEFAULT_QUESTIONS = [
  'What are the latest examination notices?',
  'Explain the latest admission notification.',
  'What is the examination form submission deadline?',
  'Summarize important university announcements.',
];

export default function SuggestedQuestions({ onSelectQuestion }) {
  return (
    <div className="w-full max-w-2xl mx-auto my-6">
      <div className="flex items-center gap-2 mb-3 text-charcoal-400">
        <HelpCircle className="w-3.5 h-3.5" />
        <span className="text-xs font-semibold uppercase tracking-wider">
          Suggested Academic Queries
        </span>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
        {DEFAULT_QUESTIONS.map((question, idx) => (
          <button
            key={idx}
            type="button"
            onClick={() => onSelectQuestion(question)}
            className="flex items-center justify-between p-3.5 bg-white hover:bg-warm-50/80 border border-warm-200/90 hover:border-crimson-300 rounded-xl text-left transition-all shadow-subtle group text-xs text-charcoal-700 font-medium"
          >
            <span className="line-clamp-2">{question}</span>
            <ArrowRight className="w-3.5 h-3.5 text-charcoal-400 group-hover:text-crimson-900 group-hover:translate-x-0.5 transition-all flex-shrink-0 ml-2" />
          </button>
        ))}
      </div>
    </div>
  );
}
