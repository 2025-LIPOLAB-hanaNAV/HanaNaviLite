const API_BASE_URL = 'http://localhost:8001/api/v1';

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