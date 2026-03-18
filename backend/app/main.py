from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.compare_routes import router as compare_router
from app.api.document_routes import router as document_router
from app.api.export_routes import router as export_router
from app.api.knowledge_base_routes import router as knowledge_base_router
from app.api.translation_routes import router as translation_router
from app.config import Settings
from app.services.knowledge_base_manager import KnowledgeBaseManager
from app.services.llm_client import OpenAICompatibleMatcherLLM
from app.services.session_store import SessionStore
from app.services.splitter_service import SplitterService


def create_app() -> FastAPI:
    settings = Settings()
    app = FastAPI(title=settings.app_name)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.state.settings = settings
    app.state.session_store = SessionStore()
    app.state.splitter_service = SplitterService(
        temp_dir=settings.temp_path,
        api_key=settings.openai_api_key,
        base_url=settings.openai_base_url,
        model=settings.openai_model,
        timeout=settings.openai_timeout,
    )
    app.state.knowledge_base_manager = KnowledgeBaseManager(settings.kb_directory)

    app.state.matcher_llm = OpenAICompatibleMatcherLLM(
        base_url=settings.openai_base_url,
        api_key=settings.openai_api_key,
        model=settings.openai_model,
        timeout=settings.openai_timeout,
    )

    @app.get("/health")
    def health_check() -> dict[str, str]:
        return {"status": "ok"}

    api_prefix = "/api/v1"
    app.include_router(document_router, prefix=api_prefix)
    app.include_router(compare_router, prefix=api_prefix)
    app.include_router(export_router, prefix=api_prefix)
    app.include_router(knowledge_base_router, prefix=api_prefix)
    app.include_router(translation_router, prefix=api_prefix)
    app.mount("/assets/logo", StaticFiles(directory=settings.logo_path), name="logo-assets")

    return app


app = create_app()
