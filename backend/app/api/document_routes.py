from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from app.api.deps import get_session_store, get_splitter_service
from app.schemas import (
    DocumentReviewResponse,
    DocumentReviewUpdateRequest,
    DocumentUploadResponse,
)
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

    document_text = splitter.extract_upload_text(file_name=file.filename or "uploaded", payload=raw)
    session = store.create(source_file_name=file.filename or "uploaded", document_text=document_text)
    return DocumentUploadResponse(
        doc_id=session.doc_id,
        source_file_name=session.source_file_name,
        document_text=session.document_text,
    )


@router.put("/{doc_id}/review", response_model=DocumentReviewResponse)
async def save_review_state(
    doc_id: str,
    request: DocumentReviewUpdateRequest,
    store: SessionStore = Depends(get_session_store),
) -> DocumentReviewResponse:
    session = store.save_review_state(
        doc_id,
        compare_rows=request.compare_rows,
        submitted_for_review=request.submitted_for_review,
    )
    if session is None:
        raise HTTPException(status_code=404, detail="Document session not found")

    return DocumentReviewResponse(
        doc_id=session.doc_id,
        compare_rows=session.compare_rows,
        submitted_for_review=session.submitted_for_review,
    )
