import os
import time
import logging
import google.generativeai as genai
from schemas import LLMResult

logger = logging.getLogger(__name__)

FALLBACK_RESPONSES = {
    "llm_error": "I'm having trouble connecting right now. My AI brain needs a moment to reboot. Please try again in a few seconds.",
    "network_error": "I'm having trouble connecting right now. Please check your internet connection and try again.",
    "general_error": "I'm having trouble connecting right now. Something unexpected happened. Please try again in a moment."
}

class LLMService:
    def __init__(self):
        self.model = None
        self.is_initialized = False
        self._initialize()
    
    def _initialize(self):
        """Initialize Gemini AI service"""
        try:
            gemini_key = os.getenv("GEMINI_API_KEY")
            if not gemini_key:
                logger.error("Gemini API key not found")
                return False
            
            genai.configure(api_key=gemini_key)
            self.model = genai.GenerativeModel('gemini-1.5-flash')
            self.is_initialized = True
            logger.info("✅ Gemini AI initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize Gemini: {e}")
            return False
    
    def is_available(self) -> bool:
        """Check if LLM service is available"""
        return self.is_initialized and self.model is not None
    
    async def generate(self, prompt: str, max_retries: int = 3) -> LLMResult:
        """Safely generate LLM response with retries and fallback"""
        if not self.is_available():
            return LLMResult(
                success=False,
                error="Gemini AI service not available",
                fallback_response=FALLBACK_RESPONSES["llm_error"]
            )
        
        for attempt in range(max_retries):
            try:
                logger.info(f"LLM generation attempt {attempt + 1}/{max_retries}")
                response = self.model.generate_content(prompt)
                
                if not response.text:
                    if attempt == max_retries - 1:
                        return LLMResult(
                            success=False,
                            error="No response generated",
                            fallback_response=FALLBACK_RESPONSES["llm_error"]
                        )
                    continue
                
                return LLMResult(
                    success=True,
                    text=response.text.strip()
                )
                
            except Exception as e:
                logger.error(f"LLM generation attempt {attempt + 1} failed: {e}")
                if attempt == max_retries - 1:
                    return LLMResult(
                        success=False,
                        error=str(e),
                        fallback_response=FALLBACK_RESPONSES["llm_error"]
                    )
                time.sleep(2)
        
        return LLMResult(
            success=False,
            error="Max retries exceeded",
            fallback_response=FALLBACK_RESPONSES["llm_error"]
        )