// API Client for HanaNaviLite Backend Integration

const API_BASE_URL = window.location.hostname === 'localhost' && window.location.port === '8011'
  ? '/api/v1'  // Production mode - relative URL
  : 'http://localhost:8011/api/v1'; // Development mode - absolute URL

// Types
export interface RAGQuery {
  query: string;
  top_k?: number;
  chunk_size?: number;
  chunk_overlap?: number;
}

export interface RAGResponse {
  answer: string;
  sources: Array<{
    content: string;
    metadata: {
      source: string;
      page?: number;
      section?: string;
    };
    score: number;
  }>;
  processing_time: number;
}

export interface ConversationSession {
  session_id: string;
  title: string;
  max_turns: number;
  expires_at: string;
  created_at: string;
}

export interface ConversationTurn {
  turn_id: string;
  session_id: string;
  query: string;
  response: string;
  sources: any[];
  created_at: string;
  processing_time: number;
}

export interface SessionListResponse {
  sessions: ConversationSession[];
  total: number;
  page: number;
  limit: number;
}

export interface SystemStats {
  total_queries: number;
  total_sessions: number;
  avg_response_time: number;
  system_uptime: string;
  cache_hit_rate?: number;
  last_updated: string;
}

export interface UsageStats {
  daily_queries: number;
  weekly_queries: number;
  monthly_queries: number;
  top_queries: Array<{
    query: string;
    count: number;
  }>;
  last_updated: string;
}

// API Client
class ApiClient {
  private baseUrl: string;

  constructor(baseUrl: string = API_BASE_URL) {
    this.baseUrl = baseUrl;
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const url = `${this.baseUrl}${endpoint}`;
    
    const config: RequestInit = {
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
      ...options,
    };

    try {
      const response = await fetch(url, config);
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      return await response.json();
    } catch (error) {
      console.error(`API request failed for ${endpoint}:`, error);
      throw error;
    }
  }

  // RAG Query Methods
  async ragQuery(query: RAGQuery): Promise<RAGResponse> {
    return this.request<RAGResponse>('/rag/query', {
      method: 'POST',
      body: JSON.stringify(query),
    });
  }

  // Conversation Session Methods
  async createSession(params: {
    title: string;
    max_turns?: number;
    session_duration_hours?: number;
  }): Promise<ConversationSession> {
    return this.request<ConversationSession>('/conversation/sessions', {
      method: 'POST',
      body: JSON.stringify(params),
    });
  }

  async getSession(sessionId: string): Promise<ConversationSession> {
    return this.request<ConversationSession>(`/conversation/sessions/${sessionId}`);
  }

  async listSessions(params?: {
    page?: number;
    limit?: number;
    order?: 'asc' | 'desc';
  }): Promise<SessionListResponse> {
    const searchParams = new URLSearchParams();
    if (params?.page) searchParams.set('page', params.page.toString());
    if (params?.limit) searchParams.set('limit', params.limit.toString());
    if (params?.order) searchParams.set('order', params.order);
    
    const query = searchParams.toString();
    return this.request<SessionListResponse>(`/conversation/sessions${query ? '?' + query : ''}`);
  }

  async deleteSession(sessionId: string): Promise<{ message: string }> {
    return this.request<{ message: string }>(`/conversation/sessions/${sessionId}`, {
      method: 'DELETE',
    });
  }

  // Conversation Turn Methods
  async addTurn(sessionId: string, query: string): Promise<ConversationTurn> {
    return this.request<ConversationTurn>(`/conversation/sessions/${sessionId}/turns`, {
      method: 'POST',
      body: JSON.stringify({ query }),
    });
  }

  async getTurns(sessionId: string): Promise<ConversationTurn[]> {
    return this.request<ConversationTurn[]>(`/conversation/sessions/${sessionId}/turns`);
  }

  // Statistics Methods
  async getSystemStats(): Promise<SystemStats> {
    return this.request<SystemStats>('/conversation/stats/system');
  }

  async getUsageStats(): Promise<UsageStats> {
    return this.request<UsageStats>('/conversation/stats/usage');
  }

  // Health Check
  async healthCheck(): Promise<{ status: string; timestamp: string }> {
    return this.request<{ status: string; timestamp: string }>('/health');
  }

  // File Upload Methods
  async uploadDocument(file: File): Promise<{ message: string; filename: string }> {
    const formData = new FormData();
    formData.append('file', file);

    const response = await fetch(`${this.baseUrl}/upload/document`, {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      throw new Error(`Upload failed: ${response.statusText}`);
    }

    return await response.json();
  }

  // Admin Methods
  async rebuildIndex(): Promise<{ message: string }> {
    return this.request<{ message: string }>('/admin/rebuild-index', {
      method: 'POST',
    });
  }

  async clearCache(): Promise<{ message: string }> {
    return this.request<{ message: string }>('/admin/clear-cache', {
      method: 'POST',
    });
  }
}

// Create and export default instance
export const apiClient = new ApiClient();
export default apiClient;