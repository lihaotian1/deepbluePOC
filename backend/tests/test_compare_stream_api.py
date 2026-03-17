import asyncio
from typing import Any, cast

from fastapi.testclient import TestClient

from app.api.deps import get_matcher_service
from app.main import create_app
from app.schemas import ChunkCompareResult


class FakeMatcher:
    async def compare_chunks_with_trace(self, chunks, batch_size=10):
        output = []
        for chunk in chunks:
            await asyncio.sleep(0)
            output.append(
                (
                    ChunkCompareResult(
                        chunk_id=chunk.chunk_id,
                        heading=chunk.heading,
                        content=chunk.content,
                        categories=[],
                        matches=cast(
                            list[Any],
                            [
                                {
                                    "entry_id": "分类A-1",
                                    "category": "分类A",
                                    "text": "符合API 610",
                                    "type_code": "P",
                                    "reason": "语义一致",
                                    "evidence_sentence_index": 0,
                                    "evidence_sentence_text": "这是正文。",
                                }
                            ],
                        ),
                        label="命中",
                    ),
                    [{"event": "classification", "categories": []}],
                )
            )
        return output


def test_compare_stream_returns_sse_events() -> None:
    app = create_app()
    app.dependency_overrides[get_matcher_service] = lambda: FakeMatcher()
    client = TestClient(app)

    content = "1 总则\n这是正文。\n"
    upload_resp = client.post(
        "/api/v1/documents/upload",
        files={"file": ("demo.md", content.encode("utf-8"), "text/markdown")},
    )
    doc_id = upload_resp.json()["doc_id"]

    with client.stream("POST", f"/api/v1/documents/{doc_id}/compare/stream") as response:
        assert response.status_code == 200
        body = "".join(response.iter_text())

    assert "event: chunk_result" in body
    assert '"label":"命中"' in body
    assert '"evidence_sentence_index":0' in body
    assert '"evidence_sentence_text":"这是正文。"' in body
    assert "event: compare_done" in body

    app.dependency_overrides.clear()
