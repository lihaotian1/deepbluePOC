from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from app.api.deps import get_session_store, get_splitter_service
from app.schemas import ChunkUpdateRequest, DocumentUploadResponse
from app.services.session_store import SessionStore
from app.services.splitter_service import SplitterService


router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    splitter: SplitterService = Depends(get_splitter_service),
    store: SessionStore = Depends(get_session_store),
) -> DocumentUploadResponse:
    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=400, detail="Empty file")
    chunks = splitter.split_upload(file_name=file.filename or "uploaded", payload=raw)
    session = store.create(source_file_name=file.filename or "uploaded", chunks=chunks)
    return DocumentUploadResponse(
        doc_id=session.doc_id,
        source_file_name=session.source_file_name,
        chunks=session.chunks,
    )


@router.patch("/{doc_id}/chunks", response_model=DocumentUploadResponse)
async def patch_chunks(
    doc_id: str,
    request: ChunkUpdateRequest,
    store: SessionStore = Depends(get_session_store),
) -> DocumentUploadResponse:
    updates = {row.chunk_id: row.content for row in request.chunks}
    session = store.update_chunks(doc_id, updates)
    if session is None:
        raise HTTPException(status_code=404, detail="Document session not found")
    return DocumentUploadResponse(
        doc_id=session.doc_id,
        source_file_name=session.source_file_name,
        chunks=session.chunks,
    )
