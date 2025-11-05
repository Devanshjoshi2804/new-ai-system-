/**
 * Vector DB API Client
 * Handles all Vector DB related API calls
 */

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

export interface VectorDBStats {
  total_chunks: number;
  total_chars: number;
  unique_documents: number;
  collection_name: string;
  embedding_model: string;
}

export interface VectorDBHealthResponse {
  status: 'healthy' | 'disabled' | 'error';
  message: string;
  stats?: VectorDBStats;
  config?: {
    embedding_model: string;
    collection_name: string;
    persist_directory: string;
  };
}

export interface VectorDBQueryResult {
  id: string;
  text: string;
  metadata: Record<string, any>;
  distance?: number;
}

export interface VectorDBQueryResponse {
  success: boolean;
  query: string;
  results_count: number;
  results: VectorDBQueryResult[];
}

export interface VectorDBStatsResponse {
  success: boolean;
  doc_id?: string;
  stats: VectorDBStats;
}

export interface EndpointContextResponse {
  success: boolean;
  endpoint: string;
  context: string;
  context_size: number;
}

/**
 * Check Vector DB health status
 */
export async function getVectorDBHealth(): Promise<VectorDBHealthResponse> {
  const response = await fetch(`${API_BASE_URL}/api/vector-db/health`, {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
    },
  });

  if (!response.ok) {
    throw new Error(`Failed to check Vector DB health: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Query Vector DB for relevant documentation
 */
export async function queryVectorDB(
  queryText: string,
  docId?: string,
  topK: number = 3
): Promise<VectorDBQueryResponse> {
  const response = await fetch(`${API_BASE_URL}/api/vector-db/query`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      query_text: queryText,
      doc_id: docId,
      top_k: topK,
    }),
  });

  if (!response.ok) {
    throw new Error(`Failed to query Vector DB: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Get Vector DB statistics for a specific document
 */
export async function getVectorDBStats(docId: string): Promise<VectorDBStatsResponse> {
  const response = await fetch(`${API_BASE_URL}/api/vector-db/stats/${docId}`, {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
    },
  });

  if (!response.ok) {
    throw new Error(`Failed to get Vector DB stats: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Get overall Vector DB statistics
 */
export async function getAllVectorDBStats(): Promise<VectorDBStatsResponse> {
  const response = await fetch(`${API_BASE_URL}/api/vector-db/stats`, {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
    },
  });

  if (!response.ok) {
    throw new Error(`Failed to get Vector DB stats: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Get focused context for a specific API endpoint
 */
export async function getEndpointContext(
  endpointPath: string,
  method?: string,
  docId?: string,
  topK: number = 3
): Promise<EndpointContextResponse> {
  const params = new URLSearchParams({
    endpoint_path: endpointPath,
    top_k: topK.toString(),
  });

  if (method) {
    params.append('method', method);
  }

  if (docId) {
    params.append('doc_id', docId);
  }

  const response = await fetch(
    `${API_BASE_URL}/api/vector-db/endpoint-context?${params.toString()}`,
    {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    }
  );

  if (!response.ok) {
    throw new Error(`Failed to get endpoint context: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Delete a document from Vector DB
 */
export async function deleteFromVectorDB(docId: string): Promise<{ success: boolean; message: string }> {
  const response = await fetch(`${API_BASE_URL}/api/vector-db/${docId}`, {
    method: 'DELETE',
    headers: {
      'Content-Type': 'application/json',
    },
  });

  if (!response.ok) {
    throw new Error(`Failed to delete from Vector DB: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Store documentation in Vector DB manually
 */
export async function storeInVectorDB(
  docId: string,
  docText: string,
  metadata?: Record<string, any>
): Promise<{
  success: boolean;
  doc_id: string;
  chunks_stored: number;
  total_chars: number;
  collection_name: string;
}> {
  const response = await fetch(`${API_BASE_URL}/api/vector-db/store`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      doc_id: docId,
      doc_text: docText,
      metadata,
    }),
  });

  if (!response.ok) {
    throw new Error(`Failed to store in Vector DB: ${response.statusText}`);
  }

  return response.json();
}
