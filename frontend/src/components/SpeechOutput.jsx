import React from 'react';
import { Volume2, VolumeX, Square, Loader2 } from 'lucide-react';

export default function SpeechOutput({
  isSpeaking,
  onSpeak,
  onStop,
  text,
}) {
  if (!text) return null;

  return (
    <div className="flex items-center gap-1">
      <button
        type="button"
        onClick={isSpeaking ? onStop : onSpeak}
        title={isSpeaking ? 'Stop speaking' : 'Listen to answer'}
        className={`p-1 rounded-lg text-xs flex items-center gap-1 transition-colors ${
          isSpeaking
            ? 'text-rose-600 bg-rose-50 hover:bg-rose-100 font-semibold'
            : 'text-charcoal-400 hover:text-crimson-800 hover:bg-warm-100'
        }`}
      >
        {isSpeaking ? (
          <>
            <Square className="w-3 h-3 fill-current animate-pulse text-rose-600" />
            <span className="text-[10px]">Speaking...</span>
          </>
        ) : (
          <>
            <Volume2 className="w-3 h-3" />
            <span className="text-[10px] hidden sm:inline">Listen</span>
          </>
        )}
      </button>
    </div>
  );
}
