"""
File Validation and Secure Storage Service.
Validates magic numbers, MIME types, and size boundaries for multimodal uploads.
Prevents path traversal, sanitizes filenames, and isolates conversation directories.
"""

import io
import logging
import os
from pathlib import Path
import re
import uuid
import wave
import zipfile
from typing import Dict, Optional, Tuple

from app.config import get_settings
from app.schemas.multimodal import AttachmentMetadata

logger = logging.getLogger("maya.file_validator")
settings = get_settings()

# Allowed MIME and extension mappings
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
IMAGE_MIMES = {"image/jpeg", "image/png", "image/webp"}

DOC_EXTENSIONS = {".pdf", ".docx"}
DOC_MIMES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}

AUDIO_EXTENSIONS = {".wav", ".mp3", ".m4a", ".aac", ".webm", ".ogg"}
AUDIO_MIMES = {
    "audio/wav",
    "audio/x-wav",
    "audio/wave",
    "audio/mpeg",
    "audio/mp3",
    "audio/mp4",
    "audio/x-m4a",
    "audio/aac",
    "audio/webm",
    "audio/ogg",
}


class FileValidationError(Exception):
    """Raised when file validation fails."""
    pass


class FileValidator:
    """Validates uploaded media formats, sizes, and magic signatures."""

    @classmethod
    def sanitize_filename(cls, filename: str) -> str:
        """Strip dangerous path characters and control characters from client filename."""
        clean = Path(filename).name
        clean = re.sub(r'[\\/*?:"<>|\x00-\x1F]', "_", clean)
        return clean.strip() or "attachment"

    @classmethod
    def validate_image_bytes(cls, data: bytes, filename: str) -> Tuple[str, str]:
        """
        Validate image magic signatures and size.
        Returns: (file_extension, mime_type)
        """
        max_bytes = settings.MAX_IMAGE_SIZE_MB * 1024 * 1024
        if len(data) > max_bytes:
            raise FileValidationError(
                f"Image exceeds maximum allowed size of {settings.MAX_IMAGE_SIZE_MB}MB ({len(data) / (1024 * 1024):.1f}MB uploaded)."
            )

        if len(data) < 16:
            raise FileValidationError("Uploaded image file is empty or corrupt.")

        # Check magic bytes
        if data.startswith(b"\xff\xd8\xff"):
            return ".jpg", "image/jpeg"
        elif data.startswith(b"\x89PNG\r\n\x1a\n"):
            return ".png", "image/png"
        elif data[:4] == b"RIFF" and data[8:12] == b"WEBP":
            return ".webp", "image/webp"

        # Fallback check extension if signature is ambiguous
        ext = Path(filename).suffix.lower()
        if ext in {".jpg", ".jpeg"}:
            return ".jpg", "image/jpeg"
        elif ext == ".png":
            return ".png", "image/png"
        elif ext == ".webp":
            return ".webp", "image/webp"

        raise FileValidationError("Unsupported image format. Allowed formats: JPG, JPEG, PNG, WEBP.")

    @classmethod
    def validate_document_bytes(cls, data: bytes, filename: str) -> Tuple[str, str]:
        """
        Validate document magic signatures and size.
        Returns: (file_extension, mime_type)
        """
        max_bytes = settings.MAX_DOCUMENT_SIZE_MB * 1024 * 1024
        if len(data) > max_bytes:
            raise FileValidationError(
                f"Document exceeds maximum allowed size of {settings.MAX_DOCUMENT_SIZE_MB}MB ({len(data) / (1024 * 1024):.1f}MB uploaded)."
            )

        if len(data) < 16:
            raise FileValidationError("Uploaded document is empty or corrupt.")

        # PDF signature check
        if data.startswith(b"%PDF-"):
            return ".pdf", "application/pdf"

        # DOCX signature check (ZIP archive containing [Content_Types].xml)
        if data.startswith(b"\x50\x4b\x03\x04"):
            try:
                with zipfile.ZipFile(io.BytesIO(data)) as zf:
                    names = zf.namelist()
                    if "[Content_Types].xml" in names or any(n.startswith("word/") for n in names):
                        return (
                            ".docx",
                            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                        )
            except Exception:
                pass

        ext = Path(filename).suffix.lower()
        if ext == ".pdf":
            return ".pdf", "application/pdf"
        elif ext == ".docx":
            return (
                ".docx",
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )

        raise FileValidationError("Unsupported document format. Allowed formats: PDF, DOCX.")

    @classmethod
    def validate_audio_bytes(cls, data: bytes, filename: str) -> Tuple[str, str, Optional[float]]:
        """
        Validate audio magic signatures, size, and duration.
        Returns: (file_extension, mime_type, duration_seconds)
        """
        max_bytes = settings.MAX_AUDIO_SIZE_MB * 1024 * 1024
        if len(data) > max_bytes:
            raise FileValidationError(
                f"Audio file exceeds maximum allowed size of {settings.MAX_AUDIO_SIZE_MB}MB ({len(data) / (1024 * 1024):.1f}MB uploaded)."
            )

        if len(data) < 16:
            raise FileValidationError("Uploaded audio file is empty or corrupt.")

        duration_sec: Optional[float] = None
        ext: str = ""
        mime: str = ""

        # WAV detection
        if data[:4] == b"RIFF" and data[8:12] == b"WAVE":
            ext = ".wav"
            mime = "audio/wav"
            try:
                with wave.open(io.BytesIO(data), "rb") as wf:
                    frames = wf.getnframes()
                    rate = wf.getframerate()
                    if rate > 0:
                        duration_sec = round(frames / float(rate), 2)
            except Exception:
                pass

        # MP3 detection
        elif (
            data.startswith(b"ID3")
            or data[:2] in (b"\xff\xfb", b"\xff\xf3", b"\xff\xf2")
        ):
            ext = ".mp3"
            mime = "audio/mpeg"
            # Approximate duration from 128kbps standard bitrate if unparsed
            duration_sec = round(len(data) / (16 * 1024), 2)

        # M4A / AAC detection
        elif data[4:8] == b"ftyp" or data[:2] in (b"\xff\xf1", b"\xff\xf9"):
            ext = ".m4a"
            mime = "audio/mp4"
            duration_sec = round(len(data) / (16 * 1024), 2)

        # WebM / OGG detection
        elif data[:4] == b"\x1a\x45\xdf\xa3":
            ext = ".webm"
            mime = "audio/webm"
            duration_sec = round(len(data) / (16 * 1024), 2)

        elif data[:4] == b"OggS":
            ext = ".ogg"
            mime = "audio/ogg"
            duration_sec = round(len(data) / (16 * 1024), 2)

        else:
            # Fallback by extension
            file_ext = Path(filename).suffix.lower()
            if file_ext in AUDIO_EXTENSIONS:
                ext = file_ext
                mime = "audio/wav" if file_ext == ".wav" else ("audio/mpeg" if file_ext == ".mp3" else "audio/mp4")
                duration_sec = round(len(data) / (16 * 1024), 2)
            else:
                raise FileValidationError("Unsupported audio format. Allowed formats: WAV, MP3, M4A, AAC.")

        # Validate maximum duration
        if duration_sec and duration_sec > settings.MAX_AUDIO_DURATION_SECONDS:
            raise FileValidationError(
                f"Audio duration ({duration_sec:.0f}s) exceeds maximum allowed {settings.MAX_AUDIO_DURATION_SECONDS}s (5 minutes)."
            )

        return ext, mime, duration_sec

    @classmethod
    def save_upload(
        cls,
        data: bytes,
        original_filename: str,
        conversation_id: str,
        file_type: str,
    ) -> AttachmentMetadata:
        """
        Save validated file into conversation-isolated storage directory.
        Generates random UUID storage name to eliminate path traversal vulnerabilities.
        """
        clean_name = cls.sanitize_filename(original_filename)
        duration_sec = None

        if file_type == "image":
            ext, mime = cls.validate_image_bytes(data, clean_name)
        elif file_type in ("pdf", "docx", "document"):
            ext, mime = cls.validate_document_bytes(data, clean_name)
            file_type = "pdf" if ext == ".pdf" else "docx"
        elif file_type == "audio":
            ext, mime, duration_sec = cls.validate_audio_bytes(data, clean_name)
        else:
            raise FileValidationError(f"Invalid file type category: '{file_type}'.")

        # Isolated directory for conversation
        target_dir = Path(settings.UPLOAD_DIR) / conversation_id
        target_dir.mkdir(parents=True, exist_ok=True)

        attachment_id = str(uuid.uuid4())
        safe_filename = f"{attachment_id}{ext}"
        storage_path = target_dir / safe_filename

        with open(storage_path, "wb") as f:
            f.write(data)

        logger.info(
            f"Saved {file_type} attachment '{clean_name}' ({len(data)} bytes) to {storage_path}"
        )

        return AttachmentMetadata(
            id=attachment_id,
            filename=clean_name,
            file_type=file_type,
            size_bytes=len(data),
            mime_type=mime,
            storage_path=str(storage_path),
            download_url=f"/api/v1/multimodal/attachments/{conversation_id}/{safe_filename}",
            duration_seconds=duration_sec,
        )
