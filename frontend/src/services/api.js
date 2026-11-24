import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'https://maya3-1.onrender.com';

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 60000,
  headers: {
    'Content-Type': 'application/json',
  },
});

/**
 * Check backend health status
 */
export const checkHealth = async () => {
  const response = await apiClient.get('/health');
  return response.data;
};

/**
 * Get v1 API status
 */
export const getApiStatus = async () => {
  const response = await apiClient.get('/api/v1/status');
  return response.data;
};

// ============================================================================
// NOTICE OPERATIONS
// ============================================================================

export const getNotices = async ({ skip = 0, limit = 20, category = '', search = '' } = {}) => {
  const params = { skip, limit };
  if (category) params.category = category;
  if (search) params.search = search;
  const response = await apiClient.get('/api/v1/notices', { params });
  return response.data;
};

export const getLatestNotices = async (limit = 10) => {
  const response = await apiClient.get('/api/v1/notices/latest', { params: { limit } });
  return response.data;
};

export const getNoticeById = async (noticeId) => {
  const response = await apiClient.get(`/api/v1/notices/${encodeURIComponent(noticeId)}`);
  return response.data;
};

// ============================================================================
// CRAWLER OPERATIONS
// ============================================================================

export const startCrawl = async ({ sources, max_pages_per_source = 5, download_pdfs = true } = {}) => {
  const payload = {
    max_pages_per_source,
    download_pdfs,
  };
  if (sources && sources.length > 0) {
    payload.sources = sources;
  }
  const response = await apiClient.post('/api/v1/crawl/start', payload);
  return response.data;
};

export const getCrawlStatus = async (jobId) => {
  const response = await apiClient.get(`/api/v1/crawl/status/${jobId}`);
  return response.data;
};

export const getCrawlHistory = async () => {
  const response = await apiClient.get('/api/v1/crawl/history');
  return response.data;
};

export const resumeCrawl = async (jobId) => {
  const response = await apiClient.post(`/api/v1/crawl/resume/${jobId}`);
  return response.data;
};

// ============================================================================
// INGESTION & DOCUMENT PROCESSING (MILESTONE 4)
// ============================================================================

export const startIngestion = async ({ batch_size = 10, force_reindex = false, force_reprocess = false } = {}) => {
  const reindex = Boolean(force_reindex || force_reprocess);
  const response = await apiClient.post('/api/v1/ingestion/start', {
    batch_size,
    force_reindex: reindex,
    force_reprocess: reindex,
  });
  return response.data;
};

export const getIngestionStatus = async (jobId) => {
  const response = await apiClient.get(`/api/v1/ingestion/status/${jobId}`);
  return response.data;
};

export const getIngestionStats = async () => {
  const response = await apiClient.get('/api/v1/ingestion/statistics');
  return response.data;
};

export const retryNoticeIngestion = async (noticeId) => {
  const response = await apiClient.post(`/api/v1/ingestion/retry/${encodeURIComponent(noticeId)}`);
  return response.data;
};

// ============================================================================
// SEMANTIC SEARCH (MILESTONE 4)
// ============================================================================

export const semanticSearch = async ({ query, top_k = 5, threshold = 0.15, category = null } = {}) => {
  const response = await apiClient.post('/api/v1/search/semantic', { query, top_k, threshold, category });
  return response.data;
};

// ============================================================================
// CONVERSATIONAL RAG CHAT (MILESTONE 5)
// ============================================================================

export const sendChatMessage = async ({ message, conversation_id = null, metadata = null }) => {
  const response = await apiClient.post(
    '/api/v1/chat/message',
    {
      message,
      conversation_id,
      metadata,
    },
    { timeout: 60000 }
  );
  return response.data;
};

export const getConversations = async (limit = 20) => {
  const response = await apiClient.get('/api/v1/chat/conversations', { params: { limit } });
  return response.data;
};

export const getConversation = async (conversationId) => {
  const response = await apiClient.get(`/api/v1/chat/conversations/${conversationId}`);
  return response.data;
};

export const deleteConversation = async (conversationId) => {
  const response = await apiClient.delete(`/api/v1/chat/conversations/${conversationId}`);
  return response.data;
};

export const getChatHealth = async () => {
  const response = await apiClient.get('/api/v1/chat/health');
  return response.data;
};

// ============================================================================
// MULTIMODAL INTERACTIONS (MILESTONE 6)
// ============================================================================

export const uploadImage = async ({ file, prompt = '', conversation_id = null }) => {
  const formData = new FormData();
  formData.append('file', file);
  if (prompt) {
    formData.append('prompt', prompt);
    formData.append('question', prompt);
  }
  if (conversation_id) formData.append('conversation_id', conversation_id);

  const response = await apiClient.post('/api/v1/multimodal/image', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 60000,
  });
  return response.data;
};

export const uploadDocument = async ({ file, prompt = '', conversation_id = null }) => {
  const formData = new FormData();
  formData.append('file', file);
  if (prompt) {
    formData.append('prompt', prompt);
    formData.append('question', prompt);
  }
  if (conversation_id) formData.append('conversation_id', conversation_id);

  const response = await apiClient.post('/api/v1/multimodal/document', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 60000,
  });
  return response.data;
};

export const uploadAudio = async ({ file, prompt = '', conversation_id = null }) => {
  const formData = new FormData();
  formData.append('file', file);
  if (prompt) {
    formData.append('prompt', prompt);
    formData.append('question', prompt);
  }
  if (conversation_id) formData.append('conversation_id', conversation_id);

  const response = await apiClient.post('/api/v1/multimodal/audio', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 90000,
  });
  return response.data;
};

export const getAttachmentUrl = (conversationId, filename) => {
  if (!conversationId || !filename) return '';
  return `${API_BASE_URL}/api/v1/multimodal/attachments/${encodeURIComponent(conversationId)}/${encodeURIComponent(filename)}`;
};

export default apiClient;
