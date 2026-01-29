"""
Voice API for EZ Common
Handles voice recording uploads, transcription, and context checking.
"""
from fastapi import APIRouter, File, UploadFile, Form, HTTPException, status
from typing import Optional
import io
from datetime import datetime

from services.voice_service import VoiceService
from s3_service import get_s3_service

router = APIRouter()

# Initialize voice service
try:
    voice_service = VoiceService()
    print("✓ Voice service initialized")
except Exception as e:
    print(f"⚠ Warning: Voice service initialization failed: {e}")
    voice_service = None

@router.post("/api/voice/transcribe")
async def transcribe_voice(
    user_id: str = Form(..., description="User ID"),
    file: UploadFile = File(..., description="Audio file"),
    section: str = Form("activity", description="Section (default: activity)")
):
    """
    Transcribe voice input, check context, and save result to S3 if valid.
    """
    if not voice_service:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Voice service is not available"
        )

    if not user_id:
        raise HTTPException(status_code=400, detail="user_id is required")

    try:
        # 1. Read audio file
        audio_content = await file.read()
        filename = file.filename or "voice_input.webm"
        
        # 2. Transcribe
        transcript = voice_service.transcribe_audio(audio_content, filename)
        
        # 3. Check context
        # User requested "context7" specifically
        context_result = voice_service.check_context(transcript, context_label="context7")
        
        # 4. Prepare result content
        # We will save the transcript as a text file in S3 so it appears in the Preview list
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        approval_status = "APPROVED" if context_result.get("approved") else "FLAGGED"
        reason = context_result.get("reason", "")
        
        file_content = (
            f"Voice Transcript ({timestamp})\n"
            f"Status: {approval_status}\n"
            f"Context Check: {reason}\n"
            f"Models: transcription={voice_service.transcribe_model}, context_check={voice_service.context_check_model}\n"
            f"----------------------------------------\n\n"
            f"{transcript}"
        )
        
        # 5. Save to S3
        # Use a .txt extension for the saved file
        txt_filename = f"voice_transcript_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        
        s3_service = get_s3_service()
        upload_result = s3_service.upload_file(
            file_content=file_content.encode('utf-8'),
            filename=txt_filename,
            user_id=user_id,
            section=section,
            content_type="text/plain"
        )
        
        return {
            "status": "success",
            "transcript": transcript,
            "context_check": context_result,
            "saved_file": upload_result
        }

    except Exception as e:
        print(f"Error processing voice input: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Processing failed: {str(e)}"
        )
