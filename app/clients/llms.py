import random
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
        # Weights for final answer (chat)
        self.chat_weights = {
            "groq": 0.7,
            "gemini": 0.3
        }

    def _get_structured_model(self, provider: str):
        """Returns a structured model instance based on the provider."""
        if provider == "groq":
            model = ChatGroq(
                model=settings.PRIMARY_LLM_MODEL,
                max_tokens=settings.PRIMARY_LLM_MAX_TOKENS,
                temperature=0.3,
                top_p=0.9,
                timeout=30,
                api_key=settings.GROK_API_KEY
            )
        else:
            model = ChatGoogleGenerativeAI(
                model=settings.FALLBACK_LLM_MODEL,
                max_tokens=settings.FALLBACK_LLM_MAX_TOKENS,
                temperature=0.3,
                top_p=0.9,
                timeout=30,
                api_key=settings.GEMINI_API_KEY
            )
        return model.with_structured_output(ChatResponse)

    def chat(self, system_promt: str, user_prompt: str, history: list[Any] = None) -> ChatResponse:
        """Weighted random selection of models for the final answer."""
        messages = [("system", system_promt)]
        if history:
            for msg in history:
                messages.append((msg.role, msg.content))
        messages.append(("user", user_prompt))

        providers = list(self.chat_weights.keys())
        probabilities = list(self.chat_weights.values())
        
        chosen_provider = random.choices(providers, weights=probabilities, k=1)[0]
        logger.info(f"Final answer using provider: {chosen_provider}")

        try:
            model = self._get_structured_model(chosen_provider)
            return model.invoke(messages)
        except Exception as e:
            logger.error(f"Chat failed with {chosen_provider}: {e}")
            # Fallback to the other provider
            fallback_provider = "gemini" if chosen_provider == "groq" else "groq"
            try:
                logger.info(f"Retrying with fallback provider: {fallback_provider}")
                model = self._get_structured_model(fallback_provider)
                return model.invoke(messages)
            except Exception as e2:
                logger.error(f"Fallback failed: {e2}")
                return ChatResponse(
                    response="Sorry, I am having trouble connecting to the LLM right now.",
                    confidence=0,
                    metadata={},
                    sources=[]
                )

    def raw_chat(self, system_prompt: str, user_prompt: str, history: list[Any] = None) -> str:
        """Fixed Groq usage for internal tasks (condensing)."""
        logger.info("Raw chat using fixed Groq")
        
        model = ChatGroq(
            model="llama-3.1-8b-instant",
            temperature=0.1,
            max_tokens=128,
            top_p=0.8,
            api_key=settings.GROK_API_KEY
        )
        
        messages = [("system", system_prompt)]
        if history:
            for msg in history:
                messages.append((msg.role, msg.content))
        messages.append(("user", user_prompt))
        
        try:
            response = model.invoke(messages)
            # print("response content:",response.content)
            return response.content
        except Exception as e:
            logger.error(f"Raw chat failed: {e}")
            return user_prompt


llm_client = LLMClient()
        
        
