from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response

from app.api.deps import get_session_store
from app.services.compare_profiles import COMPARE_PROFILES
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

    payload = build_export_workbook(
        chunks=session.chunks,
        results_by_kb=session.compare_results_by_kb,
        sheet_names_by_kb={
            kb_file: COMPARE_PROFILES.get(kb_file).sheet_name if kb_file in COMPARE_PROFILES else kb_file.removesuffix(".json")
            for kb_file in session.compare_results_by_kb
        },
    )
    filename = f"{doc_id}_compare.xlsx"
    headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
    return Response(
        content=payload,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers=headers,
    )
