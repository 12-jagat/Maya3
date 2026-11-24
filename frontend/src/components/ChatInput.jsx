import React, { useState, useRef, useEffect } from 'react';
import { Send, CornerDownLeft, Sparkles, Loader2, Mic, Radio } from 'lucide-react';
import VoiceInput from './VoiceInput';
import FileUploadButton from './FileUploadButton';
import AttachmentPreview from './AttachmentPreview';
import { useSpeechRecognition } from '../hooks/useSpeechRecognition';
import { useAudioRecorder } from '../hooks/useAudioRecorder';

export default function ChatInput({
  onSendMessage,
  isLoading,
  placeholder,
  onOpenVoiceMode,
}) {
  const [text, setText] = useState('');
  const [attachment, setAttachment] = useState(null); // { file, mediaType }
  const [isDragging, setIsDragging] = useState(false);
  const textareaRef = useRef(null);

  // Universal HTML5 MediaRecorder (works across all browsers, zero Google cloud dependency)
  const {
    isRecording,
    recordingDuration,
    error: recorderError,
    startRecording,
    stopRecording,
    cancelRecording,
  } = useAudioRecorder();

  // Web Speech recognition for inline real-time speech-to-text
  const {
    isListening,
    transcript,
    interimTranscript,
    error: speechError,
    startListening,
    stopListening,
    resetTranscript,
  } = useSpeechRecognition({ defaultLanguage: 'en-IN' });

  // Update input text with speech transcript
  useEffect(() => {
    if (transcript) {
      setText((prev) => (prev ? `${prev} ${transcript}` : transcript));
      resetTranscript();
    }
  }, [transcript, resetTranscript]);

  // Unified voice input toggle (SpeechRecognition + MediaRecorder fallback)
  const handleStartVoice = async () => {
    resetTranscript();
    startListening();
    await startRecording();
  };

  const handleStopVoice = async () => {
    stopListening();
    const recordedAudio = await stopRecording();
    const cleanSpeech = (transcript + ' ' + interimTranscript).trim();

    if (cleanSpeech) {
      setText((prev) => (prev ? `${prev} ${cleanSpeech}` : cleanSpeech));
      resetTranscript();
    } else if (recordedAudio && recordedAudio.size > 0) {
      // Automatic fallback if Web Speech API had network error
      setAttachment({
        file: recordedAudio,
        mediaType: 'audio',
      });
      if (!text.trim()) {
        setText('Voice query regarding university circulars');
      }
    }
  };

  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 140)}px`;
    }
  }, [text, interimTranscript]);

  const handleSubmit = (e) => {
    e?.preventDefault();
    const cleanText = text.trim();
    if ((!cleanText && !attachment) || isLoading) return;

    if (isListening) {
      stopListening();
    }

    onSendMessage({
      text: cleanText,
      attachment: attachment,
    });

    setText('');
    setAttachment(null);
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const handleFileSelect = (file, mediaType) => {
    setAttachment({ file, mediaType });
  };

  // Drag and drop handlers
  const handleDragOver = (e) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => {
    setIsDragging(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragging(false);
    const file = e.dataTransfer.files?.[0];
    if (!file) return;

    const ext = file.name.split('.').pop()?.toLowerCase();
    let mediaType = 'document';
    if (['jpg', 'jpeg', 'png', 'webp'].includes(ext)) {
      mediaType = 'image';
    } else if (['wav', 'mp3', 'm4a', 'aac'].includes(ext)) {
      mediaType = 'audio';
    }
    setAttachment({ file, mediaType });
  };

  const canSubmit = (text.trim().length > 0 || attachment !== null) && !isLoading;

  return (
    <div
      className="w-full max-w-3xl mx-auto px-4 pb-4"
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
    >
      {/* Pending Attachment Chip */}
      {attachment && (
        <AttachmentPreview
          file={attachment.file}
          mediaType={attachment.mediaType}
          onRemove={() => setAttachment(null)}
        />
      )}

      {/* Dragging Overlay Indicator */}
      {isDragging && (
        <div className="mb-2 p-3 rounded-2xl bg-crimson-50 border-2 border-dashed border-crimson-800 text-crimson-900 text-xs text-center font-semibold animate-pulse">
          Drop file here to attach to MAYA query
        </div>
      )}

      <form
        onSubmit={handleSubmit}
        className="relative bg-white border border-warm-300/80 focus-within:border-crimson-800 focus-within:ring-2 focus-within:ring-crimson-100 rounded-2xl shadow-premium transition-all p-2 flex items-end gap-1.5"
      >
        {/* File Attachment Button */}
        <FileUploadButton
          onFileSelect={handleFileSelect}
          disabled={isLoading}
        />

        {/* Text Area */}
        <div className="flex-1 relative">
          <textarea
            ref={textareaRef}
            value={text}
            onChange={(e) => setText(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={
              (isListening || isRecording)
                ? 'Listening / recording audio...'
                : placeholder || 'Ask MAYA about circulars or attach notice image/PDF/audio...'
            }
            rows={1}
            disabled={isLoading}
            className="w-full bg-transparent px-2 py-2 text-sm text-charcoal-900 placeholder:text-charcoal-400 focus:outline-none resize-none max-h-36 disabled:opacity-50"
          />
          {isListening && interimTranscript && (
            <div className="text-[11px] text-rose-500 italic px-2 pb-1 truncate">
              {interimTranscript}
            </div>
          )}
          {isRecording && !interimTranscript && (
            <div className="text-[11px] text-crimson-600 font-medium px-2 pb-1 flex items-center gap-1.5 animate-pulse">
              <span className="w-2 h-2 rounded-full bg-crimson-600 inline-block"></span>
              Recording voice query ({recordingDuration}s)...
            </div>
          )}
        </div>

        {/* Inline Voice Recognition & Audio Recorder Button */}
        <VoiceInput
          isListening={isListening || isRecording}
          onStartListening={handleStartVoice}
          onStopListening={handleStopVoice}
          disabled={isLoading}
          error={speechError || recorderError}
        />

        {/* Dedicated Turn-Based Voice Mode Trigger */}
        {onOpenVoiceMode && (
          <button
            type="button"
            onClick={onOpenVoiceMode}
            title="Open Turn-Based Voice Assistant Mode"
            disabled={isLoading}
            className="p-2.5 rounded-xl text-charcoal-500 hover:text-crimson-800 hover:bg-warm-100 disabled:opacity-40 transition-colors"
          >
            <Radio className="w-4 h-4" />
          </button>
        )}

        {/* Send Button */}
        <button
          type="submit"
          disabled={!canSubmit}
          className="flex-shrink-0 p-2.5 rounded-xl bg-crimson-900 text-white hover:bg-crimson-950 active:scale-95 disabled:opacity-40 disabled:hover:bg-crimson-900 disabled:cursor-not-allowed transition-all shadow-sm"
        >
          {isLoading ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : (
            <Send className="w-4 h-4 fill-current" />
          )}
        </button>
      </form>

      <div className="flex items-center justify-between text-[11px] text-charcoal-400 px-3 pt-1.5">
        <span className="hidden sm:inline">
          Press <kbd className="font-mono bg-warm-100 px-1 py-0.5 rounded border border-warm-200">Enter</kbd> to send, drag & drop files to attach
        </span>
        <span className="sm:hidden text-[10px]">
          Tap mic for voice or attach files
        </span>
        <span className="flex items-center gap-1 font-semibold text-charcoal-500 ml-auto">
          <Sparkles className="w-3 h-3 text-crimson-800" />
          Multimodal Grounding • Gemini & Zilliz
        </span>
      </div>
    </div>
  );
}
