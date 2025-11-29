"""
Abstract Repository Constructor Framework

Provides a unified, polymorphic approach to building both Planner and Knowledge repositories.
This framework harmonizes document processing, embedding generation, and storage patterns
across different repository types.

Repository Types:
- Planner Repositories: Store execution patterns and strategies
- Knowledge Repositories: Store reference documents and domain knowledge

Key Abstractions:
- RepositoryConstructor: Base class defining common construction pipeline
- DocumentProcessor: Handles chunking, parsing, metadata extraction
- EmbeddingStrategy: Configurable embedding generation
- StorageAdapter: Manages persistence to ChromaDB and file system
"""

import json
import logging
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from enum import Enum
import hashlib
import uuid

from chromadb.utils import embedding_functions

logger = logging.getLogger("repository_constructor")


class RepositoryType(Enum):
    """Types of repositories supported by the system."""
    PLANNER = "planner"  # Execution patterns and strategies
    KNOWLEDGE = "knowledge"  # Reference documents and domain knowledge


class ChunkingStrategy(Enum):
    """Document chunking strategies for Knowledge repositories."""
    FIXED_SIZE = "fixed_size"  # Fixed character/token count
    SEMANTIC = "semantic"  # Semantic boundary detection
    PARAGRAPH = "paragraph"  # Paragraph-based
    SENTENCE = "sentence"  # Sentence-based
    NONE = "none"  # No chunking (for Planner repos)


class DocumentChunk:
    """Represents a chunk of a document with metadata."""
    
    def __init__(self, content: str, metadata: Dict[str, Any], chunk_index: int = 0):
        self.content = content
        self.metadata = metadata
        self.chunk_index = chunk_index
        self.chunk_id = self._generate_chunk_id()
    
    def _generate_chunk_id(self) -> str:
        """Generate a unique ID for this chunk."""
        content_hash = hashlib.sha256(self.content.encode()).hexdigest()[:16]
        doc_id = self.metadata.get('document_id', 'unknown')
        return f"{doc_id}_chunk_{self.chunk_index}_{content_hash}"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            'chunk_id': self.chunk_id,
            'content': self.content,
            'metadata': self.metadata,
            'chunk_index': self.chunk_index
        }


