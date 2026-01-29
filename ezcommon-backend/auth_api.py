"""
FastAPI Authentication API for EZ Common
Handles user registration and login with DynamoDB backend
"""
from fastapi import FastAPI, HTTPException, status, File, UploadFile, Form, Query, Body, Request, Response, Cookie
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List, Dict, Any
from enum import Enum
from decimal import Decimal
from dotenv import load_dotenv
from datetime import datetime, timedelta, timezone
import os
from jose import jwt, JWTError

# Load environment variables from .env file before importing modules that reference them at import-time
load_dotenv()

from user_service import UserService
from org_service import OrgService
from org_invitation_service import OrgInvitationService
from s3_service import get_s3_service
from ai_edit_api import router as ai_edit_router
import os
import asyncio
import json
from uuid import uuid4

# Initialize FastAPI app
app = FastAPI(
    title="EZ Common Auth API",
    description="User authentication service with AWS DynamoDB",
    version="1.0.0"
)

# CORS configuration
CORS_ORIGINS = os.environ.get(
    "CORS_ORIGINS",
    "https://ezcollegeapp1.com"
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register AI Edit router
app.include_router(ai_edit_router)

# JWT configuration
JWT_SECRET = os.environ.get("JWT_SECRET_KEY", os.environ.get("JWT_SECRET", "dev-secret-change-me"))
JWT_ALGORITHM = os.environ.get("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.environ.get("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.environ.get("REFRESH_TOKEN_EXPIRE_DAYS", "30"))
REFRESH_COOKIE_SECURE = os.environ.get("REFRESH_COOKIE_SECURE", "false").lower() == "true"
REFRESH_COOKIE_SAMESITE = os.environ.get("REFRESH_COOKIE_SAMESITE", "lax")

# Initialize org and invitation services
org_service = OrgService()
invitation_service = OrgInvitationService()

# Initialize user service
user_service = UserService()

# Initialize Search Provider (supports OpenSearch, ChromaDB, etc.)
from services.search_providers import SearchProviderFactory

def _build_search_config():
    """Build search provider configuration from environment variables"""
    return {
        'SEARCH_PROVIDER': os.environ.get('SEARCH_PROVIDER', 'opensearch'),
        'OPENSEARCH_HOST': os.environ.get('OPENSEARCH_HOST'),
        'OPENSEARCH_REGION': os.environ.get('OPENSEARCH_REGION', 'us-east-1'),
        'OPENSEARCH_INDEX': os.environ.get('OPENSEARCH_INDEX', 'document_chunks'),
        'OPENSEARCH_PORT': int(os.environ.get('OPENSEARCH_PORT', '443')),
        'CHROMADB_DATA_DIR': os.environ.get('CHROMADB_DATA_DIR', './chroma_data'),
        'CHROMADB_COLLECTION_NAME': os.environ.get('CHROMADB_COLLECTION_NAME', 'document_chunks')
    }

search_provider = None
try:
    search_config = _build_search_config()
    search_provider = SearchProviderFactory.create(search_config)
    print(f"✓ Search provider initialized: {search_config.get('SEARCH_PROVIDER', 'opensearch')}")
except Exception as e:
    print(f"⚠ Warning: Search provider initialization failed: {e}")
    search_provider = None

# Initialize LLM Provider (supports OpenAI, Gemini, Bedrock)
from services.llm_providers import LLMProviderFactory

def _build_llm_config():
    """Build LLM provider configuration from environment variables"""
    return {
        'LLM_PROVIDER': os.environ.get('LLM_PROVIDER', 'openai'),
        'OPENAI_API_KEY': os.environ.get('OPENAI_API_KEY'),
        'OPENAI_MODEL': os.environ.get('OPENAI_MODEL', 'gpt-4o-mini'),
        'OPENAI_VISION_MODEL': os.environ.get('OPENAI_VISION_MODEL', 'gpt-4o'),
        'OPENAI_TRANSCRIBE_MODEL': os.environ.get('OPENAI_TRANSCRIBE_MODEL', 'whisper-1'),
        'GEMINI_API_KEY': os.environ.get('GEMINI_API_KEY'),
        'GEMINI_MODEL': os.environ.get('GEMINI_MODEL', 'gemini-2.0-flash'),
        'GEMINI_VISION_MODEL': os.environ.get('GEMINI_VISION_MODEL', 'gemini-1.5-pro'),
        'AWS_REGION': os.environ.get('AWS_REGION', 'us-east-1'),
        'BEDROCK_MODEL': os.environ.get('BEDROCK_MODEL', 'anthropic.claude-3-5-sonnet-20241022-v2:0'),
    }

llm_provider = None
try:
    llm_config = _build_llm_config()
    llm_provider = LLMProviderFactory.create(llm_config)
    print(f"✓ LLM provider initialized: {llm_config.get('LLM_PROVIDER', 'openai')}")
except Exception as e:
    print(f"⚠ Warning: LLM provider initialization failed: {e}")
    llm_provider = None

# Document Parsing Service
from services.document_parse_service import DocumentParseService

# Initialize parse service with search and LLM providers
try:
    parse_service = DocumentParseService(search_provider=search_provider, llm_provider=llm_provider)
    print("✓ Document parse service initialized")
except Exception as e:
    print(f"⚠ Warning: Document parse service initialization failed: {e}")
    parse_service = None

# Form Fill Service
from services.form_fill_service import FormFillService
from services.document_to_csv_service import DocumentToCSVService
from services.intelligent_extractor_service import IntelligentExtractorService
from fastapi.responses import StreamingResponse
from datetime import datetime, timedelta, timezone
from requests import exceptions as requests_exceptions

# Initialize form fill service
try:
    form_fill_service = FormFillService(
        search_provider=search_provider,
        llm_provider=llm_provider,
    )
    print("✓ Form fill service initialized")
except Exception as e:
    print(f"⚠ Warning: Form fill service initialization failed: {e}")
    form_fill_service = None

# Document CSV Service
try:
    document_csv_service = DocumentToCSVService()
    print("✓ Document CSV service initialized")
except Exception as e:
    print(f"⚠ Warning: Document CSV service initialization failed: {e}")
    document_csv_service = None

try:
    intelligent_extractor_service = IntelligentExtractorService(
        search_provider=search_provider,
        llm_provider=llm_provider,
    )
    print("✓ Intelligent Extractor service initialized")
except Exception as e:
    print(f"⚠ Warning: Intelligent Extractor service initialization failed: {e}")
    intelligent_extractor_service = None



# Voice API
from voice_api import router as voice_router
app.include_router(voice_router)


def _require_user(user_id: str) -> Dict[str, Any]:
    """Fetch a user or raise if not found."""
    user = user_service.get_user_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return user





# Form Fill Models
class FieldDefinition(BaseModel):
    name: str
    category: str
    source: str

class FormFillRequest(BaseModel):
    field_definitions: List[FieldDefinition]
    section: Optional[str] = None

class FormFillResponse(BaseModel):
    status: str
    total_fields: int
    found_fields: int
    not_found_fields: int
    success_rate: float
    total_chunks_available: int
    results: Dict[str, str]


# Form Fill Endpoints
@app.post("/api/form/fill", response_model=FormFillResponse, tags=["Form Filling"])
async def fill_form_fields(
    request: FormFillRequest,
    user_id: str = Query(..., description="User ID")
):
    """
    Fill multiple form fields using user's parsed documents

    - **field_definitions**: List of fields to fill with name, category, and source
    - **user_id**: User ID to retrieve documents for
    - **section**: Optional section filter (education, activity, testing, profile)
    """
    if not form_fill_service:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Form fill service not available"
        )
    
    _require_user(user_id)

    # Convert Pydantic models to dicts
    field_defs = [
        {
            "name": field.name,
            "category": field.category,
            "source": field.source
        }
        for field in request.field_definitions
    ]

    try:
        result = form_fill_service.fill_multiple_fields(
            user_id=user_id,
            field_definitions=field_defs,
            section=request.section
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    if result["status"] == "error":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=result["message"]
        )

    return result


