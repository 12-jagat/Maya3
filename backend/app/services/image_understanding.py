"""
Image Understanding Service for MAYA.
Processes uploaded images (JPG, PNG, WEBP), performs OCR/vision extraction with Gemini,
and cross-references claims against verified GGSIPU circulars in Zilliz.
"""

import io
import json
import logging
import re
from typing import List, Optional, Tuple
from PIL import Image

from app.config import get_settings
from app.schemas.chat import CitationItem
from app.schemas.multimodal import ImageUnderstandingResult
from app.services.file_validator import FileValidator, FileValidationError
from app.services.gemini_service import get_gemini_service
from app.services.retrieval_service import get_retrieval_service
from google.genai import types

logger = logging.getLogger("maya.image_understanding")
settings = get_settings()

MAX_IMAGE_DIMENSION = 2048


IMAGE_SYSTEM_INSTRUCTION = """
You are MAYA's University Image Understanding Specialist.
Your task is to analyze user-uploaded images (which may include photos of university notice boards, examination schedules, screenshots of error messages, circulars, or student portal pages).

ANALYSIS RULES:
1. Extract visible text accurately from the image.
2. Answer the student's question clearly, politely, and thoroughly.
3. Identify whether this appears to be an official GGSIPU university notice or document.
4. Extract any specific dates, deadlines, room numbers, course codes, or fees visible in the image.
5. If the image is blurry, cropped, ambiguous, or lacks crucial details, explicitly point that out.
6. Clearly state that unverified uploaded photos or screenshots are user-provided media, NOT independently certified university documents.

Return your response strictly in the following JSON format:
{
  "extracted_text": "<verbatim or summarized text visible in the image>",
  "explanation": "<your thorough answer to the student question>",
  "is_university_notice": <true or false>,
  "identified_dates": ["<date 1>", "<date 2>"],
  "search_query": "<a 3-8 word query to search official GGSIPU circulars to verify this document>"
}
"""