class DocumentProcessor:
    """Handles document processing with configurable chunking strategies."""
    
    def __init__(self, chunking_strategy: ChunkingStrategy = ChunkingStrategy.SEMANTIC,
                 chunk_size: int = 1000, chunk_overlap: int = 200):
        self.chunking_strategy = chunking_strategy
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
    
    def process_document(self, content: str, metadata: Dict[str, Any]) -> List[DocumentChunk]:
        """
        Process a document into chunks based on the configured strategy.
        
        Args:
            content: Document text content
            metadata: Document metadata (filename, source, etc.)
            
        Returns:
            List of DocumentChunk objects
        """
        if self.chunking_strategy == ChunkingStrategy.NONE:
            # No chunking - return single chunk (for Planner repos)
            return [DocumentChunk(content, metadata, 0)]
        
        elif self.chunking_strategy == ChunkingStrategy.FIXED_SIZE:
            return self._chunk_fixed_size(content, metadata)
        
        elif self.chunking_strategy == ChunkingStrategy.PARAGRAPH:
            return self._chunk_by_paragraph(content, metadata)
        
        elif self.chunking_strategy == ChunkingStrategy.SENTENCE:
            return self._chunk_by_sentence(content, metadata)
        
        elif self.chunking_strategy == ChunkingStrategy.SEMANTIC:
            # For now, fall back to paragraph chunking
            # TODO: Implement semantic boundary detection
            return self._chunk_by_paragraph(content, metadata)
        
        else:
            raise ValueError(f"Unsupported chunking strategy: {self.chunking_strategy}")
    
    def _chunk_fixed_size(self, content: str, metadata: Dict[str, Any]) -> List[DocumentChunk]:
        """Chunk document into fixed-size pieces with overlap."""
        chunks = []
        start = 0
        chunk_index = 0
        
        while start < len(content):
            end = start + self.chunk_size
            chunk_text = content[start:end]
            
            chunk_metadata = metadata.copy()
            chunk_metadata['chunk_method'] = 'fixed_size'
            chunk_metadata['chunk_size'] = len(chunk_text)
            
            chunks.append(DocumentChunk(chunk_text, chunk_metadata, chunk_index))
            
            start += self.chunk_size - self.chunk_overlap
            chunk_index += 1
        
        return chunks
    
    def _chunk_by_paragraph(self, content: str, metadata: Dict[str, Any]) -> List[DocumentChunk]:
        """Chunk document by paragraphs. Preserves natural document structure."""
        # Split on double newlines to respect paragraph boundaries
        paragraphs = [p.strip() for p in content.split('\n\n') if p.strip()]
        
        # If we only got 1 huge paragraph, it might be a formatting issue - fall back to fixed-size
        if len(paragraphs) == 1 and len(paragraphs[0]) > self.chunk_size * 3:
            metadata_copy = metadata.copy()
            metadata_copy['fallback_reason'] = 'single_large_paragraph'
            return self._chunk_fixed_size(content, metadata_copy)
        
        chunks = []
        for idx, para in enumerate(paragraphs):
            chunk_metadata = metadata.copy()
            chunk_metadata['chunk_method'] = 'paragraph'
            chunk_metadata['paragraph_number'] = idx + 1
            
            chunks.append(DocumentChunk(para, chunk_metadata, idx))
        
        return chunks
    
    def _chunk_by_sentence(self, content: str, metadata: Dict[str, Any]) -> List[DocumentChunk]:
        """Chunk document by sentences."""
        # Simple sentence splitting (can be enhanced with NLP libraries)
        import re
        sentences = re.split(r'(?<=[.!?])\s+', content)
        chunks = []
        
        current_chunk = []
        current_size = 0
        chunk_index = 0
        
        for sentence in sentences:
            sentence_size = len(sentence)
            
            if current_size + sentence_size > self.chunk_size and current_chunk:
                # Create chunk from accumulated sentences
                chunk_text = ' '.join(current_chunk)
                chunk_metadata = metadata.copy()
                chunk_metadata['chunk_method'] = 'sentence'
                chunk_metadata['sentence_count'] = len(current_chunk)
                
                chunks.append(DocumentChunk(chunk_text, chunk_metadata, chunk_index))
                
                current_chunk = []
                current_size = 0
                chunk_index += 1
            
            current_chunk.append(sentence)
            current_size += sentence_size
        
        # Add remaining sentences
        if current_chunk:
            chunk_text = ' '.join(current_chunk)
            chunk_metadata = metadata.copy()
            chunk_metadata['chunk_method'] = 'sentence'
            chunk_metadata['sentence_count'] = len(current_chunk)
            
            chunks.append(DocumentChunk(chunk_text, chunk_metadata, chunk_index))
        
        return chunks


