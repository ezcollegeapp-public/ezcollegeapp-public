"""
Chatbot Service using OpenAI GPT
"""
import os
from typing import List, Dict
from openai import OpenAI

class ChatbotService:
    def __init__(self):
        """Initialize the chatbot service with OpenAI client"""
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable is required")
        
        self.client = OpenAI(api_key=api_key)
        self.model = os.environ.get("CHATBOT_MODEL", "gpt-4o-mini")
        
        # System prompt for the chatbot
        self.system_prompt = """You are a helpful assistant for EZCommon, an AI-powered college application autofill system. 

Your role is to help students with:
- Understanding how to use the EZCommon platform
- Answering questions about college applications
- Providing guidance on filling out application forms
- Explaining different sections like Education, Activities, Testing, and Profile
- Helping with document uploads and parsing
- General college application advice

Be friendly, concise, and helpful. If you don't know something specific about the platform, be honest and suggest they contact support."""

    def get_response(self, user_message: str, conversation_history: List[Dict[str, str]] = None) -> str:
        """
        Get a response from the chatbot
        
        Args:
            user_message: The user's message
            conversation_history: Previous messages in the conversation (list of {role, content})
            
        Returns:
            The chatbot's response
        """
        try:
            # Build messages array
            messages = [{"role": "system", "content": self.system_prompt}]
            
            # Add conversation history if provided
            if conversation_history:
                # Only keep last 10 messages to avoid token limits
                messages.extend(conversation_history[-10:])
            
            # Add current user message
            messages.append({"role": "user", "content": user_message})
            
            # Call OpenAI API
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.7,
                max_tokens=500
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            print(f"Error in chatbot service: {str(e)}")
            return "I'm sorry, I encountered an error. Please try again or contact support if the issue persists."

# Global instance
_chatbot_service = None

def get_chatbot_service() -> ChatbotService:
    """Get or create the global chatbot service instance"""
    global _chatbot_service
    if _chatbot_service is None:
        _chatbot_service = ChatbotService()
    return _chatbot_service

