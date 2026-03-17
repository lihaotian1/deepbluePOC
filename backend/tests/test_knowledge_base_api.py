import json
import sys
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import create_app
from app.services.kb_loader import load_knowledge_base
from app.services.knowledge_base_manager import KnowledgeBaseManager


def test_knowledge_base_api_reads_and_saves_and_refreshes_matcher(tmp_path: Path) -> None:
    kb_dir = tmp_path / "knowledge"
    kb_dir.mkdir()

    target_file = kb_dir / "demo.json"
    target_file.write_text(
        json.dumps({"分类A": [{"条目1": "P"}]}, ensure_ascii=False),
        encoding="utf-8",
    )

    app = create_app()
    app.state.knowledge_base_manager = KnowledgeBaseManager(kb_dir)
    app.state.settings.kb_path = str(target_file)
    app.state.matcher_service.kb = load_knowledge_base(target_file)

    client = TestClient(app)

    list_response = client.get("/api/v1/knowledge-bases")
    assert list_response.status_code == 200
    assert list_response.json()[0]["file_name"] == "demo.json"

    get_response = client.get("/api/v1/knowledge-bases/demo.json")
    assert get_response.status_code == 200
    assert get_response.json()["categories"][0]["name"] == "分类A"
    assert get_response.json()["format"] == "grouped"

    put_response = client.put(
        "/api/v1/knowledge-bases/demo.json",
        json={
            "file_name": "demo.json",
            "display_name": "demo",
            "format": "grouped",
            "categories": [
                {
                    "name": "分类A",
                    "items": [{"text": "条目1", "value": "A"}],
                },
                {
                    "name": "分类B",
                    "items": [{"text": "条目2", "value": "B"}],
                },
            ],
        },
    )
    assert put_response.status_code == 200

    saved_payload = json.loads(target_file.read_text(encoding="utf-8"))
    assert saved_payload == {
        "分类A": [{"条目1": "A"}],
        "分类B": [{"条目2": "B"}],
    }
    assert "分类B" in app.state.matcher_service.kb.categories


def test_knowledge_base_api_supports_create_delete_and_flat_format(tmp_path: Path) -> None:
    kb_dir = tmp_path / "knowledge"
    kb_dir.mkdir()

    target_file = kb_dir / "api610.json"
    target_file.write_text(
        json.dumps({"6.1.1": "Scope clause"}, ensure_ascii=False),
        encoding="utf-8",
    )

    app = create_app()
    app.state.knowledge_base_manager = KnowledgeBaseManager(kb_dir)
    app.state.settings.kb_path = str(target_file)
    client = TestClient(app)

    flat_response = client.get("/api/v1/knowledge-bases/api610.json")
    assert flat_response.status_code == 200
    assert flat_response.json()["format"] == "flat_key_value"
    assert flat_response.json()["categories"][0]["name"] == "6.1.1"

    put_response = client.put(
        "/api/v1/knowledge-bases/api610.json",
        json={
            "file_name": "api610.json",
            "display_name": "api610",
            "format": "flat_key_value",
            "categories": [],
        },
    )
    assert put_response.status_code == 200
    assert put_response.json()["format"] == "flat_key_value"
    assert put_response.json()["categories"][0]["name"] == "1"
    assert json.loads(target_file.read_text(encoding="utf-8")) == {"1": ""}

    create_response = client.post(
        "/api/v1/knowledge-bases",
        json={"file_name": "new-kb.json", "format": "flat_key_value"},
    )
    assert create_response.status_code == 200
    assert (kb_dir / "new-kb.json").exists()

    delete_response = client.delete("/api/v1/knowledge-bases/new-kb.json")
    assert delete_response.status_code == 204
    assert not (kb_dir / "new-kb.json").exists()


def test_knowledge_base_api_rejects_deleting_active_compare_file(tmp_path: Path) -> None:
    kb_dir = tmp_path / "knowledge"
    kb_dir.mkdir()

    target_file = kb_dir / "active.json"
    target_file.write_text(json.dumps({"分类A": [{"条目1": "P"}]}, ensure_ascii=False), encoding="utf-8")

    app = create_app()
    app.state.knowledge_base_manager = KnowledgeBaseManager(kb_dir)
    app.state.settings.kb_path = str(target_file)
    client = TestClient(app)

    delete_response = client.delete("/api/v1/knowledge-bases/active.json")
    assert delete_response.status_code == 409
    assert target_file.exists()

    if sys.platform == "win32":
        case_variant_response = client.delete("/api/v1/knowledge-bases/ACTIVE.JSON")
        assert case_variant_response.status_code == 409
        assert target_file.exists()