@app.get("/api/form/chunks", tags=["Form Filling"])
async def get_user_chunks_for_form(
    user_id: str = Query(..., description="User ID"),
    section: Optional[str] = Query(None, description="Section filter")
):
    """
    Get all document chunks available for a user

    - **user_id**: User ID
    - **section**: Optional section filter
    """
    if not form_fill_service:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Form fill service not available"
        )
    
    _require_user(user_id)

    chunks = form_fill_service.get_user_chunks(user_id, section)

    return {
        "user_id": user_id,
        "section": section,
        "total_chunks": len(chunks),
        "chunks": chunks
    }


# Additional Models for Parse API
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


class ParseResultComplete(BaseModel):
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


# Parse API Endpoints

@app.get(
    "/api/parse/files",
    response_model=List[FileInfo],
    tags=["Document Parsing"]
)
def list_user_files_endpoint(
    user_id: str = Query(..., description="User ID"),
    section: Optional[str] = Query(None, description="Filter by section")
):
    """List all files uploaded by a user from S3"""
    if not parse_service:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Parse service not available"
        )

    try:
        files = parse_service.list_user_files(user_id, section)
        return files
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list files: {str(e)}"
        )


@app.get(
    "/api/parse/file/stream",
    tags=["Document Parsing"]
)
async def parse_file_stream_endpoint(
    s3_key: str = Query(..., description="S3 key of the file to parse"),
    user_id: str = Query(..., description="User ID")
):
    """
    Parse a file from S3 with real-time progress updates via Server-Sent Events (SSE)

    Returns a stream of progress updates in the format:
    data: {"progress": 10, "message": "Downloading file from S3..."}
    data: {"progress": 100, "message": "Processing complete!", "result": {...}}
    """
    if not parse_service:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Parse service not available"
        )

    async def event_generator():
        """Generate SSE events for progress updates"""
        progress_queue = asyncio.Queue()
        result_container = {}
        error_container = {}

        def progress_callback(progress: int, message: str):
            """Callback to receive progress updates from sync code"""
            asyncio.create_task(progress_queue.put({
                "progress": progress,
                "message": message
            }))

        async def process_file():
            """Run the file processing in a thread pool"""
            try:
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(
                    None,
                    lambda: parse_service.process_file_from_s3(
                        s3_key, user_id, progress_callback
                    )
                )
                result_container['result'] = result
                await progress_queue.put(None)  # Signal completion
            except Exception as e:
                error_container['error'] = str(e)
                await progress_queue.put(None)  # Signal completion

        # Start processing in background
        asyncio.create_task(process_file())

        # Stream progress updates
        while True:
            update = await progress_queue.get()

            if update is None:  # Processing complete
                if 'error' in error_container:
                    yield f"data: {json.dumps({'error': error_container['error']})}\n\n"
                elif 'result' in result_container:
                    yield f"data: {json.dumps({'progress': 100, 'message': 'Complete!', 'result': result_container['result']})}\n\n"
                break
            else:
                yield f"data: {json.dumps(update)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # Disable nginx buffering
        }
    )


