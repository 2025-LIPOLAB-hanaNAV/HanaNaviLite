// Use relative URL when in production (served from same host), absolute URL for dev
const API_BASE_URL = window.location.hostname === 'localhost' && window.location.port === '8011'
  ? '/api/v1'  // Production mode - relative URL
  : 'http://localhost:8011/api/v1'; // Development mode - absolute URL

// Conversation APIs
export interface CreateSessionRequest {
  user_id?: string;
  title?: string;
  max_turns?: number;
  session_duration_hours?: number;
  metadata?: any;
}

export interface ConversationSession {
  session_id: string;
  title: string;
  max_turns: number;
  expires_at: string;
  created_at: string;
  user_id?: string;
  status?: string;
  current_topic?: string;
  turn_count?: number;
  updated_at?: string;
  dialog_state?: string;
  active_topics?: Array<{
    name: string;
    keywords: string[];
    confidence: number;
  }>;
}

export interface SendMessageRequest {
  message: string;
  search_engine_type?: string;
  include_context?: boolean;
  max_context_turns?: number;
}

export interface SendMessageResponse {
  session_id: string;
  turn_number: number;
  user_message: string;
  assistant_message: string;
  search_context?: any;
  context_explanation: string;
  response_time_ms: number;
  confidence_score?: number;
  dialog_state: string;
  current_topics: string[];
}

export interface ConversationTurn {
  turn_number: number;
  user_message: string;
  assistant_message: string;
  search_query?: string;
  context_used?: string;
  response_time_ms?: number;
  confidence_score?: number;
  created_at?: string;
  feedback_rating?: number;
  feedback_comment?: string;
}

// Statistics APIs
export interface UsageStatistics {
  total_queries: number;
  unique_users: number;
  avg_response_time_ms: number;
  successful_queries: number;
  failed_queries: number;
  total_sessions: number;
}

export interface PopularQuery {
  query_text: string;
  hit_count: number;
  last_hit_at: string;
}

export interface DocumentUsage {
  title: string;
  view_count: number;
  search_hit_count: number;
  last_accessed_at: string;
}

export interface SystemStatus {
  database_status: {
    status: string;
    database_path: string;
    documents_count: number;
    chunks_count: number;
    cache_count: number;
    database_size_mb: number;
    wal_mode: boolean;
  };
  faiss_status: {
    status: string;
  };
  message: string;
}

// Legacy APIs (keeping for backwards compatibility)
export interface QueryRequest {
  query: string;
  mode?: string;
  filters?: {
    department?: string;
    dateRange?: string;
    documentType?: string;
  };
}

export interface QueryResponse {
  answer: string;
  sources: Array<{
    id: string;
    title: string;
    content: string;
    score: number;
    metadata?: any;
  }>;
  responseTime: number;
  evidenceCount: number;
}

export interface HealthResponse {
  status: string;
  database: boolean;
  memory_usage: {
    used: number;
    available: number;
    percent: number;
  };
  system_info: any;
}

