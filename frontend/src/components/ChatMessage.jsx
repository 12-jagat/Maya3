import React, { useState } from 'react';
import { User, Sparkles, Copy, Check, AlertCircle, ShieldCheck } from 'lucide-react';
import CitationCard from './CitationCard';
import SpeechOutput from './SpeechOutput';
import ImagePreview from './ImagePreview';
import DocumentPreview from './DocumentPreview';
import AudioPlayer from './AudioPlayer';
import { useSpeechSynthesis } from '../hooks/useSpeechSynthesis';

export default function ChatMessage({ message, onSelectSource }) {
  const [copied, setCopied] = useState(false);
  const isUser = message.role === 'user';
  const citations = message.citations || [];
  const insufficientEvidence = message.metadata?.insufficient_evidence || message.insufficient_evidence;
  const attachment = message.attachment || message.metadata?.attachment;

  const { isSpeaking, speak, stop } = useSpeechSynthesis();

  const handleCopy = () => {
    navigator.clipboard.writeText(message.content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className={`flex items-start gap-3.5 my-4 ${isUser ? 'flex-row-reverse' : 'flex-row'}`}>
      {/* Avatar */}
      <div
        className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 shadow-subtle ${
          isUser
            ? 'bg-charcoal-800 text-warm-100'
            : 'bg-crimson-900 text-warm-50 border border-crimson-800'
        }`}
      >
        {isUser ? <User className="w-4 h-4" /> : <Sparkles className="w-4 h-4" />}
      </div>

      {/* Message Box */}
      <div
        className={`max-w-[85%] sm:max-w-[78%] rounded-2xl p-4 transition-all shadow-subtle ${
          isUser
            ? 'bg-crimson-900 text-white rounded-tr-sm'
            : 'bg-white text-charcoal-900 border border-warm-200/90 rounded-tl-sm'
        }`}
      >
        {/* Role header for assistant */}
        {!isUser && (
          <div className="flex items-center justify-between gap-2 mb-2 pb-1.5 border-b border-warm-100">
            <div className="flex items-center gap-1.5 text-crimson-900">
              <ShieldCheck className="w-3.5 h-3.5" />
              <span className="text-[11px] font-bold uppercase tracking-wider">
                MAYA • GGSIPU Academic Assistant
              </span>
            </div>

            <div className="flex items-center gap-1">
              {/* Text to Speech Button */}
              <SpeechOutput
                isSpeaking={isSpeaking}
                onSpeak={() => speak(message.content)}
                onStop={stop}
                text={message.content}
              />

              <button
                type="button"
                onClick={handleCopy}
                title="Copy answer"
                className="p-1 rounded text-charcoal-400 hover:text-charcoal-700 hover:bg-warm-100 transition-colors"
              >
                {copied ? <Check className="w-3 h-3 text-emerald-600" /> : <Copy className="w-3 h-3" />}
              </button>
            </div>
          </div>
        )}

        {/* Insufficient Evidence Warning Banner */}
        {!isUser && insufficientEvidence && (
          <div className="flex items-center gap-2 p-2.5 rounded-xl bg-amber-50 border border-amber-200 text-amber-900 text-xs mb-3">
            <AlertCircle className="w-4 h-4 flex-shrink-0 text-amber-700" />
            <span>Official evidence in indexed circulars was insufficient to fully confirm this response.</span>
          </div>
        )}

        {/* Attached Media Render (User or Assistant) */}
        {attachment && (
          <div className="mb-3">
            {attachment.media_type === 'image' && (
              <ImagePreview
                src={attachment.preview_url || attachment.url}
                alt={attachment.filename}
                caption={attachment.filename}
              />
            )}
            {attachment.media_type === 'document' && (
              <DocumentPreview
                filename={attachment.filename}
                pageCount={attachment.page_count}
                downloadUrl={attachment.preview_url || attachment.url}
              />
            )}
            {attachment.media_type === 'audio' && (
              <AudioPlayer
                src={attachment.preview_url || attachment.url}
                title={attachment.filename}
                durationSeconds={attachment.duration_seconds}
              />
            )}
          </div>
        )}

        {/* Text Content */}
        {message.content && (
          <div className="text-sm leading-relaxed whitespace-pre-wrap font-sans">
            {message.content}
          </div>
        )}

        {/* Citations Grid */}
        {!isUser && citations.length > 0 && (
          <div className="mt-4 pt-3 border-t border-warm-100">
            <div className="flex items-center justify-between mb-2">
              <span className="text-[11px] font-bold uppercase tracking-wider text-charcoal-400">
                Official Sources & References ({citations.length})
              </span>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
              {citations.map((citation, idx) => (
                <CitationCard
                  key={citation.source_id || idx}
                  citation={citation}
                  onSelectSource={onSelectSource}
                />
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
