"""
Gemini Service using official Google GenAI Python SDK (google-genai).
Manages generation, temperature tuning, bounded retries, rate-limit resilience,
and structured Pydantic response parsing.
"""

import asyncio
import json
import logging
import re
from typing import Any, AsyncGenerator, Dict, List, Optional
from google import genai
from google.genai import types

try:
    from google.genai import errors
    APIError = errors.APIError
    ClientError = errors.ClientError
    ServerError = errors.ServerError
except (ImportError, AttributeError):
    try:
        from google.genai.errors import APIError, ClientError, ServerError  # type: ignore
    except ImportError:
        # Graceful fallback for IDE language servers running outside project virtualenv
        class APIError(Exception):  # type: ignore
            pass

        class ClientError(APIError):  # type: ignore
            pass

        class ServerError(APIError):  # type: ignore
            pass

from app.config import get_settings
from app.schemas.chat import RAGGenerationOutput

settings = get_settings()
logger = logging.getLogger("maya.gemini_service")


class GeminiServiceException(Exception):
    """Base exception for Gemini LLM service errors."""
    pass


class GeminiQuotaExhaustedException(GeminiServiceException):
    """Raised when account quota or rate limits are hit."""
    pass


class GeminiModelUnavailableException(GeminiServiceException):
    """Raised when the specified model does not exist or is currently unavailable."""
    pass


class GeminiService:
    """
    Client for Google Gemini generation with async support, structured output enforcement,
    and resilience against transient server errors.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.2,
        max_output_tokens: int = 2048,
    ):
        self.api_key = api_key or settings.GEMINI_API_KEY
        self.model_name = model or settings.GEMINI_MODEL
        self.temperature = temperature
        self.max_output_tokens = max_output_tokens

        if not self.api_key:
            logger.warning("GeminiService initialized without GEMINI_API_KEY. Calls will fail unless configured.")
            self._client = None
        else:
            self._client = genai.Client(api_key=self.api_key, http_options={"api_version": "v1beta"})

    @property
    def is_configured(self) -> bool:
        return bool(self._client and self.api_key)

    async def generate_rag_response(
        self,
        prompt: str,
        system_instruction: str,
        max_retries: int = 3,
        temperature: Optional[float] = None,
    ) -> RAGGenerationOutput:
        """
        Generate a strictly grounded, citation-validated structured response using Gemini.
        Applies exponential backoff on transient errors (503, 429).
        """
        if not self.is_configured or self._client is None:
            raise GeminiServiceException("GEMINI_API_KEY is not configured in backend environment.")
        client = self._client

        temp = temperature if temperature is not None else self.temperature

        config = types.GenerateContentConfig(
            temperature=temp,
            max_output_tokens=self.max_output_tokens,
            system_instruction=system_instruction,
            response_mime_type="application/json",
            response_schema=RAGGenerationOutput,
        )

        candidate_models = [self.model_name]
        for fallback in ["gemini-2.5-flash", "gemini-3.1-flash-lite", "gemini-3.5-flash-lite", "gemini-3.5-flash"]:
            if fallback not in candidate_models:
                candidate_models.append(fallback)

        last_error = None
        for current_model in candidate_models:
            for attempt in range(1, max_retries + 1):
                try:
                    logger.info(
                        f"Calling Gemini model '{current_model}' (attempt {attempt}/{max_retries}, temp={temp})..."
                    )
                    response = await client.aio.models.generate_content(
                        model=current_model,
                        contents=prompt,
                        config=config,
                    )

                    raw_text = response.text or ""
                    return self._parse_structured_output(raw_text)

                except ServerError as se:
                    last_error = se
                    logger.warning(f"Gemini ServerError (503/500) for '{current_model}' on attempt {attempt}: {se}")
                    # If high demand 503, immediately try the next model without waiting
                    if "503" in str(se) or "demand" in str(se).lower():
                        break
                    if attempt < max_retries:
                        await asyncio.sleep(1.0 * attempt)
                    else:
                        break  # Fall back to next model

                except ClientError as ce:
                    last_error = ce
                    err_str = str(ce)
                    logger.warning(f"Gemini ClientError for '{current_model}': {ce}")
                    if "RESOURCE_EXHAUSTED" in err_str or "429" in err_str or "NOT_FOUND" in err_str or "404" in err_str:
                        # Immediately fall back to next available model
                        break
                    if attempt < max_retries:
                        await asyncio.sleep(1.0 * attempt)
                    else:
                        break

                except Exception as exc:
                    last_error = exc
                    logger.warning(f"Unexpected error calling Gemini '{current_model}' on attempt {attempt}: {exc}")
                    if attempt < max_retries:
                        await asyncio.sleep(1.0 * attempt)
                    else:
                        break

        raise GeminiServiceException(f"Failed to generate content across available models: {last_error}")

    async def generate_stream(
        self,
        prompt: str,
        system_instruction: str,
        temperature: Optional[float] = None,
    ) -> AsyncGenerator[str, None]:
        """
        Stream generated tokens progressively for Server-Sent Events (SSE).
        """
        if not self.is_configured or self._client is None:
            yield "Error: Gemini API is not configured."
            return
        client = self._client

        temp = temperature if temperature is not None else self.temperature
        config = types.GenerateContentConfig(
            temperature=temp,
            max_output_tokens=self.max_output_tokens,
            system_instruction=system_instruction,
        )

        try:
            response_stream = await client.aio.models.generate_content_stream(
                model=self.model_name,
                contents=prompt,
                config=config,
            )
            async for chunk in response_stream:
                if chunk.text:
                    yield chunk.text
        except Exception as e:
            logger.error(f"Error in Gemini streaming generation: {e}")
            yield f"\n[Generation error: {str(e)}]"

    def _parse_structured_output(self, raw_text: str) -> RAGGenerationOutput:
        """
        Parse Gemini JSON output safely into validated Pydantic model.
        Falls back to regex extraction if JSON envelope is nested or wrapped in markdown fences.
        """
        cleaned = raw_text.strip()
        # Remove potential markdown json fences
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        elif cleaned.startswith("```"):
            cleaned = cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()

        try:
            data = json.loads(cleaned)
            return RAGGenerationOutput.model_validate(data)
        except Exception as parse_err:
            logger.warning(f"Failed direct JSON parse of Gemini output: {parse_err}. Attempting recovery...")
            # Fallback regex extraction of answer
            answer_match = re.search(r'"answer"\s*:\s*"((?:[^"\\]|\\.)*)"', cleaned, re.DOTALL)
            if answer_match:
                extracted_ans = answer_match.group(1).encode().decode("unicode_escape")
                return RAGGenerationOutput(
                    answer=extracted_ans,
                    citations=[],
                    confidence="medium",
                    insufficient_evidence=False,
                )
            # Safe raw text fallback
            return RAGGenerationOutput(
                answer=cleaned or "Could not verify official information from the supplied notices.",
                citations=[],
                confidence="low",
                insufficient_evidence=True,
            )


# Process-level singleton
_global_gemini_service: Optional[GeminiService] = None


def get_gemini_service() -> GeminiService:
    """Return singleton instance of GeminiService."""
    global _global_gemini_service
    if _global_gemini_service is None:
        _global_gemini_service = GeminiService()
    return _global_gemini_service
