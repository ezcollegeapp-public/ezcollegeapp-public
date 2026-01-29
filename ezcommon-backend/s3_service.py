"""
S3 Service for file uploads
Handles uploading user files to AWS S3
"""
import os
import uuid
from typing import List, Optional, Dict, Any
from datetime import datetime
import boto3
from botocore.exceptions import ClientError, EndpointConnectionError
from aws_config import AWS_REGION, get_s3_client

# S3 Configuration
S3_BUCKET_NAME = os.environ.get("S3_BUCKET_NAME", "ezcommon-uploads")
S3_UPLOAD_PREFIX = os.environ.get("S3_UPLOAD_PREFIX", "user-uploads")


class S3Service:
    """Service for managing file uploads to S3"""
    
    def __init__(self):
        self.s3_client = get_s3_client()
        self.bucket_name = S3_BUCKET_NAME
        self.region = AWS_REGION
    
    def ensure_bucket_exists(self) -> bool:
        """
        Ensure the S3 bucket exists, create if it doesn't
        Returns True if bucket exists or was created successfully
        """
        try:
            # Check if bucket exists
            self.s3_client.head_bucket(Bucket=self.bucket_name)
            print(f"Bucket {self.bucket_name} already exists")
            return True
        except EndpointConnectionError as e:
            # Avoid crashing the app when S3 isn't reachable (e.g., offline/local dev)
            print(f"Error connecting to S3 endpoint: {e}")
            return False
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == '404':
                # Bucket doesn't exist, create it
                try:
                    if self.region == 'us-east-1':
                        # us-east-1 doesn't need LocationConstraint
                        self.s3_client.create_bucket(Bucket=self.bucket_name)
                    else:
                        self.s3_client.create_bucket(
                            Bucket=self.bucket_name,
                            CreateBucketConfiguration={'LocationConstraint': self.region}
                        )
                    
                    # Enable versioning (optional but recommended)
                    self.s3_client.put_bucket_versioning(
                        Bucket=self.bucket_name,
                        VersioningConfiguration={'Status': 'Enabled'}
                    )
                    
                    # Set CORS configuration to allow frontend access
                    cors_configuration = {
                        'CORSRules': [{
                            'AllowedHeaders': ['*'],
                            'AllowedMethods': ['GET', 'PUT', 'POST', 'DELETE', 'HEAD'],
                            'AllowedOrigins': ['*'],  # In production, specify your domain
                            'ExposeHeaders': ['ETag'],
                            'MaxAgeSeconds': 3000
                        }]
                    }
                    self.s3_client.put_bucket_cors(
                        Bucket=self.bucket_name,
                        CORSConfiguration=cors_configuration
                    )
                    
                    print(f"Created bucket {self.bucket_name}")
                    return True
                except ClientError as create_error:
                    print(f"Error creating bucket: {create_error}")
                    return False
            else:
                print(f"Error checking bucket: {e}")
                return False
        except Exception as e:
            # Catch-all to keep the app running even if S3 setup fails
            print(f"Unexpected error checking bucket: {e}")
            return False
    
    def upload_file(
        self,
        file_content: bytes,
        filename: str,
        user_id: str,
        section: str,
        content_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Upload a file to S3
        
        Args:
            file_content: File content as bytes
            filename: Original filename
            user_id: User ID for organizing files
            section: Section (profile, education, activity, testing)
            content_type: MIME type of the file
        
        Returns:
            Dict with file metadata including S3 key and URL
        """
        # Generate unique filename to avoid collisions
        file_extension = os.path.splitext(filename)[1]
        unique_filename = f"{uuid.uuid4()}{file_extension}"
        
        # Construct S3 key: user-uploads/{user_id}/{section}/{unique_filename}
        s3_key = f"{S3_UPLOAD_PREFIX}/{user_id}/{section}/{unique_filename}"
        
        # Prepare upload parameters
        upload_params = {
            'Bucket': self.bucket_name,
            'Key': s3_key,
            'Body': file_content,
        }
        
        if content_type:
            upload_params['ContentType'] = content_type
        
        # Add metadata
        upload_params['Metadata'] = {
            'original_filename': filename,
            'user_id': user_id,
            'section': section,
            'upload_timestamp': datetime.utcnow().isoformat()
        }
        
        try:
            # Upload to S3
            self.s3_client.put_object(**upload_params)
            
            # Generate URL (presigned URL for private files, or public URL if bucket is public)
            file_url = self.generate_presigned_url(s3_key)
            
            return {
                'success': True,
                'filename': filename,
                'unique_filename': unique_filename,
                's3_key': s3_key,
                'url': file_url,
                'size': len(file_content),
                'section': section,
                'uploaded_at': datetime.utcnow().isoformat()
            }
        except ClientError as e:
            print(f"Error uploading file to S3: {e}")
            return {
                'success': False,
                'error': str(e),
                'filename': filename
            }
    
    def generate_presigned_url(self, s3_key: str, expiration: int = 3600) -> str:
        """
        Generate a presigned URL for accessing a file
        
        Args:
            s3_key: S3 object key
            expiration: URL expiration time in seconds (default 1 hour)
        
        Returns:
            Presigned URL string
        """
        try:
            url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': self.bucket_name,
                    'Key': s3_key
                },
                ExpiresIn=expiration
            )
            return url
        except ClientError as e:
            print(f"Error generating presigned URL: {e}")
            return ""
    
    def list_user_files(self, user_id: str, section: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        List all files for a user, optionally filtered by section
        
        Args:
            user_id: User ID
            section: Optional section filter
        
        Returns:
            List of file metadata dictionaries
        """
        prefix = f"{S3_UPLOAD_PREFIX}/{user_id}/"
        if section:
            prefix += f"{section}/"
        
        try:
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=prefix
            )
            
            files = []
            if 'Contents' in response:
                for obj in response['Contents']:
                    # Get object metadata
                    head_response = self.s3_client.head_object(
                        Bucket=self.bucket_name,
                        Key=obj['Key']
                    )
                    
                    metadata = head_response.get('Metadata', {})
                    
                    files.append({
                        'filename': metadata.get('original_filename', os.path.basename(obj['Key'])),
                        's3_key': obj['Key'],
                        'size': obj['Size'],
                        'last_modified': obj['LastModified'].isoformat(),
                        'url': self.generate_presigned_url(obj['Key']),
                        'section': metadata.get('section', '')
                    })
            
            return files
        except ClientError as e:
            print(f"Error listing files: {e}")
            return []
    
    def delete_file(self, s3_key: str) -> bool:
        """
        Delete a file from S3
        
        Args:
            s3_key: S3 object key
        
        Returns:
            True if successful, False otherwise
        """
        try:
            self.s3_client.delete_object(
                Bucket=self.bucket_name,
                Key=s3_key
            )
            return True
        except ClientError as e:
            print(f"Error deleting file: {e}")
            return False
    
    def get_file_metadata(self, s3_key: str) -> Optional[Dict[str, Any]]:
        """
        Get metadata for a specific file
        
        Args:
            s3_key: S3 object key
        
        Returns:
            File metadata dictionary or None if not found
        """
        try:
            response = self.s3_client.head_object(
                Bucket=self.bucket_name,
                Key=s3_key
            )
            
            metadata = response.get('Metadata', {})
            
            return {
                'filename': metadata.get('original_filename', os.path.basename(s3_key)),
                's3_key': s3_key,
                'size': response['ContentLength'],
                'content_type': response.get('ContentType', ''),
                'last_modified': response['LastModified'].isoformat(),
                'url': self.generate_presigned_url(s3_key),
                'metadata': metadata
            }
        except ClientError as e:
            print(f"Error getting file metadata: {e}")
            return None


# Singleton instance
_s3_service = None


def get_s3_service() -> S3Service:
    """Get or create S3Service singleton instance"""
    global _s3_service
    if _s3_service is None:
        _s3_service = S3Service()
    return _s3_service
