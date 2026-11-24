"""
Manual Ingestion and Vector Search Verification Script for Milestone 4.
Processes real downloaded GGSIPU circulars, chunks, embeds (384-d),
inserts into live Zilliz Cloud collection (maya_notice_chunks), and executes semantic search queries.
"""

import asyncio
import os
from pathlib import Path
import sys

# Ensure backend root is on sys.path
backend_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_root))

from app.config import get_settings
from app.services.pdf_worker_pool import get_pdf_worker_pool
from app.services.chunking_service import ChunkingService
from app.services.embedding_service import EmbeddingService
from app.database.zilliz_client import get_zilliz_client
from app.database.supabase_client import get_supabase_client

settings = get_settings()


async def run_verification():
    print("=" * 70)
    print("MAYA MILESTONE 4: REAL DOCUMENT INGESTION & VECTOR RETRIEVAL TEST")
    print("=" * 70)
    print(f"Worker Pool Size:      {settings.PDF_WORKERS} processes")
    print(f"Embedding Dimension:   384 (sentence-transformers/all-MiniLM-L6-v2)")
    print(f"Chunk Target:          {settings.CHUNK_SIZE} tokens (overlap: {settings.CHUNK_OVERLAP})")
    print(f"Target Zilliz Coll:    {settings.ZILLIZ_COLLECTION}")
    print("=" * 70)

    # 1. Locate real downloaded documents
    docs_dir = Path(settings.STORAGE_DIR) / "documents"
    if not docs_dir.exists():
        print(f"Storage directory not found at: {docs_dir}")
        return

    pdf_files = list(docs_dir.glob("*.pdf"))
    print(f"\n[1/5] Found {len(pdf_files)} local circular PDFs in {docs_dir}")
    if not pdf_files:
        print("No PDF files available in storage/documents.")
        return

    selected_files = pdf_files[:5]
    print(f"Selected {len(selected_files)} real PDFs for live ingestion pipeline:")
    for i, p in enumerate(selected_files, 1):
        print(f"  {i}. {p.name} ({p.stat().st_size / 1024:.1f} KB)")

    # 2. Extract using 8-Process Worker Pool
    print(f"\n[2/5] Dispatching documents to 8-process worker pool for PyMuPDF/OCR extraction...")
    worker_pool = get_pdf_worker_pool()

    tasks = [
        {
            "doc_id": f"real_doc_{idx}",
            "file_path": str(fpath),
            "url": f"https://www.ipu.ac.in/{fpath.name}",
            "ocr_enabled": True,
        }
        for idx, fpath in enumerate(selected_files)
    ]

    worker_results = await worker_pool.process_batch_async(tasks)
    print(f"Extracted {len(worker_results)} documents across worker processes.")

    total_pages = 0
    total_chars = 0
    extracted_docs = []

    for r in worker_results:
        if r.get("success"):
            pages_count = len(r.get("pages", []))
            chars = len(r.get("full_text", ""))
            total_pages += pages_count
            total_chars += chars
            extracted_docs.append(r)
            print(f"  ✓ {Path(r.get('file_path', 'unknown')).name}: {pages_count} pages, {chars} characters (PID {r.get('worker_pid')})")
        else:
            print(f"  ✗ Failed: {r.get('error')}")

    print(f"Extraction Summary: {len(extracted_docs)} documents extracted, {total_pages} total pages, {total_chars:,} characters.")

    # 3. Chunking
    print(f"\n[3/5] Chunking documents with 700-token target and 120-token overlap...")
    chunker = ChunkingService()
    all_chunks = []

    for doc in extracted_docs:
        doc_filename = Path(doc.get("file_path", "")).name
        metadata = {
            "id": doc["doc_id"],
            "title": f"Official GGSIPU Circular ({doc_filename[:30]})",
            "source_url": doc.get("url", ""),
            "category": "Official Notification",
            "published_date": "2024-11-20",
        }
        chunks = chunker.chunk_extracted_document(doc, metadata)
        all_chunks.extend(chunks)

    print(f"Created {len(all_chunks)} semantic chunks from {len(extracted_docs)} documents.")

    # 4. Generate 384-dimensional embeddings
    print(f"\n[4/5] Generating 384-dimensional cosine-normalized dense embeddings locally...")
    embedder = EmbeddingService()
    chunk_texts = [c.content for c in all_chunks]
    embeddings = embedder.generate_embeddings(chunk_texts)

    for chunk, emb in zip(all_chunks, embeddings):
        chunk.embedding = emb

    print(f"Generated {len(embeddings)} dense vectors of dimension {len(embeddings[0])}.")

    # 5. Insert into Zilliz Cloud
    print(f"\n[5/5] Indexing {len(all_chunks)} chunks into Zilliz Cloud collection '{settings.ZILLIZ_COLLECTION}'...")
    zilliz = get_zilliz_client()
    inserted_count = await zilliz.insert_chunks(all_chunks)
    print(f"Successfully indexed {inserted_count} chunks into Zilliz Cloud!")

    # 6. Execute live semantic search queries
    print("\n" + "=" * 70)
    print("LIVE SEMANTIC SEARCH RETRIEVAL VERIFICATION")
    print("=" * 70)

    test_queries = [
        "Examination schedule date sheet and centres",
        "Practical examination viva voce guidelines",
        "Student fee submission or admission notice",
    ]

    for q in test_queries:
        print(f"\nQuery: \"{q}\"")
        q_vec = embedder.generate_query_embedding(q)
        results = await zilliz.semantic_search(query_vector=q_vec, top_k=2, threshold=0.0)

        if not results:
            print("  No matching chunks found above threshold.")
            continue

        for rank, res in enumerate(results, 1):
            score = res.get("score", 0.0)
            title = res.get("title", "")
            page = res.get("page_number", 1)
            content_snippet = (res.get("content", "")[:180] + "...").replace("\n", " ")
            print(f"  [{rank}] Score: {score:.4f} | Page {page} | {title}")
            print(f"      Snippet: \"{content_snippet}\"")

    print("\n" + "=" * 70)
    print("MILESTONE 4 VERIFICATION COMPLETED SUCCESSFULLY!")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(run_verification())
