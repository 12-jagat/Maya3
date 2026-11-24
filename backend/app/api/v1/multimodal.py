"""
Multimodal API Endpoints (Image, Document, Audio, and Voice Uploads).
Integrates with conversation persistence and RAG services.
"""

import logging
import os
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status
from fastapi.responses import FileResponse

from app.config import get_settings
from app.schemas.multimodal import (
    AttachmentMetadata,
    MultimodalResponse,
)
from app.services.audio_understanding import get_audio_understanding_service
from app.services.conversation_service import get_conversation_service
from app.services.document_understanding import get_document_understanding_service
from app.services.file_validator import FileValidator, FileValidationError
from app.services.image_understanding import get_image_understanding_service

router = APIRouter(prefix="/multimodal", tags=["Multimodal Assistant"])
logger = logging.getLogger("maya.api.multimodal")
settings = get_settings()


@router.post("/image", response_model=MultimodalResponse, status_code=status.HTTP_200_OK)
async def process_image_upload(
    file: UploadFile = File(...),
    conversation_id: Optional[str] = Form(None),
    question: Optional[str] = Form(None),
    prompt: Optional[str] = Form(None),
):
    """
    Process an uploaded image (JPG, PNG, WEBP).
    Performs Gemini vision extraction, cross-references with official circulars, and stores interaction.
    """
    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail="Uploaded image is empty.")

    conv_svc = get_conversation_service()
    raw_prompt = question or prompt or ""
    user_prompt = raw_prompt.strip() if raw_prompt.strip() else "Analyze this image."

    # 1. Initialize conversation
    conv = await conv_svc.get_or_create_conversation(
        conversation_id=conversation_id,
        initial_prompt=f"[Image: {file.filename}] {user_prompt}",
    )
    active_conv_id = conv["id"]

    # 2. Validate and save image attachment
    try:
        attachment = FileValidator.save_upload(
            data=file_bytes,
            original_filename=file.filename or "image.jpg",
            conversation_id=active_conv_id,
            file_type="image",
        )
    except FileValidationError as fve:
        raise HTTPException(status_code=400, detail=str(fve))

    # 3. Record user message
    await conv_svc.add_message(
        conversation_id=active_conv_id,
        role="user",
        content=f"[Attached Image: {attachment.filename}]\n{user_prompt}",
        metadata={"attachment": attachment.model_dump()},
    )

    # 4. Image understanding
    img_svc = get_image_understanding_service()
    result = await img_svc.analyze_image(
        image_bytes=file_bytes,
        filename=attachment.filename,
        question=user_prompt,
        conversation_id=active_conv_id,
    )

    content_text = result.explanation
    if result.official_verification:
        content_text += f"\n\n---\n**Official University Cross-Check:**\n{result.official_verification}"

    # 5. Record assistant response
    asst_msg = await conv_svc.add_message(
        conversation_id=active_conv_id,
        role="assistant",
        content=content_text,
        citations=[c.model_dump() for c in result.citations],
        metadata={
            "is_university_notice": result.is_university_notice,
            "identified_dates": result.identified_dates,
            "attachment_id": attachment.id,
        },
    )

    return MultimodalResponse(
        conversation_id=active_conv_id,
        message_id=asst_msg["id"],
        role="assistant",
        content=content_text,
        attachment=attachment,
        citations=result.citations,
        confidence="high" if result.is_university_notice else "medium",
        insufficient_evidence=False,
        created_at=asst_msg["created_at"],
        metadata={"result": result.model_dump()},
    )


