"""OpenSearch implementation of SearchProvider"""

from typing import Dict, Any, List, Optional
from .search_interface import SearchProvider
import boto3
from opensearchpy import OpenSearch, RequestsHttpConnection
from requests_aws4auth import AWS4Auth


class OpenSearchProvider(SearchProvider):
    """OpenSearch provider for document search and storage"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize OpenSearch provider
        
        Args:
            config: Configuration dictionary containing:
                - OPENSEARCH_HOST: OpenSearch domain endpoint
                - OPENSEARCH_REGION: AWS region
                - OPENSEARCH_INDEX: Index name
                - OPENSEARCH_PORT: Port number
        """
        self.host = config.get('OPENSEARCH_HOST')
        self.region = config.get('OPENSEARCH_REGION', 'us-east-1')
        self.index_name = config.get('OPENSEARCH_INDEX', 'document_chunks')
        self.port = config.get('OPENSEARCH_PORT', 443)
        
        self.client = None
        self._initialized = False
    
    def initialize(self) -> None:
        """Initialize OpenSearch client and create index if needed"""
        if not self.host:
            print("⚠ OpenSearch host not configured")
            return
        
        try:
            self.client = self._create_client()
            self._create_index_if_not_exists()
            self._initialized = True
            print(f"✓ OpenSearch initialized: {self.host}/{self.index_name}")
        except Exception as e:
            print(f"⚠ OpenSearch initialization failed: {e}")
            self._initialized = False
    
    def _create_client(self) -> OpenSearch:
        """Create and return OpenSearch client with AWS authentication"""
        credentials = boto3.Session().get_credentials()
        
        awsauth = AWS4Auth(
            credentials.access_key,
            credentials.secret_key,
            self.region,
            'es',
            session_token=credentials.token
        )
        
        client = OpenSearch(
            hosts=[{'host': self.host, 'port': self.port}],
            http_auth=awsauth,
            use_ssl=True,
            verify_certs=True,
            connection_class=RequestsHttpConnection,
            timeout=5
        )
        
        # Test connection
        client.info()
        return client
    
    def _create_index_if_not_exists(self) -> None:
        """Create OpenSearch index if it doesn't exist"""
        if not self.client:
            return
        
        try:
            if not self.client.indices.exists(self.index_name):
                self.client.indices.create(
                    index=self.index_name,
                    body={
                        "settings": {
                            "number_of_shards": 1,
                            "number_of_replicas": 1
                        },
                        "mappings": {
                            "properties": {
                                "user_id": {"type": "keyword"},
                                "source_file": {"type": "keyword"},
                                "section": {"type": "keyword"},
                                "file_type": {"type": "keyword"},
                                "information_chunks": {
                                    "type": "nested",
                                    "properties": {
                                        "content": {"type": "text"},
                                        "category": {"type": "keyword"},
                                        "chunk_index": {"type": "integer"}
                                    }
                                }
                            }
                        }
                    }
                )
                print(f"✓ Index '{self.index_name}' created")
        except Exception as e:
            print(f"⚠ Error creating index: {e}")
    
    def store_document(self, document_id: str, document: Dict[str, Any]) -> bool:
        """Store document in OpenSearch"""
        if not self.client or not self._initialized:
            return False
        
        try:
            self.client.index(
                index=self.index_name,
                id=document_id,
                body=document
            )
            return True
        except Exception as e:
            print(f"Error storing document: {e}")
            return False
    
    def get_documents_by_user(self, user_id: str, section: Optional[str] = None) -> List[Dict[str, Any]]:
        """Retrieve documents for a user"""
        if not self.client or not self._initialized:
            return []
        
        try:
            query = {
                "bool": {
                    "must": [{"term": {"user_id": user_id}}]
                }
            }
            
            if section:
                query["bool"]["must"].append({"term": {"section": section}})
            
            response = self.client.search(
                index=self.index_name,
                body={"query": query, "size": 100}
            )
            
            documents = []
            for hit in response['hits']['hits']:
                doc = hit['_source']
                doc['_id'] = hit['_id']
                documents.append(doc)
            
            return documents
        except Exception as e:
            print(f"Error retrieving documents: {e}")
            return []
    
    def get_all_chunks_for_user(self, user_id: str, section: Optional[str] = None) -> List[Dict[str, Any]]:
        """Retrieve all chunks for a user"""
        if not self.client or not self._initialized:
            return []
        
        try:
            query = {
                "bool": {
                    "must": [{"term": {"user_id": user_id}}]
                }
            }
            
            if section:
                query["bool"]["must"].append({"term": {"section": section}})
            
            response = self.client.search(
                index=self.index_name,
                body={
                    "query": query,
                    "size": 100,
                    "_source": ["information_chunks", "source_file", "section", "file_type"]
                }
            )
            
            all_chunks = []
            for hit in response['hits']['hits']:
                doc = hit['_source']
                chunks = doc.get('information_chunks', [])
                
                for chunk in chunks:
                    chunk['source_file'] = doc.get('source_file', 'unknown')
                    chunk['section'] = doc.get('section', 'unknown')
                    chunk['file_type'] = doc.get('file_type', 'unknown')
                    all_chunks.append(chunk)
            
            return all_chunks
        except Exception as e:
            print(f"Error retrieving chunks: {e}")
            return []
    
    def is_available(self) -> bool:
        """Check if OpenSearch is available"""
        if not self.client or not self._initialized:
            return False
        
        try:
            self.client.info()
            return True
        except Exception:
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """Get OpenSearch statistics"""
        if not self.client or not self._initialized:
            return {}
        
        try:
            stats = self.client.indices.stats(index=self.index_name)
            return {
                "provider": "OpenSearch",
                "index": self.index_name,
                "documents": stats['indices'][self.index_name]['primaries']['docs']['count']
            }
        except Exception as e:
            print(f"Error getting stats: {e}")
            return {}
    
    def get_provider_info(self) -> Dict[str, str]:
        """Get provider information"""
        return {
            "provider_name": "OpenSearch",
            "host": self.host,
            "region": self.region,
            "index": self.index_name,
            "port": str(self.port)
        }
