"""
File Upload API for EZ Common
Handles file uploads to AWS S3
"""
from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional
from enum import Enum
import os

from s3_service import get_s3_service

# CORS Configuration
CORS_ORIGINS = os.environ.get(
    "CORS_ORIGINS",
    "https://ezcollegeapp1.com"
).split(",")

app = FastAPI(
    title="EZ Common Upload API",
    description="File upload service for EZ Common application",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class Section(str, Enum):
    """Upload sections"""
    profile = "profile"
    education = "education"
    activity = "activity"
    testing = "testing"


@app.on_event("startup")
async def startup_event():
    """Initialize S3 bucket on startup"""
    s3_service = get_s3_service()
    if not s3_service.ensure_bucket_exists():
        print("Warning: S3 bucket initialization failed")


@app.get("/healthz")
async def health_check():
    """Health check endpoint"""
    return {
        "ok": True,
        "service": "upload-api",
        "status": "healthy"
    }


@app.post("/api/upload/{section}")
async def upload_files(
    section: Section,
    user_id: str = Form(..., description="User ID"),
    files: List[UploadFile] = File(..., description="Files to upload")
):
    """
    Upload files to S3
    
    Args:
        section: Upload section (profile, education, activity, testing)
        user_id: User ID for organizing files
        files: List of files to upload
    
    Returns:
        Upload results with file metadata
    """
    if not user_id:
        raise HTTPException(status_code=400, detail="user_id is required")
    
    if not files:
        raise HTTPException(status_code=400, detail="No files provided")
    
    s3_service = get_s3_service()
    uploaded_files = []
    errors = []
    
    for file in files:
        try:
            # Read file content
            content = await file.read()
            
            # Upload to S3
            result = s3_service.upload_file(
                file_content=content,
                filename=file.filename or "unnamed",
                user_id=user_id,
                section=section.value,
                content_type=file.content_type
            )
            
            if result['success']:
                uploaded_files.append({
                    'filename': result['filename'],
                    'unique_filename': result['unique_filename'],
                    's3_key': result['s3_key'],
                    'url': result['url'],
                    'size': result['size'],
                    'section': result['section']
                })
            else:
                errors.append({
                    'filename': result['filename'],
                    'error': result.get('error', 'Upload failed')
                })
        except Exception as e:
            errors.append({
                'filename': file.filename or "unknown",
                'error': str(e)
            })
    
    return {
        "ok": True,
        "count": len(uploaded_files),
        "files": uploaded_files,
        "errors": errors if errors else None
    }


@app.get("/api/upload/{section}")
async def list_files(
    section: Section,
    user_id: str = Query(..., description="User ID")
):
    """
    List uploaded files for a user and section
    
    Args:
        section: Upload section
        user_id: User ID
    
    Returns:
        List of file metadata
    """
    if not user_id:
        raise HTTPException(status_code=400, detail="user_id is required")
    
    s3_service = get_s3_service()
    files = s3_service.list_user_files(user_id=user_id, section=section.value)
    
    return {
        "ok": True,
        "files": files
    }


@app.delete("/api/upload/file")
async def delete_file(
    s3_key: str = Query(..., description="S3 key of file to delete"),
    user_id: str = Query(..., description="User ID for authorization")
):
    """
    Delete a file from S3
    
    Args:
        s3_key: S3 object key
        user_id: User ID (for authorization check)
    
    Returns:
        Deletion result
    """
    if not s3_key or not user_id:
        raise HTTPException(status_code=400, detail="s3_key and user_id are required")
    
    # Verify the file belongs to the user
    if not s3_key.startswith(f"user-uploads/{user_id}/"):
        raise HTTPException(status_code=403, detail="Unauthorized to delete this file")
    
    s3_service = get_s3_service()
    success = s3_service.delete_file(s3_key)
    
    if success:
        return {
            "ok": True,
            "message": "File deleted successfully"
        }
    else:
        raise HTTPException(status_code=500, detail="Failed to delete file")


@app.get("/api/upload/file/metadata")
async def get_file_metadata(
    s3_key: str = Query(..., description="S3 key"),
    user_id: str = Query(..., description="User ID for authorization")
):
    """
    Get metadata for a specific file
    
    Args:
        s3_key: S3 object key
        user_id: User ID (for authorization check)
    
    Returns:
        File metadata
    """
    if not s3_key or not user_id:
        raise HTTPException(status_code=400, detail="s3_key and user_id are required")
    
    # Verify the file belongs to the user
    if not s3_key.startswith(f"user-uploads/{user_id}/"):
        raise HTTPException(status_code=403, detail="Unauthorized to access this file")
    
    s3_service = get_s3_service()
    metadata = s3_service.get_file_metadata(s3_key)
    
    if metadata:
        return {
            "ok": True,
            "file": metadata
        }
    else:
        raise HTTPException(status_code=404, detail="File not found")


@app.get("/api/upload/user/{user_id}")
async def list_all_user_files(user_id: str):
    """
    List all files for a user across all sections
    
    Args:
        user_id: User ID
    
    Returns:
        List of all user files
    """
    s3_service = get_s3_service()
    files = s3_service.list_user_files(user_id=user_id)
    
    return {
        "ok": True,
        "count": len(files),
        "files": files
    }


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8001))
    uvicorn.run(app, host="0.0.0.0", port=port)
