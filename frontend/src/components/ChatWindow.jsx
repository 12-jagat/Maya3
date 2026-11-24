import React, { useRef, useEffect } from 'react';
import ChatMessage from './ChatMessage';
import TypingIndicator from './TypingIndicator';
import SuggestedQuestions from './SuggestedQuestions';
import { Sparkles, Shield, BookOpen } from 'lucide-react';

export default function ChatWindow({
  messages,
  isLoading,
  onSendMessage,
  onSelectSource,
}) {
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  return (
    <div className="flex-1 overflow-y-auto px-4 sm:px-8 py-6 flex flex-col justify-between">
      {messages.length === 0 ? (
        <div className="flex-1 flex flex-col items-center justify-center text-center my-auto max-w-xl mx-auto py-12">
          <div className="w-14 h-14 rounded-2xl bg-crimson-50 text-crimson-900 border border-crimson-200/80 flex items-center justify-center mb-4 shadow-subtle">
            <Sparkles className="w-7 h-7" />
          </div>

          <h2 className="text-2xl font-bold text-charcoal-900 tracking-tight mb-2">
            MAYA University Assistant
          </h2>
          <p className="text-sm text-charcoal-500 max-w-md leading-relaxed mb-6">
            Ask any question regarding Guru Gobind Singh Indraprastha University official datesheets, results, circulars, and admissions.
          </p>

          <SuggestedQuestions onSelectQuestion={onSendMessage} />
        </div>
      ) : (
        <div className="w-full max-w-3xl mx-auto">
          {messages.map((msg, idx) => (
            <ChatMessage
              key={msg.id || idx}
              message={msg}
              onSelectSource={onSelectSource}
            />
          ))}

          {isLoading && <TypingIndicator />}
          <div ref={bottomRef} />
        </div>
      )}
    </div>
  );
}
