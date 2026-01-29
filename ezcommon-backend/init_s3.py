#!/usr/bin/env python3
"""
Initialize S3 bucket for EZ Common file uploads
Creates the S3 bucket and configures it for file storage
"""
import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from s3_service import get_s3_service


def main():
    """Initialize S3 bucket"""
    print("=" * 60)
    print("EZ Common S3 Bucket Initialization")
    print("=" * 60)
    print()
    
    # Get S3 service
    s3_service = get_s3_service()
    
    print(f"Bucket Name: {s3_service.bucket_name}")
    print(f"Region: {s3_service.region}")
    print()
    
    # Ensure bucket exists
    print("Checking/Creating S3 bucket...")
    if s3_service.ensure_bucket_exists():
        print("✅ S3 bucket is ready!")
        print()
        
        # Test upload
        print("Testing file upload...")
        test_content = b"This is a test file for EZ Common"
        result = s3_service.upload_file(
            file_content=test_content,
            filename="test.txt",
            user_id="test-user",
            section="profile",
            content_type="text/plain"
        )
        
        if result['success']:
            print("✅ Test upload successful!")
            print(f"   S3 Key: {result['s3_key']}")
            print(f"   URL: {result['url'][:80]}...")
            print()
            
            # Test listing
            print("Testing file listing...")
            files = s3_service.list_user_files(user_id="test-user", section="profile")
            print(f"✅ Found {len(files)} file(s)")
            print()
            
            # Clean up test file
            print("Cleaning up test file...")
            if s3_service.delete_file(result['s3_key']):
                print("✅ Test file deleted")
            print()
            
            print("=" * 60)
            print("S3 Initialization Complete!")
            print("=" * 60)
            print()
            print("Your S3 bucket is ready to accept file uploads.")
            print()
            print("Next steps:")
            print("1. Make sure your .env file has the correct AWS credentials")
            print("2. Start the API server: python auth_api.py")
            print("3. Test file uploads from the frontend")
            print()
        else:
            print(f"❌ Test upload failed: {result.get('error')}")
            sys.exit(1)
    else:
        print("❌ Failed to initialize S3 bucket")
        print()
        print("Please check:")
        print("1. AWS credentials are correct in .env file")
        print("2. IAM user has S3 permissions (s3:CreateBucket, s3:PutObject, etc.)")
        print("3. Bucket name is available and follows S3 naming rules")
        sys.exit(1)


if __name__ == "__main__":
    main()

