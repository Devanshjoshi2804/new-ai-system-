/**
 * Chat API client
 * Handles communication with the autonomous AI execution backend
 */
import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || '/api';

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: Date;
  intent?: string;
  entities?: Record<string, any>;
  apiCalls?: Array<{
    endpoint: string;
    method: string;
    status: string;
    response?: any;
  }>;
}

export interface SendMessageRequest {
  message: string;
  sessionId?: string;
}

export interface SendMessageResponse {
  response: string;
  intent?: string;
  entities?: Record<string, any>;
  api_calls?: Array<any>;
  success: boolean;
  session_id?: string;
}

export interface ChatCapabilities {
  partner_name: string;
  integration_active: boolean;
  available_operations: string[];
  example_commands: string[];
}

class ChatAPI {
  private tenantId: string | null = null;

  setTenantId(tenantId: string) {
    this.tenantId = tenantId;
  }

  private getHeaders() {
    return {
      'Content-Type': 'application/json',
      ...(this.tenantId && { 'X-Tenant-ID': this.tenantId }),
    };
  }

  async sendMessage(request: SendMessageRequest): Promise<SendMessageResponse> {
    try {
      const response = await axios.post<SendMessageResponse>(
        `${API_BASE_URL}/chat/message`,
        request,
        { headers: this.getHeaders() }
      );
      return response.data;
    } catch (error: any) {
      throw new Error(error.response?.data?.detail || 'Failed to send message');
    }
  }

  async getCapabilities(): Promise<ChatCapabilities> {
    try {
      const response = await axios.get<ChatCapabilities>(
        `${API_BASE_URL}/chat/capabilities`,
        { headers: this.getHeaders() }
      );
      return response.data;
    } catch (error: any) {
      throw new Error(error.response?.data?.detail || 'Failed to get capabilities');
    }
  }
}

export const chatAPI = new ChatAPI();

