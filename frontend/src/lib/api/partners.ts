/**
 * Partners API client
 */
import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || '/api';

export interface RegisterPartnerRequest {
  company_name: string;
  company_email: string;
  contact_name: string;
  contact_email: string;
  contact_phone?: string;
  website?: string;
  address?: string;
}

export interface RegisterPartnerResponse {
  id: string;
  tenant_id: string;
  company_name: string;
  company_email: string;
  status: string;
  created_at: string;
}

export interface UploadDocumentResponse {
  documentation_id: string;  // Backend returns 'documentation_id'
  id?: string;  // Keep for backwards compatibility
  partner_id: string;
  filename: string;
  file_name?: string;
  file_size: number;
  detected_format: string;
  format?: string;
  format_confidence: number;
  upload_date?: string;
  created_at: string;
  status: string;
}

export interface ParseDocumentResponse {
  id: string;
  status: string;
  format: string;
  api_spec: any;
  workflows: any[];
}

export interface AnalyzeDocumentResponse {
  id: string;
  status: string;
  message: string;
  api_spec: any;
  endpoints_found: number;
}

class PartnersAPI {
  async registerPartner(data: RegisterPartnerRequest): Promise<RegisterPartnerResponse> {
    try {
      const response = await axios.post<RegisterPartnerResponse>(
        `${API_BASE_URL}/partners/register`,
        data
      );
      return response.data;
    } catch (error: any) {
      throw new Error(error.response?.data?.detail || 'Failed to register partner');
    }
  }

  async uploadDocumentation(partnerId: string, file: File): Promise<UploadDocumentResponse> {
    try {
      const formData = new FormData();
      formData.append('file', file);

      const response = await axios.post<UploadDocumentResponse>(
        `${API_BASE_URL}/partners/${partnerId}/documentation`,
        formData,
        {
          headers: {
            'Content-Type': 'multipart/form-data',
          },
        }
      );
      return response.data;
    } catch (error: any) {
      throw new Error(error.response?.data?.detail || 'Failed to upload documentation');
    }
  }

  async parseDocumentation(docId: string): Promise<ParseDocumentResponse> {
    try {
      const response = await axios.post<ParseDocumentResponse>(
        `${API_BASE_URL}/documentation/${docId}/parse`
      );
      return response.data;
    } catch (error: any) {
      throw new Error(error.response?.data?.detail || 'Failed to parse documentation');
    }
  }

  async analyzeDocumentation(docId: string): Promise<AnalyzeDocumentResponse> {
    try {
      const response = await axios.post<AnalyzeDocumentResponse>(
        `${API_BASE_URL}/documentation/${docId}/analyze`
      );
      return response.data;
    } catch (error: any) {
      throw new Error(error.response?.data?.detail || 'Failed to analyze documentation');
    }
  }

  async analyzeMultipleDocuments(docIds: string[]): Promise<AnalyzeDocumentResponse> {
    try {
      const response = await axios.post<AnalyzeDocumentResponse>(
        `${API_BASE_URL}/documentation/analyze-multiple`,
        docIds
      );
      return response.data;
    } catch (error: any) {
      throw new Error(error.response?.data?.detail || 'Failed to analyze multiple documents');
    }
  }

  async getPartner(partnerId: string): Promise<any> {
    try {
      const response = await axios.get(`${API_BASE_URL}/partners/${partnerId}`);
      return response.data;
    } catch (error: any) {
      throw new Error(error.response?.data?.detail || 'Failed to get partner');
    }
  }
}

export const partnersAPI = new PartnersAPI();

