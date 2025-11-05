/**
 * Simple Testing API Client - Clean and effective
 */
import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';

export interface TestRequest {
  partnerId: string;
  documentationId: string;
  baseUrl?: string;
}

export interface TestResult {
  endpoint: string;
  url?: string;
  status_code: number;
  success: boolean;
  attempts: number;
  final_payload: Record<string, any>;
  response?: Record<string, any> | string; // Can be JSON object or HTML string
  error?: string;
}

export interface TestResponse {
  status: string;
  total_tests: number;
  passed: number;
  failed: number;
  pass_rate: number;
  execution_time: number;
  base_url: string;
  results: TestResult[];
  started_at: string;
  completed_at: string;
}

class SimpleTestingAPI {
  /**
   * Start simple, effective API testing
   */
  async startTest(request: TestRequest): Promise<TestResponse> {
    try {
      // Convert camelCase to snake_case for backend
      const payload = {
        partner_id: request.partnerId,
        documentation_id: request.documentationId,
        base_url: request.baseUrl,
      };
      
      console.log('🚀 Starting simple test:', payload);
      
      const response = await axios.post(`${API_BASE_URL}/simple-testing/test`, payload);
      
      console.log('✅ Test complete:', response.data);
      
      return response.data;
    } catch (error: any) {
      console.error('❌ Test failed:', error);
      throw new Error(error.response?.data?.detail || error.message || 'Test execution failed');
    }
  }

  /**
   * Check health of testing service
   */
  async checkHealth(): Promise<any> {
    try {
      const response = await axios.get(`${API_BASE_URL}/simple-testing/health`);
      return response.data;
    } catch (error: any) {
      console.error('❌ Health check failed:', error);
      throw new Error(error.message);
    }
  }
}

export const simpleTestingAPI = new SimpleTestingAPI();
