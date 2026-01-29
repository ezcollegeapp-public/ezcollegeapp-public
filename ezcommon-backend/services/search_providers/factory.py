"""Factory for creating search provider instances"""

from typing import Dict, Any
from .search_interface import SearchProvider


class SearchProviderFactory:
    """Factory for creating search provider instances based on configuration"""
    
    @staticmethod
    def create(config: Dict[str, Any]) -> SearchProvider:
        """
        Create a search provider instance based on configuration
        
        Args:
            config: Configuration dictionary with:
                - SEARCH_PROVIDER: 'opensearch' or 'chromadb'
                - Other provider-specific settings
                
        Returns:
            SearchProvider instance
            
        Raises:
            ValueError: If provider type is not supported
        """
        provider_type = config.get('SEARCH_PROVIDER', 'opensearch').lower()
        
        if provider_type == 'opensearch':
            from .opensearch_provider import OpenSearchProvider
            return OpenSearchProvider(config)
        
        elif provider_type == 'chromadb':
            from .chromadb_provider import ChromaDBProvider
            return ChromaDBProvider(config)
        
        else:
            raise ValueError(
                f"Unsupported search provider: {provider_type}. "
                f"Supported providers: opensearch, chromadb"
            )
