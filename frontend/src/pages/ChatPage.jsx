import React, { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import Header from '../components/Header';
import ConversationSidebar from '../components/ConversationSidebar';
import ChatWindow from '../components/ChatWindow';
import ChatInput from '../components/ChatInput';
import SourceDrawer from '../components/SourceDrawer';
import VoiceMode from '../components/VoiceMode';
import ProcessingIndicator from '../components/ProcessingIndicator';
import {
  checkHealth,
  getConversations,
  getConversation,
  sendChatMessage,
  deleteConversation,
  uploadImage,
  uploadDocument,
  uploadAudio,
} from '../services/api';
import { PanelLeft, AlertCircle, Sparkles, Radio } from 'lucide-react';

export default function ChatPage() {
  const [searchParams] = useSearchParams();
  const urlConvId = searchParams.get('id');

  const [healthStatus, setHealthStatus] = useState(null);
  const [isCheckingHealth, setIsCheckingHealth] = useState(true);

  // Conversations & Messages State
  const [conversations, setConversations] = useState([]);
  const [activeConversationId, setActiveConversationId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [processingMediaType, setProcessingMediaType] = useState(null);
  const [errorBanner, setErrorBanner] = useState(null);

  // UI State
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);
  const [selectedSource, setSelectedSource] = useState(null);
  const [isSourceDrawerOpen, setIsSourceDrawerOpen] = useState(false);
  const [isVoiceModeOpen, setIsVoiceModeOpen] = useState(false);
  const [lastAssistantAnswer, setLastAssistantAnswer] = useState('');

  // Check health on mount
  useEffect(() => {
    checkHealth()
      .then((data) => {
        setHealthStatus(data);
        setIsCheckingHealth(false);
      })
      .catch(() => {
        setHealthStatus(null);
        setIsCheckingHealth(false);
      });

    loadConversations();
    if (urlConvId) {
      handleSelectConversation(urlConvId);
    }
  }, [urlConvId]);

  // Fetch recent conversation list
  const loadConversations = async () => {
    try {
      const list = await getConversations(25);
      setConversations(list || []);
    } catch (err) {
      console.error('Failed to load conversations:', err);
    }
  };

  // Load messages when active conversation changes
  const handleSelectConversation = async (conversationId) => {
    setActiveConversationId(conversationId);
    setErrorBanner(null);
    try {
      const detail = await getConversation(conversationId);
      setMessages(detail.messages || []);
    } catch (err) {
      console.error('Failed to load thread messages:', err);
      setErrorBanner('Failed to load conversation history.');
    }
  };

  // Start new conversation
  const handleNewConversation = () => {
    setActiveConversationId(null);
    setMessages([]);
    setErrorBanner(null);
  };

  // Delete conversation
  const handleDeleteConversation = async (conversationId) => {
    try {
      await deleteConversation(conversationId);
      if (activeConversationId === conversationId) {
        handleNewConversation();
      }
      loadConversations();
    } catch (err) {
      console.error('Failed to delete thread:', err);
    }
  };

  // Send message or multimodal upload
  const handleSendMessage = async (payload) => {
    let text = '';
    let attachment = null;

    if (typeof payload === 'string') {
      text = payload.trim();
    } else if (payload && typeof payload === 'object') {
      text = (payload.text || '').trim();
      attachment = payload.attachment || null;
    }

    if (!text && !attachment) return;
    if (isLoading) return;

    setErrorBanner(null);

    // Optimistically add user message
    let localPreviewUrl = null;
    if (attachment?.file) {
      localPreviewUrl = URL.createObjectURL(attachment.file);
    }

    const tempUserMsg = {
      id: `temp_${Date.now()}`,
      role: 'user',
      content: text,
      created_at: new Date().toISOString(),
      attachment: attachment
        ? {
            filename: attachment.file.name,
            media_type: attachment.mediaType,
            preview_url: localPreviewUrl,
            size_bytes: attachment.file.size,
          }
        : null,
    };

    setMessages((prev) => [...prev, tempUserMsg]);
    setIsLoading(true);
    setProcessingMediaType(attachment ? attachment.mediaType : null);

    try {
      let asstContent = '';
      let asstCitations = [];
      let newConvId = activeConversationId;
      let newMsgId = `asst_${Date.now()}`;
      let confidence = 'high';
      let insufficientEvidence = false;

      if (attachment) {
        // MULTIMODAL API ROUTING
        if (attachment.mediaType === 'image') {
          const res = await uploadImage({
            file: attachment.file,
            prompt: text,
            conversation_id: activeConversationId,
          });
          newConvId = res.conversation_id;
          newMsgId = res.message_id;
          asstContent = res.content || res.result?.answer || res.message;
          asstCitations = res.citations || res.result?.citations || [];
          confidence = res.confidence || (res.result?.is_official ? 'high' : 'medium');
        } else if (attachment.mediaType === 'document') {
          const res = await uploadDocument({
            file: attachment.file,
            prompt: text,
            conversation_id: activeConversationId,
          });
          newConvId = res.conversation_id;
          newMsgId = res.message_id;
          asstContent = res.content || res.result?.answer || res.message;
          asstCitations = res.citations || res.result?.citations || [];
          confidence = res.confidence || 'high';
        } else if (attachment.mediaType === 'audio') {
          const res = await uploadAudio({
            file: attachment.file,
            prompt: text,
            conversation_id: activeConversationId,
          });
          newConvId = res.conversation_id;
          newMsgId = res.message_id;
          asstContent = res.content || (res.result?.summary
            ? `${res.result.summary}\n\n**Key Points:**\n${(res.result.key_points || []).map((p) => `• ${p}`).join('\n')}`
            : res.message);
          asstCitations = res.citations || res.result?.citations || [];
          confidence = res.confidence || 'high';
        }
      } else {
        // STANDARD TEXT RAG CHAT
        const response = await sendChatMessage({
          message: text,
          conversation_id: activeConversationId,
        });
        newConvId = response.conversation_id;
        newMsgId = response.message_id;
        asstContent = response.content;
        asstCitations = response.citations || [];
        confidence = response.confidence;
        insufficientEvidence = response.insufficient_evidence;
      }

      // Update active thread ID if new
      if (!activeConversationId && newConvId) {
        setActiveConversationId(newConvId);
      }

      // Add assistant response
      const asstMsg = {
        id: newMsgId,
        role: 'assistant',
        content: asstContent,
        citations: asstCitations,
        confidence: confidence,
        insufficient_evidence: insufficientEvidence,
        created_at: new Date().toISOString(),
      };

      setMessages((prev) => [...prev, asstMsg]);
      setLastAssistantAnswer(asstContent);
      loadConversations();
    } catch (err) {
      console.error('Error sending chat or file:', err);
      const errDetail = err.response?.data?.detail || err.message;
      setErrorBanner(`MAYA could not process your request: ${errDetail}`);
    } finally {
      setIsLoading(false);
      setProcessingMediaType(null);
    }
  };

  // Open source details drawer
  const handleSelectSource = (citation) => {
    setSelectedSource(citation);
    setIsSourceDrawerOpen(true);
  };

  return (
    <div className="h-screen flex flex-col bg-warm-50 overflow-hidden font-sans">
      <Header
        isConnected={Boolean(healthStatus?.status === 'healthy')}
        isChecking={isCheckingHealth}
        appName={healthStatus?.application}
      />

      <div className="flex-1 flex overflow-hidden relative">
        {/* Sidebar */}
        <ConversationSidebar
          conversations={conversations}
          activeId={activeConversationId}
          onSelectConversation={handleSelectConversation}
          onNewConversation={handleNewConversation}
          onDeleteConversation={handleDeleteConversation}
          isOpen={isSidebarOpen}
          onToggleOpen={() => setIsSidebarOpen((prev) => !prev)}
        />

        {/* Main Chat Workspace */}
        <main className="flex-1 flex flex-col h-full overflow-hidden bg-white/70">
          {/* Subheader Toolbar */}
          <div className="px-6 py-2.5 border-b border-warm-200/80 bg-white/90 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <button
                type="button"
                onClick={() => setIsSidebarOpen((prev) => !prev)}
                title="Toggle Sidebar"
                className="p-1.5 rounded-lg text-charcoal-600 hover:text-charcoal-900 hover:bg-warm-100 transition-colors"
              >
                <PanelLeft className="w-4 h-4" />
              </button>
              <h2 className="text-xs font-bold text-charcoal-800 tracking-tight flex items-center gap-2">
                <span>Academic Q&A Workspace</span>
              </h2>
            </div>

            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={() => setIsVoiceModeOpen(true)}
                className="px-2.5 py-1 rounded-lg bg-crimson-50 text-crimson-900 border border-crimson-200 hover:bg-crimson-100 text-xs font-semibold flex items-center gap-1.5 transition-colors"
                title="Launch Turn-Based Voice Assistant"
              >
                <Radio className="w-3.5 h-3.5" />
                <span className="hidden sm:inline">Voice Assistant Mode</span>
              </button>

              <span className="text-[11px] font-semibold text-emerald-800 bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200">
                Grounded Multimodal
              </span>
            </div>
          </div>

          {/* Error Banner */}
          {errorBanner && (
            <div className="mx-6 mt-3 p-3 bg-red-50 border border-red-200 rounded-xl text-xs text-red-900 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <AlertCircle className="w-4 h-4 text-red-700 flex-shrink-0" />
                <span>{errorBanner}</span>
              </div>
              <button
                type="button"
                onClick={() => setErrorBanner(null)}
                className="text-xs font-bold text-red-800 hover:underline"
              >
                Dismiss
              </button>
            </div>
          )}

          {/* Messages Window */}
          <ChatWindow
            messages={messages}
            isLoading={isLoading}
            onSendMessage={handleSendMessage}
            onSelectSource={handleSelectSource}
          />

          {/* Multimodal Processing Indicator */}
          {isLoading && processingMediaType && (
            <div className="max-w-3xl mx-auto px-4 w-full">
              <ProcessingIndicator mediaType={processingMediaType} />
            </div>
          )}

          {/* Prompt Input */}
          <ChatInput
            onSendMessage={handleSendMessage}
            isLoading={isLoading}
            onOpenVoiceMode={() => setIsVoiceModeOpen(true)}
          />
        </main>
      </div>

      {/* Slide-out Source Details Drawer */}
      <SourceDrawer
        isOpen={isSourceDrawerOpen}
        onClose={() => setIsSourceDrawerOpen(false)}
        source={selectedSource}
      />

      {/* Turn-Based Voice Assistant Overlay Modal */}
      <VoiceMode
        isOpen={isVoiceModeOpen}
        onClose={() => setIsVoiceModeOpen(false)}
        onSendQuery={(spokenText) => handleSendMessage(spokenText)}
        lastAssistantAnswer={lastAssistantAnswer}
        isThinking={isLoading}
      />
    </div>
  );
}
