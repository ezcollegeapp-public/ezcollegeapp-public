"""
AI Text Editing API for Chrome Extension
Follows the logic of server.js - uses LLM providers for intelligent text editing
"""

from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel
import os
import json
from pathlib import Path
from typing import Optional, Dict, Any
from services.llm_providers.factory import LLMFactory

# Create router for easy integration
router = APIRouter()

# Get the config/outputs directory
CONFIG_OUTPUTS_DIR = Path(__file__).parent / "config" / "outputs"


class AIEditRequest(BaseModel):
    """Request model for AI editing - matches server.js structure"""
    prompt: str
    context: str
    model: Optional[str] = "gpt-4o-mini"


class AIEditResponse(BaseModel):
    """Response model for AI editing"""
    success: bool
    data: Optional[str] = None
    error: Optional[str] = None


class ProfileResponse(BaseModel):
    """Response model for profile data"""
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


def initialize_llm_provider(provider_type: str = 'openai'):
    """
    Initialize and return LLM provider
    Matches server.js logic for getting OpenAI (or other) provider
    """
    try:
        llm_provider = LLMFactory.create_provider(provider_type)
        if not llm_provider:
            raise ValueError(f"Failed to create LLM provider: {provider_type}")
        
        # Initialize the provider
        if not llm_provider.initialize():
            raise RuntimeError(f"Failed to initialize {provider_type} provider")
        
        return llm_provider
    except Exception as e:
        print(f"Error initializing LLM provider: {e}")
        raise


@router.post('/api/ai-edit')
async def ai_edit(request_data: AIEditRequest):
    """
    AI-powered text editing endpoint
    Follows the logic of server.js - uses LLM provider for text transformation
    
    Request:
    {
        "prompt": "make it shorter|professional|fix grammar|improve",
        "context": "text to edit",
        "model": "gpt-4o-mini" (optional, defaults to gpt-4o-mini)
    }
    
    Response:
    {
        "success": true,
        "data": "edited text from LLM"
    }
    """
    try:
        prompt = request_data.prompt.strip()
        context = request_data.context.strip()
        model = request_data.model or "gpt-4o-mini"
        
        if not prompt:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Prompt is required"
            )
        
        print('Received AI Edit request:', {
            'promptLength': len(prompt),
            'contextLength': len(context) if context else 0,
            'model': model
        })
        
        # Initialize LLM provider (defaults to openai like server.js)
        llm_provider = initialize_llm_provider('openai')
        
        # Build the messages - matches server.js structure
        messages = [
            {
                "role": "system",
                "content": "You are a helpful writing assistant. Your task is to improve, summarize, or edit the provided text based on the user's instruction. Return ONLY the edited text, without any conversational filler or explanations, unless specifically asked."
            },
            {
                "role": "user",
                "content": f'Context/Text to edit: "{context or ""}\n\nInstruction: {prompt}'
            }
        ]
        
        # Call LLM provider to edit text
        response = llm_provider.chat_completion(
            messages=messages,
            temperature=0.7
        )
        
        # Extract the edited text from LLM response
        edited_text = response['content'].strip()
        
        print('AI Edit completed successfully')
        
        return AIEditResponse(
            success=True,
            data=edited_text
        )
    
    except HTTPException:
        raise
    except Exception as e:
        print(f'Error in ai_edit: {str(e)}')
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f'Internal server error: {str(e)}'
        )


@router.get('/api/profile/{user_id}')
async def get_user_profile(user_id: str):
    """
    Get all pre-filled profile data for a user
    Returns all JSON files for this user
    
    Example: GET /api/profile/test_user_001
    Returns: {
        "success": true,
        "data": {
            "schools": [...],
            "general_questions": [...]
        }
    }
    """
    try:
        user_data = {}
        
        # Find all JSON files for this user
        if CONFIG_OUTPUTS_DIR.exists():
            for json_file in CONFIG_OUTPUTS_DIR.glob(f"*{user_id}*.json"):
                try:
                    with open(json_file, 'r') as f:
                        data = json.load(f)
                        # Use filename as key (without extension)
                        key = json_file.stem
                        user_data[key] = data
                except Exception as e:
                    print(f"Error reading {json_file}: {e}")
        
        if not user_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No data found for user: {user_id}"
            )
        
        return ProfileResponse(
            success=True,
            data=user_data
        )
    
    except HTTPException:
        raise
    except Exception as e:
        print(f'Error in get_user_profile: {str(e)}')
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get('/api/profile/{user_id}/{school_id}')
async def get_school_data(user_id: str, school_id: str):
    """
    Get pre-filled data for a specific school
    
    Example: GET /api/profile/test_user_001/school_130
    Returns: {
        "success": true,
        "data": {...school form data...}
    }
    """
    try:
        # Find the specific school file
        pattern = f"*{user_id}*{school_id}*.json"
        
        if CONFIG_OUTPUTS_DIR.exists():
            matching_files = list(CONFIG_OUTPUTS_DIR.glob(pattern))
            
            if matching_files:
                json_file = matching_files[0]  # Get first match
                with open(json_file, 'r') as f:
                    data = json.load(f)
                
                return ProfileResponse(
                    success=True,
                    data=data
                )
        
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No data found for user {user_id}, school {school_id}"
        )
    
    except HTTPException:
        raise
    except Exception as e:
        print(f'Error in get_school_data: {str(e)}')
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get('/health')
async def health_check():
    """Health check endpoint"""
    return {
        'status': 'ok',
        'service': 'profile-data-api',
        'config_outputs_exists': CONFIG_OUTPUTS_DIR.exists()
    }
