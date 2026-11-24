import { useState, useEffect, useRef, useCallback } from 'react';

/**
 * Hook for Web SpeechSynthesis API.
 * Provides text-to-speech with Indian English / natural voice prioritization,
 * rate control, mute toggle, and play/pause/cancel states.
 */
export function useSpeechSynthesis() {
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [isPaused, setIsPaused] = useState(false);
  const [isMuted, setIsMuted] = useState(false);
  const [rate, setRate] = useState(1.0);
  const [voices, setVoices] = useState([]);
  const [selectedVoice, setSelectedVoice] = useState(null);

  const utteranceRef = useRef(null);
  const isSupported = typeof window !== 'undefined' && 'speechSynthesis' in window;

  // Load available voices
  const updateVoices = useCallback(() => {
    if (!isSupported) return;
    const available = window.speechSynthesis.getVoices();
    setVoices(available);

    if (available.length > 0 && !selectedVoice) {
      // Prefer en-IN or hi-IN or natural English voices
      const preferred =
        available.find((v) => v.lang === 'en-IN') ||
        available.find((v) => v.lang.startsWith('en-') && (v.name.includes('Natural') || v.name.includes('India'))) ||
        available.find((v) => v.lang.startsWith('en')) ||
        available[0];
      setSelectedVoice(preferred);
    }
  }, [isSupported, selectedVoice]);

  useEffect(() => {
    if (!isSupported) return;
    updateVoices();
    window.speechSynthesis.onvoiceschanged = updateVoices;

    return () => {
      try {
        window.speechSynthesis.cancel();
      } catch {
        // Ignore
      }
    };
  }, [isSupported, updateVoices]);

  const cleanTextForSpeech = (text) => {
    if (!text) return '';
    // Strip markdown links, bolding, code blocks, URLs
    return text
      .replace(/```[\s\S]*?```/g, 'Code block omitted.')
      .replace(/`([^`]+)`/g, '$1')
      .replace(/\[([^\]]+)\]\([^)]+\)/g, '$1')
      .replace(/https?:\/\/\S+/g, 'link')
      .replace(/[*_~#]/g, '')
      .replace(/\[SOURCE_\d+\]/gi, '')
      .replace(/\[DOCUMENT_EXCERPT_\d+\]/gi, '')
      .trim();
  };

  const speak = useCallback(
    (rawText, onEndCallback) => {
      if (!isSupported || isMuted) return;

      const cleanText = cleanTextForSpeech(rawText);
      if (!cleanText) return;

      try {
        // Resume synthesis context if suspended by browser autoplay policy
        if (window.speechSynthesis.paused) {
          window.speechSynthesis.resume();
        }
        window.speechSynthesis.cancel();

        setTimeout(() => {
          try {
            const utterance = new SpeechSynthesisUtterance(cleanText);
            utterance.rate = rate;
            if (selectedVoice) {
              utterance.voice = selectedVoice;
            }

            utterance.onstart = () => {
              setIsSpeaking(true);
              setIsPaused(false);
            };

            utterance.onend = () => {
              setIsSpeaking(false);
              setIsPaused(false);
              if (onEndCallback) onEndCallback();
            };

            utterance.onerror = (err) => {
              console.warn('SpeechSynthesis error:', err);
              setIsSpeaking(false);
              setIsPaused(false);
            };

            utteranceRef.current = utterance;
            window.speechSynthesis.speak(utterance);
          } catch (speakErr) {
            console.error('Error invoking speak:', speakErr);
            setIsSpeaking(false);
          }
        }, 50);
      } catch (err) {
        console.error('Error triggering speech synthesis:', err);
        setIsSpeaking(false);
      }
    },
    [isSupported, isMuted, rate, selectedVoice]
  );

  const stop = useCallback(() => {
    if (!isSupported) return;
    try {
      window.speechSynthesis.cancel();
    } catch {
      // Ignore
    }
    setIsSpeaking(false);
    setIsPaused(false);
  }, [isSupported]);

  const pause = useCallback(() => {
    if (!isSupported) return;
    try {
      window.speechSynthesis.pause();
      setIsPaused(true);
    } catch {
      // Ignore
    }
  }, [isSupported]);

  const resume = useCallback(() => {
    if (!isSupported) return;
    try {
      window.speechSynthesis.resume();
      setIsPaused(false);
    } catch {
      // Ignore
    }
  }, [isSupported]);

  const toggleMute = useCallback(() => {
    setIsMuted((prev) => {
      if (!prev) {
        stop();
      }
      return !prev;
    });
  }, [stop]);

  return {
    isSpeaking,
    isPaused,
    isMuted,
    rate,
    setRate,
    voices,
    selectedVoice,
    setSelectedVoice,
    speak,
    stop,
    pause,
    resume,
    toggleMute,
    isSupported,
  };
}
