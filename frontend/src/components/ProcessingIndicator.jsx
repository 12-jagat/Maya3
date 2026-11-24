import React from 'react';
import { Loader2, Sparkles, FileText, Image, Music } from 'lucide-react';

export default function ProcessingIndicator({ mediaType, customMessage }) {
  const getInfo = () => {
    if (mediaType === 'image') {
      return {
        icon: <Image className="w-4 h-4 text-crimson-800 animate-pulse" />,
        text: customMessage || 'Analyzing image notice with Gemini Vision & verifying official records...',
      };
    }
    if (mediaType === 'document') {
      return {
        icon: <FileText className="w-4 h-4 text-amber-700 animate-pulse" />,
        text: customMessage || 'Extracting document text, generating local embeddings & isolating context...',
      };
    }
    if (mediaType === 'audio') {
      return {
        icon: <Music className="w-4 h-4 text-blue-700 animate-pulse" />,
        text: customMessage || 'Transcribing audio note with Gemini & extracting key academic points...',
      };
    }
    return {
      icon: <Sparkles className="w-4 h-4 text-crimson-800 animate-pulse" />,
      text: customMessage || 'MAYA is reviewing official university circulars...',
    };
  };

  const { icon, text } = getInfo();

  return (
    <div className="flex items-center gap-3 p-3 my-3 max-w-md rounded-2xl bg-white border border-warm-200/90 shadow-subtle animate-in fade-in duration-200">
      <div className="p-2 rounded-xl bg-warm-100 flex items-center justify-center">
        {icon}
      </div>
      <div className="flex-1">
        <p className="text-xs text-charcoal-800 font-medium leading-tight">{text}</p>
        <span className="text-[10px] text-charcoal-400">Processing media...</span>
      </div>
      <Loader2 className="w-4 h-4 text-charcoal-400 animate-spin flex-shrink-0" />
    </div>
  );
}
