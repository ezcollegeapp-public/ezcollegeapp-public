"""Voice transcription and context verification service."""

import io
import json
import os
from typing import Any, Dict, Optional


class VoiceService:
    """Handles audio transcription and lightweight context validation via LLM provider."""

    def __init__(self, llm_provider=None):
        """Initialize the voice service
        
        Args:
            llm_provider: LLM provider instance for transcription and context checking
        """
        # Use injected LLM provider
        self.llm_provider = llm_provider

    def transcribe_audio(self, audio_bytes: bytes, filename: str = "voice-input.webm") -> str:
        """Transcribe raw audio bytes into text using the LLM provider."""
        if not audio_bytes:
            raise ValueError("Audio file is empty")

        if not self.llm_provider:
            raise RuntimeError("LLM provider not initialized")

        # Prepare audio buffer
        audio_buffer = io.BytesIO(audio_bytes)
        audio_buffer.name = filename

        try:
            result = self.llm_provider.transcribe_audio(
                audio_bytes=audio_bytes,
                filename=filename
            )
            return result['content']
        except NotImplementedError as e:
            # Some providers don't support audio transcription
            print(f"Audio transcription not available: {e}")
            raise RuntimeError(f"Audio transcription not available with current LLM provider: {e}")
        except Exception as e:
            print(f"Transcription error: {e}")
            raise e

    def check_context(self, transcript: str, context_label: Optional[str] = None) -> Dict[str, Any]:
        """Validate transcript alignment with the requested context using LLM provider."""
        label = (context_label or "context7").strip() or "context7"
        if not transcript:
            return {
                "approved": False,
                "reason": "No transcript text available",
                "context_label": label,
                "model": "unknown",
            }

        if not self.llm_provider:
            return {
                "approved": False,
                "reason": "LLM provider not initialized",
                "context_label": label,
                "model": "unknown",
            }

        # context7 specific prompt logic could go here if "context7" implies something specific.
        # For now, assuming it implies general "Activity" relevance as per user request.
        # Prompt explicitly supports multilingual transcripts by asking the model
        # to understand any language and provide English reasoning (with an
        # optional short native-language summary to help debugging).
        system_prompt = (
            "You are a multilingual reviewer who can understand transcripts in ANY language.\n"
            f"Purpose/context label: {label}.\n"
            "Steps:\n"
            "1. If the transcript is not in English, internally translate it (you may mention a short summary in the reason).\n"
            "2. For 'context7', accept content describing extracurricular activities, volunteer work, internships, clubs, "
            "sports, artistic pursuits, or hobbies relevant to a college application activity list. Reject unrelated content.\n"
            "3. Return strict JSON: {\"approved\": boolean, \"reason\": string}. The reason must be in English and may end with "
            "a short native-language quote if helpful."
        )

        try:
            response = self.llm_provider.chat_completion(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": transcript},
                ],
                temperature=0,
                max_tokens=200
            )

            content = response['content'].strip()
            parsed = json.loads(content)
            
            provider_info = self.llm_provider.get_provider_info() if self.llm_provider else {}
            model = provider_info.get('chat_model', 'unknown')
            
            return {
                "approved": bool(parsed.get("approved")),
                "reason": str(parsed.get("reason", "")),
                "context_label": label,
                "model": model
            }
        except Exception as e:
            print(f"Context check error: {e}")
            # Fail safe
            provider_info = self.llm_provider.get_provider_info() if self.llm_provider else {}
            model = provider_info.get('chat_model', 'unknown')
            
            return {
                "approved": False,
                "reason": f"Error checking context: {str(e)}",
                "context_label": label,
                "model": model
            }
