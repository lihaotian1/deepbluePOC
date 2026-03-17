from __future__ import annotations

import os
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Response

from app.api.deps import get_knowledge_base_manager, get_settings
from app.config import Settings
from app.schemas import KnowledgeBaseCreateRequest, KnowledgeBaseDocument, KnowledgeBaseFileSummary
from app.services.compare_profiles import COMPARE_PROFILES
from app.services.knowledge_base_manager import KnowledgeBaseManager


router = APIRouter(prefix="/knowledge-bases", tags=["knowledge-bases"])


def _is_active_compare_file(candidate_path: Path, settings: Settings) -> bool:
    return os.path.normcase(str(candidate_path.resolve(strict=False))) == os.path.normcase(
        str(settings.kb_file.resolve(strict=False))
    )


def _is_required_compare_profile(file_name: str) -> bool:
    return file_name in COMPARE_PROFILES


@router.get("", response_model=list[KnowledgeBaseFileSummary])
async def list_knowledge_base_files(
    manager: KnowledgeBaseManager = Depends(get_knowledge_base_manager),
) -> list[KnowledgeBaseFileSummary]:
    return manager.list_files()


@router.get("/{file_name}", response_model=KnowledgeBaseDocument)
async def get_knowledge_base_file(
    file_name: str,
    manager: KnowledgeBaseManager = Depends(get_knowledge_base_manager),
) -> KnowledgeBaseDocument:
    try:
        return manager.read_file(file_name)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Knowledge base file not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.put("/{file_name}", response_model=KnowledgeBaseDocument)
async def save_knowledge_base_file(
    file_name: str,
    document: KnowledgeBaseDocument,
    manager: KnowledgeBaseManager = Depends(get_knowledge_base_manager),
) -> KnowledgeBaseDocument:
    try:
        manager.save_file(file_name, document)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Knowledge base file not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return manager.read_file(file_name)


@router.post("", response_model=KnowledgeBaseDocument)
async def create_knowledge_base_file(
    request: KnowledgeBaseCreateRequest,
    manager: KnowledgeBaseManager = Depends(get_knowledge_base_manager),
) -> KnowledgeBaseDocument:
    try:
        manager.create_file(request.file_name, request.format)
    except FileExistsError as exc:
        raise HTTPException(status_code=409, detail="Knowledge base file already exists") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return manager.read_file(request.file_name)


@router.delete("/{file_name}", status_code=204)
async def delete_knowledge_base_file(
    file_name: str,
    manager: KnowledgeBaseManager = Depends(get_knowledge_base_manager),
    settings: Settings = Depends(get_settings),
) -> Response:
    if _is_active_compare_file(manager.kb_dir / file_name, settings) or _is_required_compare_profile(file_name):
        raise HTTPException(status_code=409, detail="Cannot delete active compare knowledge base file")

    try:
        manager.delete_file(file_name)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Knowledge base file not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return Response(status_code=204)