export const apiClient = {
  // Conversation APIs
  async createSession(request: CreateSessionRequest): Promise<ConversationSession> {
    const response = await fetch(`${API_BASE_URL}/conversation/sessions`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(request),
    });

    if (!response.ok) {
      throw new Error(`Create session failed: ${response.statusText}`);
    }

    return response.json();
  },

  async getSession(sessionId: string): Promise<ConversationSession> {
    const response = await fetch(`${API_BASE_URL}/conversation/sessions/${sessionId}`);
    
    if (!response.ok) {
      throw new Error(`Get session failed: ${response.statusText}`);
    }

    return response.json();
  },

  async sendMessage(sessionId: string, request: SendMessageRequest): Promise<SendMessageResponse> {
    const response = await fetch(`${API_BASE_URL}/conversation/sessions/${sessionId}/messages`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(request),
    });

    if (!response.ok) {
      throw new Error(`Send message failed: ${response.statusText}`);
    }

    return response.json();
  },

  async getConversationHistory(sessionId: string): Promise<{ session_id: string; turns: ConversationTurn[]; total_turns: number }> {
    const response = await fetch(`${API_BASE_URL}/conversation/sessions/${sessionId}/history`);
    
    if (!response.ok) {
      throw new Error(`Get conversation history failed: ${response.statusText}`);
    }

    return response.json();
  },

  async listSessions(): Promise<{ sessions: ConversationSession[]; total_count: number }> {
    const response = await fetch(`${API_BASE_URL}/conversation/sessions`);
    
    if (!response.ok) {
      throw new Error(`List sessions failed: ${response.statusText}`);
    }

    return response.json();
  },

  async submitFeedback(sessionId: string, turnNumber: number, rating: number, comment?: string): Promise<{ message: string }> {
    const params = new URLSearchParams({
      turn_number: turnNumber.toString(),
      rating: rating.toString(),
    });
    if (comment) {
      params.append('comment', comment);
    }

    const response = await fetch(`${API_BASE_URL}/conversation/sessions/${sessionId}/feedback?${params}`, {
      method: 'POST',
    });

    if (!response.ok) {
      throw new Error(`Submit feedback failed: ${response.statusText}`);
    }

    return response.json();
  },

  // Statistics APIs
  async getUsageStatistics(period: 'daily' | 'monthly' | 'total' = 'total', date?: string): Promise<UsageStatistics> {
    const params = new URLSearchParams({ period });
    if (date) {
      params.append('date', date);
    }

    const response = await fetch(`${API_BASE_URL}/stats/usage?${params}`);
    
    if (!response.ok) {
      throw new Error(`Get usage statistics failed: ${response.statusText}`);
    }

    return response.json();
  },

  async getPopularQueries(topK: number = 10): Promise<PopularQuery[]> {
    const response = await fetch(`${API_BASE_URL}/stats/popular_queries?top_k=${topK}`);
    
    if (!response.ok) {
      throw new Error(`Get popular queries failed: ${response.statusText}`);
    }

    return response.json();
  },

  async getDocumentUsage(topK: number = 10): Promise<DocumentUsage[]> {
    const response = await fetch(`${API_BASE_URL}/stats/document_usage?top_k=${topK}`);
    
    if (!response.ok) {
      throw new Error(`Get document usage failed: ${response.statusText}`);
    }

    return response.json();
  },

  // Admin APIs
  async getSystemStatus(): Promise<SystemStatus> {
    const response = await fetch(`${API_BASE_URL}/admin/system_status`);
    
    if (!response.ok) {
      throw new Error(`Get system status failed: ${response.statusText}`);
    }

    return response.json();
  },

  async clearCache(): Promise<{ message: string; status: string }> {
    const response = await fetch(`${API_BASE_URL}/admin/clear_cache`, {
      method: 'POST',
    });

    if (!response.ok) {
      throw new Error(`Clear cache failed: ${response.statusText}`);
    }

    return response.json();
  },

  async reindexDocuments(documentIds?: number[]): Promise<{ message: string; status: string }> {
    const params = documentIds ? `?${documentIds.map(id => `document_ids=${id}`).join('&')}` : '';
    
    const response = await fetch(`${API_BASE_URL}/admin/reindex_documents${params}`, {
      method: 'POST',
    });

    if (!response.ok) {
      throw new Error(`Reindex documents failed: ${response.statusText}`);
    }

    return response.json();
  },

  // Legacy APIs (keeping for backwards compatibility)
  async query(request: QueryRequest): Promise<QueryResponse> {
    const response = await fetch(`${API_BASE_URL}/rag/query`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(request),
    });

    if (!response.ok) {
      throw new Error(`API request failed: ${response.statusText}`);
    }

    return response.json();
  },

  async uploadFile(file: File): Promise<{ message: string; file_id: string }> {
    const formData = new FormData();
    formData.append('file', file);

    const response = await fetch(`${API_BASE_URL}/upload`, {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      throw new Error(`File upload failed: ${response.statusText}`);
    }

    return response.json();
  },

  async getHealth(): Promise<HealthResponse> {
    const response = await fetch(`${API_BASE_URL}/health`);
    
    if (!response.ok) {
      throw new Error(`Health check failed: ${response.statusText}`);
    }

    return response.json();
  },

  async getDocuments(): Promise<Array<{ id: string; name: string; type: string; uploadedAt: string }>> {
    const response = await fetch(`${API_BASE_URL}/documents`);
    
    if (!response.ok) {
      throw new Error(`Get documents failed: ${response.statusText}`);
    }

    return response.json();
  }
};