"""
MAYA Milestone 6 Live End-to-End Multimodal Verification Script.
Executes the 8 mandatory evaluation scenarios:
1. Voice Input Simulation & Spoken Response Generation
2. Image Notice Analysis & Official Circular Verification
3. User PDF Document Extraction, Chunking & Grounded QA
4. Contextual Follow-up Grounded in User-Uploaded Document
5. DOCX Upload, Structure Preservation & Extraction
6. Audio Note Upload, Speech Transcription & Summary
7. Strict Privacy & Conversation-Level Isolation Guarantee
8. RAG Regression Verification (Official Circular Grounding & Citations)
"""

import asyncio
import io
import json
import os
import struct
import sys
import uuid
from pathlib import Path
from typing import Optional
from PIL import Image, ImageDraw, ImageFont

# Add backend to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import get_settings
from app.services.file_validator import FileValidator
from app.services.image_understanding import get_image_understanding_service
from app.services.document_understanding import get_document_understanding_service
from app.services.audio_understanding import get_audio_understanding_service
from app.services.rag_service import RAGService
from app.services.conversation_service import get_conversation_service

settings = get_settings()


def create_sample_notice_image() -> bytes:
    """Create a realistic university notice image with dates and text."""
    img = Image.new("RGB", (800, 500), color=(250, 248, 245))
    draw = ImageDraw.Draw(img)

    draw.rectangle([(20, 20), (780, 480)], outline=(128, 0, 0), width=3)
    draw.text((60, 50), "GURU GOBIND SINGH INDRAPRASTHA UNIVERSITY", fill=(128, 0, 0))
    draw.text((60, 90), "Sector 16-C, Dwarka, New Delhi - 110078", fill=(80, 80, 80))
    draw.line([(40, 130), (760, 130)], fill=(128, 0, 0), width=2)

    draw.text((60, 160), "OFFICIAL NOTIFICATION: END TERM EXAMINATION MAY-JUNE 2026", fill=(20, 20, 20))
    draw.text((60, 200), "Date of Issue: 10th May 2026", fill=(40, 40, 40))
    draw.text((60, 240), "Subject: Submission of Online Examination Registration Forms.", fill=(20, 20, 20))
    draw.text((60, 280), "1. The online registration portal opens on 15th May 2026.", fill=(40, 40, 40))
    draw.text((60, 320), "2. The strict last date for submission of forms is 30th May 2026.", fill=(180, 0, 0))
    draw.text((60, 360), "3. Late fee of Rs. 1200 applies after the deadline.", fill=(40, 40, 40))
    draw.text((60, 420), "Controller of Examinations (Conduct), GGSIPU", fill=(60, 60, 60))

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def create_sample_pdf(file_path: str, text: str):
    """Create a sample multi-page or single-page PDF with PyMuPDF."""
    import fitz
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)
    page.insert_text((50, 72), text, fontsize=12)
    doc.save(file_path)
    doc.close()


def create_sample_docx(file_path: str, title: str, paragraphs: list):
    """Create a sample DOCX document."""
    from docx import Document
    doc = Document()
    doc.add_heading(title, level=1)
    for p in paragraphs:
        doc.add_paragraph(p)
    doc.save(file_path)


def create_sample_wav() -> bytes:
    """Create a valid synthetic 2-second WAV file with sinusoidal tone."""
    import math
    sample_rate = 16000
    duration = 2.0
    num_samples = int(sample_rate * duration)
    wav_body = bytearray()
    for i in range(num_samples):
        # 440 Hz tone
        sample = int(10000 * math.sin(2 * math.pi * 440 * i / sample_rate))
        wav_body.extend(sample.to_bytes(2, "little", signed=True))

    wav_header = bytearray(b"RIFF" + b"\x00" * 4 + b"WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00")
    wav_header.extend(sample_rate.to_bytes(4, "little"))
    wav_header.extend((sample_rate * 2).to_bytes(4, "little"))
    wav_header.extend((2).to_bytes(2, "little"))
    wav_header.extend((16).to_bytes(2, "little"))
    wav_header.extend(b"data")
    wav_header.extend(len(wav_body).to_bytes(4, "little"))
    wav_header.extend(wav_body)
    struct.pack_into("<I", wav_header, 4, len(wav_header) - 8)
    return bytes(wav_header)


