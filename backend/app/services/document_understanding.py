"""
Document Understanding Service for User Uploads (PDF & DOCX).
Processes uploaded circulars and guidelines with conversation-level isolation.
User-uploaded documents are NEVER indexed into the global university circular database.
"""

import io
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
import numpy as np

from app.config import get_settings
from app.schemas.chat import CitationItem
from app.schemas.multimodal import DocumentUnderstandingResult
from app.services.chunking_service import ChunkingService, NoticeChunk
from app.services.docx_extractor import DOCXExtractor
from app.services.embedding_service import get_embedding_service
from app.services.file_validator import FileValidator, FileValidationError
from app.services.gemini_service import get_gemini_service
from app.services.pdf_extractor import PDFExtractor
from google.genai import types

logger = logging.getLogger("maya.document_understanding")
settings = get_settings()


DOCUMENT_SYSTEM_INSTRUCTION = """
You are MAYA's Document Understanding Specialist.
Your task is to analyze user-uploaded university circulars, guidelines, exam papers, or syllabus documents.

STRICT INSTRUCTIONS:
1. Ground your answers strictly in the provided excerpts of the user's uploaded document.
2. If the user asks for a summary, provide a comprehensive summary highlighting purpose, important dates, eligibility, and instructions.
3. If the user asks a specific question, answer it directly and cite the relevant page numbers.
4. If the document does not contain the answer, explicitly state that it is not mentioned in the uploaded file.
5. Do not invent page numbers or information not in the text.

Return your response strictly in the following JSON schema:
{
  "summary": "<2-4 sentence executive summary of the document>",
  "answer": "<direct, thorough response to the student's question>",
  "relevant_pages": [<integer page numbers>]
}
"""


class UserDocumentChunk:
    """Passage from a user-uploaded document scoped strictly to a single conversation."""

    def __init__(
        self,
        id: str,
        conversation_id: str,
        document_id: str,
        filename: str,
        page_number: int,
        content: str,
        embedding: List[float],
    ):
        self.id = id
        self.conversation_id = conversation_id
        self.document_id = document_id
        self.filename = filename
        self.page_number = page_number
        self.content = content
        self.embedding = embedding


