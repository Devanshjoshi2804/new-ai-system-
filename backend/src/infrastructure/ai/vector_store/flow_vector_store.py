"""
Flow Vector Store - Semantic memory for test execution context
THE KEY COMPONENT that makes the system work with intelligent context awareness
"""
import chromadb
from mistralai import Mistral
import json
import os
from typing import Dict, Any, List, Optional
import logging
import re
from datetime import datetime
import asyncio

logger = logging.getLogger(__name__)


class FlowVectorStore:
    """
    Stores test execution flow data with semantic search
    
    This is the missing piece that enables:
    - Finding "token from login response"
    - Finding "plain password from signup REQUEST"
    - Finding "userId from user creation"
    - Context propagation across test executions
    
    Philosophy:
    - Every request/response stored with embeddings
    - Semantic search for finding related data
    - No context loss between tests
    - AI-friendly querying
    """
    
    def __init__(self, persist_dir: str = "./data/flow_chroma_db"):
        """
        Initialize Flow Vector Store
        
        Args:
            persist_dir: Directory to persist ChromaDB data
        """
        self.persist_directory = persist_dir
        
        # Ensure directory exists
        os.makedirs(self.persist_directory, exist_ok=True)
        
        # Initialize ChromaDB
        self.client = chromadb.PersistentClient(path=self.persist_directory)
        
        # Initialize Mistral for embeddings
        mistral_key = os.getenv("MISTRAL_API_KEY")
        if not mistral_key:
            logger.warning("[WARN]  MISTRAL_API_KEY not found, Flow Store will have limited functionality")
            self.mistral_client = None
        else:
            self.mistral_client = Mistral(api_key=mistral_key)
        
        self.embedding_model = "mistral-embed"
        
        # Create or get collection
        try:
            self.collection = self.client.get_collection(name="test_flow")
            logger.info("[OK] Using existing test_flow collection")
        except Exception as e:
            # Collection doesn't exist or error occurred
            logger.info(f"Collection not found ({e}), creating new one")
            try:
                self.collection = self.client.create_collection(
                    name="test_flow",
                    metadata={"description": "Test execution flow data"}
                )
                logger.info("[OK] Created new test_flow collection")
            except Exception as create_error:
                logger.error(f"Failed to create collection: {create_error}")
                raise RuntimeError(f"Could not initialize ChromaDB collection: {create_error}")
        
        # Compile regex patterns once for performance (Fix #3)
        self.field_patterns = [
            re.compile(r'"token":\s*"([^"]+)"', re.IGNORECASE),
            re.compile(r'"access_token":\s*"([^"]+)"', re.IGNORECASE),
            re.compile(r'"auth_token":\s*"([^"]+)"', re.IGNORECASE),
            re.compile(r'"password":\s*"([^"]+)"', re.IGNORECASE),
            re.compile(r'"userId":\s*"([^"]+)"', re.IGNORECASE),
            re.compile(r'"user_id":\s*"([^"]+)"', re.IGNORECASE),
            re.compile(r'"id":\s*"([^"]+)"', re.IGNORECASE),
            re.compile(r'"email":\s*"([^"]+)"', re.IGNORECASE),
            re.compile(r':\s*"([^"]+)"', re.IGNORECASE)  # Generic - last resort
        ]
        
        # Session tracking
        self.session_id = datetime.utcnow().isoformat()
        self.request_count = 0
        self.response_count = 0
        
        logger.info(f"[OK] FlowVectorStore initialized (session: {self.session_id})")
    
    def _sanitize_endpoint_key(self, endpoint_key: str) -> str:
        """Sanitize endpoint key for use as document ID (Fix #5)"""
        if not endpoint_key or not isinstance(endpoint_key, str):
            return "unknown_endpoint"
        
        # Replace special characters
        safe_key = endpoint_key.replace('/', '_').replace(' ', '_')
        # Keep only alphanumeric and underscores
        safe_key = ''.join(c for c in safe_key if c.isalnum() or c == '_')
        
        return safe_key[:100]  # Limit length
    
    async def _generate_embedding_with_retry(self, text: str, max_retries: int = 3) -> List[float]:
        """
        Generate embedding with retry logic for reliability (Fix #2)
        
        Args:
            text: Text to generate embedding for
            max_retries: Maximum number of retry attempts
            
        Returns:
            Embedding vector
            
        Raises:
            Exception: If all retries fail
        """
        for attempt in range(max_retries):
            try:
                embeddings_response = await asyncio.to_thread(
                    self.mistral_client.embeddings.create,
                    model=self.embedding_model,
                    inputs=[text]
                )
                return embeddings_response.data[0].embedding
            
            except Exception as e:
                if attempt == max_retries - 1:
                    # Final attempt failed
                    logger.error(f"Failed to generate embedding after {max_retries} attempts: {e}")
                    raise
                
                # Exponential backoff
                delay = 2 ** attempt
                logger.warning(f"Embedding attempt {attempt + 1} failed, retrying in {delay}s: {e}")
                await asyncio.sleep(delay)
        
        # Should never reach here
        raise RuntimeError("Embedding generation failed unexpectedly")
    
    async def store_request(self, endpoint_key: str, request_payload: Dict[str, Any]):
        """
        Store API request with embeddings for semantic search
        
        Args:
            endpoint_key: Endpoint identifier (e.g., "POST /api/signup")
            request_payload: The request payload that was sent
        """
        if not self.mistral_client:
            logger.debug("Skipping request storage (no Mistral client)")
            return
        
        # Validate inputs (Fix #5)
        if not endpoint_key or not isinstance(endpoint_key, str):
            logger.warning("Invalid endpoint_key, skipping storage")
            return
        
        if not isinstance(request_payload, dict):
            logger.warning(f"Invalid request_payload type: {type(request_payload)}, skipping")
            return
        
        try:
            # Sanitize endpoint_key
            safe_endpoint = self._sanitize_endpoint_key(endpoint_key)
            
            # Try to serialize payload
            try:
                payload_json = json.dumps(request_payload, indent=2, default=str)
            except Exception as e:
                logger.warning(f"Failed to serialize request_payload: {e}")
                return
            
            # Create document text
            doc_text = f"""REQUEST for {endpoint_key}:
{payload_json}

Endpoint: {endpoint_key}
Type: REQUEST
Session: {self.session_id}
"""
            
            # Generate embedding with retry (Fix #2)
            embedding = await self._generate_embedding_with_retry(doc_text)
            
            # Store in ChromaDB
            doc_id = f"{self.session_id}_req_{self.request_count}_{safe_endpoint}"
            
            self.collection.add(
                documents=[doc_text],
                embeddings=[embedding],
                metadatas=[{
                    "type": "request",
                    "endpoint": endpoint_key,
                    "session": self.session_id,
                    "timestamp": datetime.utcnow().isoformat()
                }],
                ids=[doc_id]
            )
            
            self.request_count += 1
            logger.debug(f"[INFO] Stored request for {endpoint_key} (count: {self.request_count})")
        
        except Exception as e:
            logger.error(f"Failed to store request: {e}", exc_info=True)
    
    async def store_response(self, endpoint_key: str, response_data: Dict[str, Any]):
        """
        Store API response with embeddings
        
        Args:
            endpoint_key: Endpoint identifier
            response_data: The response data received
        """
        if not self.mistral_client:
            logger.debug("Skipping response storage (no Mistral client)")
            return
        
        # Validate inputs (Fix #5)
        if not endpoint_key or not isinstance(endpoint_key, str):
            logger.warning("Invalid endpoint_key, skipping storage")
            return
        
        if not isinstance(response_data, dict):
            logger.warning(f"Invalid response_data type: {type(response_data)}, skipping")
            return
        
        try:
            # Sanitize endpoint_key
            safe_endpoint = self._sanitize_endpoint_key(endpoint_key)
            
            # Try to serialize response
            try:
                response_json = json.dumps(response_data, indent=2, default=str)
            except Exception as e:
                logger.warning(f"Failed to serialize response_data: {e}")
                return
            
            # Create document text
            doc_text = f"""RESPONSE from {endpoint_key}:
{response_json}

Endpoint: {endpoint_key}
Type: RESPONSE
Session: {self.session_id}
"""
            
            # Generate embedding with retry (Fix #2)
            embedding = await self._generate_embedding_with_retry(doc_text)
            
            # Store in ChromaDB
            doc_id = f"{self.session_id}_res_{self.response_count}_{safe_endpoint}"
            
            self.collection.add(
                documents=[doc_text],
                embeddings=[embedding],
                metadatas=[{
                    "type": "response",
                    "endpoint": endpoint_key,
                    "session": self.session_id,
                    "timestamp": datetime.utcnow().isoformat()
                }],
                ids=[doc_id]
            )
            
            self.response_count += 1
            logger.debug(f"[INFO] Stored response from {endpoint_key} (count: {self.response_count})")
        
        except Exception as e:
            logger.error(f"Failed to store response: {e}", exc_info=True)
    
    async def query(self, query_text: str, k: int = 3) -> str:
        """
        Semantic search across all stored requests/responses
        
        This is the KEY feature that enables:
        - "find token from login"
        - "get password used in signup"
        - "find userId from user creation"
        
        Args:
            query_text: Natural language query
            k: Number of results to return
            
        Returns:
            Concatenated text of top-k matching documents
        """
        if not self.mistral_client:
            logger.debug("Skipping query (no Mistral client)")
            return ""
        
        try:
            # Generate query embedding with retry (Fix #2)
            query_embedding = await self._generate_embedding_with_retry(query_text)
            
            # Query ChromaDB
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=k,
                where={"session": self.session_id}  # Only query current session
            )
            
            if results['documents'] and results['documents'][0]:
                context = "\n\n---\n\n".join(results['documents'][0])
                logger.debug(f"[SEARCH] Query '{query_text}' returned {len(results['documents'][0])} results")
                return context
            
            logger.debug(f"[SEARCH] Query '{query_text}' returned no results")
            return ""
        
        except Exception as e:
            logger.error(f"Query failed: {e}", exc_info=True)
            return ""
    
    async def get_field(self, field_query: str) -> Optional[str]:
        """
        Smart field extraction using semantic search
        
        This solves the password/token extraction problem:
        - get_field("token from login") → extracts actual token value
        - get_field("password from signup REQUEST") → gets plain password
        - get_field("userId from user creation") → gets user ID
        
        Args:
            field_query: Natural language description of field to extract
            
        Returns:
            Extracted field value or None
        """
        flow_data = await self.query(field_query, k=1)
        
        if not flow_data:
            logger.debug(f"[SEARCH] Field query '{field_query}' found no data")
            return None
        
        # Try to extract value using pre-compiled patterns (Fix #4)
        for pattern in self.field_patterns:
            match = pattern.search(flow_data)
            if match:
                value = match.group(1)
                logger.info(f"[OK] Extracted field value: {value[:20]}... from query: {field_query}")
                return value
        
        logger.debug(f"[SEARCH] Could not extract field from query: {field_query}")
        return None
    
    async def get_all_context(self, max_results: int = 10) -> str:
        """
        Get all context from current session
        
        Useful for understanding what has happened so far
        
        Args:
            max_results: Maximum number of entries to return
            
        Returns:
            All stored context as text
        """
        try:
            results = self.collection.get(
                where={"session": self.session_id},
                limit=max_results
            )
            
            if results['documents']:
                context = "\n\n---\n\n".join(results['documents'])
                logger.debug(f"[DOC] Retrieved {len(results['documents'])} context entries")
                return context
            
            return ""
        
        except Exception as e:
            logger.error(f"Failed to get all context: {e}", exc_info=True)
            return ""
    
    async def query_for_credentials(self, endpoint_key: str = "") -> Dict[str, Any]:
        """
        Query for credentials (tokens, passwords, IDs) relevant to an endpoint
        
        This enables smart test payload generation:
        - Find login tokens from previous login
        - Find plain passwords from signup REQUEST (not response)
        - Find user IDs from user creation
        - Find any credentials needed for dependent endpoints
        
        Args:
            endpoint_key: Optional endpoint context to narrow search
            
        Returns:
            Dictionary with found credentials
        """
        if not self.mistral_client:
            logger.debug("Skipping credentials query (no Mistral client)")
            return {}
        
        credentials = {}
        
        try:
            # Query for authentication tokens
            token_query = f"Find authentication token, bearer token, access token"
            if endpoint_key:
                token_query += f" needed for {endpoint_key}"
            
            token_data = await self.query(token_query, k=2)
            
            # Try to extract token
            token_patterns = [
                re.compile(r'"token":\s*"([^"]+)"', re.IGNORECASE),
                re.compile(r'"access_token":\s*"([^"]+)"', re.IGNORECASE),
                re.compile(r'"auth_token":\s*"([^"]+)"', re.IGNORECASE),
            ]
            
            for pattern in token_patterns:
                match = pattern.search(token_data)
                if match:
                    credentials['token'] = match.group(1)
                    logger.info(f"[OK] Found token for credentials")
                    break
            
            # Query for user IDs
            id_query = f"Find userId, user_id, vendorCode, customerId"
            if endpoint_key:
                id_query += f" for {endpoint_key}"
            
            id_data = await self.query(id_query, k=2)
            
            id_patterns = [
                re.compile(r'"userId":\s*"([^"]+)"', re.IGNORECASE),
                re.compile(r'"user_id":\s*"([^"]+)"', re.IGNORECASE),
                re.compile(r'"vendorCode":\s*"([^"]+)"', re.IGNORECASE),
                re.compile(r'"id":\s*"([^"]+)"', re.IGNORECASE),
            ]
            
            for pattern in id_patterns:
                match = pattern.search(id_data)
                if match:
                    credentials['userId'] = match.group(1)
                    logger.info(f"[OK] Found userId for credentials")
                    break
            
            # Query for passwords (from REQUEST, not response)
            pwd_query = "Find password from signup REQUEST or registration REQUEST"
            pwd_data = await self.query(pwd_query, k=1)
            
            pwd_pattern = re.compile(r'"password":\s*"([^"]+)"', re.IGNORECASE)
            match = pwd_pattern.search(pwd_data)
            if match:
                credentials['password'] = match.group(1)
                logger.info(f"[OK] Found password from REQUEST")
            
            logger.info(f"[INFO] Retrieved credentials: {list(credentials.keys())}")
            return credentials
            
        except Exception as e:
            logger.error(f"Failed to query credentials: {e}")
            return credentials
    
    async def query_for_dependencies(self, endpoint_key: str) -> str:
        """
        Query for data that the given endpoint might depend on
        
        Args:
            endpoint_key: Endpoint to find dependencies for
            
        Returns:
            Context text with relevant dependency data
        """
        if not self.mistral_client:
            return ""
        
        try:
            query = f"Find data, IDs, tokens, and fields from previous API calls that {endpoint_key} might need"
            context = await self.query(query, k=5)
            
            if context:
                logger.info(f"[OK] Found dependency context for {endpoint_key} ({len(context)} chars)")
            
            return context
            
        except Exception as e:
            logger.error(f"Failed to query dependencies: {e}")
            return ""
    
    def clear_session(self):
        """
        Clear all flow data for current session (Fix #1)
        
        Call this at the start of a new test run to ensure clean state
        """
        try:
            # Delete old session data from ChromaDB (Fix #1)
            old_session = self.session_id
            
            try:
                # Get all documents from old session
                old_docs = self.collection.get(where={"session": old_session})
                if old_docs and old_docs.get('ids'):
                    # Delete them
                    self.collection.delete(ids=old_docs['ids'])
                    logger.info(f"[DEL]  Deleted {len(old_docs['ids'])} documents from old session")
            except Exception as e:
                logger.warning(f"Failed to delete old session data: {e}")
            
            # Start new session
            self.session_id = datetime.utcnow().isoformat()
            self.request_count = 0
            self.response_count = 0
            
            logger.info(f"[INFO] Session cleared and reset: {self.session_id}")
        
        except Exception as e:
            logger.error(f"Failed to clear session: {e}", exc_info=True)
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics about stored data
        
        Returns:
            Statistics dictionary
        """
        try:
            total_count = self.collection.count()
            
            return {
                "session_id": self.session_id,
                "total_stored": total_count,
                "requests_stored": self.request_count,
                "responses_stored": self.response_count,
                "persist_directory": self.persist_directory
            }
        
        except Exception as e:
            logger.error(f"Failed to get stats: {e}", exc_info=True)
            return {}

