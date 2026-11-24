import React, { useEffect, useState, useRef } from 'react';
import { Mic, MicOff, Volume2, X, Sparkles, Loader2, ArrowRight } from 'lucide-react';
import { useSpeechRecognition } from '../hooks/useSpeechRecognition';
import { useSpeechSynthesis } from '../hooks/useSpeechSynthesis';
import { useAudioRecorder } from '../hooks/useAudioRecorder';

export default function VoiceMode({ isOpen, onClose, onSendQuery, lastAssistantAnswer, isThinking }) {
  const [modeState, setModeState] = useState('idle'); // 'listening', 'thinking', 'speaking', 'idle'
  const {
    isListening,
    transcript,
    interimTranscript,
    error: speechError,
    startListening,
    stopListening,
    resetTranscript,
  } = useSpeechRecognition({ defaultLanguage: 'en-IN' });

  const {
    isSpeaking,
    speak,
    stop: stopSpeaking,
  } = useSpeechSynthesis();

  const {
    isRecording,
    recordingDuration,
    startRecording,
    stopRecording,
    cancelRecording,
  } = useAudioRecorder();

  const silenceTimeoutRef = useRef(null);

  // Sync isThinking state
  useEffect(() => {
    if (isThinking) {
      setModeState('thinking');
    }
  }, [isThinking]);

  // When lastAssistantAnswer updates and we were thinking, speak it
  useEffect(() => {
    if (lastAssistantAnswer && modeState === 'thinking') {
      setModeState('speaking');
      // Speak the answer, and when speech ends, automatically set to idle
      speak(lastAssistantAnswer, () => {
        setModeState('idle');
      });
    }
  }, [lastAssistantAnswer, modeState, speak]);

  // Handle voice mode opened/closed
  useEffect(() => {
    if (isOpen) {
      setModeState('idle');
      resetTranscript();
    } else {
      stopListening();
      stopSpeaking();
      cancelRecording();
    }
  }, [isOpen, resetTranscript, stopListening, stopSpeaking, cancelRecording]);

  // Handle start listening
  const handleStartTalk = () => {
    stopSpeaking();
    resetTranscript();
    setModeState('listening');
    startListening();
    startRecording();
  };

  // Handle stop listening and send
  const handleStopAndSend = async () => {
    stopListening();
    const recordedAudio = await stopRecording();
    const query = (transcript + ' ' + interimTranscript).trim();

    if (query) {
      setModeState('thinking');
      onSendQuery(query);
      resetTranscript();
    } else if (recordedAudio) {
      setModeState('thinking');
      onSendQuery({
        text: 'Voice query regarding GGSIPU circulars',
        attachment: { file: recordedAudio, mediaType: 'audio' },
      });
      resetTranscript();
    } else {
      setModeState('idle');
    }
  };

  if (!isOpen) return null;

  const currentDisplaySpeech = (transcript + ' ' + interimTranscript).trim();

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-charcoal-950/80 backdrop-blur-md p-4 animate-in fade-in duration-200">
      <div className="relative w-full max-w-lg bg-gradient-to-b from-charcoal-900 to-charcoal-950 border border-warm-800/60 rounded-3xl p-6 sm:p-8 shadow-2xl flex flex-col items-center text-center text-white">
        {/* Close Button */}
        <button
          type="button"
          onClick={() => {
            stopListening();
            stopSpeaking();
            onClose();
          }}
          className="absolute top-5 right-5 p-2 rounded-full text-charcoal-400 hover:text-white hover:bg-charcoal-800 transition-colors"
        >
          <X className="w-5 h-5" />
        </button>

        {/* Header Tag */}
        <div className="flex items-center gap-2 text-crimson-400 text-xs font-bold tracking-widest uppercase mb-6">
          <Sparkles className="w-4 h-4" />
          <span>MAYA Voice Mode • GGSIPU Assistant</span>
        </div>

        {/* Central Visual Animation */}
        <div className="my-8 relative flex items-center justify-center">
          {modeState === 'listening' ? (
            <div className="relative flex items-center justify-center">
              <div className="w-36 h-36 rounded-full bg-rose-600/20 animate-ping absolute" />
              <div className="w-28 h-28 rounded-full bg-rose-600/40 animate-pulse absolute" />
              <button
                type="button"
                onClick={handleStopAndSend}
                className="w-20 h-20 rounded-full bg-rose-600 hover:bg-rose-700 text-white flex items-center justify-center shadow-lg transform active:scale-95 transition-transform z-10"
              >
                <Mic className="w-8 h-8 animate-pulse" />
              </button>
            </div>
          ) : modeState === 'speaking' ? (
            <div className="relative flex items-center justify-center">
              <div className="w-36 h-36 rounded-full bg-crimson-500/20 animate-ping absolute" />
              <div className="w-28 h-28 rounded-full bg-crimson-600/30 animate-pulse absolute" />
              <button
                type="button"
                onClick={() => {
                  stopSpeaking();
                  setModeState('idle');
                }}
                title="Click to interrupt"
                className="w-20 h-20 rounded-full bg-crimson-700 hover:bg-crimson-800 text-white flex items-center justify-center shadow-lg z-10"
              >
                <Volume2 className="w-8 h-8 animate-bounce" />
              </button>
            </div>
          ) : modeState === 'thinking' ? (
            <div className="w-20 h-20 rounded-full bg-charcoal-800 border-2 border-crimson-500/50 flex items-center justify-center shadow-lg">
              <Loader2 className="w-8 h-8 text-crimson-400 animate-spin" />
            </div>
          ) : (
            <button
              type="button"
              onClick={handleStartTalk}
              className="w-20 h-20 rounded-full bg-crimson-900 hover:bg-crimson-800 text-white flex items-center justify-center shadow-lg transform active:scale-95 transition-all"
            >
              <Mic className="w-8 h-8" />
            </button>
          )}
        </div>

        {/* Status text */}
        <div className="text-sm font-medium mb-3">
          {modeState === 'listening' && (
            <span className="text-rose-400 font-semibold animate-pulse">Listening to your question...</span>
          )}
          {modeState === 'thinking' && (
            <span className="text-warm-300">Consulting official GGSIPU notices...</span>
          )}
          {modeState === 'speaking' && (
            <span className="text-crimson-300">MAYA is answering... (click circle to interrupt)</span>
          )}
          {modeState === 'idle' && (
            <span className="text-charcoal-300">Tap the microphone to speak your question</span>
          )}
        </div>

        {/* Live Transcript / Speech Preview Box */}
        <div className="w-full bg-charcoal-900/90 border border-charcoal-800 rounded-2xl p-4 min-h-[90px] max-h-40 overflow-y-auto text-left text-sm text-charcoal-200">
          {currentDisplaySpeech ? (
            <p className="leading-relaxed">
              <span className="text-white font-medium">{transcript}</span>{' '}
              <span className="text-rose-300 italic">{interimTranscript}</span>
            </p>
          ) : (
            <p className="text-charcoal-500 italic text-center pt-5">
              {modeState === 'speaking'
                ? lastAssistantAnswer || 'Speaking answer...'
                : 'Your spoken words will appear here...'}
            </p>
          )}
        </div>

        {/* Error notice */}
        {speechError && (
          <p className="text-rose-400 text-xs mt-3">{speechError}</p>
        )}

        {/* Action Controls */}
        <div className="mt-6 flex items-center gap-3 w-full justify-center">
          {modeState === 'listening' && (
            <button
              type="button"
              onClick={handleStopAndSend}
              disabled={!currentDisplaySpeech}
              className="px-5 py-2.5 rounded-xl bg-crimson-900 hover:bg-crimson-950 text-white text-xs font-semibold flex items-center gap-2 disabled:opacity-40 shadow-sm"
            >
              <span>Ask MAYA</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          )}

          {modeState === 'idle' && (
            <button
              type="button"
              onClick={handleStartTalk}
              className="px-5 py-2.5 rounded-xl bg-crimson-900 hover:bg-crimson-950 text-white text-xs font-semibold flex items-center gap-2 shadow-sm"
            >
              <Mic className="w-3.5 h-3.5" />
              <span>Start Speaking</span>
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
