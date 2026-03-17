from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response

from app.api.deps import get_session_store
from app.services.export_service import build_export_workbook
from app.services.session_store import SessionStore


router = APIRouter(prefix="/documents", tags=["export"])


@router.get("/{doc_id}/export.xlsx")
async def export_excel(
    doc_id: str,
    store: SessionStore = Depends(get_session_store),
):
    session = store.get(doc_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Document session not found")

    payload = build_export_workbook(chunks=session.chunks, results=session.compare_results)
    filename = f"{doc_id}_compare.xlsx"
    headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
    return Response(
        content=payload,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers=headers,
    )
