"""
MAYA Milestone 6 Comprehensive Test Suite.
Verifies Multimodal Configuration, Magic Byte & Size Validation,
Image Understanding & Official Notice Cross-checking,
Document Extraction & Conversation-Level Isolation (Privacy Guarantee),
Audio Processing & Duration Limits,
and Multimodal REST API Endpoints.
All tests run with zero external network dependencies via mocks where required.
"""

import asyncio
import io
import os
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import httpx
from PIL import Image

from app.config import get_settings
from app.services.file_validator import FileValidator, FileValidationError
from app.services.image_understanding import ImageUnderstandingService
from app.services.document_understanding import DocumentUnderstandingService
from app.services.audio_understanding import AudioUnderstandingService
from app.schemas.multimodal import MultimodalResponse, ImageUnderstandingResult, AudioUnderstandingResult
from app.main import app

settings = get_settings()


# =============================================================================
# 1. CONFIGURATION TESTS
# =============================================================================

def test_milestone6_settings():
    """Verify strict Milestone 6 configuration parameters."""
    assert settings.MAX_IMAGE_SIZE_MB == 10
    assert settings.MAX_DOCUMENT_SIZE_MB == 30
    assert settings.MAX_AUDIO_SIZE_MB == 20
    assert settings.MAX_AUDIO_DURATION_SECONDS == 300
    assert settings.OCR_ENABLED is True
    assert settings.PDF_WORKERS == 8
    assert settings.PDF_DOWNLOAD_CONCURRENCY == 10


# =============================================================================
# 2. FILE VALIDATOR TESTS (MAGIC BYTES & SECURITY)
# =============================================================================

def test_file_validator_magic_bytes_detection():
    """Verify magic byte detection for valid image, pdf, and audio."""
    # Valid PNG
    png_bytes = b"\x89PNG\r\n\x1a\n" + b"\x00" * 50
    ext, mime = FileValidator.validate_image_bytes(png_bytes, "test.png")
    assert ext == ".png"
    assert mime == "image/png"

    # Valid JPEG
    jpeg_bytes = b"\xff\xd8\xff\xe0" + b"\x00" * 50
    ext, mime = FileValidator.validate_image_bytes(jpeg_bytes, "test.jpg")
    assert ext == ".jpg"
    assert mime == "image/jpeg"

    # Valid PDF
    pdf_bytes = b"%PDF-1.5" + b"\x00" * 50
    ext, mime = FileValidator.validate_document_bytes(pdf_bytes, "test.pdf")
    assert ext == ".pdf"
    assert mime == "application/pdf"

    # Valid WAV
    wav_bytes = b"RIFF" + b"\x00\x00\x00\x00" + b"WAVE" + b"\x00" * 50
    ext, mime, dur = FileValidator.validate_audio_bytes(wav_bytes, "test.wav")
    assert ext == ".wav"
    assert mime == "audio/wav"

    # Valid MP3
    mp3_bytes = b"ID3" + b"\x00" * 50
    ext, mime, dur = FileValidator.validate_audio_bytes(mp3_bytes, "test.mp3")
    assert ext == ".mp3"
    assert mime == "audio/mpeg"


def test_file_validator_spoof_detection():
    """Reject spoofed files where extension does not match magic bytes."""
    fake_txt = b"Hello world"
    with pytest.raises(FileValidationError):
        FileValidator.validate_document_bytes(fake_txt, "fake_notice.txt")

    with pytest.raises(FileValidationError):
        FileValidator.validate_image_bytes(b"short", "fake.png")


def test_file_validator_size_limits():
    """Reject files that exceed the configured size ceilings."""
    oversized = b"\x89PNG\r\n\x1a\n" + b"\x00" * (11 * 1024 * 1024)
    with pytest.raises(FileValidationError) as exc:
        FileValidator.validate_image_bytes(oversized, "huge.png")
    assert "exceeds maximum allowed" in str(exc.value)