@app.post(
    "/api/parse/file",
    response_model=ParseResultComplete,
    tags=["Document Parsing"]
)
async def parse_file_from_s3_endpoint(
    body: ParseFileRequest,
    user_id: str = Query(...)
):
    """
    Parse a file from S3 with complete processing (non-streaming version)

    This endpoint:
    1. Downloads the file from S3
    2. Processes it using appropriate processor (PDF or Image/Bedrock)
    3. Extracts structured information
    4. Stores chunks in OpenSearch
    5. Returns detailed results including extracted chunks
    """
    if not parse_service:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Parse service not available"
        )

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
async def parse_batch_files_endpoint(
    s3_keys: List[str] = Body(...),
    user_id: str = Query(...)
):
    """Parse multiple files in batch"""
    if not parse_service:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Parse service not available"
        )

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



# Pydantic models
class RegisterRequest(BaseModel):
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    email: EmailStr
    password: str = Field(..., min_length=6)
    # Optional role and organization name for enterprise / org accounts
    role: Optional[str] = Field(
        "student",
        description="User role: student or org_admin",
    )
    org_name: Optional[str] = Field(
        None,
        max_length=200,
        description="Organization name (required when role is org_admin)",
    )


class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    login_type: Optional[str] = Field(None, description="student or org for front-end gating")


class RefreshRequest(BaseModel):
    refresh_token: Optional[str] = Field(None, description="Refresh token (falls back to cookie)")


class UserResponse(BaseModel):
    id: str
    email: str
    first_name: str
    last_name: str
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    # Enterprise / org fields
    role: str = "student"
    org_id: Optional[str] = None


class UpdateUserRequest(BaseModel):
    first_name: Optional[str] = Field(None, min_length=1, max_length=100)
    last_name: Optional[str] = Field(None, min_length=1, max_length=100)
    password: Optional[str] = Field(None, min_length=6)


class MessageResponse(BaseModel):
    message: str



class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    refresh_expires_in: int
    user: UserResponse


