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
    stream_responses: list[object] = []

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
        if self.stream_responses:
            next_item = self.stream_responses.pop(0)
            if isinstance(next_item, Exception):
                raise next_item
            if isinstance(next_item, _FakeAsyncStreamResponse):
                return next_item
        return _FakeAsyncStreamResponse(self.stream_chunks)


class _FakeAsyncStreamResponse:
    def __init__(self, chunks: list[str], status_code: int = 200) -> None:
        self.status_code = status_code
        self.headers: dict[str, str] = {}
        self._chunks = list(chunks)
        self.request = httpx.Request("POST", "https://example.test/v1/chat/completions")

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise httpx.HTTPStatusError("boom", request=self.request, response=self)

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
    _SequencedAsyncClient.responses = []
    _SequencedAsyncClient.stream_responses = [
        _FakeAsyncStreamResponse([], status_code=429),
        _FakeAsyncStreamResponse(
            [
                'data: {"choices":[{"delta":{"content":"{\\"entry_id\\":\\"kb-1\\",\\"chapter_title\\":\\"1 总则\\",\\"source_excerpt\\":\\"source\\",\\"difference_summary\\":\\"存在冲突：需要澄清。\\",\\"difference_summary_brief\\":\\"需要澄清。\\"}\\n"}}]}\n\n',
                "data: [DONE]\n\n",
            ]
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
    async def fake_extract_document_candidates(*, document_title, document_text):
        return [{"chapter_title": "1 总则", "source_excerpt": "source"}]
    client.extract_document_candidates = fake_extract_document_candidates
    rows = asyncio.run(
        client.compare_document_rows(
            document_title="demo.pdf",
            document_text="source",
            entries=[KnowledgeEntry(entry_id="kb-1", category="分类A", text="标准条目", type_code="P", raw_value="P")],
        )
    )

    assert len(rows) == 1
    assert rows[0]["entry_id"] == "kb-1"
    assert rows[0]["difference_summary_brief"] == "需要澄清。"
    assert sleep_calls == [1.0]


def test_compare_document_rows_retries_read_timeout_before_succeeding(monkeypatch) -> None:
    _SequencedAsyncClient.responses = []
    _SequencedAsyncClient.stream_responses = [
        httpx.ReadTimeout("timed out"),
        _FakeAsyncStreamResponse(
            [
                'data: {"choices":[{"delta":{"content":"{\\"entry_id\\":\\"kb-1\\",\\"chapter_title\\":\\"1 总则\\",\\"source_excerpt\\":\\"source\\",\\"difference_summary\\":\\"直接满足：可满足。\\",\\"difference_summary_brief\\":\\"可直接满足。\\"}\\n"}}]}\n\n',
                "data: [DONE]\n\n",
            ]
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
    async def fake_extract_document_candidates(*, document_title, document_text):
        return [{"chapter_title": "1 总则", "source_excerpt": "source"}]
    client.extract_document_candidates = fake_extract_document_candidates
    rows = asyncio.run(
        client.compare_document_rows(
            document_title="demo.pdf",
            document_text="source",
            entries=[KnowledgeEntry(entry_id="kb-1", category="分类A", text="标准条目", type_code="P", raw_value="P")],
        )
    )

    assert len(rows) == 1
    assert rows[0]["difference_summary"] == "直接满足：可满足。"
    assert rows[0]["difference_summary_brief"] == "可直接满足。"
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
    _SequencedAsyncClient.stream_responses = []

    monkeypatch.setattr(llm_client_module.httpx, "AsyncClient", _SequencedAsyncClient)

    client = OpenAICompatibleMatcherLLM(
        base_url="https://example.test/v1",
        api_key="demo-key",
        model="demo-model",
        timeout=60,
    )
    async def fake_extract_document_candidates(*, document_title, document_text):
        return [{"chapter_title": "1 总则", "source_excerpt": "source"}]
    client.extract_document_candidates = fake_extract_document_candidates

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


def test_stream_compare_document_rows_yields_rows_incrementally_from_json_lines(monkeypatch) -> None:
    _SequencedAsyncClient.responses = []
    _SequencedAsyncClient.stream_chunks = [
        'data: {"choices":[{"delta":{"content":"{\\"entry_id\\":\\"kb-1\\",\\"chapter_title\\":\\"1 总则\\",\\"source_excerpt\\":\\"A\\""}}]}\n\n',
        'data: {"choices":[{"delta":{"content":",\\"difference_summary\\":\\"存在冲突：需要澄清\\",\\"difference_summary_brief\\":\\"需要澄清\\"}\\n"}}]}\n\n',
        'data: {"choices":[{"delta":{"content":"{\\"entry_id\\":\\"kb-1\\",\\"chapter_title\\":\\"2 铭牌\\",\\"source_excerpt\\":\\"B\\",\\"difference_summary\\":\\"直接满足：可满足\\",\\"difference_summary_brief\\":\\"可满足\\"}\\n"}}]}\n\n',
        "data: [DONE]\n\n",
    ]
    monkeypatch.setattr(llm_client_module.httpx, "AsyncClient", _SequencedAsyncClient)

    client = OpenAICompatibleMatcherLLM(
        base_url="https://example.test/v1",
        api_key="demo-key",
        model="demo-model",
        timeout=60,
    )

    async def collect():
        output = []
        async for row in client.stream_compare_document_rows(
            document_title="demo.pdf",
            document_text="source",
            entries=[KnowledgeEntry(entry_id="kb-1", category="分类A", text="标准条目", type_code="P", raw_value="P")],
        ):
            output.append(row)
        return output

    rows = asyncio.run(collect())

    assert rows == [
        {
            "entry_id": "kb-1",
            "chapter_title": "1 总则",
            "source_excerpt": "A",
            "difference_summary": "存在冲突：需要澄清",
            "difference_summary_brief": "需要澄清",
        },
        {
            "entry_id": "kb-1",
            "chapter_title": "2 铭牌",
            "source_excerpt": "B",
            "difference_summary": "直接满足：可满足",
            "difference_summary_brief": "可满足",
        },
    ]
