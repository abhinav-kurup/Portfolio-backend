from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq
from pydantic import BaseModel
from typing import Any
from app.core.config import settings
from app.core.logging import setup_logging

logger = setup_logging()

from app.models.chat import ChatResponse


class LLMClient:
    def __init__(self):
        self.primary_client = self._get_primary_llm()
        self.fallback_client = self._get_fallback_llm()
    
    def _get_primary_llm(self):
        model =  ChatGroq(
            model=settings.PRIMARY_LLM_MODEL,
            max_tokens=settings.PRIMARY_LLM_MAX_TOKENS,
            temperature=0.3,
            timeout=30,
            api_key=settings.PRIMARY_LLM_API_KEY
        )
        return model.with_structured_output(ChatResponse)
    
    def _get_fallback_llm(self):
        model =  ChatGoogleGenerativeAI(
            model=settings.FALLBACK_LLM_MODEL,
            max_tokens=settings.FALLBACK_LLM_MAX_TOKENS,
            temperature=0.3,
            timeout=30,
            api_key=settings.FALLBACK_LLM_API_KEY
        )
        return model.with_structured_output(ChatResponse)

    def chat(self, system_promt:str, user_prompt:str) -> ChatResponse:
        messages = [
                ("system", system_promt),
                ("user",user_prompt)
            ]
        try:
            logger.info("Using primary LLM")
            response = self.primary_client.invoke(messages)
            # response.metadata["source"] = "primary"
            return response            
        except Exception as e:
            logger.error("Error using primary LLM: %s", e)
            try:
                logger.info("Using fallback LLM")
                response = self.fallback_client.invoke(messages)
                # response.metadata["source"] = "fallback"
                return response
            except Exception as e:
                logger.error("Error using fallback LLM: %s", e)
                return ChatResponse(
                    response="Sorry, I am having trouble connecting to the LLM right now. Please try again later.",
                    confidence=0,
                    metadata={},  # no metadata on failure
                    sources=[]
                )      


llm_client = LLMClient()
        
        