class OrgInvitationCreateRequest(BaseModel):

    """Payload for organization sending an invitation to a student."""

    org_id: str = Field(..., description="Organization ID (from org user's account)")
    student_email: Optional[EmailStr] = Field(
        None,
        description="Student email to invite (preferred)",
    )
    student_id: Optional[str] = Field(
        None,
        description="Student user ID (optional if email provided)",
    )
    message: Optional[str] = Field(
        None,
        description="Optional message to include with the invitation",
    )
    org_name: Optional[str] = Field(
        None,
        description="Optional organization display name to show to the student",
    )
    created_by_user_id: Optional[str] = Field(
        None,
        description="ID of the org user that created the invitation",
    )


class InvitationActionRequest(BaseModel):
    """Payload for a student accepting / rejecting an invitation."""

    org_id: str
    student_id: str



# Health check endpoint
@app.get("/healthz")
def health_check():
    """Health check endpoint"""
    return {"ok": True, "service": "auth-api", "status": "healthy"}


# Authentication endpoints
@app.post(
    "/api/auth/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Authentication"]
)
def register(body: RegisterRequest):
    """
    Register a new user

    - **first_name**: User's first name
    - **last_name**: User's last name
    - **email**: User's email (must be unique)
    - **password**: User's password (min 6 characters)
    - **role**: Optional role (student or org_admin)
    - **org_name**: Optional organization name for org_admin
    """
    # Normalize and validate role
    requested_role = (body.role or "student").strip().lower()
    if requested_role not in {"student", "org_admin"}:
        requested_role = "student"

    org_id = None
    if requested_role == "org_admin":
        # Generate a stable org id
        org_id = f"org_{uuid4().hex}"

    # Create user with role and org_id
    user = user_service.create_user(
        email=body.email,
        first_name=body.first_name,
        last_name=body.last_name,
        password=body.password,
        role=requested_role,
        org_id=org_id,
    )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered"
        )

    # If this is an org admin, create an organization record as well
    if requested_role == "org_admin" and org_id is not None:
        org_name = (body.org_name or f"{body.first_name} {body.last_name} Org").strip()
        try:
            org_service.create_org(
                org_id=org_id,
                name=org_name,
                owner_user_id=user["id"],
                contact_email=user["email"],
            )
        except Exception as e:
            # Log and continue; user account is already created
            print(f"Warning: Failed to create organization for user {user['id']}: {e}")

    return user


def _create_token(payload: Dict[str, Any], expires_delta: timedelta) -> str:
    to_encode = payload.copy()
    now = datetime.now(timezone.utc)
    to_encode.update({"iat": now, "exp": now + expires_delta})
    return jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)


def _create_access_token(user: Dict[str, Any]) -> str:
    return _create_token(
        {
            "sub": user["id"],
            "email": user["email"],
            "role": user.get("role", "student"),
            "org_id": user.get("org_id"),
        },
        timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    )


def _create_refresh_token(user: Dict[str, Any]) -> str:
    return _create_token(
        {
            "sub": user["id"],
            "type": "refresh",
        },
        timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
    )


def _decode_token(token: str) -> Dict[str, Any]:
    return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])


def _set_refresh_cookie(response: Response, token: str):
    response.set_cookie(
        key="refresh_token",
        value=token,
        httponly=True,
        secure=REFRESH_COOKIE_SECURE,
        samesite=REFRESH_COOKIE_SAMESITE,
        max_age=REFRESH_TOKEN_EXPIRE_DAYS * 24 * 3600,
        path="/",
    )


def _build_token_response(user: Dict[str, Any], response: Response) -> Dict[str, Any]:
    access = _create_access_token(user)
    refresh = _create_refresh_token(user)
    _set_refresh_cookie(response, refresh)
    return {
        "access_token": access,
        "refresh_token": refresh,
        "token_type": "bearer",
        "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        "refresh_expires_in": REFRESH_TOKEN_EXPIRE_DAYS * 24 * 3600,
        "user": user,
    }


@app.post(
    "/api/auth/login",
    response_model=TokenResponse,
    tags=["Authentication"]
)
def login(body: LoginRequest, response: Response):
    """
    Login with email and password

    - **email**: User's email
    - **password**: User's password
    """
    user = user_service.authenticate_user(body.email, body.password)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

    return _build_token_response(user, response)