def test_file_validator_path_traversal_sanitization():
    """Ensure directory traversal attacks in filenames are neutralized."""
    clean = FileValidator.sanitize_filename("../../etc/evil_passwd.png")
    assert ".." not in clean
    assert clean == "evil_passwd.png"

    clean_win = FileValidator.sanitize_filename("C:\\Windows\\System32\\bad.dll")
    assert "\\" not in clean_win
    assert "bad.dll" in clean_win


# =============================================================================
# 3. IMAGE UNDERSTANDING SERVICE TESTS
# =============================================================================

def test_image_resizing_on_large_images():
    """Verify that images larger than 2048px are safely resized."""
    service = ImageUnderstandingService()

    img = Image.new("RGB", (3000, 2000), color=(255, 0, 0))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    raw_bytes = buf.getvalue()

    resized_bytes = service._resize_if_needed(raw_bytes, "image/jpeg")
    with Image.open(io.BytesIO(resized_bytes)) as r_img:
        w, h = r_img.size
        assert max(w, h) <= 2048
        assert abs((w / h) - 1.5) < 0.05


def test_image_understanding_analysis():
    """Test image analysis with mock Gemini response."""
    async def _test():
        service = ImageUnderstandingService()

        img = Image.new("RGB", (200, 100), color=(255, 255, 255))
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        img_bytes = buf.getvalue()

        mock_gemini_json = (
            '{"extracted_text": "GGSIPU End Term Examination 2026", '
            '"explanation": "Official notice regarding end term examination guidelines.", '
            '"is_university_notice": true, '
            '"identified_dates": ["2026-05-10"], '
            '"search_query": "End Term Examination 2026"}'
        )

        mock_client = MagicMock()
        mock_generate = AsyncMock()
        mock_res = MagicMock()
        mock_res.text = mock_gemini_json
        mock_generate.return_value = mock_res
        mock_client.aio.models.generate_content = mock_generate

        with patch.object(service.gemini_service, "_client", mock_client), \
             patch.object(service.retrieval_service, "retrieve_relevant_chunks", AsyncMock(return_value=[])):
            result = await service.analyze_image(
                image_bytes=img_bytes,
                filename="notice.png",
                question="What is this notice about?",
            )

            assert result.is_university_notice is True
            assert "End Term Examination" in result.extracted_text
            assert "2026-05-10" in result.identified_dates

    asyncio.run(_test())


# =============================================================================
# 4. DOCUMENT UNDERSTANDING & CONVERSATION ISOLATION (PRIVACY)
# =============================================================================

def test_document_conversation_isolation(tmp_path):
    """
    STRICT PRIVACY TEST:
    A user document uploaded in Conversation A must NEVER be discoverable
    or retrievable from Conversation B.
    """
    service = DocumentUnderstandingService()

    with patch.object(service.pdf_extractor, "extract_pdf") as mock_extract:
        mock_extract.return_value = {
            "full_text": "Guru Gobind Singh Indraprastha University Secret Syllabus 2026. Module A, Module B.",
            "total_pages": 1,
            "pages": [{"page_number": 1, "text": "Secret Syllabus 2026."}],
        }

        doc_a = tmp_path / "doc_a.pdf"
        doc_a.write_bytes(b"%PDF-1.5" + b"\x00" * 50)

        service.index_user_document(
            conversation_id="conv_user_secret_A",
            document_id="doc_secret_1",
            file_path=str(doc_a),
            filename="confidential_syllabus.pdf",
        )

        # 1. Search in Conversation A -> MUST FIND IT
        res_a = service.search_user_document(
            conversation_id="conv_user_secret_A",
            query="syllabus",
        )
        assert len(res_a) > 0
        assert res_a[0].filename == "confidential_syllabus.pdf"

        # 2. Search in Conversation B -> MUST RETURN EMPTY (ZERO DATA LEAKAGE)
        res_b = service.search_user_document(
            conversation_id="conv_user_unauthorized_B",
            query="syllabus",
        )
        assert len(res_b) == 0


# =============================================================================
# 5. AUDIO UNDERSTANDING SERVICE TESTS
# =============================================================================

