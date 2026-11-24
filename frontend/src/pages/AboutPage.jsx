import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import Header from '../components/Header';
import {
  ShieldCheck,
  Cpu,
  Database,
  Mic,
  Volume2,
  FileText,
  Image as ImageIcon,
  CheckCircle2,
  AlertTriangle,
  ArrowRight,
  ExternalLink,
  Lock,
} from 'lucide-react';
import { checkHealth, apiClient } from '../services/api';

export default function AboutPage() {
  const [healthStatus, setHealthStatus] = useState(null);
  const [dbHealth, setDbHealth] = useState(null);
  const [isChecking, setIsChecking] = useState(true);

  // Check Web Speech API support
  const hasSTT = typeof window !== 'undefined' && ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window);
  const hasTTS = typeof window !== 'undefined' && 'speechSynthesis' in window;

  useEffect(() => {
    let isMounted = true;
    const fetchStatus = async () => {
      try {
        const h = await checkHealth();
        if (isMounted) setHealthStatus(h);
      } catch (e) {
        if (isMounted) setHealthStatus(null);
      }

      try {
        const dbRes = await apiClient.get('/api/v1/health/database');
        if (isMounted) setDbHealth(dbRes.data);
      } catch (e) {
        if (isMounted) setDbHealth(null);
      }

      if (isMounted) setIsChecking(false);
    };

    fetchStatus();
    return () => {
      isMounted = false;
    };
  }, []);

  return (
    <div className="min-h-screen flex flex-col bg-warm-50">
      <Header
        isConnected={Boolean(healthStatus?.status === 'healthy')}
        isChecking={isChecking}
        appName={healthStatus?.application || 'MAYA'}
      />

      <main className="flex-1 max-w-4xl mx-auto w-full px-4 sm:px-6 py-10">
        {/* Page Title */}
        <div className="mb-8 text-center sm:text-left">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-semibold bg-crimson-100/70 text-crimson-900 mb-3">
            <ShieldCheck className="w-3.5 h-3.5" />
            <span>Architecture & Verification Standards</span>
          </div>
          <h1 className="text-3xl sm:text-4xl font-bold text-charcoal-900 tracking-tight">
            About MAYA
          </h1>
          <p className="text-charcoal-600 mt-2 text-sm sm:text-base leading-relaxed">
            MAYA is an intelligent, multimodal university assistant engineered for Guru Gobind Singh Indraprastha University (GGSIPU). It grounds academic guidance in official circulars and verified regulations.
          </p>
        </div>

        {/* Core Pillars */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-8">
          <div className="bg-white border border-warm-200 rounded-2xl p-5 shadow-subtle">
            <div className="flex items-center gap-3 mb-3">
              <div className="w-10 h-10 rounded-xl bg-crimson-50 text-crimson-900 flex items-center justify-center font-bold">
                <FileText className="w-5 h-5" />
              </div>
              <div>
                <h3 className="font-bold text-charcoal-900 text-sm">Grounded Conversational RAG</h3>
                <p className="text-xs text-charcoal-500">Zero-hallucination policy on university notices</p>
              </div>
            </div>
            <p className="text-xs text-charcoal-600 leading-relaxed">
              MAYA searches indexed official circulars using 384-dimensional dense vectors (<code className="bg-warm-100 px-1 py-0.5 rounded text-[11px]">all-MiniLM-L6-v2</code>) and synthesizes factual answers via Gemini with precise page-level citations.
            </p>
          </div>

          <div className="bg-white border border-warm-200 rounded-2xl p-5 shadow-subtle">
            <div className="flex items-center gap-3 mb-3">
              <div className="w-10 h-10 rounded-xl bg-crimson-50 text-crimson-900 flex items-center justify-center font-bold">
                <Lock className="w-5 h-5" />
              </div>
              <div>
                <h3 className="font-bold text-charcoal-900 text-sm">Strict Privacy & Session Isolation</h3>
                <p className="text-xs text-charcoal-500">Student upload security guarantee</p>
              </div>
            </div>
            <p className="text-xs text-charcoal-600 leading-relaxed">
              Personal documents, fee receipts, and syllabi uploaded by students are tagged strictly with their conversation UUID. Uploaded files are never ingested into the public university knowledge base.
            </p>
          </div>
        </div>

        {/* Voice & Browser Compatibility Matrix */}
        <div className="bg-white border border-warm-200 rounded-2xl p-6 shadow-subtle mb-8">
          <h2 className="text-base font-bold text-charcoal-900 mb-2 flex items-center gap-2">
            <Mic className="w-4 h-4 text-crimson-800" />
            <span>Voice & Browser Compatibility</span>
          </h2>
          <p className="text-xs text-charcoal-500 mb-4">
            MAYA uses native Web APIs for real-time speech transcription (STT) and synthesized speech responses (TTS).
          </p>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="border border-warm-200 rounded-xl p-4 bg-warm-50/50">
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-bold text-charcoal-800">Speech-to-Text (STT)</span>
                {hasSTT ? (
                  <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded-full border border-emerald-200">
                    <CheckCircle2 className="w-3 h-3" /> Supported
                  </span>
                ) : (
                  <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-amber-700 bg-amber-50 px-2 py-0.5 rounded-full border border-amber-200">
                    <AlertTriangle className="w-3 h-3" /> Unsupported
                  </span>
                )}
              </div>
              <p className="text-[11px] text-charcoal-600 mb-2">
                Languages: <code className="bg-warm-100 px-1 py-0.5 rounded">en-IN</code> (Indian English), <code className="bg-warm-100 px-1 py-0.5 rounded">hi-IN</code> (Hindi).
              </p>
              <p className="text-[11px] text-charcoal-400">
                Recommended: Google Chrome, Microsoft Edge, Brave, Safari. (Firefox does not support SpeechRecognition).
              </p>
            </div>

            <div className="border border-warm-200 rounded-xl p-4 bg-warm-50/50">
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-bold text-charcoal-800">Text-to-Speech (TTS)</span>
                {hasTTS ? (
                  <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded-full border border-emerald-200">
                    <CheckCircle2 className="w-3 h-3" /> Supported
                  </span>
                ) : (
                  <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-amber-700 bg-amber-50 px-2 py-0.5 rounded-full border border-amber-200">
                    <AlertTriangle className="w-3 h-3" /> Unsupported
                  </span>
                )}
              </div>
              <p className="text-[11px] text-charcoal-600 mb-2">
                Browser SpeechSynthesis engine with play, pause, stop, and speaking indicator controls.
              </p>
              <p className="text-[11px] text-charcoal-400">
                Supported across all modern evergreen browsers (Chrome, Edge, Firefox, Safari).
              </p>
            </div>
          </div>
        </div>

        {/* System Subsystems & Dependencies */}
        <div className="bg-white border border-warm-200 rounded-2xl p-6 shadow-subtle mb-8">
          <h2 className="text-base font-bold text-charcoal-900 mb-4 flex items-center gap-2">
            <Cpu className="w-4 h-4 text-crimson-800" />
            <span>Live System Status & Subsystems</span>
          </h2>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs">
            <div className="p-3 rounded-xl border border-warm-200 bg-warm-50">
              <div className="text-[11px] text-charcoal-400 uppercase tracking-wider font-semibold mb-1">Backend Server</div>
              <div className="font-bold text-charcoal-800">
                {healthStatus?.status === 'healthy' ? (
                  <span className="text-emerald-700 flex items-center gap-1">
                    <CheckCircle2 className="w-3.5 h-3.5" /> Healthy (Port 8000)
                  </span>
                ) : (
                  <span className="text-amber-700">Connecting...</span>
                )}
              </div>
            </div>

            <div className="p-3 rounded-xl border border-warm-200 bg-warm-50">
              <div className="text-[11px] text-charcoal-400 uppercase tracking-wider font-semibold mb-1">Supabase DB</div>
              <div className="font-bold text-charcoal-800">
                {dbHealth?.supabase === 'connected' ? (
                  <span className="text-emerald-700 flex items-center gap-1">
                    <CheckCircle2 className="w-3.5 h-3.5" /> PostgREST Connected
                  </span>
                ) : (
                  <span className="text-charcoal-600">Local Fallback</span>
                )}
              </div>
            </div>

            <div className="p-3 rounded-xl border border-warm-200 bg-warm-50">
              <div className="text-[11px] text-charcoal-400 uppercase tracking-wider font-semibold mb-1">Zilliz Cloud / Milvus</div>
              <div className="font-bold text-charcoal-800">
                {dbHealth?.zilliz === 'connected' ? (
                  <span className="text-emerald-700 flex items-center gap-1">
                    <CheckCircle2 className="w-3.5 h-3.5" /> Collection Active
                  </span>
                ) : (
                  <span className="text-charcoal-600">Local Dense Search</span>
                )}
              </div>
            </div>
          </div>
        </div>

        {/* Quick Return Action */}
        <div className="flex items-center justify-between pt-4 border-t border-warm-200">
          <Link
            to="/"
            className="text-xs font-semibold text-charcoal-600 hover:text-charcoal-900 transition-colors"
          >
            ← Return to Dashboard
          </Link>
          <Link
            to="/chat"
            className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-crimson-900 text-white font-medium text-xs hover:bg-crimson-800 transition-all shadow-subtle"
          >
            <span>Open Chat Assistant</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </Link>
        </div>
      </main>

      <footer className="w-full border-t border-warm-200/80 py-6 text-center text-xs text-charcoal-400">
        <p>MAYA • Multimodal AI-Powered University Assistant • GGSIPU Student Evaluation Edition</p>
      </footer>
    </div>
  );
}
