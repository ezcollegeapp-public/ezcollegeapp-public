"""Search Providers Package - Abstraction layer for different search backends"""

from .search_interface import SearchProvider
from .factory import SearchProviderFactory

__all__ = ['SearchProvider', 'SearchProviderFactory']