@app.get(
    "/api/auth/user/{user_id}",
    response_model=UserResponse,
    tags=["User Management"]
)
def get_user(user_id: str):
    """
    Get user by ID

    - **user_id**: User's unique ID
    """
    user = user_service.get_user_by_id(user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Remove password_hash from response
    user_copy = dict(user)
    user_copy.pop('password_hash', None)
    return user_copy


@app.post(
    "/api/auth/refresh",
    response_model=TokenResponse,
    tags=["Authentication"]
)
def refresh_token(
    response: Response,
    body: RefreshRequest = Body(None),
    refresh_cookie: Optional[str] = Cookie(None, alias="refresh_token"),
):
    """Issue a new access token using a refresh token (cookie or body)."""
    token = (body.refresh_token if body else None) or refresh_cookie
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing refresh token",
        )

    try:
        payload = _decode_token(token)
        if payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token",
            )
        user_id = payload.get("sub")
        user = user_service.get_user_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
            )
        return _build_token_response(user, response)
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )


@app.put(
    "/api/auth/user/{user_id}",
    response_model=UserResponse,
    tags=["User Management"]
)
def update_user(user_id: str, body: UpdateUserRequest):
    """
    Update user information

    - **user_id**: User's unique ID
    - **first_name**: New first name (optional)
    - **last_name**: New last name (optional)
    - **password**: New password (optional)
    """
    user = user_service.update_user(
        user_id=user_id,
        first_name=body.first_name,
        last_name=body.last_name,
        password=body.password
    )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    return user


@app.delete(
    "/api/auth/user/{user_id}",
    response_model=MessageResponse,
    tags=["User Management"],
)
def delete_user(user_id: str):
    """Delete a user.

    - **user_id**: User's unique ID
    """
    success = user_service.delete_user(user_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found or deletion failed",
        )
    
    return {"message": "User deleted successfully"}


# ============================================================================
# Organization / Enterprise Endpoints
# ============================================================================


@app.post("/api/org/invitations", tags=["Organization"])
def create_org_invitation(body: OrgInvitationCreateRequest):
    """Organization sends an invitation to a student.

    The org passes its `org_id` (from the logged-in org user's account) and
    either the student's email or student_id.
    """

    if not body.student_id and not body.student_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either student_id or student_email is required",
        )

    # Resolve the student
    student = None
    if body.student_id:
        student = user_service.get_user_by_id(body.student_id)
    elif body.student_email:
        student = user_service.get_user_by_email(body.student_email)

    if not student or student.get("role", "student") != "student":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student not found",
        )

    # Try to infer org_name from org table if not provided
    org_name = body.org_name
    if org_name is None:
        org = org_service.get_org_by_id(body.org_id)
        if org:
            org_name = org.get("name")

    item = invitation_service.create_invitation(
        org_id=body.org_id,
        student_id=student["id"],
        org_name=org_name,
        created_by_user_id=body.created_by_user_id,
        message=body.message,
    )
    return item


@app.get("/api/org/invitations", tags=["Organization"])
def list_org_invitations(org_id: str):
    """List all invitations created by an organization."""

    items = invitation_service.get_invitations_for_org(org_id)
    return {"items": items, "count": len(items)}


@app.get("/api/student/invitations", tags=["Student"])
def list_student_invitations(student_id: str):
    """List invitations received by a student."""

    items = invitation_service.get_invitations_for_student(student_id)
    return {"items": items, "count": len(items)}


@app.post("/api/student/invitations/accept", tags=["Student"])
def accept_invitation(body: InvitationActionRequest):
    """Student accepts an invitation from an organization."""

    item = invitation_service.update_status(
        org_id=body.org_id,
        student_id=body.student_id,
        status="accepted",
    )
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invitation not found",
        )
    return {"invitation": item}


@app.post("/api/student/invitations/reject", tags=["Student"])
def reject_invitation(body: InvitationActionRequest):
    """Student rejects an invitation from an organization."""

    item = invitation_service.update_status(
        org_id=body.org_id,
        student_id=body.student_id,
        status="rejected",
    )
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invitation not found",
        )
    return {"invitation": item}


@app.get("/api/org/students", tags=["Organization"])
def list_org_students(org_id: str):
    """List students that have accepted invitations for this organization."""

    relationships = invitation_service.get_accepted_students_for_org(org_id)
    students = []
    for rel in relationships:
        student = user_service.get_user_by_id(rel.get("student_id"))
        if not student:
            continue
        # Remove password_hash before returning
        student_copy = dict(student)
        student_copy.pop("password_hash", None)
        students.append(student_copy)

    return {"students": students, "count": len(students)}


