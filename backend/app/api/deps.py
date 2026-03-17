from __future__ import annotations

from fastapi import Request

from app.config import Settings
from app.services.matcher_service import MatcherService
from app.services.knowledge_base_manager import KnowledgeBaseManager
from app.services.session_store import SessionStore
from app.services.splitter_service import SplitterService


def get_settings(request: Request) -> Settings:
    return request.app.state.settings


def get_session_store(request: Request) -> SessionStore:
    return request.app.state.session_store


def get_splitter_service(request: Request) -> SplitterService:
    return request.app.state.splitter_service


def get_matcher_service(request: Request) -> MatcherService:
    return request.app.state.matcher_service


def get_knowledge_base_manager(request: Request) -> KnowledgeBaseManager:
    return request.app.state.knowledge_base_manager
