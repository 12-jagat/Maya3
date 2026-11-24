"""
Audio Understanding and Transcription Service for MAYA.
Processes uploaded audio files (WAV, MP3, M4A, AAC) using Gemini Audio Capabilities
through the official Google GenAI Python SDK.
"""

import json
import logging
from typing import List, Optional

from app.config import get_settings
from app.schemas.multimodal import AudioUnderstandingResult
from app.services.file_validator import FileValidator, FileValidationError
from app.services.gemini_service import get_gemini_service
from google.genai import types

logger = logging.getLogger("maya.audio_understanding")
settings = get_settings()

AUDIO_SYSTEM_INSTRUCTION = """
You are MAYA's University Audio Understanding Specialist.
Your task is to transcribe and analyze uploaded audio recordings (such as classroom lectures, official announcements, voice notes, or discussions among GGSIPU students).

RULES:
1. Provide a verbatim or clean transcription of the spoken audio.
2. Provide a concise 2-4 sentence summary of the recording.
3. Extract key bullet points, deadlines, dates, instructions, or course details mentioned.
4. Answer any specific question asked by the student regarding the audio.
5. If the audio is unclear, noisy, cut off, or unintelligible in parts, explicitly note that.
6. Never fabricate speaker identities, fake official endorsements, or university circular numbers not mentioned in the audio.

Return your response strictly in the following JSON format:
{
  "transcription": "<complete speech transcription>",
  "summary": "<2-4 sentence summary of the audio>",
  "key_points": ["<point 1>", "<point 2>"],
  "answer": "<answer to the student's specific question, or a brief recap if no question was provided>"
}
"""


class AudioUnderstandingService:
    """Processes audio files with Google Gemini and formats structured transcriptions."""

    def __init__(self):
        self.gemini_service = get_gemini_service()

    async def analyze_audio(
        self,
        audio_bytes: bytes,
        filename: str,
        question: Optional[str] = None,
        conversation_id: Optional[str] = None,
    ) -> AudioUnderstandingResult:
        """
        Transcribe and analyze uploaded audio using Gemini.
        """
        # 1. Validation
        ext, mime, duration_sec = FileValidator.validate_audio_bytes(audio_bytes, filename)

        user_prompt = question.strip() if question and question.strip() else "Transcribe and summarize this audio recording."

        # 2. Build Gemini Audio Payload using official SDK
        if not self.gemini_service.is_configured or self.gemini_service._client is None:
            return AudioUnderstandingResult(
                transcription="[Audio transcription unavailable - Gemini API key not configured]",
                summary="Uploaded audio received successfully.",
                key_points=[],
                answer="Gemini audio processing is not configured on the server.",
                official_verification=None,
            )

        client = self.gemini_service._client
        audio_part = types.Part.from_bytes(data=audio_bytes, mime_type=mime)
        contents = [audio_part, user_prompt]

        config = types.GenerateContentConfig(
            temperature=0.2,
            max_output_tokens=2048,
            system_instruction=AUDIO_SYSTEM_INSTRUCTION,
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
                res = await client.aio.models.generate_content(
                    model=current_model,
                    contents=contents,
                    config=config,
                )
                raw_text = res.text or "{}"
                last_err = None
                break
            except Exception as e:
                last_err = e
                logger.warning(f"Error calling Gemini for audio on {current_model}: {e}")

        if last_err is not None:
            logger.error(f"Error calling Gemini for audio understanding: {last_err}")
            return AudioUnderstandingResult(
                transcription="Could not transcribe audio.",
                summary=f"Audio processing error: {str(last_err)}",
                key_points=[],
                answer="An error occurred while processing the audio recording.",
                official_verification=None,
            )

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
                "transcription": cleaned,
                "summary": "Audio analyzed.",
                "key_points": [],
                "answer": cleaned,
            }

        return AudioUnderstandingResult(
            transcription=data.get("transcription", ""),
            summary=data.get("summary", ""),
            key_points=data.get("key_points", []),
            answer=data.get("answer", data.get("summary", "")),
            official_verification=None,
        )


# Singleton
_audio_understanding_service: Optional[AudioUnderstandingService] = None


def get_audio_understanding_service() -> AudioUnderstandingService:
    global _audio_understanding_service
    if _audio_understanding_service is None:
        _audio_understanding_service = AudioUnderstandingService()
    return _audio_understanding_service