@router.post("/document", response_model=MultimodalResponse, status_code=status.HTTP_200_OK)
async def process_document_upload(
    file: UploadFile = File(...),
    conversation_id: Optional[str] = Form(None),
    question: Optional[str] = Form(None),
    prompt: Optional[str] = Form(None),
):
    """
    Process an uploaded PDF or DOCX circular/document.
    Maintains conversation-isolated extraction, chunking, and question answering.
    """
    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail="Uploaded document is empty.")

    conv_svc = get_conversation_service()
    raw_prompt = question or prompt or ""
    user_prompt = raw_prompt.strip() if raw_prompt.strip() else "Summarize this document."

    # 1. Initialize conversation
    conv = await conv_svc.get_or_create_conversation(
        conversation_id=conversation_id,
        initial_prompt=f"[Document: {file.filename}] {user_prompt}",
    )
    active_conv_id = conv["id"]

    # 2. Validate and save document attachment
    try:
        attachment = FileValidator.save_upload(
            data=file_bytes,
            original_filename=file.filename or "document.pdf",
            conversation_id=active_conv_id,
            file_type="document",
        )
    except FileValidationError as fve:
        raise HTTPException(status_code=400, detail=str(fve))

    # 3. Record user message
    await conv_svc.add_message(
        conversation_id=active_conv_id,
        role="user",
        content=f"[Attached Document: {attachment.filename}]\n{user_prompt}",
        metadata={"attachment": attachment.model_dump()},
    )

    # 4. Document understanding
    doc_svc = get_document_understanding_service()
    result = await doc_svc.analyze_document(
        conversation_id=active_conv_id,
        document_id=attachment.id,
        filename=attachment.filename,
        file_path=attachment.storage_path or "",
        question=user_prompt,
    )

    attachment.page_count = result.page_count

    response_text = result.answer
    if result.summary and result.summary != result.answer:
        response_text = f"**Document Summary ({result.filename}, {result.page_count} pages):**\n{result.summary}\n\n**Details:**\n{result.answer}"

    # 5. Record assistant response
    asst_msg = await conv_svc.add_message(
        conversation_id=active_conv_id,
        role="assistant",
        content=response_text,
        citations=[c.model_dump() for c in result.citations],
        metadata={
            "page_count": result.page_count,
            "relevant_pages": result.relevant_pages,
            "attachment_id": attachment.id,
        },
    )

    return MultimodalResponse(
        conversation_id=active_conv_id,
        message_id=asst_msg["id"],
        role="assistant",
        content=response_text,
        attachment=attachment,
        citations=result.citations,
        confidence="high",
        insufficient_evidence=False,
        created_at=asst_msg["created_at"],
        metadata={"result": result.model_dump()},
    )


@router.post("/audio", response_model=MultimodalResponse, status_code=status.HTTP_200_OK)
async def process_audio_upload(
    file: UploadFile = File(...),
    conversation_id: Optional[str] = Form(None),
    question: Optional[str] = Form(None),
    prompt: Optional[str] = Form(None),
):
    """
    Process an uploaded audio recording (WAV, MP3, M4A, AAC).
    Performs speech transcription and understanding via Gemini.
    """
    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail="Uploaded audio file is empty.")

    conv_svc = get_conversation_service()
    raw_prompt = question or prompt or ""
    user_prompt = raw_prompt.strip() if raw_prompt.strip() else "Transcribe and summarize this recording."

    # 1. Initialize conversation
    conv = await conv_svc.get_or_create_conversation(
        conversation_id=conversation_id,
        initial_prompt=f"[Audio: {file.filename}] {user_prompt}",
    )
    active_conv_id = conv["id"]

    # 2. Validate and save audio attachment
    try:
        attachment = FileValidator.save_upload(
            data=file_bytes,
            original_filename=file.filename or "recording.wav",
            conversation_id=active_conv_id,
            file_type="audio",
        )
    except FileValidationError as fve:
        raise HTTPException(status_code=400, detail=str(fve))

    # 3. Record user message
    await conv_svc.add_message(
        conversation_id=active_conv_id,
        role="user",
        content=f"[Attached Audio: {attachment.filename}]\n{user_prompt}",
        metadata={"attachment": attachment.model_dump()},
    )

    # 4. Audio understanding
    audio_svc = get_audio_understanding_service()
    result = await audio_svc.analyze_audio(
        audio_bytes=file_bytes,
        filename=attachment.filename,
        question=user_prompt,
        conversation_id=active_conv_id,
    )

    response_text = f"**Audio Transcription:**\n> {result.transcription}\n\n**Summary:**\n{result.summary}"
    if result.key_points:
        response_text += "\n\n**Key Takeaways:**\n" + "\n".join(f"- {kp}" for kp in result.key_points)
    if result.answer and result.answer != result.summary:
        response_text += f"\n\n**Response to Question:**\n{result.answer}"

    # 5. Record assistant response
    asst_msg = await conv_svc.add_message(
        conversation_id=active_conv_id,
        role="assistant",
        content=response_text,
        metadata={
            "transcription": result.transcription,
            "attachment_id": attachment.id,
        },
    )

    return MultimodalResponse(
        conversation_id=active_conv_id,
        message_id=asst_msg["id"],
        role="assistant",
        content=response_text,
        attachment=attachment,
        citations=[],
        confidence="high",
        insufficient_evidence=False,
        created_at=asst_msg["created_at"],
        metadata={"result": result.model_dump()},
    )


@router.get("/attachments/{conversation_id}/{filename}")
async def get_attachment_file(conversation_id: str, filename: str):
    """Securely stream or preview user-uploaded media with conversation scoping."""
    clean_filename = Path(filename).name
    target_path = Path(settings.UPLOAD_DIR) / conversation_id / clean_filename

    if not target_path.exists() or not target_path.is_file():
        raise HTTPException(status_code=404, detail="Attachment not found.")

    return FileResponse(path=str(target_path))
