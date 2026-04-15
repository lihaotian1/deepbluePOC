import json
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import create_app
from app.services.compare_profiles import STANDARD_KB_FILE_NAME
from app.services.knowledge_base_manager import KnowledgeBaseManager


class FakeDocumentCompareLLM:
    async def compare_document_rows(self, *, document_title, document_text, entries):
        assert document_title == "demo.md"
        assert "这是正文。" in document_text
        assert len(entries) == 2
        return [
            {
                "entry_id": entries[0].entry_id,
                "chapter_title": "1 总则",
                "source_excerpt": "这是正文。",
                "difference_summary": "部分满足：存在语言范围差异，需要与甲方澄清。",
            },
            {
                "entry_id": entries[0].entry_id,
                "chapter_title": "2 铭牌",
                "source_excerpt": "另一个正文。",
                "difference_summary": "存在冲突：甲方要求与我方标准明确不一致，需要与甲方澄清。",
            },
            {
                "entry_id": entries[0].entry_id,
                "chapter_title": "1 总则",
                "source_excerpt": "这是正文。",
                "difference_summary": "部分满足：重复结果不应再次输出。",
            },
        ]


class BlankMessageFailureLLM:
    async def compare_document_rows(self, *, document_title, document_text, entries):
        raise RuntimeError()


def _write_compare_files(kb_dir: Path) -> None:
    kb_dir.mkdir(parents=True, exist_ok=True)
    (kb_dir / STANDARD_KB_FILE_NAME).write_text(
        json.dumps(
            {
                "标准分类": [
                    {"标准条目一": "P"},
                    {"标准条目二": "A"},
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


def test_compare_stream_returns_row_events_for_full_document_results(tmp_path: Path) -> None:
    kb_dir = tmp_path / "知识库"
    _write_compare_files(kb_dir)

    app = create_app()
    app.state.knowledge_base_manager = KnowledgeBaseManager(kb_dir)
    app.state.matcher_llm = FakeDocumentCompareLLM()
    client = TestClient(app)

    content = "1 总则\n这是正文。\n\n2 铭牌\n另一个正文。\n"
    upload_resp = client.post(
        "/api/v1/documents/upload",
        files={"file": ("demo.md", content.encode("utf-8"), "text/markdown")},
    )
    doc_id = upload_resp.json()["doc_id"]

    with client.stream(
        "POST",
        f"/api/v1/documents/{doc_id}/compare/stream",
    ) as response:
        assert response.status_code == 200
        body = "".join(response.iter_text())

    assert body.count("event: compare_row") == 2
    assert '"chapter_title":"1 总则"' in body
    assert '"chapter_title":"2 铭牌"' in body
    assert '"source_excerpt":"这是正文。"' in body
    assert '"source_excerpt":"另一个正文。"' in body
    assert '"kb_entry_text":"标准条目一"' in body
    assert '"type_code":"P"' in body
    assert '"type_code":"A"' not in body
    assert '"OTHER"' not in body
    assert '"row_count":2' in body
    assert "event: compare_done" in body


def test_compare_stream_reports_blank_exceptions_without_emitting_compare_done(tmp_path: Path) -> None:
    kb_dir = tmp_path / "知识库"
    _write_compare_files(kb_dir)

    app = create_app()
    app.state.knowledge_base_manager = KnowledgeBaseManager(kb_dir)
    app.state.matcher_llm = BlankMessageFailureLLM()
    client = TestClient(app)

    content = "1 总则\n这是正文。\n"
    upload_resp = client.post(
        "/api/v1/documents/upload",
        files={"file": ("demo.md", content.encode("utf-8"), "text/markdown")},
    )
    doc_id = upload_resp.json()["doc_id"]

    with client.stream(
        "POST",
        f"/api/v1/documents/{doc_id}/compare/stream",
    ) as response:
        assert response.status_code == 200
        body = "".join(response.iter_text())

    assert "event: error" in body
    assert '"message":"RuntimeError"' in body
    assert "event: compare_done" not in body