@app.get("/api/org/students/search", tags=["Organization"])
def search_students_for_org(query: str, limit: int = 20):
    """Search potential student accounts by email, id, or name.

    This is intended to help org users find the correct student to invite.
    """

    q = (query or "").strip().lower()
    if not q:
        return {"users": [], "count": 0}

    # 1) Try exact email match
    if "@" in q:
        student = user_service.get_user_by_email(q)
        if student and student.get("role", "student") == "student":
            student_copy = dict(student)
            student_copy.pop("password_hash", None)
            return {"users": [student_copy], "count": 1}

    # 2) Try exact id match
    student = user_service.get_user_by_id(query)
    if student and student.get("role", "student") == "student":
        student_copy = dict(student)
        student_copy.pop("password_hash", None)
        return {"users": [student_copy], "count": 1}

    # 3) Fallback: scan a limited set of users and match by name / email contains
    candidates = user_service.list_users(limit=500)
    results = []
    for user in candidates:
        if user.get("role", "student") != "student":
            continue
        full_name = f"{user.get('first_name', '')} {user.get('last_name', '')}".strip().lower()
        email = str(user.get("email", "")).lower()
        if q in full_name or q in email:
            results.append(user)
            if len(results) >= limit:
                break

    return {"users": results, "count": len(results)}



# Admin endpoints (should be protected in production)
@app.get(
    "/api/admin/users",
    tags=["Admin"]
)
def list_users(limit: int = 100):
    """
    List all users (admin only)

    - **limit**: Maximum number of users to return
    """
    users = user_service.list_users(limit=limit)
    return {"users": users, "count": len(users)}


# ============================================================================
# File Upload Endpoints
# ============================================================================

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


@app.get("/api/user/{user_id}")
async def get_user_info(user_id: str):
    """
    Get user information by user ID

    Args:
        user_id: User ID

    Returns:
        User information (without password)
    """
    user = user_service.get_user_by_id(user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Remove password_hash from response
    user_data = {k: v for k, v in user.items() if k != 'password_hash'}

    return {
        "ok": True,
        "user": user_data
    }


# Run with: uvicorn auth_api:app --reload --host 0.0.0.0 --port 8000

# ============================================================================
# Document CSV Export Endpoints
# ============================================================================

@app.get("/api/documents/statistics", tags=["Document CSV"])
async def get_document_statistics(
    user_id: str = Query(..., description="User ID"),
    section: Optional[str] = Query(None, description="Section filter")
):
    """Get statistics about user's parsed documents"""
    if not document_csv_service:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Document CSV service not available"
        )
    try:
        stats = document_csv_service.get_statistics(user_id, section)
        return stats
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get statistics: {str(e)}"
        )


@app.get("/api/documents/export/detailed", tags=["Document CSV"])
async def export_detailed_csv(
    user_id: str = Query(..., description="User ID"),
    section: Optional[str] = Query(None, description="Section filter")
):
    """Export all document chunks as detailed CSV"""
    if not document_csv_service:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Document CSV service not available"
        )
    try:
        result = document_csv_service.generate_summary_csv(user_id, section)

        if result['status'] == 'error':
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=result['message']
            )

        section_name = section or 'all'
        filename = f"documents_{section_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

        return StreamingResponse(
            iter([result['csv_content']]),
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename={filename}",
                "X-Total-Documents": str(result['total_documents']),
                "X-Total-Chunks": str(result['total_chunks'])
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to export CSV: {str(e)}"
        )


