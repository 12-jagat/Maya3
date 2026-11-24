import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import Header from '../components/Header';
import ChatInputPlaceholder from '../components/ChatInputPlaceholder';
import FeatureGrid from '../components/FeatureGrid';
import { checkHealth, getConversations, getLatestNotices } from '../services/api';
import { Bell, BookOpen, ExternalLink, ArrowRight, MessageSquare, Clock, Sparkles } from 'lucide-react';

export default function WelcomePage() {
  const [healthStatus, setHealthStatus] = useState(null);
  const [isChecking, setIsChecking] = useState(true);
  const [recentConversations, setRecentConversations] = useState([]);
  const [latestNotices, setLatestNotices] = useState([]);

  useEffect(() => {
    let isMounted = true;

    const verifyBackend = async () => {
      try {
        const data = await checkHealth();
        if (isMounted) {
          setHealthStatus(data);
          setIsChecking(false);
        }
      } catch (err) {
        if (isMounted) {
          setHealthStatus(null);
          setIsChecking(false);
        }
      }
    };

    const loadDashboardData = async () => {
      try {
        const [convs, notices] = await Promise.allSettled([
          getConversations(3),
          getLatestNotices(3),
        ]);
        if (isMounted) {
          if (convs.status === 'fulfilled' && Array.isArray(convs.value)) {
            setRecentConversations(convs.value);
          }
          if (notices.status === 'fulfilled' && Array.isArray(notices.value)) {
            setLatestNotices(notices.value);
          }
        }
      } catch (e) {
        // Safe graceful degradation
      }
    };

    verifyBackend();
    loadDashboardData();
    const interval = setInterval(verifyBackend, 15000);
    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, []);

  return (
    <div className="min-h-screen flex flex-col bg-warm-50">
      <Header
        isConnected={Boolean(healthStatus?.status === 'healthy')}
        isChecking={isChecking}
        appName={healthStatus?.application}
      />

      <main className="flex-1 flex flex-col justify-center items-center px-4 sm:px-6 py-12 max-w-5xl mx-auto w-full text-center">
        {/* Subtle pill badge */}
        <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full text-xs font-medium bg-crimson-50 text-crimson-900 border border-crimson-200/60 mb-6 shadow-sm">
          <span className="w-1.5 h-1.5 rounded-full bg-crimson-800 animate-pulse"></span>
          <span>Guru Gobind Singh Indraprastha University</span>
        </div>

        {/* Main Branding */}
        <h1 className="text-4xl sm:text-5xl lg:text-6xl font-bold text-charcoal-900 tracking-tight mb-3">
          MAYA
        </h1>

        {/* Subtitle explicitly requested */}
        <p className="text-xl sm:text-2xl font-medium text-crimson-900 tracking-tight mb-4">
          Your Intelligent University Assistant.
        </p>

        {/* Welcome message */}
        <p className="text-sm sm:text-base text-charcoal-600 max-w-xl mx-auto mb-6 leading-relaxed">
          Welcome to MAYA. Seamlessly access official university circulars, exam notices, and academic guidelines through multimodal AI and verified semantic search.
        </p>

        {/* Action Buttons */}
        <div className="flex items-center justify-center gap-3 mb-8">
          <Link
            to="/chat"
            className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-crimson-900 text-white font-medium text-sm hover:bg-crimson-800 shadow-crimson-glow transition-all"
          >
            <span>Ask MAYA AI</span>
            <ArrowRight className="w-4 h-4" />
          </Link>
          <Link
            to="/notices"
            className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-white border border-warm-200 text-charcoal-700 font-medium text-sm hover:bg-warm-100 transition-all shadow-subtle"
          >
            <Bell className="w-4 h-4 text-crimson-800" />
            <span>Notice Center</span>
          </Link>
        </div>

        {/* Planned Crawler Architecture Notice */}
        <div className="w-full max-w-2xl bg-white/70 border border-warm-200 rounded-xl p-4 mb-8 text-left shadow-subtle">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-semibold text-charcoal-700 uppercase tracking-wider flex items-center gap-1.5">
              <Bell className="w-3.5 h-3.5 text-crimson-800" />
              Official Data Sources Configured
            </span>
            <span className="text-[11px] text-charcoal-400 font-mono">ipu.ac.in</span>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs text-charcoal-600 mb-3">
            <div className="p-2 rounded bg-warm-50 border border-warm-100 flex items-center justify-between">
              <span>Main Notices Portal</span>
              <span className="text-[10px] px-1.5 py-0.5 rounded bg-warm-200 text-charcoal-700">ipu.ac.in/notices.php</span>
            </div>
            <div className="p-2 rounded bg-warm-50 border border-warm-100 flex items-center justify-between">
              <span>Examination Dept Portal</span>
              <span className="text-[10px] px-1.5 py-0.5 rounded bg-warm-200 text-charcoal-700">examdept.ggsipu.ac.in</span>
            </div>
          </div>
          <div className="flex justify-end pt-1">
            <Link
              to="/notices"
              className="inline-flex items-center gap-1.5 text-xs font-semibold text-crimson-900 hover:text-crimson-700 hover:underline"
            >
              <span>Explore & Crawl Notice Center</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </Link>
          </div>
        </div>

        {/* Placeholder Chat Input */}
        <ChatInputPlaceholder />

        {/* Dashboard Dynamic Sections: Recent Conversations & Latest Notices */}
        <div className="w-full max-w-4xl grid grid-cols-1 md:grid-cols-2 gap-4 my-8 text-left">
          {/* Recent Conversations */}
          <div className="bg-white border border-warm-200 rounded-2xl p-5 shadow-subtle flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between mb-3 pb-2 border-b border-warm-100">
                <span className="text-xs font-bold text-charcoal-800 uppercase tracking-wider flex items-center gap-1.5">
                  <MessageSquare className="w-3.5 h-3.5 text-crimson-800" />
                  Recent Conversations
                </span>
                <Link to="/chat" className="text-[11px] font-semibold text-crimson-800 hover:underline">
                  Open Chat
                </Link>
              </div>

              {recentConversations.length > 0 ? (
                <div className="space-y-2">
                  {recentConversations.map((c) => (
                    <Link
                      key={c.id}
                      to={`/chat?id=${c.id}`}
                      className="block p-2.5 rounded-xl border border-warm-100 bg-warm-50/60 hover:bg-warm-100 transition-colors"
                    >
                      <div className="text-xs font-semibold text-charcoal-900 truncate">
                        {c.title || 'Conversation'}
                      </div>
                      <div className="text-[10px] text-charcoal-500 flex items-center gap-1 mt-0.5">
                        <Clock className="w-2.5 h-2.5" />
                        <span>{new Date(c.updated_at || c.created_at).toLocaleDateString()}</span>
                      </div>
                    </Link>
                  ))}
                </div>
              ) : (
                <div className="py-6 text-center text-xs text-charcoal-400">
                  No previous conversations yet. Ask MAYA a question!
                </div>
              )}
            </div>

            <div className="pt-3 mt-2 border-t border-warm-100">
              <Link
                to="/chat"
                className="inline-flex items-center gap-1 text-xs font-semibold text-crimson-800 hover:text-crimson-950"
              >
                <Sparkles className="w-3 h-3" />
                <span>Start a new conversation thread →</span>
              </Link>
            </div>
          </div>

          {/* Latest University Notices */}
          <div className="bg-white border border-warm-200 rounded-2xl p-5 shadow-subtle flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between mb-3 pb-2 border-b border-warm-100">
                <span className="text-xs font-bold text-charcoal-800 uppercase tracking-wider flex items-center gap-1.5">
                  <Bell className="w-3.5 h-3.5 text-crimson-800" />
                  Latest University Notices
                </span>
                <Link to="/notices" className="text-[11px] font-semibold text-crimson-800 hover:underline">
                  All Notices
                </Link>
              </div>

              {latestNotices.length > 0 ? (
                <div className="space-y-2">
                  {latestNotices.map((n) => (
                    <div
                      key={n.id}
                      className="p-2.5 rounded-xl border border-warm-100 bg-warm-50/60 hover:bg-warm-100 transition-colors"
                    >
                      <div className="text-xs font-semibold text-charcoal-900 line-clamp-1">
                        {n.title}
                      </div>
                      <div className="flex items-center justify-between mt-1 text-[10px] text-charcoal-500">
                        <span className="px-1.5 py-0.2 rounded bg-warm-200 text-charcoal-700 font-medium">
                          {n.category || 'General'}
                        </span>
                        <span>{n.published_date || 'Recent'}</span>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="py-6 text-center text-xs text-charcoal-400">
                  Connecting to university notice feed...
                </div>
              )}
            </div>

            <div className="pt-3 mt-2 border-t border-warm-100">
              <Link
                to="/notices"
                className="inline-flex items-center gap-1 text-xs font-semibold text-crimson-800 hover:text-crimson-950"
              >
                <span>Browse & search official archive →</span>
              </Link>
            </div>
          </div>
        </div>

        {/* Feature Highlights Grid */}
        <FeatureGrid />
      </main>

      {/* Footer */}
      <footer className="w-full border-t border-warm-200/80 py-6 text-center text-xs text-charcoal-400">
        <p>MAYA • Multimodal AI-Powered University Assistant • GGSIPU Student Evaluation Edition</p>
      </footer>
    </div>
  );
}
