/**
 * Types for partner onboarding flow
 */

export enum OnboardingStep {
  COMPANY_INFO = 0,
  DOCUMENT_UPLOAD = 1,
  PARSING_PROGRESS = 2,
  OCR_REVIEW = 3,
  INTEGRATION_REVIEW = 4,
  API_TESTING = 5,  // NEW: Automated API testing
  ACTIVATION = 6,   // Moved from 5 to 6
}

export interface CompanyInfo {
  companyName: string;
  companyEmail: string;
  contactName: string;
  contactEmail: string;
  contactPhone?: string;
  website?: string;
  address?: string;
}

export interface DocumentUploadInfo {
  files: File[];
  uploadProgress: number;
  uploadedDocIds: string[];
}

export interface ParsingProgress {
  docId: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  progress: number;
  message?: string;
  format?: string;
  endpoints?: number;
}

export interface IntegrationReview {
  partnerId: string;
  apiSpec: {
    baseUrl: string;
    endpoints: Array<{
      path: string;
      method: string;
      summary?: string;
    }>;
    auth?: any;
  };
  workflows: Array<{
    name: string;
    description: string;
  }>;
  generatedCode?: string;
}

export interface TestResult {
  endpoint: string;
  method: string;
  status: 'passed' | 'failed' | 'retrying';
  attemptNumber: number;
  responseTime: number;
  errorMessage?: string;
  testCaseName?: string;
}

export interface APITestingProgress {
  testExecutionId: string;
  status: 'analyzing' | 'testing' | 'retrying' | 'completed' | 'completed_with_failures' | 'failed';
  currentPhase: string;
  currentEndpoint?: string;
  totalEndpoints: number;
  testedEndpoints: number;
  passedTests: number;
  failedTests: number;
  dependencyGraph?: Record<string, string[]>;
  executionOrder?: string[];
  testResults: TestResult[];
}

export interface OnboardingState {
  currentStep: OnboardingStep;
  companyInfo?: CompanyInfo;
  documentInfo?: DocumentUploadInfo;
  parsingProgress?: ParsingProgress[];
  integrationReview?: IntegrationReview;
  apiTestingProgress?: APITestingProgress;
  partnerId?: string;
  tenantId?: string;
  isComplete: boolean;
}

