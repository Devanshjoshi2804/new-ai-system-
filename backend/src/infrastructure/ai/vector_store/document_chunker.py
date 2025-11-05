"""
Document chunking service for Vector DB
Intelligently splits API documentation into semantic chunks
"""
import re
from typing import List, Dict, Any
from dataclasses import dataclass


@dataclass
class DocumentChunk:
    """Represents a chunk of documentation with metadata"""
    text: str
    metadata: Dict[str, Any]
    chunk_id: str


class DocumentChunker:
    """Intelligent document chunking for API documentation"""
    
    def __init__(self, max_chunk_size: int = 1000, overlap: int = 200):
        self.max_chunk_size = max_chunk_size
        self.overlap = overlap
        
    def chunk_by_api_sections(self, text: str, doc_id: str) -> List[DocumentChunk]:
        """
        Split documentation by API endpoints and sections
        
        Args:
            text: Full documentation text
            doc_id: Document identifier
            
        Returns:
            List of DocumentChunk objects
        """
        chunks = []
        
        # Try to split by common API documentation patterns
        # Pattern 1: Endpoint definitions (e.g., "POST /api/endpoint")
        endpoint_pattern = r'((?:GET|POST|PUT|DELETE|PATCH)\s+/[^\s\n]+)'
        sections = re.split(endpoint_pattern, text)
        
        chunk_id = 0
        current_endpoint = None
        
        for i, section in enumerate(sections):
            if not section.strip():
                continue
                
            # Check if this is an endpoint header
            if re.match(endpoint_pattern, section.strip()):
                current_endpoint = section.strip()
                continue
            
            # Process the content after an endpoint
            if current_endpoint:
                # Extract metadata from the section
                metadata = self.extract_metadata(section, current_endpoint)
                
                # Split large sections into smaller chunks
                sub_chunks = self._split_large_section(section, current_endpoint, metadata)
                
                for sub_chunk in sub_chunks:
                    chunks.append(DocumentChunk(
                        text=sub_chunk,
                        metadata=metadata,
                        chunk_id=f"{doc_id}_chunk_{chunk_id}"
                    ))
                    chunk_id += 1
                    
                current_endpoint = None
            else:
                # General content without endpoint context
                metadata = self.extract_metadata(section, None)
                sub_chunks = self._split_large_section(section, None, metadata)
                
                for sub_chunk in sub_chunks:
                    chunks.append(DocumentChunk(
                        text=sub_chunk,
                        metadata=metadata,
                        chunk_id=f"{doc_id}_chunk_{chunk_id}"
                    ))
                    chunk_id += 1
        
        return chunks
    
    def chunk_by_semantic_blocks(self, text: str, doc_id: str) -> List[DocumentChunk]:
        """
        Split by semantic blocks (paragraphs, sections)
        
        Args:
            text: Full documentation text
            doc_id: Document identifier
            
        Returns:
            List of DocumentChunk objects
        """
        chunks = []
        
        # Split by double newlines (paragraphs)
        paragraphs = re.split(r'\n\s*\n', text)
        
        current_chunk = ""
        chunk_id = 0
        
        for paragraph in paragraphs:
            paragraph = paragraph.strip()
            if not paragraph:
                continue
            
            # If adding this paragraph exceeds max size, save current chunk
            if len(current_chunk) + len(paragraph) > self.max_chunk_size and current_chunk:
                metadata = self.extract_metadata(current_chunk, None)
                chunks.append(DocumentChunk(
                    text=current_chunk,
                    metadata=metadata,
                    chunk_id=f"{doc_id}_chunk_{chunk_id}"
                ))
                chunk_id += 1
                
                # Start new chunk with overlap
                overlap_text = current_chunk[-self.overlap:] if len(current_chunk) > self.overlap else current_chunk
                current_chunk = overlap_text + "\n\n" + paragraph
            else:
                current_chunk += "\n\n" + paragraph if current_chunk else paragraph
        
        # Add final chunk
        if current_chunk:
            metadata = self.extract_metadata(current_chunk, None)
            chunks.append(DocumentChunk(
                text=current_chunk,
                metadata=metadata,
                chunk_id=f"{doc_id}_chunk_{chunk_id}"
            ))
        
        return chunks
    
    def extract_metadata(self, chunk: str, endpoint: str = None) -> Dict[str, Any]:
        """
        Extract metadata from a chunk
        
        Args:
            chunk: Text chunk
            endpoint: Optional endpoint (e.g., "POST /api/endpoint")
            
        Returns:
            Metadata dictionary
        """
        metadata = {}
        
        # Extract endpoint info
        if endpoint:
            parts = endpoint.split()
            if len(parts) >= 2:
                metadata['method'] = parts[0]
                metadata['path'] = parts[1]
        else:
            # Try to find endpoint in chunk
            endpoint_match = re.search(r'(GET|POST|PUT|DELETE|PATCH)\s+(/[^\s\n]+)', chunk)
            if endpoint_match:
                metadata['method'] = endpoint_match.group(1)
                metadata['path'] = endpoint_match.group(2)
        
        # Extract field names (common patterns)
        field_patterns = [
            r'"([a-zA-Z_][a-zA-Z0-9_]*)":\s*',  # JSON field names
            r'`([a-zA-Z_][a-zA-Z0-9_]*)`',  # Markdown code
            r'\b([a-zA-Z_][a-zA-Z0-9_]*)\s*:\s*(?:string|number|boolean|object|array)',  # Type definitions
        ]
        
        fields = set()
        for pattern in field_patterns:
            matches = re.findall(pattern, chunk)
            fields.update(matches)
        
        if fields:
            metadata['fields'] = list(fields)
        
        # Extract requirements/validation keywords
        requirement_keywords = ['required', 'mandatory', 'must', 'validation', 'constraint']
        found_requirements = [kw for kw in requirement_keywords if kw.lower() in chunk.lower()]
        if found_requirements:
            metadata['has_requirements'] = True
            metadata['requirement_keywords'] = found_requirements
        
        # Extract examples
        if 'example' in chunk.lower() or '"' in chunk or '{' in chunk:
            metadata['has_examples'] = True
        
        # Extract error codes
        error_codes = re.findall(r'\b[4-5]\d{2}\b', chunk)
        if error_codes:
            metadata['error_codes'] = list(set(error_codes))
        
        # Chunk size
        metadata['chunk_size'] = len(chunk)
        
        return metadata
    
    def _split_large_section(self, section: str, endpoint: str = None, metadata: Dict = None) -> List[str]:
        """
        Split a large section into smaller chunks
        
        Args:
            section: Text section
            endpoint: Optional endpoint
            metadata: Optional metadata
            
        Returns:
            List of chunk strings
        """
        if len(section) <= self.max_chunk_size:
            # Add endpoint context if available
            if endpoint:
                return [f"{endpoint}\n\n{section}"]
            return [section]
        
        # Split by sentences
        sentences = re.split(r'(?<=[.!?])\s+', section)
        
        chunks = []
        current_chunk = endpoint + "\n\n" if endpoint else ""
        
        for sentence in sentences:
            if len(current_chunk) + len(sentence) > self.max_chunk_size and current_chunk:
                chunks.append(current_chunk)
                
                # Start new chunk with overlap and endpoint
                overlap_text = current_chunk[-self.overlap:] if len(current_chunk) > self.overlap else current_chunk
                current_chunk = overlap_text + " " + sentence
            else:
                current_chunk += " " + sentence if current_chunk and not current_chunk.endswith("\n\n") else sentence
        
        if current_chunk:
            chunks.append(current_chunk)
        
        return chunks