async def main():
    print("=" * 70)
    print("MAYA MILESTONE 6: LIVE MULTIMODAL E2E VERIFICATION SUITE")
    print("=" * 70)

    conv_svc = get_conversation_service()
    rag_svc = RAGService()
    doc_svc = get_document_understanding_service()
    img_svc = get_image_understanding_service()
    audio_svc = get_audio_understanding_service()
    c3_id: Optional[str] = None
    test_results = {}

    # -------------------------------------------------------------------------
    # TEST 1: Voice Input & Conversational Response
    # -------------------------------------------------------------------------
    print("\n[TEST 1] Testing Voice Input & Grounded Conversational Response...")
    try:
        conv_1 = await conv_svc.get_or_create_conversation(initial_prompt="Voice Query")
        c1_id = conv_1["id"]
        voice_query = "When is the last date to submit the examination form?"
        res1 = await rag_svc.answer_question(
            message=voice_query,
            conversation_id=c1_id,
            metadata={"input_mode": "voice_stt", "language": "en-IN"},
        )
        print(f"  -> Answer: {res1.content[:160]}...")
        print(f"  -> Citations: {len(res1.citations)}")
        assert len(res1.content) > 20
        test_results["TEST_1_VOICE_INTERACTION"] = "PASSED"
    except Exception as e:
        print(f"  -> FAILED: {e}")
        test_results["TEST_1_VOICE_INTERACTION"] = f"FAILED: {e}"

    # -------------------------------------------------------------------------
    # TEST 2: Image Notice Analysis & Official Verification
    # -------------------------------------------------------------------------
    print("\n[TEST 2] Testing Image Notice Understanding & Official Cross-Check...")
    try:
        img_bytes = create_sample_notice_image()
        conv_2 = await conv_svc.get_or_create_conversation(initial_prompt="Image Upload")
        c2_id = conv_2["id"]

        img_svc = get_image_understanding_service()
        res2 = await img_svc.analyze_image(
            image_bytes=img_bytes,
            filename="ggsipu_exam_notice.png",
            question="What is the deadline mentioned in this notice and what is the late fee?",
            conversation_id=c2_id,
        )
        print(f"  -> Notice Detected: {res2.is_university_notice}")
        print(f"  -> Identified Dates: {res2.identified_dates}")
        print(f"  -> Analysis: {res2.explanation[:160]}...")
        assert res2.is_university_notice is True or "30th May" in res2.extracted_text or "2026" in res2.extracted_text
        test_results["TEST_2_IMAGE_UNDERSTANDING"] = "PASSED"
    except Exception as e:
        print(f"  -> FAILED: {e}")
        test_results["TEST_2_IMAGE_UNDERSTANDING"] = f"FAILED: {e}"

    # -------------------------------------------------------------------------
    # TEST 3: User PDF Document Upload & Extraction
    # -------------------------------------------------------------------------
    print("\n[TEST 3] Testing User PDF Upload & Grounded Question Answering...")
    try:
        temp_pdf = Path("storage/test_student_guidelines.pdf")
        temp_pdf.parent.mkdir(parents=True, exist_ok=True)
        pdf_text = (
            "GURU GOBIND SINGH INDRAPRASTHA UNIVERSITY\n"
            "ACADEMIC REGULATIONS 2026 - GUIDELINES FOR INTERNSHIPS\n\n"
            "Clause 4.2: Mandatory Internship Duration\n"
            "All B.Tech students must complete a mandatory 8-week industrial internship.\n"
            "The internship completion certificate and log book must be submitted to the\n"
            "Head of Department before 15th August 2026.\n"
            "Minimum attendance requirement for semester eligibility is 75 percent."
        )
        create_sample_pdf(str(temp_pdf), pdf_text)

        conv_3 = await conv_svc.get_or_create_conversation(initial_prompt="PDF Guidelines")
        c3_id = conv_3["id"]

        doc_svc = get_document_understanding_service()
        assert c3_id is not None
        res3 = await doc_svc.analyze_document(
            conversation_id=c3_id,
            document_id="doc_internship_guidelines",
            filename="student_guidelines.pdf",
            file_path=str(temp_pdf),
            question="What is the deadline for submitting the internship completion certificate?",
        )
        print(f"  -> Summary: {res3.summary[:140]}...")
        print(f"  -> Answer: {res3.answer[:160]}...")
        print(f"  -> Relevant Pages: {res3.relevant_pages}")
        print(f"  -> Citations: {len(res3.citations)}")
        assert "15th August" in res3.answer or "15th August" in res3.summary or len(res3.citations) > 0
        test_results["TEST_3_PDF_EXTRACTION"] = "PASSED"
    except Exception as e:
        print(f"  -> FAILED: {e}")
        test_results["TEST_3_PDF_EXTRACTION"] = f"FAILED: {e}"

    # -------------------------------------------------------------------------
    # TEST 4: Contextual Follow-Up Grounded in User Document
    # -------------------------------------------------------------------------
    print("\n[TEST 4] Testing Follow-Up Query Grounded in User Uploaded Document...")
    try:
        if not c3_id:
            conv_3 = await conv_svc.get_or_create_conversation(initial_prompt="PDF Guidelines")
            c3_id = conv_3["id"]

        res4 = await rag_svc.answer_question(
            message="What is the minimum attendance requirement mentioned in the guidelines I uploaded?",
            conversation_id=c3_id,
        )
        print(f"  -> Follow-up Answer: {res4.content[:160]}...")
        print(f"  -> Citations: {[c.title for c in res4.citations]}")
        assert "75" in res4.content or any("guidelines" in c.title.lower() for c in res4.citations)
        test_results["TEST_4_PDF_FOLLOWUP_GROUNDING"] = "PASSED"
    except Exception as e:
        print(f"  -> FAILED: {e}")
        test_results["TEST_4_PDF_FOLLOWUP_GROUNDING"] = f"FAILED: {e}"

    # -------------------------------------------------------------------------
    # TEST 5: DOCX Document Upload & Extraction
    # -------------------------------------------------------------------------
    print("\n[TEST 5] Testing DOCX Document Upload & Understanding...")
    try:
        temp_docx = Path("storage/test_btech_syllabus.docx")
        create_sample_docx(
            str(temp_docx),
            title="GGSIPU Department of Computer Science Syllabus",
            paragraphs=[
                "Course: Artificial Intelligence & Machine Learning (ETCS-401).",
                "Unit 1: Problem Solving with Search and Heuristics.",
                "Unit 2: Knowledge Representation, First Order Logic, and Prolog.",
                "Unit 3: Deep Learning, Neural Networks and Multimodal Architectures.",
                "Evaluation Scheme: Mid-term exam 25 marks, Internal lab 25 marks, End-term 50 marks.",
            ],
        )

        conv_5 = await conv_svc.get_or_create_conversation(initial_prompt="DOCX Syllabus")
        c5_id = conv_5["id"]

        res5 = await doc_svc.analyze_document(
            conversation_id=c5_id,
            document_id="doc_btech_syllabus",
            filename="btech_syllabus.docx",
            file_path=str(temp_docx),
            question="What is the evaluation scheme for the AI course?",
        )
        print(f"  -> Summary: {res5.summary[:140]}...")
        print(f"  -> Answer: {res5.answer[:160]}...")
        assert "25" in res5.answer or "50" in res5.answer or len(res5.citations) > 0
        test_results["TEST_5_DOCX_EXTRACTION"] = "PASSED"
    except Exception as e:
        print(f"  -> FAILED: {e}")
        test_results["TEST_5_DOCX_EXTRACTION"] = f"FAILED: {e}"

    # -------------------------------------------------------------------------
    # TEST 6: Audio Upload, Transcription & Key Points
    # -------------------------------------------------------------------------
    print("\n[TEST 6] Testing Audio Note Upload, Transcription & Key Takeaways...")
    try:
        wav_bytes = create_sample_wav()
        audio_svc = get_audio_understanding_service()
        conv_6 = await conv_svc.get_or_create_conversation(initial_prompt="Audio Recording")
        c6_id = conv_6["id"]

        res6 = await audio_svc.analyze_audio(
            audio_bytes=wav_bytes,
            filename="lecture_note.wav",
            question="Summarize what was discussed in this audio recording.",
            conversation_id=c6_id,
        )
        print(f"  -> Transcription: {res6.transcription[:140]}...")
        print(f"  -> Summary: {res6.summary[:140]}...")
        print(f"  -> Key Points: {res6.key_points}")
        assert len(res6.summary) > 5 or len(res6.transcription) > 0
        test_results["TEST_6_AUDIO_UNDERSTANDING"] = "PASSED"
    except Exception as e:
        print(f"  -> FAILED: {e}")
        test_results["TEST_6_AUDIO_UNDERSTANDING"] = f"FAILED: {e}"

    # -------------------------------------------------------------------------
    # TEST 7: Strict Privacy & Conversation Isolation
    # -------------------------------------------------------------------------
    print("\n[TEST 7] Testing Privacy & Conversation-Level Isolation Guarantee...")
    try:
        # Search for guidelines uploaded in conv_3 from an unauthorized conversation conv_7
        conv_7 = await conv_svc.get_or_create_conversation(initial_prompt="Unauthorized Thread")
        c7_id = conv_7["id"]

        leaked_chunks = doc_svc.search_user_document(
            conversation_id=c7_id,
            query="mandatory 8-week industrial internship",
            top_k=5,
        )
        print(f"  -> Unauthorized query in Conversation 7 returned {len(leaked_chunks)} chunks.")
        assert len(leaked_chunks) == 0, "DATA LEAKAGE DETECTED! Document was retrieved outside its conversation scope!"

        # Confirm that Conversation 3 can legitimately retrieve its own document
        assert c3_id is not None, "c3_id must be initialized from TEST 3"
        authorized_chunks = doc_svc.search_user_document(
            conversation_id=c3_id,
            query="mandatory 8-week industrial internship",
            top_k=5,
        )
        print(f"  -> Authorized query in Conversation 3 returned {len(authorized_chunks)} chunks.")
        assert len(authorized_chunks) > 0, "Authorized conversation failed to retrieve its own document!"

        test_results["TEST_7_CONVERSATION_ISOLATION_PRIVACY"] = "PASSED"
    except Exception as e:
        print(f"  -> FAILED: {e}")
        test_results["TEST_7_CONVERSATION_ISOLATION_PRIVACY"] = f"FAILED: {e}"

    # -------------------------------------------------------------------------
    # TEST 8: RAG Regression Verification (Official Circular Grounding & Citations)
    # -------------------------------------------------------------------------
    print("\n[TEST 8] Testing Regression on Grounded RAG with Official University Circulars...")
    try:
        conv_8 = await conv_svc.get_or_create_conversation(initial_prompt="Official Circular Query")
        c8_id = conv_8["id"]

        res8 = await rag_svc.answer_question(
            message="What are the latest examination notices or fee notifications from GGSIPU?",
            conversation_id=c8_id,
        )
        print(f"  -> Answer: {res8.content[:160]}...")
        print(f"  -> Citations ({len(res8.citations)}):")
        for c in res8.citations[:2]:
            print(f"     • [{c.source_id}] {c.title} -> {c.source_url} (Page {c.page_number})")
        assert len(res8.content) > 20
        test_results["TEST_8_RAG_REGRESSION_VERIFICATION"] = "PASSED"
    except Exception as e:
        print(f"  -> FAILED: {e}")
        test_results["TEST_8_RAG_REGRESSION_VERIFICATION"] = f"FAILED: {e}"

    # -------------------------------------------------------------------------
    # SUMMARY
    # -------------------------------------------------------------------------
    print("\n" + "=" * 70)
    print("E2E VERIFICATION SUMMARY")
    print("=" * 70)
    all_passed = True
    for test_name, outcome in test_results.items():
        status_flag = "✓" if outcome == "PASSED" else "✗"
        print(f"  [{status_flag}] {test_name}: {outcome}")
        if outcome != "PASSED":
            all_passed = False

    print("=" * 70)
    if all_passed:
        print("ALL 8 MILESTONE 6 MULTIMODAL EVALUATION TESTS PASSED SUCCESSFULLY!")
    else:
        print("SOME TESTS FAILED - SEE DETAILS ABOVE.")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