class DocumentUnderstandingService:
    """
    Coordinates extraction, chunking, conversation-isolated retrieval,
    and Gemini understanding for user-uploaded documents.
    """

    def __init__(self):
        self.pdf_extractor = PDFExtractor()
        self.docx_extractor = DOCXExtractor()
        self.chunker = ChunkingService()
        self.embedder = get_embedding_service()
        self.gemini_service = get_gemini_service()

        # Conversation-scoped isolated document chunks: conversation_id -> list of chunks
        self._isolated_chunks: Dict[str, List[UserDocumentChunk]] = {}
        # Document metadata: conversation_id -> doc_id -> metadata
        self._isolated_docs: Dict[str, Dict[str, Any]] = {}

    def index_user_document(
        self,
        conversation_id: str,
        document_id: str,
        file_path: str,
        filename: str,
    ) -> Dict[str, Any]:
        """
        Extract text, chunk, and embed an uploaded document strictly within conversation scope.
        Guarantees zero cross-conversation document leakage.
        """
        path = Path(file_path)
        ext = path.suffix.lower()

        if ext == ".pdf":
            extract_res = self.pdf_extractor.extract_pdf(str(path))
            pages = extract_res.get("pages", [])
            total_pages = extract_res.get("total_pages", len(pages))
            full_text = extract_res.get("full_text", "")
        elif ext == ".docx":
            extract_res = self.docx_extractor.extract_docx(str(path))
            full_text = extract_res.get("full_text", "")
            total_pages = 1
            pages = [{"page_number": 1, "text": full_text}]
        else:
            raise FileValidationError(f"Unsupported document extension: {ext}")

        if not full_text.strip():
            logger.warning(f"Uploaded document {filename} yielded 0 characters of text.")

        # Chunk the document
        raw_chunks = self.chunker.chunk_extracted_document(
            extracted_doc={
                "full_text": full_text,
                "pages": pages,
                "total_pages": total_pages,
            },
            notice_metadata={
                "id": document_id,
                "title": filename,
                "source_url": f"user_upload://{conversation_id}/{filename}",
                "category": "UserUpload",
            },
        )

        # Generate local 384-d embeddings
        texts = [c.content for c in raw_chunks]
        embeddings = self.embedder.generate_embeddings(texts) if texts else []

        user_chunks: List[UserDocumentChunk] = []
        for idx, (rc, emb) in enumerate(zip(raw_chunks, embeddings)):
            page_num = 1
            if ext == ".pdf" and pages:
                # Estimate page number from content match
                for p in pages:
                    p_text = p.get("text", "") if isinstance(p, dict) else p.text
                    p_num = p.get("page_number", 1) if isinstance(p, dict) else p.page_number
                    if rc.content[:60] in p_text:
                        page_num = p_num
                        break

            chunk_obj = UserDocumentChunk(
                id=f"{document_id}_c{idx}",
                conversation_id=conversation_id,
                document_id=document_id,
                filename=filename,
                page_number=page_num,
                content=rc.content,
                embedding=emb,
            )
            user_chunks.append(chunk_obj)

        # Store strictly in conversation-isolated index
        if conversation_id not in self._isolated_chunks:
            self._isolated_chunks[conversation_id] = []
        self._isolated_chunks[conversation_id].extend(user_chunks)

        doc_meta = {
            "document_id": document_id,
            "filename": filename,
            "page_count": total_pages,
            "total_chunks": len(user_chunks),
            "file_path": file_path,
        }
        if conversation_id not in self._isolated_docs:
            self._isolated_docs[conversation_id] = {}
        self._isolated_docs[conversation_id][document_id] = doc_meta

        logger.info(
            f"Indexed user document '{filename}' ({total_pages} pages, {len(user_chunks)} chunks) "
            f"for conversation '{conversation_id}'"
        )
        return doc_meta

    def search_user_document(
        self,
        conversation_id: str,
        query: str,
        top_k: int = 4,
    ) -> List[UserDocumentChunk]:
        """
        Search user-uploaded document chunks strictly within the specified conversation.
        """
        chunks = self._isolated_chunks.get(conversation_id, [])
        if not chunks or not query.strip():
            return []

        q_vec = self.embedder.generate_query_embedding(query)
        q_norm = np.linalg.norm(q_vec)

        scored = []
        for chk in chunks:
            c_norm = np.linalg.norm(chk.embedding)
            if q_norm > 0 and c_norm > 0:
                dot = float(np.dot(q_vec, chk.embedding))
                score = dot / (q_norm * c_norm)
            else:
                score = 0.0
            scored.append((score, chk))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [c for _, c in scored[:top_k]]

    async def analyze_document(
        self,
        conversation_id: str,
        document_id: str,
        filename: str,
        file_path: str,
        question: Optional[str] = None,
    ) -> DocumentUnderstandingResult:
        """
        Summarize or answer a question regarding a user-uploaded document.
        """
        # Ensure document is indexed
        if conversation_id not in self._isolated_docs or document_id not in self._isolated_docs[conversation_id]:
            self.index_user_document(
                conversation_id=conversation_id,
                document_id=document_id,
                file_path=file_path,
                filename=filename,
            )

        doc_meta = self._isolated_docs[conversation_id][document_id]
        user_prompt = question.strip() if question and question.strip() else "Summarize the key instructions and details in this document."

        # Retrieve relevant passages from the user document
        relevant_chunks = self.search_user_document(
            conversation_id=conversation_id,
            query=user_prompt,
            top_k=4,
        )

        context_passages = []
        citations: List[CitationItem] = []
        relevant_pages = set()

        for idx, rc in enumerate(relevant_chunks, 1):
            context_passages.append(
                f"[DOCUMENT_EXCERPT_{idx}] (Page {rc.page_number})\n{rc.content.strip()}"
            )
            relevant_pages.add(rc.page_number)
            citations.append(
                CitationItem(
                    source_id=f"USER_DOC_PAGE_{rc.page_number}",
                    notice_id=document_id,
                    title=f"{filename} (Page {rc.page_number})",
                    source_url=f"user_upload://{filename}",
                    pdf_url=None,
                    page_number=rc.page_number,
                    relevant_excerpt=rc.content[:200] + "...",
                )
            )

        context_text = "\n\n".join(context_passages) if context_passages else "No text extracted from document."

        # If Gemini is not configured, generate fallback answer from top excerpt
        if not self.gemini_service.is_configured or self.gemini_service._client is None:
            return DocumentUnderstandingResult(
                document_id=document_id,
                filename=filename,
                page_count=doc_meta.get("page_count", 1),
                summary=f"Uploaded document '{filename}' contains {doc_meta.get('page_count', 1)} pages.",
                answer=f"Extracted content from document:\n\n{context_text[:500]}...",
                relevant_pages=sorted(list(relevant_pages)),
                citations=citations,
            )

        client = self.gemini_service._client
        assembled_prompt = (
            f"USER UPLOADED DOCUMENT: '{filename}'\n\n"
            f"EXCERPTS FROM DOCUMENT:\n{context_text}\n\n"
            f"STUDENT QUESTION: {user_prompt}"
        )

        config = types.GenerateContentConfig(
            temperature=0.2,
            max_output_tokens=2048,
            system_instruction=DOCUMENT_SYSTEM_INSTRUCTION,
            response_mime_type="application/json",
        )

        try:
            res = await client.aio.models.generate_content(
                model=self.gemini_service.model_name,
                contents=assembled_prompt,
                config=config,
            )
            raw_text = res.text or "{}"
        except Exception as e:
            logger.error(f"Error calling Gemini for document understanding: {e}")
            return DocumentUnderstandingResult(
                document_id=document_id,
                filename=filename,
                page_count=doc_meta.get("page_count", 1),
                summary=f"Processed '{filename}'.",
                answer=f"Could not generate Gemini response: {e}. Excerpt: {context_text[:300]}",
                relevant_pages=sorted(list(relevant_pages)),
                citations=citations,
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
            data = {"summary": "Document analyzed.", "answer": cleaned, "relevant_pages": list(relevant_pages)}

        summary = data.get("summary", f"Document summary for {filename}")
        answer = data.get("answer", cleaned)
        pages_out = data.get("relevant_pages", sorted(list(relevant_pages)))

        return DocumentUnderstandingResult(
            document_id=document_id,
            filename=filename,
            page_count=doc_meta.get("page_count", 1),
            summary=summary,
            answer=answer,
            relevant_pages=pages_out,
            citations=citations,
        )


# Singleton
_document_understanding_service: Optional[DocumentUnderstandingService] = None


def get_document_understanding_service() -> DocumentUnderstandingService:
    global _document_understanding_service
    if _document_understanding_service is None:
        _document_understanding_service = DocumentUnderstandingService()
    return _document_understanding_service
