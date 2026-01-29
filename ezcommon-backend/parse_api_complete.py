"""
Complete Parse API endpoints to add to auth_api.py
This includes listing user files and parsing them with full OpenSearch integration
"""

# Add these imports at the top of auth_api.py
from document_parse_service import DocumentParseService

# Initialize parse service (add after user_service initialization)
parse_service = DocumentParseService()


# Models for Parse API
class FileInfo(BaseModel):
    key: str
    filename: str
    section: str
    file_type: str
    size: int
    last_modified: str
    url: str


class ParseFileRequest(BaseModel):
    s3_key: str


class ParseResult(BaseModel):
    status: str
    document_id: str
    source_file: str
    s3_key: str
    section: str
    file_type: str
    chunks_created: int
    chunks: List[Dict[str, Any]]
    processor_used: str
    opensearch_stored: bool


# API Endpoints

@app.get(
    "/api/parse/files",
    response_model=List[FileInfo],
    tags=["Document Parsing"]
)
def list_user_files(
    user_id: str = Query(..., description="User ID"),
    section: Optional[str] = Query(None, description="Filter by section (education, activity, testing, profile)")
):
    """
    List all files uploaded by a user
    
    - **user_id**: User ID
    - **section**: Optional section filter
    """
    try:
        files = parse_service.list_user_files(user_id, section)
        return files
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list files: {str(e)}"
        )


@app.post(
    "/api/parse/file",
    response_model=ParseResult,
    tags=["Document Parsing"]
)
async def parse_file_from_s3(body: ParseFileRequest, user_id: str = Query(...)):
    """
    Parse a file from S3 with complete processing
    
    - **s3_key**: S3 object key of the file to parse
    - **user_id**: User ID for tracking
    
    This endpoint:
    1. Downloads the file from S3
    2. Processes it using appropriate processor (PDF or Image/Bedrock)
    3. Extracts structured information
    4. Stores chunks in OpenSearch
    5. Returns detailed results including extracted chunks
    """
    try:
        result = parse_service.process_file_from_s3(body.s3_key, user_id)
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to parse file: {str(e)}"
        )


@app.post(
    "/api/parse/batch",
    tags=["Document Parsing"]
)
async def parse_batch_files(
    s3_keys: List[str] = Body(..., description="List of S3 keys to parse"),
    user_id: str = Query(..., description="User ID")
):
    """
    Parse multiple files in batch
    
    - **s3_keys**: List of S3 object keys
    - **user_id**: User ID for tracking
    """
    results = []
    
    for s3_key in s3_keys:
        try:
            result = parse_service.process_file_from_s3(s3_key, user_id)
            results.append(result)
        except Exception as e:
            results.append({
                "status": "error",
                "s3_key": s3_key,
                "error": str(e)
            })
    
    # Calculate summary
    successful = len([r for r in results if r.get('status') == 'success'])
    failed = len([r for r in results if r.get('status') == 'error'])
    total_chunks = sum([r.get('chunks_created', 0) for r in results if r.get('status') == 'success'])
    
    return {
        "total_files": len(s3_keys),
        "successful": successful,
        "failed": failed,
        "total_chunks": total_chunks,
        "results": results
    }

