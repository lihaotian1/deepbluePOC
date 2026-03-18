from pathlib import Path

from fastapi.testclient import TestClient

from app.main import create_app
from app.services.knowledge_base_manager import KnowledgeBaseManager
from app.services.llm_client import OpenAICompatibleMatcherLLM


class FakeTranslatorLLM:
    async def translate_to_chinese(self, *, text: str) -> str:
        return f"中文:{text}"


class FailingTranslatorLLM:
    async def translate_to_chinese(self, *, text: str) -> str:
        raise RuntimeError("upstream translate failure")


def test_translate_api_returns_chinese_translation(tmp_path: Path) -> None:
    kb_dir = tmp_path / "knowledge"
    kb_dir.mkdir()

    app = create_app()
    app.state.knowledge_base_manager = KnowledgeBaseManager(kb_dir)
    app.state.matcher_llm = FakeTranslatorLLM()
    client = TestClient(app)

    response = client.post("/api/v1/translate/chinese", json={"text": "Pump shall include bearings."})

    assert response.status_code == 200
    assert response.json() == {"translation": "中文:Pump shall include bearings."}


def test_translate_api_rejects_blank_text(tmp_path: Path) -> None:
    kb_dir = tmp_path / "knowledge"
    kb_dir.mkdir()

    app = create_app()
    app.state.knowledge_base_manager = KnowledgeBaseManager(kb_dir)
    app.state.matcher_llm = FakeTranslatorLLM()
    client = TestClient(app)

    response = client.post("/api/v1/translate/chinese", json={"text": "   "})

    assert response.status_code == 422


def test_translate_api_surfaces_llm_failures(tmp_path: Path) -> None:
    kb_dir = tmp_path / "knowledge"
    kb_dir.mkdir()

    app = create_app()
    app.state.knowledge_base_manager = KnowledgeBaseManager(kb_dir)
    app.state.matcher_llm = FailingTranslatorLLM()
    client = TestClient(app)

    response = client.post("/api/v1/translate/chinese", json={"text": "Translate me"})

    assert response.status_code == 502
    assert response.json()["detail"] == "Translation failed"


def test_translate_api_reports_unconfigured_service_without_leaking_internal_state(tmp_path: Path) -> None:
    kb_dir = tmp_path / "knowledge"
    kb_dir.mkdir()

    app = create_app()
    app.state.knowledge_base_manager = KnowledgeBaseManager(kb_dir)
    app.state.matcher_llm = OpenAICompatibleMatcherLLM(
        base_url="https://example.test",
        api_key="",
        model="demo",
    )
    client = TestClient(app)

    response = client.post("/api/v1/translate/chinese", json={"text": "Translate me"})

    assert response.status_code == 503
    assert response.json()["detail"] == "Translation service unavailable"
