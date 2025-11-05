"""
Flow Data Storage - ChromaDB for storing test flow data
"""
import os
import asyncio
import json
from typing import Dict, Any

import chromadb
from chromadb.config import Settings
from mistralai import Mistral


class FlowDataStore:
    """Store ongoing test flow data in ChromaDB for efficient retrieval"""
    
    def __init__(self):
        self.persist_directory = "./data/flow_chroma_db"
        os.makedirs(self.persist_directory, exist_ok=True)
        
        self.client = chromadb.PersistentClient(
            path=self.persist_directory,
            settings=Settings(anonymized_telemetry=False, allow_reset=True)
        )
        
        # Initialize Mistral client for embeddings
        self.mistral_client = Mistral(api_key=os.getenv("MISTRAL_API_KEY"))
        self.embedding_model = "mistral-embed"
        
        # Create collection for this test session
        self.collection_name = f"test_flow_{int(asyncio.get_event_loop().time())}"
        try:
            self.collection = self.client.create_collection(name=self.collection_name)
        except:
            self.collection = self.client.get_collection(name=self.collection_name)
        
        print(f"[OK] Flow ChromaDB initialized: {self.collection_name}")
    
    def store_request(self, endpoint_key: str, request_payload: Dict[str, Any]):
        """Store request payload in ChromaDB"""
        doc_text = f"REQUEST for {endpoint_key}:\n{json.dumps(request_payload, indent=2)}"
        
        # Generate embedding using Mistral
        embeddings_response = self.mistral_client.embeddings.create(
            model=self.embedding_model,
            inputs=[doc_text]
        )
        embedding = embeddings_response.data[0].embedding
        
        # Store in ChromaDB
        self.collection.add(
            documents=[doc_text],
            embeddings=[embedding],
            metadatas=[{
                "type": "request",
                "endpoint": endpoint_key,
                "data": json.dumps(request_payload)
            }],
            ids=[f"{endpoint_key}_request"]
        )
        print(f"   [FLOPPY] Stored request in Flow DB: {endpoint_key}")
    
    def store_response(self, endpoint_key: str, response_data: Dict[str, Any]):
        """Store response data in ChromaDB"""
        doc_text = f"RESPONSE from {endpoint_key}:\n{json.dumps(response_data, indent=2)}"
        
        # Generate embedding using Mistral
        embeddings_response = self.mistral_client.embeddings.create(
            model=self.embedding_model,
            inputs=[doc_text]
        )
        embedding = embeddings_response.data[0].embedding
        
        # Store in ChromaDB
        self.collection.add(
            documents=[doc_text],
            embeddings=[embedding],
            metadatas=[{
                "type": "response",
                "endpoint": endpoint_key,
                "data": json.dumps(response_data)
            }],
            ids=[f"{endpoint_key}_response"]
        )
        print(f"   [FLOPPY] Stored response in Flow DB: {endpoint_key}")
    
    def query_for_fields(self, query: str, k: int = 3) -> str:
        """Query ChromaDB for relevant previous requests/responses"""
        # Generate query embedding using Mistral
        embeddings_response = self.mistral_client.embeddings.create(
            model=self.embedding_model,
            inputs=[query]
        )
        query_embedding = embeddings_response.data[0].embedding
        
        # Search ChromaDB
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=k
        )
        
        if not results['documents'] or not results['documents'][0]:
            return "No previous flow data found."
        
        # Combine relevant documents
        combined_text = "\n\n---\n\n".join(results['documents'][0])
        return combined_text
    
    def cleanup(self):
        """Clean up the test session collection"""
        try:
            self.client.delete_collection(name=self.collection_name)
            print(f"[DEL]  Cleaned up Flow DB: {self.collection_name}")
        except:
            pass