def test_audio_understanding_transcription():
    """Test audio analysis with mock Gemini response."""
    async def _test():
        service = AudioUnderstandingService()

        wav_bytes = b"RIFF" + b"\x00" * 4 + b"WAVEfmt " + b"\x10\x00\x00\x00\x01\x00\x01\x00D\xac\x00\x00\x88X\x01\x00\x02\x00\x10\x00data" + b"\x00" * 100

        mock_gemini_json = (
            '{"transcription": "When is the last date to submit the exam form?", '
            '"summary": "Student inquiring about examination form submission deadline.", '
            '"key_points": ["Examination form deadline inquiry", "Academic semester end-term"], '
            '"answer": "The submission deadline is announced on the official portal."}'
        )

        mock_client = MagicMock()
        mock_generate = AsyncMock()
        mock_res = MagicMock()
        mock_res.text = mock_gemini_json
        mock_generate.return_value = mock_res
        mock_client.aio.models.generate_content = mock_generate

        with patch.object(service.gemini_service, "_client", mock_client):
            result = await service.analyze_audio(
                audio_bytes=wav_bytes,
                filename="voice_query.wav",
            )

            assert "exam form" in result.transcription
            assert len(result.key_points) == 2
            assert "submission deadline" in result.summary

    asyncio.run(_test())


# =============================================================================
# 6. MULTIMODAL REST API ENDPOINT TESTS
# =============================================================================

def test_multimodal_api_status():
    """Verify GET /api/v1/status reports multimodal_interaction as ready."""
    async def _test():
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            res = await client.get("/api/v1/status")
            assert res.status_code == 200
            data = res.json()
            assert data["subsystems"]["multimodal_interaction"] == "ready"

    asyncio.run(_test())


def test_multimodal_api_image_upload():
    """Verify POST /api/v1/multimodal/image endpoint."""
    async def _test():
        img = Image.new("RGB", (100, 100), color=(200, 200, 200))
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        png_bytes = buf.getvalue()

        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            with patch("app.services.image_understanding.ImageUnderstandingService.analyze_image") as mock_img:
                mock_img.return_value = ImageUnderstandingResult(
                    extracted_text="Notice regarding exam fee",
                    explanation="Exam fee notice summary",
                    is_university_notice=True,
                    identified_dates=[],
                    official_verification="Verified against official records.",
                    citations=[],
                )

                files = {"file": ("fee_notice.png", png_bytes, "image/png")}
                data = {"prompt": "What is the fee?"}
                res = await client.post("/api/v1/multimodal/image", files=files, data=data)

                assert res.status_code == 200
                res_data = res.json()
                assert res_data["attachment"]["file_type"] == "image"
                assert "Exam fee notice summary" in res_data["content"]
                assert res_data["metadata"]["result"]["is_university_notice"] is True

    asyncio.run(_test())


def test_multimodal_api_spoofed_file_rejected():
    """Verify POST /api/v1/multimodal/document rejects invalid file with 400."""
    async def _test():
        fake_txt = b"short"
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            files = {"file": ("malicious.pdf", fake_txt, "application/pdf")}
            res = await client.post("/api/v1/multimodal/document", files=files)
            assert res.status_code == 400

    asyncio.run(_test())


def test_multimodal_api_attachment_retrieval():
    """Verify GET /api/v1/multimodal/attachments/{conv_id}/{filename} securely serves uploaded files."""
    async def _test():
        png_bytes = b"\x89PNG\r\n\x1a\n" + b"\x00" * 30
        meta = FileValidator.save_upload(
            data=png_bytes,
            original_filename="verified_doc.png",
            conversation_id="conv_serve_test",
            file_type="image",
        )
        stored_name = os.path.basename(meta.storage_path)

        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            res = await client.get(f"/api/v1/multimodal/attachments/conv_serve_test/{stored_name}")
            assert res.status_code == 200
            assert res.content == png_bytes

            # Path traversal check
            bad_res = await client.get("/api/v1/multimodal/attachments/conv_serve_test/..%2F..%2Fsecret.txt")
            assert bad_res.status_code in [400, 404]

    asyncio.run(_test())
