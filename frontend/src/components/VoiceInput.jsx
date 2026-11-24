import React from 'react';
import { Mic, MicOff, AlertCircle } from 'lucide-react';

export default function VoiceInput({
  isListening,
  onStartListening,
  onStopListening,
  disabled,
  error,
}) {
  return (
    <div className="relative flex items-center">
      <button
        type="button"
        onClick={isListening ? onStopListening : onStartListening}
        disabled={disabled}
        title={isListening ? 'Stop listening (click or speak)' : 'Start voice input (speech-to-text)'}
        className={`p-2.5 rounded-xl transition-all relative ${
          isListening
            ? 'bg-rose-600 text-white shadow-md animate-pulse ring-4 ring-rose-200'
            : 'text-charcoal-500 hover:text-crimson-800 hover:bg-warm-100 disabled:opacity-40 disabled:hover:bg-transparent'
        }`}
      >
        {isListening ? (
          <MicOff className="w-4 h-4 animate-bounce" />
        ) : (
          <Mic className="w-4 h-4" />
        )}
      </button>

      {error && (
        <div
          title={error}
          className="absolute bottom-full mb-2 right-0 max-w-xs bg-charcoal-900 text-white text-[11px] py-1.5 px-3 rounded-lg shadow-xl flex items-center gap-1.5 z-50 border border-rose-500/50"
        >
          <AlertCircle className="w-3.5 h-3.5 text-rose-400 flex-shrink-0" />
          <span className="leading-tight">{error}</span>
        </div>
      )}
    </div>
  );
}