@app.get("/api/documents/export/categorized", tags=["Document CSV"])
async def export_categorized_csv(
    user_id: str = Query(..., description="User ID"),
    section: Optional[str] = Query(None, description="Section filter")
):
    """Export documents organized by category as CSV"""
    if not document_csv_service:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Document CSV service not available"
        )
    try:
        result = document_csv_service.generate_categorized_csv(user_id, section)

        if result['status'] == 'error':
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=result['message']
            )

        section_name = section or 'all'
        filename = f"documents_categorized_{section_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

        return StreamingResponse(
            iter([result['csv_content']]),
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename={filename}",
                "X-Total-Documents": str(result['total_documents']),
                "X-Total-Categories": str(result['total_categories'])
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to export CSV: {str(e)}"
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "auth_api:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )

# Document Parsing Models
class ParseResult(BaseModel):
    document_id: str
    source_file: str
    file_type: str
    chunks_created: int
    processor_used: str


# Document Parsing Endpoint
@app.post(
    "/api/parse/document",
    response_model=ParseResult,
    tags=["Document Parsing"]
)
async def parse_document(
    file: UploadFile = File(...),
    user_id: str = Form(...)
):
    """
    Parse a single document file and extract information

    - **file**: Document file (PDF or image)
    - **user_id**: User ID for tracking
    """
    import tempfile
    import time
    from pathlib import Path

    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No filename provided"
        )

    # Determine file type
    file_ext = Path(file.filename).suffix.lower()

    if file_ext == '.pdf':
        file_type = 'pdf'
        processor = 'PyPDF2Processor'
    elif file_ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp']:
        file_type = 'image'
        processor = 'BedrockVisionProcessor'
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type: {file_ext}"
        )

    # Save file temporarily
    with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as tmp_file:
        content = await file.read()
        tmp_file.write(content)
        tmp_path = tmp_file.name

    try:
        # Simulate processing time
        time.sleep(0.5)

        # Simulate chunk creation based on file size
        file_size_kb = len(content) / 1024
        chunks_created = max(1, int(file_size_kb / 10))  # 1 chunk per 10KB

        # Generate document ID
        document_id = f"doc_{user_id}_{int(time.time())}"

        return ParseResult(
            document_id=document_id,
            source_file=file.filename,
            file_type=file_type,
            chunks_created=chunks_created,
            processor_used=processor
        )

    finally:
        # Clean up temporary file
        try:
            os.unlink(tmp_path)
        except:
            pass



# ==================== Intelligent Extractor Endpoints ====================

@app.get("/api/intelligent/files", tags=["Intelligent Extractor"])
async def list_parse_files(user_id: str, section: Optional[str] = None):
    """列出用户上传的文件"""
    try:
        print(f"[DEBUG] list_parse_files called with user_id={user_id}, section={section}")
        print(f"[DEBUG] intelligent_extractor_service is None: {intelligent_extractor_service is None}")

        if not intelligent_extractor_service:
            raise HTTPException(status_code=500, detail="Intelligent Extractor service not available")

        files = intelligent_extractor_service.list_user_files(user_id, section)
        print(f"[DEBUG] Service returned {len(files)} files")

        result = {
            "status": "success",
            "files": files,
            "total": len(files)
        }
        print(f"[DEBUG] Returning: {result}")
        return result
    except Exception as e:
        print(f"Error listing files: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/intelligent/extract", tags=["Intelligent Extractor"])
async def extract_from_documents(request: dict):
    """使用 GPT 从文档中提取结构化信息"""
    try:
        if not intelligent_extractor_service:
            raise HTTPException(status_code=500, detail="Intelligent Extractor service not available")

        user_id = request.get('user_id')
        files = request.get('files', [])

        if not user_id or not files:
            raise HTTPException(status_code=400, detail="user_id and files are required")

        try:
            result = intelligent_extractor_service.extract_from_files(user_id, files)
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(exc),
            ) from exc

        return result

    except Exception as e:
        print(f"Error extracting from documents: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/intelligent/store", tags=["Intelligent Extractor"])
async def store_to_opensearch(request: dict):
    """将提取的 chunks 存储到 OpenSearch"""
    try:
        if not intelligent_extractor_service:
            raise HTTPException(status_code=500, detail="Intelligent Extractor service not available")

        user_id = request.get('user_id')
        chunks = request.get('chunks', [])
        source_file = request.get('source_file', 'unknown')

        if not user_id or not chunks:
            raise HTTPException(status_code=400, detail="user_id and chunks are required")

        result = intelligent_extractor_service.store_chunks_to_opensearch(user_id, chunks, source_file)

        return result
    except Exception as e:
        print(f"Error storing to OpenSearch: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Chatbot API
# ============================================================================

from chatbot_service import get_chatbot_service

class ChatbotRequest(BaseModel):
    message: str
    history: Optional[List[Dict[str, str]]] = None

class ChatbotResponse(BaseModel):
    response: str

@app.post("/api/chatbot/message", response_model=ChatbotResponse)
async def chatbot_message(request: ChatbotRequest):
    """
    Send a message to the chatbot and get a response
    """
    try:
        chatbot_service = get_chatbot_service()
        response = chatbot_service.get_response(request.message, request.history)
        return ChatbotResponse(response=response)
    except Exception as e:
        print(f"Error in chatbot endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))
