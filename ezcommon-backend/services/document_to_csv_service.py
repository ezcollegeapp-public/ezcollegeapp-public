"""
Service for generating CSV files from parsed documents stored in OpenSearch
"""
import os
import csv
import io
from typing import Dict, Any, List, Optional
from datetime import datetime
from opensearchpy import OpenSearch, RequestsHttpConnection
from requests_aws4auth import AWS4Auth
import boto3


class DocumentToCSVService:
    """Service for converting parsed documents to CSV format"""
    
    def __init__(self):
        """Initialize the service with OpenSearch connection"""
        # OpenSearch configuration
        self.opensearch_host = os.environ.get('OPENSEARCH_HOST')
        self.opensearch_region = os.environ.get('OPENSEARCH_REGION', 'us-east-1')
        self.index_name = os.environ.get('OPENSEARCH_INDEX', 'document_chunks')
        self.opensearch_port = int(os.environ.get('OPENSEARCH_PORT', 443))
        
        # Initialize OpenSearch client
        self.opensearch_client = self._get_opensearch_client()
    
    def _get_opensearch_client(self):
        """Initialize OpenSearch client with AWS authentication"""
        if not self.opensearch_host:
            raise ValueError("OpenSearch host not configured")
        
        # Get AWS credentials
        aws_access_key = os.environ.get('AWS_ACCESS_KEY_ID')
        aws_secret_key = os.environ.get('AWS_SECRET_ACCESS_KEY')
        
        awsauth = AWS4Auth(
            aws_access_key,
            aws_secret_key,
            self.opensearch_region,
            'es'
        )
        
        client = OpenSearch(
            hosts=[{'host': self.opensearch_host, 'port': self.opensearch_port}],
            http_auth=awsauth,
            use_ssl=True,
            verify_certs=True,
            connection_class=RequestsHttpConnection
        )
        return client
    
    def get_user_documents(self, user_id: str, section: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Retrieve all documents for a user from OpenSearch
        
        Args:
            user_id: User ID
            section: Optional section filter (education, activity, testing, profile)
            
        Returns:
            List of document dictionaries
        """
        query = {
            "query": {
                "bool": {
                    "must": [
                        {"term": {"user_id": user_id}}
                    ]
                }
            },
            "size": 1000  # Adjust as needed
        }
        
        # Add section filter if provided
        if section:
            query["query"]["bool"]["must"].append({"term": {"section": section}})
        
        try:
            response = self.opensearch_client.search(
                index=self.index_name,
                body=query
            )
            
            documents = []
            for hit in response['hits']['hits']:
                documents.append(hit['_source'])
            
            return documents
        except Exception as e:
            print(f"Error retrieving documents: {str(e)}")
            return []
    
    def extract_structured_data(self, documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Extract structured data from document chunks
        
        Args:
            documents: List of document dictionaries from OpenSearch
            
        Returns:
            List of structured data rows for CSV
        """
        rows = []
        
        for doc in documents:
            source_file = doc.get('source_file', 'Unknown')
            file_type = doc.get('file_type', 'Unknown')
            section = doc.get('section', 'Unknown')
            extraction_timestamp = doc.get('extraction_timestamp', '')
            
            # Get information chunks
            chunks = doc.get('information_chunks', [])
            
            for chunk in chunks:
                row = {
                    'Source File': source_file,
                    'File Type': file_type,
                    'Section': section,
                    'Category': chunk.get('category', ''),
                    'Chunk Type': chunk.get('chunk_type', ''),
                    'Content': chunk.get('text', ''),
                    'Extraction Date': extraction_timestamp
                }
                rows.append(row)
        
        return rows
    
    def generate_csv_content(self, rows: List[Dict[str, Any]]) -> str:
        """
        Generate CSV content from structured data rows
        
        Args:
            rows: List of data rows
            
        Returns:
            CSV content as string
        """
        if not rows:
            return ""
        
        # Create CSV in memory
        output = io.StringIO()
        
        # Get field names from first row
        fieldnames = list(rows[0].keys())
        
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
        
        csv_content = output.getvalue()
        output.close()
        
        return csv_content
    
    def generate_summary_csv(self, user_id: str, section: Optional[str] = None) -> Dict[str, Any]:
        """
        Generate a summary CSV with key information extracted from documents
        
        Args:
            user_id: User ID
            section: Optional section filter
            
        Returns:
            Dictionary with CSV content and metadata
        """
        # Get documents
        documents = self.get_user_documents(user_id, section)
        
        if not documents:
            return {
                'status': 'error',
                'message': 'No documents found for this user',
                'csv_content': '',
                'total_documents': 0,
                'total_chunks': 0
            }
        
        # Extract structured data
        rows = self.extract_structured_data(documents)
        
        # Generate CSV
        csv_content = self.generate_csv_content(rows)
        
        return {
            'status': 'success',
            'csv_content': csv_content,
            'total_documents': len(documents),
            'total_chunks': len(rows),
            'section': section or 'all',
            'generated_at': datetime.now().isoformat()
        }
    
    def generate_categorized_csv(self, user_id: str, section: Optional[str] = None) -> Dict[str, Any]:
        """
        Generate a CSV organized by categories with aggregated information
        
        Args:
            user_id: User ID
            section: Optional section filter
            
        Returns:
            Dictionary with CSV content and metadata
        """
        # Get documents
        documents = self.get_user_documents(user_id, section)
        
        if not documents:
            return {
                'status': 'error',
                'message': 'No documents found for this user',
                'csv_content': '',
                'total_documents': 0
            }
        
        # Organize by category
        category_data = {}
        
        for doc in documents:
            chunks = doc.get('information_chunks', [])
            source_file = doc.get('source_file', 'Unknown')
            section_name = doc.get('section', 'Unknown')
            
            for chunk in chunks:
                category = chunk.get('category', 'uncategorized')
                text = chunk.get('text', '')
                
                if category not in category_data:
                    category_data[category] = []
                
                category_data[category].append({
                    'Category': category,
                    'Information': text,
                    'Source File': source_file,
                    'Section': section_name
                })
        
        # Flatten to rows
        rows = []
        for category, items in category_data.items():
            for item in items:
                rows.append(item)
        
        # Generate CSV
        csv_content = self.generate_csv_content(rows)
        
        return {
            'status': 'success',
            'csv_content': csv_content,
            'total_documents': len(documents),
            'total_categories': len(category_data),
            'categories': list(category_data.keys()),
            'section': section or 'all',
            'generated_at': datetime.now().isoformat()
        }
    
    def get_statistics(self, user_id: str, section: Optional[str] = None) -> Dict[str, Any]:
        """
        Get statistics about user's parsed documents
        
        Args:
            user_id: User ID
            section: Optional section filter
            
        Returns:
            Dictionary with statistics
        """
        documents = self.get_user_documents(user_id, section)
        
        if not documents:
            return {
                'total_documents': 0,
                'total_chunks': 0,
                'categories': [],
                'sections': [],
                'file_types': []
            }
        
        # Collect statistics
        categories = set()
        sections = set()
        file_types = set()
        total_chunks = 0
        
        for doc in documents:
            sections.add(doc.get('section', 'Unknown'))
            file_types.add(doc.get('file_type', 'Unknown'))
            
            chunks = doc.get('information_chunks', [])
            total_chunks += len(chunks)
            
            for chunk in chunks:
                categories.add(chunk.get('category', 'uncategorized'))
        
        return {
            'total_documents': len(documents),
            'total_chunks': total_chunks,
            'categories': sorted(list(categories)),
            'sections': sorted(list(sections)),
            'file_types': sorted(list(file_types))
        }