class ImageUnderstandingService:
    """Processes images with Google Gemini Vision and cross-checks with RAG."""

    def __init__(self):
        self.gemini_service = get_gemini_service()
        self.retrieval_service = get_retrieval_service()

    def _resize_if_needed(self, image_bytes: bytes, mime_type: str) -> bytes:
        """Resize excessively large images to max dimension of 2048px while preserving aspect ratio."""
        try:
            with Image.open(io.BytesIO(image_bytes)) as img:
                width, height = img.size
                if width <= MAX_IMAGE_DIMENSION and height <= MAX_IMAGE_DIMENSION:
                    return image_bytes

                # Calculate new dimensions
                if width > height:
                    new_width = MAX_IMAGE_DIMENSION
                    new_height = int(height * (MAX_IMAGE_DIMENSION / width))
                else:
                    new_height = MAX_IMAGE_DIMENSION
                    new_width = int(width * (MAX_IMAGE_DIMENSION / height))

                resized = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                out_io = io.BytesIO()
                fmt = "JPEG" if "jpeg" in mime_type or "jpg" in mime_type else ("PNG" if "png" in mime_type else "WEBP")
                resized.save(out_io, format=fmt, quality=88)
                return out_io.getvalue()
        except Exception as e:
            logger.warning(f"Image resize check skipped: {e}")
            return image_bytes

    async def analyze_image(
        self,
        image_bytes: bytes,
        filename: str,
        question: Optional[str] = None,
        conversation_id: Optional[str] = None,
    ) -> ImageUnderstandingResult:
        """
        Execute image understanding with Gemini and cross-reference with official circulars.
        """
        # 1. Validation
        ext, mime = FileValidator.validate_image_bytes(image_bytes, filename)
        processed_bytes = self._resize_if_needed(image_bytes, mime)

        user_prompt = question.strip() if question and question.strip() else "Analyze this image and explain the important details for a GGSIPU student."

        # 2. Build Gemini Vision Payload using official SDK
        if not self.gemini_service.is_configured or self.gemini_service._client is None:
            return ImageUnderstandingResult(
                extracted_text="[Vision unavailable - Gemini API key not configured]",
                explanation="I received your image, but Gemini vision processing is not configured on the server.",
                is_university_notice=False,
                identified_dates=[],
                official_verification="Cannot cross-verify without active Gemini service.",
                citations=[],
            )

        client = self.gemini_service._client
        image_part = types.Part.from_bytes(data=processed_bytes, mime_type=mime)
        contents = [image_part, user_prompt]

        config = types.GenerateContentConfig(
            temperature=0.2,
            max_output_tokens=2048,
            system_instruction=IMAGE_SYSTEM_INSTRUCTION,
            response_mime_type="application/json",
        )

        raw_text = "{}"
        candidate_models = [self.gemini_service.model_name]
        for m in ["gemini-2.5-flash", "gemini-3.1-flash-lite", "gemini-3.5-flash"]:
            if m not in candidate_models:
                candidate_models.append(m)

        last_err = None
        for current_model in candidate_models:
            try:
                response = await client.aio.models.generate_content(
                    model=current_model,
                    contents=contents,
                    config=config,
                )
                raw_text = response.text or "{}"
                last_err = None
                break
            except Exception as gen_err:
                last_err = gen_err
                logger.warning(f"Error calling Gemini vision on {current_model}: {gen_err}")

        if last_err is not None:
            logger.error(f"Error calling Gemini vision: {last_err}")
            return ImageUnderstandingResult(
                extracted_text="Could not process image contents.",
                explanation=f"An error occurred while analyzing the image: {str(last_err)}. Please verify the image file.",
                is_university_notice=False,
                identified_dates=[],
                official_verification=None,
                citations=[],
            )

        # 3. Parse Gemini output
        cleaned = raw_text.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        elif cleaned.startswith("```"):
            cleaned = cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()

        try:
            data = json.loads(cleaned)
        except Exception:
            data = {
                "extracted_text": "",
                "explanation": cleaned,
                "is_university_notice": False,
                "identified_dates": [],
                "search_query": "",
            }

        extracted_text = data.get("extracted_text", "")
        explanation = data.get("explanation", cleaned)
        is_notice = bool(data.get("is_university_notice", False))
        identified_dates = data.get("identified_dates", [])
        search_query = data.get("search_query", "").strip()

        # 4. Cross-Verification with Official RAG
        citations: List[CitationItem] = []
        verification_text: Optional[str] = None

        if is_notice and (search_query or extracted_text):
            verification_query = search_query or " ".join(extracted_text.split()[:8])
            try:
                retrieved_chunks = await self.retrieval_service.retrieve_relevant_chunks(
                    query=verification_query,
                    top_k=2,
                )
                if retrieved_chunks:
                    top_chunk = retrieved_chunks[0]
                    citations.append(
                        CitationItem(
                            source_id="OFFICIAL_SOURCE_1",
                            notice_id=top_chunk.notice_id,
                            title=top_chunk.title,
                            source_url=top_chunk.source_url,
                            pdf_url=top_chunk.pdf_url,
                            page_number=top_chunk.page_number,
                            relevant_excerpt=top_chunk.content[:200] + "...",
                        )
                    )
                    verification_text = (
                        f"Official Verification: Found matching official GGSIPU circular "
                        f"'{top_chunk.title}' (Page {top_chunk.page_number}). "
                        f"Please compare the image with the official published circular."
                    )
                else:
                    verification_text = (
                        "Official Verification: No matching official university circular was found in the indexed database. "
                        "Please verify whether this notice has been officially posted on ipu.ac.in."
                    )
            except Exception as e:
                logger.warning(f"Error during image RAG cross-verification: {e}")

        return ImageUnderstandingResult(
            extracted_text=extracted_text,
            explanation=explanation,
            is_university_notice=is_notice,
            identified_dates=identified_dates,
            official_verification=verification_text,
            citations=citations,
        )


# Singleton
_image_understanding_service: Optional[ImageUnderstandingService] = None


def get_image_understanding_service() -> ImageUnderstandingService:
    global _image_understanding_service
    if _image_understanding_service is None:
        _image_understanding_service = ImageUnderstandingService()
    return _image_understanding_service
