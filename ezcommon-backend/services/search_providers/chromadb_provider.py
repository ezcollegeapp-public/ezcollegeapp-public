"""ChromaDB implementation of SearchProvider"""

from typing import Dict, Any, List, Optional
from .search_interface import SearchProvider


class ChromaDBProvider(SearchProvider):
    """ChromaDB provider for document search and storage"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize ChromaDB provider
        
        Args:
            config: Configuration dictionary containing:
                - CHROMADB_DATA_DIR: Local data directory for ChromaDB
                - CHROMADB_COLLECTION_NAME: Collection name
        """
        self.data_dir = config.get('CHROMADB_DATA_DIR', './chroma_data')
        self.collection_name = config.get('CHROMADB_COLLECTION_NAME', 'document_chunks')
        
        self.client = None
        self.collection = None
        self._initialized = False
    
    def initialize(self) -> None:
        """Initialize ChromaDB client and collection"""
        try:
            import chromadb
            
            self.client = chromadb.PersistentClient(path=self.data_dir)
            self.collection = self.client.get_or_create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": "cosine"}
            )
            
            self._initialized = True
            print(f"✓ ChromaDB initialized: {self.data_dir}/{self.collection_name}")
        except ImportError:
            print("⚠ ChromaDB not installed. Install with: pip install chromadb")
            self._initialized = False
        except Exception as e:
            print(f"⚠ ChromaDB initialization failed: {e}")
            self._initialized = False
    
    def store_document(self, document_id: str, document: Dict[str, Any]) -> bool:
        """Store document in ChromaDB"""
        if not self.collection or not self._initialized:
            return False
        
        try:
            chunks = document.get('information_chunks', [])
            user_id = document.get('user_id', 'unknown')
            source_file = document.get('source_file', 'unknown')
            section = document.get('section', 'unknown')
            file_type = document.get('file_type', 'unknown')
            
            for idx, chunk in enumerate(chunks):
                chunk_id = f"{document_id}_chunk_{idx}"
                # Handle both 'content' field (semantic blocks) and 'text' field (naive chunks)
                content = chunk.get('content') or chunk.get('text', '')
                
                self.collection.add(
                    ids=[chunk_id],
                    documents=[content],
                    metadatas=[{
                        "user_id": user_id,
                        "source_file": source_file,
                        "section": section,
                        "file_type": file_type,
                        "category": chunk.get('category', ''),
                        "chunk_index": idx
                    }]
                )
            
            return True
        except Exception as e:
            print(f"Error storing document: {e}")
            return False
    
    def get_documents_by_user(self, user_id: str, section: Optional[str] = None) -> List[Dict[str, Any]]:
        """Retrieve documents for a user"""
        if not self.collection or not self._initialized:
            return []
        
        try:
            where = {"user_id": user_id}
            if section:
                where["section"] = section
            
            results = self.collection.get(where=where)
            
            documents = []
            for doc_id, metadata in zip(results['ids'], results['metadatas']):
                doc = {
                    '_id': doc_id,
                    'user_id': metadata.get('user_id'),
                    'source_file': metadata.get('source_file'),
                    'section': metadata.get('section'),
                    'file_type': metadata.get('file_type')
                }
                documents.append(doc)
            
            return documents
        except Exception as e:
            print(f"Error retrieving documents: {e}")
            return []
    
    def get_all_chunks_for_user(self, user_id: str, section: Optional[str] = None) -> List[Dict[str, Any]]:
        """Retrieve all chunks for a user"""
        if not self.collection or not self._initialized:
            return []
        
        try:
            where = {"user_id": user_id}
            if section:
                where["section"] = section
            
            results = self.collection.get(where=where)
            
            all_chunks = []
            for doc_content, metadata in zip(results['documents'], results['metadatas']):
                chunk = {
                    'content': doc_content,
                    'category': metadata.get('category', ''),
                    'chunk_index': metadata.get('chunk_index', 0),
                    'source_file': metadata.get('source_file', 'unknown'),
                    'section': metadata.get('section', 'unknown'),
                    'file_type': metadata.get('file_type', 'unknown')
                }
                all_chunks.append(chunk)
            
            return all_chunks
        except Exception as e:
            print(f"Error retrieving chunks: {e}")
            return []
    
    def is_available(self) -> bool:
        """Check if ChromaDB is available"""
        if not self.collection or not self._initialized:
            return False
        
        try:
            count = self.collection.count()
            return count >= 0
        except Exception:
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """Get ChromaDB statistics"""
        if not self.collection or not self._initialized:
            return {}
        
        try:
            count = self.collection.count()
            return {
                "provider": "ChromaDB",
                "collection": self.collection_name,
                "documents": count
            }
        except Exception as e:
            print(f"Error getting stats: {e}")
            return {}
    
    def get_provider_info(self) -> Dict[str, str]:
        """Get provider information"""
        return {
            "provider_name": "ChromaDB",
            "data_dir": self.data_dir,
            "collection": self.collection_name
        }
