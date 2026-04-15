import asyncio
import json
from types import SimpleNamespace

import httpx

from app.services import llm_client as llm_client_module
from app.services.kb_loader import KnowledgeEntry
from app.services.llm_client import OpenAICompatibleMatcherLLM


class _FakeResponse:
    def __init__(self, status_code: int, payload: dict | None = None, text: str = "") -> None:
        self.status_code = status_code
        self._payload = payload or {}
        self.text = text
        self.headers: dict[str, str] = {}
        self.request = httpx.Request("POST", "https://example.test/v1/chat/completions")

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise httpx.HTTPStatusError("boom", request=self.request, response=self)

    def json(self) -> dict:
        return self._payload


class _SequencedAsyncClient:
    responses: list[object] = []
    stream_chunks: list[str] = []

    def __init__(self, *args, **kwargs) -> None:
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def post(self, *args, **kwargs):
        next_item = self.responses.pop(0)
        if isinstance(next_item, Exception):
            raise next_item
        return next_item

    def stream(self, *args, **kwargs):
        return _FakeAsyncStreamResponse(self.stream_chunks)


class _FakeAsyncStreamResponse:
    def __init__(self, chunks: list[str]) -> None:
        self.status_code = 200
        self.headers: dict[str, str] = {}
        self._chunks = list(chunks)

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    def raise_for_status(self) -> None:
        return None

    async def aiter_text(self):
        for chunk in self._chunks:
            yield chunk


def _build_success_payload(content: dict) -> dict:
    return {
        "choices": [
            {
                "message": {
                    "content": json.dumps(content, ensure_ascii=False),
                }
            }
        ]
    }


def test_compare_document_rows_retries_http_429_before_succeeding(monkeypatch) -> None:
    _SequencedAsyncClient.responses = [
        _FakeResponse(429, {"error": "Too many concurrent requests"}),
        _FakeResponse(
            200,
            _build_success_payload(
                {
                    "results": [
                        {
                            "entry_id": "kb-1",
                            "chapter_title": "1 总则",
                            "source_excerpt": "source",
                            "difference_summary": "部分满足：需要澄清。",
                        }
                    ]
                }
            ),
        ),
    ]
    sleep_calls: list[float] = []

    async def fake_sleep(seconds: float) -> None:
        sleep_calls.append(seconds)

    monkeypatch.setattr(llm_client_module.httpx, "AsyncClient", _SequencedAsyncClient)
    monkeypatch.setattr(llm_client_module, "asyncio", SimpleNamespace(sleep=fake_sleep), raising=False)

    client = OpenAICompatibleMatcherLLM(
        base_url="https://example.test/v1",
        api_key="demo-key",
        model="demo-model",
        timeout=60,
    )
    rows = asyncio.run(
        client.compare_document_rows(
            document_title="demo.pdf",
            document_text="source",
            entries=[KnowledgeEntry(entry_id="kb-1", category="分类A", text="标准条目", type_code="P", raw_value="P")],
        )
    )

    assert len(rows) == 1
    assert rows[0]["entry_id"] == "kb-1"
    assert sleep_calls == [1.0]


def test_compare_document_rows_retries_read_timeout_before_succeeding(monkeypatch) -> None:
    _SequencedAsyncClient.responses = [
        httpx.ReadTimeout("timed out"),
        _FakeResponse(
            200,
            _build_success_payload(
                {
                    "results": [
                        {
                            "entry_id": "kb-1",
                            "chapter_title": "1 总则",
                            "source_excerpt": "source",
                            "difference_summary": "直接满足：可满足。",
                        }
                    ]
                }
            ),
        ),
    ]
    sleep_calls: list[float] = []

    async def fake_sleep(seconds: float) -> None:
        sleep_calls.append(seconds)

    monkeypatch.setattr(llm_client_module.httpx, "AsyncClient", _SequencedAsyncClient)
    monkeypatch.setattr(llm_client_module, "asyncio", SimpleNamespace(sleep=fake_sleep), raising=False)

    client = OpenAICompatibleMatcherLLM(
        base_url="https://example.test/v1",
        api_key="demo-key",
        model="demo-model",
        timeout=60,
    )
    rows = asyncio.run(
        client.compare_document_rows(
            document_title="demo.pdf",
            document_text="source",
            entries=[KnowledgeEntry(entry_id="kb-1", category="分类A", text="标准条目", type_code="P", raw_value="P")],
        )
    )

    assert len(rows) == 1
    assert rows[0]["difference_summary"] == "直接满足：可满足。"
    assert sleep_calls == [1.0]


def test_compare_document_rows_reports_empty_assistant_messages_clearly(monkeypatch) -> None:
    _SequencedAsyncClient.responses = [
        _FakeResponse(
            200,
            {
                "choices": [
                    {
                        "message": {
                            "role": "assistant",
                            "content": None,
                            "reasoning_content": None,
                            "tool_calls": None,
                        }
                    }
                ]
            },
        )
    ]
    _SequencedAsyncClient.stream_chunks = []

    monkeypatch.setattr(llm_client_module.httpx, "AsyncClient", _SequencedAsyncClient)

    client = OpenAICompatibleMatcherLLM(
        base_url="https://example.test/v1",
        api_key="demo-key",
        model="demo-model",
        timeout=60,
    )

    try:
        asyncio.run(
            client.compare_document_rows(
                document_title="demo.pdf",
                document_text="source",
                entries=[KnowledgeEntry(entry_id="kb-1", category="分类A", text="标准条目", type_code="P", raw_value="P")],
            )
        )
    except ValueError as exc:
        assert str(exc) == "LLM stream returned no assistant content."
    else:
        raise AssertionError("Expected ValueError for empty assistant message")


def test_chat_json_falls_back_to_streaming_when_non_stream_content_is_empty(monkeypatch) -> None:
    _SequencedAsyncClient.responses = [
        _FakeResponse(
            200,
            {
                "choices": [
                    {
                        "message": {
                            "role": "assistant",
                            "content": None,
                            "reasoning_content": None,
                            "tool_calls": None,
                        }
                    }
                ]
            },
        )
    ]
    _SequencedAsyncClient.stream_chunks = [
        'data: {"choices":[{"delta":{"content":"{\\"results\\":"}}]}\n\n',
        'data: {"choices":[{"delta":{"content":"[]}"}}]}\n\n',
        "data: [DONE]\n\n",
    ]

    monkeypatch.setattr(llm_client_module.httpx, "AsyncClient", _SequencedAsyncClient)

    client = OpenAICompatibleMatcherLLM(
        base_url="https://example.test/v1",
        api_key="demo-key",
        model="demo-model",
        timeout=60,
    )

    payload = asyncio.run(client._chat_json([{"role": "user", "content": "{}"}]))

    assert payload == {"results": []}