class EmbeddingStrategy:
    """Handles embedding generation with configurable models."""
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model_name = model_name
        self.embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name=model_name
        )
        logger.info(f"Initialized embedding strategy with model: {model_name}")
    
    def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for a list of texts."""
        return self.embedding_function(texts)


class StorageAdapter:
    """Manages persistence to ChromaDB and file system."""
    
    def __init__(self, chroma_client, storage_dir: Path):
        self.chroma_client = chroma_client
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
    
    def store_chunks(self, collection, chunks: List[DocumentChunk],
                    embedding_function) -> Dict[str, Any]:
        """
        Store document chunks in ChromaDB and optionally on file system.
        
        Returns:
            Dictionary with storage results
        """
        if not chunks:
            return {"status": "error", "message": "No chunks to store"}
        
        # Prepare data for ChromaDB
        ids = [chunk.chunk_id for chunk in chunks]
        documents = [chunk.content for chunk in chunks]
        metadatas = [chunk.metadata for chunk in chunks]
        
        # Store in ChromaDB
        collection.upsert(
            ids=ids,
            documents=documents,
            metadatas=metadatas
        )
        
        logger.info(f"Stored {len(chunks)} chunks in ChromaDB collection: {collection.name}")
        
        return {
            "status": "success",
            "chunks_stored": len(chunks),
            "collection_name": collection.name
        }
    
    def save_document_file(self, document_id: str, content: str, metadata: Dict[str, Any]) -> Path:
        """Save original document to file system for reference."""
        doc_file = self.storage_dir / f"doc_{document_id}.json"
        
        doc_data = {
            "document_id": document_id,
            "content": content,
            "metadata": metadata,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        
        with open(doc_file, 'w', encoding='utf-8') as f:
            json.dump(doc_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Saved document file: {doc_file}")
        return doc_file


class RepositoryConstructor(ABC):
    """
    Abstract base class for repository constructors.
    
    Defines the common pipeline for building repositories regardless of type.
    Subclasses implement type-specific behavior while reusing shared infrastructure.
    """
    
    def __init__(self, repository_type: RepositoryType, chroma_client, storage_dir: Path,
                 embedding_model: str = "all-MiniLM-L6-v2"):
        self.repository_type = repository_type
        self.chroma_client = chroma_client
        self.storage_dir = Path(storage_dir)
        self.embedding_strategy = EmbeddingStrategy(embedding_model)
        self.storage_adapter = StorageAdapter(chroma_client, storage_dir)
        
        # Configure document processor based on repository type
        if repository_type == RepositoryType.PLANNER:
            # Planner repos don't chunk - store complete execution traces
            self.document_processor = DocumentProcessor(ChunkingStrategy.NONE)
        else:
            # Knowledge repos use semantic chunking
            self.document_processor = DocumentProcessor(ChunkingStrategy.SEMANTIC)
    
    @abstractmethod
    def prepare_metadata(self, **kwargs) -> Dict[str, Any]:
        """Prepare repository-specific metadata. Implemented by subclasses."""
        pass
    
    @abstractmethod
    def validate_input(self, **kwargs) -> Tuple[bool, Optional[str]]:
        """Validate input data. Returns (is_valid, error_message)."""
        pass
    
    def construct(self, collection_id: int, content: str, **kwargs) -> Dict[str, Any]:
        """
        Main construction pipeline - processes and stores content in repository.
        
        Args:
            collection_id: Target collection ID
            content: Text content to process
            **kwargs: Additional metadata and configuration
            
        Returns:
            Dictionary with construction results
        """
        # Step 1: Validate input
        is_valid, error_msg = self.validate_input(content=content, **kwargs)
        if not is_valid:
            return {"status": "error", "message": error_msg}
        
        # Step 2: Prepare metadata
        metadata = self.prepare_metadata(
            collection_id=collection_id,
            repository_type=self.repository_type.value,
            **kwargs
        )
        
        # Step 3: Process document into chunks
        chunks = self.document_processor.process_document(content, metadata)
        logger.info(f"Processed document into {len(chunks)} chunk(s)")
        
        # Step 4: Get or create collection
        collection_name = kwargs.get('collection_name', f"collection_{collection_id}")
        collection = self.chroma_client.get_or_create_collection(
            name=collection_name,
            embedding_function=self.embedding_strategy.embedding_function,
            metadata={"repository_type": self.repository_type.value}
        )
        
        # Step 5: Store chunks
        result = self.storage_adapter.store_chunks(
            collection, chunks, self.embedding_strategy.embedding_function
        )
        
        # Step 6: Save original document if requested
        if kwargs.get('save_original', True):
            document_id = metadata.get('document_id', str(uuid.uuid4()))
            self.storage_adapter.save_document_file(document_id, content, metadata)
        
        result.update({
            "repository_type": self.repository_type.value,
            "collection_id": collection_id,
            "metadata": metadata
        })
        
        return result


class PlannerRepositoryConstructor(RepositoryConstructor):
    """Constructor for Planner Repositories - stores execution patterns."""
    
    def __init__(self, chroma_client, storage_dir: Path, embedding_model: str = "all-MiniLM-L6-v2"):
        super().__init__(RepositoryType.PLANNER, chroma_client, storage_dir, embedding_model)
    
    def prepare_metadata(self, **kwargs) -> Dict[str, Any]:
        """Prepare metadata for planner execution pattern."""
        return {
            "document_id": kwargs.get('case_id', str(uuid.uuid4())),
            "collection_id": kwargs['collection_id'],
            "repository_type": "planner",
            "user_query": kwargs.get('user_query', ''),
            "strategy_type": kwargs.get('strategy_type', 'unknown'),
            "mcp_server_id": kwargs.get('mcp_server_id'),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "is_most_efficient": kwargs.get('is_most_efficient', False),
            "output_tokens": kwargs.get('output_tokens', 0),
            "user_feedback_score": kwargs.get('user_feedback_score')
        }
    
    def validate_input(self, **kwargs) -> Tuple[bool, Optional[str]]:
        """Validate planner repository input."""
        content = kwargs.get('content', '')
        if not content or len(content) < 10:
            return False, "Content is required and must be at least 10 characters"
        
        if not kwargs.get('user_query'):
            return False, "user_query is required for planner repositories"
        
        return True, None


class KnowledgeRepositoryConstructor(RepositoryConstructor):
    """Constructor for Knowledge Repositories - stores reference documents."""
    
    def __init__(self, chroma_client, storage_dir: Path, embedding_model: str = "all-MiniLM-L6-v2",
                 chunking_strategy: ChunkingStrategy = ChunkingStrategy.SEMANTIC,
                 chunk_size: int = 1000, chunk_overlap: int = 200):
        super().__init__(RepositoryType.KNOWLEDGE, chroma_client, storage_dir, embedding_model)
        
        # Override document processor with Knowledge-specific configuration
        self.document_processor = DocumentProcessor(chunking_strategy, chunk_size, chunk_overlap)
    
    def prepare_metadata(self, **kwargs) -> Dict[str, Any]:
        """Prepare metadata for knowledge document."""
        # Convert tags list to comma-separated string for ChromaDB
        tags = kwargs.get('tags', [])
        tags_str = ','.join(tags) if isinstance(tags, list) else str(tags)
        
        return {
            "document_id": kwargs.get('document_id', str(uuid.uuid4())),
            "collection_id": kwargs['collection_id'],
            "repository_type": "knowledge",
            "filename": kwargs.get('filename', 'unknown'),
            "document_type": kwargs.get('document_type', 'text'),
            "source": kwargs.get('source', 'upload'),
            "title": kwargs.get('title', ''),
            "author": kwargs.get('author', ''),
            "tags": tags_str,
            "category": kwargs.get('category', ''),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "file_size": kwargs.get('file_size', 0),
            "page_count": kwargs.get('page_count', 0)
        }
    
    def validate_input(self, **kwargs) -> Tuple[bool, Optional[str]]:
        """Validate knowledge repository input."""
        content = kwargs.get('content', '')
        if not content or len(content) < 50:
            return False, "Content is required and must be at least 50 characters"
        
        filename = kwargs.get('filename', '')
        if not filename:
            return False, "filename is required for knowledge repositories"
        
        return True, None


# Factory function for creating appropriate constructor
def create_repository_constructor(repository_type: RepositoryType, chroma_client,
                                  storage_dir: Path, **config) -> RepositoryConstructor:
    """
    Factory function to create appropriate constructor based on repository type.
    
    Args:
        repository_type: Type of repository to construct
        chroma_client: ChromaDB client instance
        storage_dir: Directory for file storage
        **config: Additional configuration options
        
    Returns:
        Appropriate RepositoryConstructor instance
    """
    if repository_type == RepositoryType.PLANNER:
        return PlannerRepositoryConstructor(
            chroma_client, storage_dir,
            embedding_model=config.get('embedding_model', 'all-MiniLM-L6-v2')
        )
    elif repository_type == RepositoryType.KNOWLEDGE:
        return KnowledgeRepositoryConstructor(
            chroma_client, storage_dir,
            embedding_model=config.get('embedding_model', 'all-MiniLM-L6-v2'),
            chunking_strategy=config.get('chunking_strategy', ChunkingStrategy.SEMANTIC),
            chunk_size=config.get('chunk_size', 1000),
            chunk_overlap=config.get('chunk_overlap', 200)
        )
    else:
        raise ValueError(f"Unsupported repository type: {repository_type}")
