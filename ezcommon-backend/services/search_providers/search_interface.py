"""Abstract base class for search providers"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional


class SearchProvider(ABC):
    """Abstract base class defining the interface for search providers"""
    
    @abstractmethod
    def initialize(self) -> None:
        """Initialize the search provider (e.g., create index, connect to database)"""
        pass
    
    @abstractmethod
    def store_document(self, document_id: str, document: Dict[str, Any]) -> bool:
        """
        Store a document with its chunks in the search provider
        
        Args:
            document_id: Unique identifier for the document
            document: Document data containing information_chunks, source_file, section, file_type
            
        Returns:
            True if successful, False otherwise
        """
        pass
    
    @abstractmethod
    def get_documents_by_user(self, user_id: str, section: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Retrieve full documents for a user
        
        Args:
            user_id: User ID
            section: Optional section filter (education, activity, testing, profile)
            
        Returns:
            List of documents
        """
        pass
    
    @abstractmethod
    def get_all_chunks_for_user(self, user_id: str, section: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Retrieve all chunks for a user, flattened across all documents
        
        Args:
            user_id: User ID
            section: Optional section filter (education, activity, testing, profile)
            
        Returns:
            List of flattened chunks with metadata
        """
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """Check if the search provider is available and connected"""
        pass
    
    @abstractmethod
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about the search provider (e.g., document count, storage used)"""
        pass
    
    @abstractmethod
    def get_provider_info(self) -> Dict[str, str]:
        """Get information about the provider (name, version, configuration)"""
        pass
