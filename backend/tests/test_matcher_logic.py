import asyncio
import json
from typing import cast

import pytest

from app.schemas import Chunk
from app.services import llm_client as llm_client_module
from app.services.kb_loader import KnowledgeBase, KnowledgeEntry, load_tender_instruction_knowledge_base
from app.services.llm_client import OpenAICompatibleMatcherLLM
from app.services.matcher_service import MatcherService, _split_sentences
from app.services.prompt_builder import build_batch_item_messages


class FakeLLM:
    def __init__(self, categories_by_chunk, hits_by_chunk_and_category):
        self._categories_by_chunk = categories_by_chunk
        self._hits_by_chunk_and_category = hits_by_chunk_and_category
        self.classify_batch_calls = 0
        self.match_batch_calls = 0
        self.match_batch_chunks = []

    async def classify_categories(self, *, chunk_text, category_keys):
        return []

    async def match_items(self, *, chunk_text, category, entries):
        return []

    async def classify_categories_batch(self, *, chunks, category_keys):
        self.classify_batch_calls += 1
        output = {}
        for chunk_id, _ in chunks:
            output[chunk_id] = self._categories_by_chunk.get(chunk_id, [])
        return output

    async def match_items_batch(self, *, category, entries, chunks):
        self.match_batch_calls += 1
        self.match_batch_chunks.append(chunks)
        output = {}
        for chunk in chunks:
            if isinstance(chunk, tuple):
                chunk_id = chunk[0]
            else:
                chunk_id = chunk["chunk_id"]
            output[chunk_id] = self._hits_by_chunk_and_category.get((chunk_id, category), [])
        return output


class StubChatMatcherLLM(OpenAICompatibleMatcherLLM):
    def __init__(self, payload):
        super().__init__(base_url="https://example.test", api_key="token", model="demo")
        self.payload = payload

    async def _chat_json(self, messages):
        return self.payload


class FakeHTTPResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


class FakeAsyncClient:
    def __init__(self, payload, *, timeout):
        self._payload = payload
        self.timeout = timeout

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def post(self, url, headers, json):
        return FakeHTTPResponse(self._payload)


def _build_kb() -> KnowledgeBase:
    entries = [
        KnowledgeEntry(
            entry_id="分类A-1",
            category="分类A",
            text="符合API 610",
            type_code="P",
            raw_value="P",
        ),
        KnowledgeEntry(
            entry_id="分类A-2",
            category="分类A",
            text="满足防爆要求",
            type_code="A",
            raw_value="A",
        ),
        KnowledgeEntry(
            entry_id="分类B-1",
            category="分类B",
            text="其他要求",
            type_code="A",
            raw_value="A",
        ),
    ]
    return KnowledgeBase(entries=entries)


def test_matcher_marks_other_when_no_category_hit() -> None:
    matcher = MatcherService(
        kb=_build_kb(),
        llm=FakeLLM(categories_by_chunk={}, hits_by_chunk_and_category={}),
    )
    chunk = Chunk(chunk_id=1, source="demo.pdf", heading="1", level=1, line_no=1, content="abc")

    result = asyncio.run(matcher.compare_chunk(chunk))

    assert result.label == "其他"
    assert result.matches == []


def test_matcher_returns_hit_items_with_type_code() -> None:
    llm = FakeLLM(
        categories_by_chunk={2: ["分类A"]},
        hits_by_chunk_and_category={(2, "分类A"): [{"entry_id": "分类A-1", "reason": "语义一致"}]},
    )
    matcher = MatcherService(
        kb=_build_kb(),
        llm=llm,
    )
    chunk = Chunk(chunk_id=2, source="demo.pdf", heading="2", level=1, line_no=2, content="符合API")

    result = asyncio.run(matcher.compare_chunk(chunk))

    assert result.label == "命中"
    assert len(result.matches) == 1
    assert result.matches[0].type_code == "P"


def test_matcher_forwards_indexed_sentences_to_batch_item_matching() -> None:
    llm = FakeLLM(
        categories_by_chunk={7: ["分类A"]},
        hits_by_chunk_and_category={(7, "分类A"): [{"entry_id": "分类A-1", "reason": "命中"}]},
    )
    matcher = MatcherService(kb=_build_kb(), llm=llm)
    chunk = Chunk(
        chunk_id=7,
        source="demo.pdf",
        heading="7",
        level=1,
        line_no=7,
        content="第一句；第二句。\nThird sentence; fourth sentence!",
    )

    result = asyncio.run(matcher.compare_chunk(chunk))

    assert result.label == "命中"
    assert llm.match_batch_chunks == [
        [
            {
                "chunk_id": 7,
                "content": "第一句；第二句。\nThird sentence; fourth sentence!",
                "sentences": [
                    {"index": 0, "text": "第一句；"},
                    {"index": 1, "text": "第二句。"},
                    {"index": 2, "text": "Third sentence;"},
                    {"index": 3, "text": "fourth sentence!"},
                ],
            }
        ]
    ]


def test_matcher_deduplicates_classifier_categories_preserving_order() -> None:
    llm = FakeLLM(
        categories_by_chunk={8: ["分类A", "分类A", "分类B", "分类A", "幻觉分类"]},
        hits_by_chunk_and_category={
            (8, "分类A"): [{"entry_id": "分类A-1", "reason": "A命中"}],
            (8, "分类B"): [{"entry_id": "分类B-1", "reason": "B命中"}],
        },
    )
    matcher = MatcherService(kb=_build_kb(), llm=llm)
    chunk = Chunk(chunk_id=8, source="demo.pdf", heading="8", level=1, line_no=8, content="第一句。第二句。")

    result = asyncio.run(matcher.compare_chunk(chunk))

    assert result.categories == ["分类A", "分类B"]
    assert llm.match_batch_calls == 2
    assert llm.match_batch_chunks == [
        [
            {
                "chunk_id": 8,
                "content": "第一句。第二句。",
                "sentences": [
                    {"index": 0, "text": "第一句。"},
                    {"index": 1, "text": "第二句。"},
                ],
            }
        ],
        [
            {
                "chunk_id": 8,
                "content": "第一句。第二句。",
                "sentences": [
                    {"index": 0, "text": "第一句。"},
                    {"index": 1, "text": "第二句。"},
                ],
            }
        ],
    ]


def test_matcher_rejects_duplicate_input_chunk_ids() -> None:
    matcher = MatcherService(
        kb=_build_kb(),
        llm=FakeLLM(categories_by_chunk={}, hits_by_chunk_and_category={}),
    )
    chunks = [
        Chunk(chunk_id=9, source="demo.pdf", heading="9", level=1, line_no=9, content="A"),
        Chunk(chunk_id=9, source="demo.pdf", heading="9.1", level=1, line_no=10, content="B"),
    ]

    with pytest.raises(ValueError, match="chunk_id"):
        asyncio.run(matcher.compare_chunks_with_trace(chunks, batch_size=10))


def test_matcher_dedupes_duplicate_entry_matches_preserving_first_hit() -> None:
    llm = FakeLLM(
        categories_by_chunk={10: ["分类A"]},
        hits_by_chunk_and_category={
            (10, "分类A"): [
                {
                    "entry_id": "分类A-1",
                    "reason": "首个命中",
                    "evidence_sentence_index": 0,
                    "evidence_sentence_text": "第一句。",
                },
                {
                    "entry_id": "分类A-1",
                    "reason": "重复命中",
                    "evidence_sentence_index": 1,
                    "evidence_sentence_text": "第二句。",
                },
            ]
        },
    )
    matcher = MatcherService(kb=_build_kb(), llm=llm)
    chunk = Chunk(
        chunk_id=10,
        source="demo.pdf",
        heading="10",
        level=1,
        line_no=10,
        content="第一句。第二句。",
    )

    result = asyncio.run(matcher.compare_chunk(chunk))
    match_dump = result.matches[0].model_dump()

    assert len(result.matches) == 1
    assert match_dump["reason"] == "首个命中"
    assert match_dump["evidence_sentence_index"] == 0
    assert match_dump["evidence_sentence_text"] == "第一句。"


def test_matcher_preserves_valid_evidence_metadata() -> None:
    llm = FakeLLM(
        categories_by_chunk={4: ["分类A"]},
        hits_by_chunk_and_category={
            (4, "分类A"): [
                {
                    "entry_id": "分类A-1",
                    "reason": "第二句直接对应知识库要求",
                    "evidence_sentence_index": 1,
                    "evidence_sentence_text": "第二句。",
                }
            ]
        },
    )
    matcher = MatcherService(kb=_build_kb(), llm=llm)
    chunk = Chunk(
        chunk_id=4,
        source="demo.pdf",
        heading="4",
        level=1,
        line_no=4,
        content="第一句。第二句。",
    )

    result = asyncio.run(matcher.compare_chunk(chunk))
    match_dump = result.matches[0].model_dump()

    assert result.label == "命中"
    assert match_dump["evidence_sentence_index"] == 1
    assert match_dump["evidence_sentence_text"] == "第二句。"


def test_matcher_uses_local_sentence_text_for_valid_evidence_index() -> None:
    llm = FakeLLM(
        categories_by_chunk={6: ["分类A"]},
        hits_by_chunk_and_category={
            (6, "分类A"): [
                {
                    "entry_id": "分类A-1",
                    "reason": "模型返回了空证据文本",
                    "evidence_sentence_index": 0,
                    "evidence_sentence_text": None,
                },
                {
                    "entry_id": "分类A-2",
                    "reason": "模型返回了错误证据文本",
                    "evidence_sentence_index": 1,
                    "evidence_sentence_text": "完全不匹配的句子",
                },
            ]
        },
    )
    matcher = MatcherService(kb=_build_kb(), llm=llm)
    chunk = Chunk(
        chunk_id=6,
        source="demo.pdf",
        heading="6",
        level=1,
        line_no=6,
        content="第一句。第二句。",
    )

    result = asyncio.run(matcher.compare_chunk(chunk))
    first_match_dump = result.matches[0].model_dump()
    second_match_dump = result.matches[1].model_dump()

    assert result.label == "命中"
    assert first_match_dump["evidence_sentence_index"] == 0
    assert first_match_dump["evidence_sentence_text"] == "第一句。"
    assert second_match_dump["evidence_sentence_index"] == 1
    assert second_match_dump["evidence_sentence_text"] == "第二句。"


def test_matcher_preserves_evidence_text_when_evidence_index_is_invalid_or_out_of_range() -> None:
    llm = FakeLLM(
        categories_by_chunk={5: ["分类A"]},
        hits_by_chunk_and_category={
            (5, "分类A"): [
                {
                    "entry_id": "分类A-1",
                    "reason": "证据索引不是整数",
                    "evidence_sentence_index": "oops",
                    "evidence_sentence_text": "第一句。",
                },
                {
                    "entry_id": "分类A-2",
                    "reason": "证据索引越界",
                    "evidence_sentence_index": 9,
                    "evidence_sentence_text": "不存在的句子。",
                },
            ]
        },
    )
    matcher = MatcherService(kb=_build_kb(), llm=llm)
    chunk = Chunk(
        chunk_id=5,
        source="demo.pdf",
        heading="5",
        level=1,
        line_no=5,
        content="第一句。第二句。",
    )

    result = asyncio.run(matcher.compare_chunk(chunk))
    first_match_dump = result.matches[0].model_dump()
    second_match_dump = result.matches[1].model_dump()

    assert result.label == "命中"
    assert len(result.matches) == 2
    assert first_match_dump["evidence_sentence_index"] is None
    assert first_match_dump["evidence_sentence_text"] == "第一句。"
    assert second_match_dump["evidence_sentence_index"] is None
    assert second_match_dump["evidence_sentence_text"] == "不存在的句子。"


def test_split_sentences_handles_common_project_delimiters() -> None:
    assert _split_sentences("第一句；第二句。\nThird sentence; fourth sentence!\nLast line") == [
        "第一句；",
        "第二句。",
        "Third sentence;",
        "fourth sentence!",
        "Last line",
    ]


def test_split_sentences_keeps_technical_english_tokens_aligned_with_frontend() -> None:
    technical_chunk = (
        "Use e.g. inspection logs for reference. "
        "Visit portal.example.com for updates. "
        "Email qa.team@example.com before noon. "
        "Attach report.v2.1.pdf to the ticket. "
        "U.S.A. vendor data remains acceptable. "
        "U.S.A. Next sentence starts here."
    )

    assert _split_sentences(technical_chunk) == [
        "Use e.g. inspection logs for reference.",
        "Visit portal.example.com for updates.",
        "Email qa.team@example.com before noon.",
        "Attach report.v2.1.pdf to the ticket.",
        "U.S.A. vendor data remains acceptable.",
        "U.S.A.",
        "Next sentence starts here.",
    ]


def test_matcher_marks_other_when_only_category_hit_without_items() -> None:
    matcher = MatcherService(
        kb=_build_kb(),
        llm=FakeLLM(
            categories_by_chunk={3: ["分类A"]},
            hits_by_chunk_and_category={(3, "分类A"): []},
        ),
    )
    chunk = Chunk(chunk_id=3, source="demo.pdf", heading="3", level=1, line_no=3, content="一般描述")

    result = asyncio.run(matcher.compare_chunk(chunk))

    assert result.label == "其他"
    assert result.matches == []


def test_matcher_batches_multiple_chunks_for_higher_efficiency() -> None:
    llm = FakeLLM(
        categories_by_chunk={1: ["分类A"], 2: ["分类B"]},
        hits_by_chunk_and_category={
            (1, "分类A"): [{"entry_id": "分类A-1", "reason": "命中"}],
            (2, "分类B"): [{"entry_id": "分类B-1", "reason": "命中"}],
        },
    )
    matcher = MatcherService(kb=_build_kb(), llm=llm)
    chunks = [
        Chunk(chunk_id=1, source="demo.pdf", heading="1", level=1, line_no=1, content="A"),
        Chunk(chunk_id=2, source="demo.pdf", heading="2", level=1, line_no=2, content="B"),
    ]

    output = asyncio.run(matcher.compare_chunks_with_trace(chunks, batch_size=10))

    assert len(output) == 2
    assert llm.classify_batch_calls == 1
    assert llm.match_batch_calls == 2


def test_matcher_uses_tender_instruction_display_labels_instead_of_top_level_keys(tmp_path) -> None:
    kb_path = tmp_path / "投标说明知识库.json"
    kb_path.write_text(
        json.dumps(
            {
                "3.2": [
                    {"Clarify the tender action.": "非强制-报价行动-Tutorial-Action"},
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    kb = load_tender_instruction_knowledge_base(kb_path)
    llm = FakeLLM(
        categories_by_chunk={11: ["非强制-报价行动", "3.2"]},
        hits_by_chunk_and_category={
            (11, "非强制-报价行动"): [{"entry_id": kb.entries[0].entry_id, "reason": "语义一致"}],
        },
    )
    matcher = MatcherService(kb=kb, llm=llm)
    chunk = Chunk(chunk_id=11, source="demo.pdf", heading="11", level=1, line_no=11, content="Clarify the tender action.")

    result = asyncio.run(matcher.compare_chunk(chunk))

    assert result.categories == ["非强制-报价行动"]
    assert result.matches[0].category == "非强制-报价行动"
    assert result.matches[0].type_code == "非强制-报价行动"


def test_batch_item_prompt_includes_sentences_and_indexed_evidence_fields() -> None:
    messages = build_batch_item_messages(
        category="分类A",
        entries=_build_kb().by_category("分类A"),
        chunks=[
            {
                "chunk_id": 1,
                "content": "First sentence. Second sentence.",
                "sentences": [
                    {"index": 0, "text": "First sentence."},
                    {"index": 1, "text": "Second sentence."},
                ],
            }
        ],
    )

    assert '"entry_id":string' in messages[0]["content"]
    assert '"reason":string' in messages[0]["content"]
    assert '"evidence_sentence_index":int' in messages[0]["content"]
    assert '"evidence_sentence_text":string' in messages[0]["content"]

    user_payload = json.loads(messages[1]["content"])

    assert user_payload["chunks"] == [
        {
            "chunk_id": 1,
            "content": "First sentence. Second sentence.",
            "sentences": [
                {"index": 0, "text": "First sentence."},
                {"index": 1, "text": "Second sentence."},
            ],
        }
    ]


def test_batch_item_prompt_derives_sentence_metadata_for_tuple_chunks() -> None:
    messages = build_batch_item_messages(
        category="分类A",
        entries=_build_kb().by_category("分类A"),
        chunks=[(2, "First sentence. Second sentence.")],
    )

    user_payload = json.loads(messages[1]["content"])

    assert user_payload["chunks"] == [
        {
            "chunk_id": 2,
            "content": "First sentence. Second sentence.",
            "sentences": [
                {"index": 0, "text": "First sentence."},
                {"index": 1, "text": "Second sentence."},
            ],
        }
    ]


def test_batch_item_prompt_derives_frontend_aligned_sentence_metadata_for_technical_text() -> None:
    messages = build_batch_item_messages(
        category="分类A",
        entries=_build_kb().by_category("分类A"),
        chunks=[
            (
                3,
                "Visit portal.example.com for updates. "
                "Email qa.team@example.com before noon. "
                "Attach report.v2.1.pdf to the ticket. "
                "U.S.A. vendor data remains acceptable.",
            )
        ],
    )

    user_payload = json.loads(messages[1]["content"])

    assert user_payload["chunks"] == [
        {
            "chunk_id": 3,
            "content": (
                "Visit portal.example.com for updates. "
                "Email qa.team@example.com before noon. "
                "Attach report.v2.1.pdf to the ticket. "
                "U.S.A. vendor data remains acceptable."
            ),
            "sentences": [
                {"index": 0, "text": "Visit portal.example.com for updates."},
                {"index": 1, "text": "Email qa.team@example.com before noon."},
                {"index": 2, "text": "Attach report.v2.1.pdf to the ticket."},
                {"index": 3, "text": "U.S.A. vendor data remains acceptable."},
            ],
        }
    ]


def test_batch_item_prompt_raises_for_duplicate_input_chunk_ids() -> None:
    with pytest.raises(ValueError, match="duplicate.*chunk_id"):
        build_batch_item_messages(
            category="分类A",
            entries=_build_kb().by_category("分类A"),
            chunks=[(2, "First sentence."), (2, "Second sentence.")],
        )


def test_batch_item_prompt_raises_for_tuple_chunk_without_valid_integer_chunk_id() -> None:
    with pytest.raises(ValueError, match="chunk_id"):
        build_batch_item_messages(
            category="分类A",
            entries=_build_kb().by_category("分类A"),
            chunks=[(True, "First sentence.")],
        )


def test_batch_item_parser_normalizes_indexed_evidence_fields() -> None:
    llm = StubChatMatcherLLM(
        payload={
            "results": [
                {
                    "chunk_id": 1,
                    "matches": [
                        {
                            "entry_id": " 分类A-1 ",
                            "reason": " 原文描述与标准要求一致 ",
                            "evidence_sentence_index": "0",
                            "evidence_sentence_text": " Optional vibration detectors wired to an auxiliary conduit box ",
                        }
                    ],
                }
            ]
        }
    )

    result = asyncio.run(
        llm.match_items_batch(
            category="分类A",
            entries=_build_kb().by_category("分类A"),
            chunks=[(1, "Optional vibration detectors wired to an auxiliary conduit box")],
        )
    )

    assert result == {
        1: [
            {
                "entry_id": "分类A-1",
                "reason": "原文描述与标准要求一致",
                "evidence_sentence_index": 0,
                "evidence_sentence_text": "Optional vibration detectors wired to an auxiliary conduit box",
            }
        ]
    }


def test_classify_categories_raises_for_non_list_categories_payload() -> None:
    llm = StubChatMatcherLLM(payload={"categories": "分类A"})

    with pytest.raises(ValueError, match="categories"):
        asyncio.run(llm.classify_categories(chunk_text="abc", category_keys=["分类A"]))


def test_match_items_raises_for_non_list_matches_payload() -> None:
    llm = StubChatMatcherLLM(payload={"matches": {"entry_id": "分类A-1", "reason": "命中"}})

    with pytest.raises(ValueError, match="matches"):
        asyncio.run(
            llm.match_items(
                chunk_text="abc",
                category="分类A",
                entries=_build_kb().by_category("分类A"),
            )
        )


def test_match_items_raises_for_missing_matches_payload() -> None:
    llm = StubChatMatcherLLM(payload={})

    with pytest.raises(ValueError, match="matches"):
        asyncio.run(
            llm.match_items(
                chunk_text="abc",
                category="分类A",
                entries=_build_kb().by_category("分类A"),
            )
        )


def test_classify_categories_ignores_categories_not_requested() -> None:
    llm = StubChatMatcherLLM(payload={"categories": ["分类A", "幻觉分类"]})

    result = asyncio.run(llm.classify_categories(chunk_text="abc", category_keys=["分类A"]))

    assert result == ["分类A"]


def test_classify_categories_deduplicates_valid_categories_preserving_order() -> None:
    llm = StubChatMatcherLLM(payload={"categories": ["分类A", "分类A", "分类B", "分类A"]})

    result = asyncio.run(llm.classify_categories(chunk_text="abc", category_keys=["分类A", "分类B"]))

    assert result == ["分类A", "分类B"]


def test_classify_categories_batch_ignores_chunk_ids_not_in_input() -> None:
    llm = StubChatMatcherLLM(
        payload={
            "results": [
                {"chunk_id": 1, "categories": ["分类A"]},
                {"chunk_id": 999, "categories": ["分类A"]},
            ]
        }
    )

    result = asyncio.run(llm.classify_categories_batch(chunks=[(1, "abc")], category_keys=["分类A"]))

    assert result == {1: ["分类A"]}


def test_classify_categories_batch_raises_for_duplicate_input_chunk_ids() -> None:
    llm = StubChatMatcherLLM(payload={"results": []})

    with pytest.raises(ValueError, match="duplicate.*chunk_id"):
        asyncio.run(
            llm.classify_categories_batch(
                chunks=[(1, "abc"), (1, "def")],
                category_keys=["分类A"],
            )
        )


def test_classify_categories_batch_raises_for_dict_chunk_without_integer_chunk_id() -> None:
    llm = StubChatMatcherLLM(payload={"results": []})

    with pytest.raises(ValueError, match="chunk_id"):
        asyncio.run(
            llm.classify_categories_batch(
                chunks=cast(list[tuple[int, str]], [{"content": "abc"}]),
                category_keys=["分类A"],
            )
        )


def test_classify_categories_batch_raises_for_tuple_chunk_without_valid_integer_chunk_id() -> None:
    llm = StubChatMatcherLLM(payload={"results": []})

    with pytest.raises(ValueError, match="chunk_id"):
        asyncio.run(
            llm.classify_categories_batch(
                chunks=[(True, "abc")],
                category_keys=["分类A"],
            )
        )


def test_classify_categories_batch_raises_for_dict_chunk_without_integer_chunk_id_when_api_key_missing() -> None:
    llm = OpenAICompatibleMatcherLLM(base_url="https://example.test", api_key="", model="demo")

    with pytest.raises(ValueError, match="chunk_id"):
        asyncio.run(
            llm.classify_categories_batch(
                chunks=cast(list[tuple[int, str]], [{"chunk_id": "bad", "content": "abc"}]),
                category_keys=["分类A"],
            )
        )


def test_classify_categories_batch_deduplicates_valid_categories_preserving_order() -> None:
    llm = StubChatMatcherLLM(
        payload={
            "results": [
                {"chunk_id": 1, "categories": ["分类A", "分类A", "分类B", "分类A"]},
            ]
        }
    )

    result = asyncio.run(
        llm.classify_categories_batch(chunks=[(1, "abc")], category_keys=["分类A", "分类B"])
    )

    assert result == {1: ["分类A", "分类B"]}


def test_classify_categories_batch_ignores_malformed_extra_row_for_unknown_chunk_id() -> None:
    llm = StubChatMatcherLLM(
        payload={
            "results": [
                {"chunk_id": 1, "categories": ["分类A"]},
                {"chunk_id": 999, "categories": "bad"},
            ]
        }
    )

    result = asyncio.run(llm.classify_categories_batch(chunks=[(1, "abc")], category_keys=["分类A"]))

    assert result == {1: ["分类A"]}


def test_classify_categories_batch_raises_for_duplicate_in_scope_chunk_rows() -> None:
    llm = StubChatMatcherLLM(
        payload={
            "results": [
                {"chunk_id": 1, "categories": ["分类A"]},
                {"chunk_id": 1, "categories": ["分类B"]},
            ]
        }
    )

    with pytest.raises(ValueError, match="duplicate.*chunk_id"):
        asyncio.run(llm.classify_categories_batch(chunks=[(1, "abc")], category_keys=["分类A", "分类B"]))


def test_match_items_ignores_entry_ids_not_in_provided_entries() -> None:
    llm = StubChatMatcherLLM(
        payload={
            "matches": [
                {"entry_id": "分类A-1", "reason": "命中"},
                {"entry_id": "幻觉条目", "reason": "模型臆造"},
            ]
        }
    )

    result = asyncio.run(
        llm.match_items(
            chunk_text="abc",
            category="分类A",
            entries=_build_kb().by_category("分类A"),
        )
    )

    assert result == [{"entry_id": "分类A-1", "reason": "命中"}]


def test_match_items_deduplicates_valid_entry_ids_preserving_first_match() -> None:
    llm = StubChatMatcherLLM(
        payload={
            "matches": [
                {"entry_id": "分类A-1", "reason": "first"},
                {"entry_id": "分类A-1", "reason": "second"},
                {"entry_id": "分类A-2", "reason": "third"},
            ]
        }
    )

    result = asyncio.run(
        llm.match_items(
            chunk_text="abc",
            category="分类A",
            entries=_build_kb().by_category("分类A"),
        )
    )

    assert result == [
        {"entry_id": "分类A-1", "reason": "first"},
        {"entry_id": "分类A-2", "reason": "third"},
    ]


def test_match_items_batch_ignores_unknown_chunk_ids_and_entry_ids() -> None:
    llm = StubChatMatcherLLM(
        payload={
            "results": [
                {
                    "chunk_id": 1,
                    "matches": [
                        {
                            "entry_id": "分类A-1",
                            "reason": "命中",
                            "evidence_sentence_index": 0,
                            "evidence_sentence_text": "First sentence.",
                        },
                        {
                            "entry_id": "幻觉条目",
                            "reason": "模型臆造",
                            "evidence_sentence_index": 0,
                            "evidence_sentence_text": "First sentence.",
                        },
                    ],
                },
                {
                    "chunk_id": 999,
                    "matches": [
                        {
                            "entry_id": "分类A-1",
                            "reason": "不应返回",
                            "evidence_sentence_index": 0,
                            "evidence_sentence_text": "Ghost sentence.",
                        }
                    ],
                },
            ]
        }
    )

    result = asyncio.run(
        llm.match_items_batch(
            category="分类A",
            entries=_build_kb().by_category("分类A"),
            chunks=[(1, "First sentence.")],
        )
    )

    assert result == {
        1: [
            {
                "entry_id": "分类A-1",
                "reason": "命中",
                "evidence_sentence_index": 0,
                "evidence_sentence_text": "First sentence.",
            }
        ]
    }


def test_match_items_batch_raises_for_duplicate_input_chunk_ids() -> None:
    llm = StubChatMatcherLLM(payload={"results": []})

    with pytest.raises(ValueError, match="duplicate.*chunk_id"):
        asyncio.run(
            llm.match_items_batch(
                category="分类A",
                entries=_build_kb().by_category("分类A"),
                chunks=[(1, "abc"), (1, "def")],
            )
        )


def test_match_items_batch_raises_for_dict_chunk_without_integer_chunk_id() -> None:
    llm = StubChatMatcherLLM(payload={"results": []})

    with pytest.raises(ValueError, match="chunk_id"):
        asyncio.run(
            llm.match_items_batch(
                category="分类A",
                entries=_build_kb().by_category("分类A"),
                chunks=[{"content": "abc"}],
            )
        )


def test_match_items_batch_raises_for_tuple_chunk_without_valid_integer_chunk_id() -> None:
    llm = StubChatMatcherLLM(payload={"results": []})

    with pytest.raises(ValueError, match="chunk_id"):
        asyncio.run(
            llm.match_items_batch(
                category="分类A",
                entries=_build_kb().by_category("分类A"),
                chunks=cast(list[tuple[int, str]], [("1", "abc")]),
            )
        )


def test_match_items_batch_raises_for_dict_chunk_without_integer_chunk_id_when_api_key_missing() -> None:
    llm = OpenAICompatibleMatcherLLM(base_url="https://example.test", api_key="", model="demo")

    with pytest.raises(ValueError, match="chunk_id"):
        asyncio.run(
            llm.match_items_batch(
                category="分类A",
                entries=_build_kb().by_category("分类A"),
                chunks=[{"chunk_id": None, "content": "abc"}],
            )
        )


def test_match_items_batch_deduplicates_valid_entry_ids_preserving_first_match() -> None:
    llm = StubChatMatcherLLM(
        payload={
            "results": [
                {
                    "chunk_id": 1,
                    "matches": [
                        {
                            "entry_id": "分类A-1",
                            "reason": "first",
                            "evidence_sentence_index": 0,
                            "evidence_sentence_text": "First sentence.",
                        },
                        {
                            "entry_id": "分类A-1",
                            "reason": "second",
                            "evidence_sentence_index": 1,
                            "evidence_sentence_text": "Second sentence.",
                        },
                        {
                            "entry_id": "分类A-2",
                            "reason": "third",
                            "evidence_sentence_index": 0,
                            "evidence_sentence_text": "First sentence.",
                        },
                    ],
                }
            ]
        }
    )

    result = asyncio.run(
        llm.match_items_batch(
            category="分类A",
            entries=_build_kb().by_category("分类A"),
            chunks=[(1, "First sentence. Second sentence.")],
        )
    )

    assert result == {
        1: [
            {
                "entry_id": "分类A-1",
                "reason": "first",
                "evidence_sentence_index": 0,
                "evidence_sentence_text": "First sentence.",
            },
            {
                "entry_id": "分类A-2",
                "reason": "third",
                "evidence_sentence_index": 0,
                "evidence_sentence_text": "First sentence.",
            },
        ]
    }


def test_match_items_batch_ignores_malformed_extra_row_for_unknown_chunk_id() -> None:
    llm = StubChatMatcherLLM(
        payload={
            "results": [
                {
                    "chunk_id": 1,
                    "matches": [
                        {
                            "entry_id": "分类A-1",
                            "reason": "命中",
                            "evidence_sentence_index": 0,
                            "evidence_sentence_text": "First sentence.",
                        }
                    ],
                },
                {"chunk_id": 999, "matches": "bad"},
            ]
        }
    )

    result = asyncio.run(
        llm.match_items_batch(
            category="分类A",
            entries=_build_kb().by_category("分类A"),
            chunks=[(1, "First sentence.")],
        )
    )

    assert result == {
        1: [
            {
                "entry_id": "分类A-1",
                "reason": "命中",
                "evidence_sentence_index": 0,
                "evidence_sentence_text": "First sentence.",
            }
        ]
    }


def test_match_items_batch_raises_for_duplicate_in_scope_chunk_rows() -> None:
    llm = StubChatMatcherLLM(
        payload={
            "results": [
                {
                    "chunk_id": 1,
                    "matches": [
                        {
                            "entry_id": "分类A-1",
                            "reason": "first",
                            "evidence_sentence_index": 0,
                            "evidence_sentence_text": "First sentence.",
                        }
                    ],
                },
                {
                    "chunk_id": 1,
                    "matches": [
                        {
                            "entry_id": "分类A-2",
                            "reason": "second",
                            "evidence_sentence_index": 0,
                            "evidence_sentence_text": "First sentence.",
                        }
                    ],
                },
            ]
        }
    )

    with pytest.raises(ValueError, match="duplicate.*chunk_id"):
        asyncio.run(
            llm.match_items_batch(
                category="分类A",
                entries=_build_kb().by_category("分类A"),
                chunks=[(1, "First sentence.")],
            )
        )


def test_classify_categories_batch_raises_for_non_list_results_payload() -> None:
    llm = StubChatMatcherLLM(payload={"results": {"chunk_id": 1, "categories": ["分类A"]}})

    with pytest.raises(ValueError, match="results"):
        asyncio.run(llm.classify_categories_batch(chunks=[(1, "abc")], category_keys=["分类A"]))


def test_classify_categories_batch_raises_for_non_list_categories_row() -> None:
    llm = StubChatMatcherLLM(payload={"results": [{"chunk_id": 1, "categories": "分类A"}]})

    with pytest.raises(ValueError, match="categories"):
        asyncio.run(llm.classify_categories_batch(chunks=[(1, "abc")], category_keys=["分类A"]))


def test_classify_categories_batch_raises_for_boolean_response_chunk_id() -> None:
    llm = StubChatMatcherLLM(payload={"results": [{"chunk_id": True, "categories": ["分类A"]}]})

    with pytest.raises(ValueError, match="chunk_id"):
        asyncio.run(llm.classify_categories_batch(chunks=[(1, "abc")], category_keys=["分类A"]))


def test_match_items_batch_raises_for_non_list_results_payload() -> None:
    llm = StubChatMatcherLLM(payload={"results": {"chunk_id": 1, "matches": []}})

    with pytest.raises(ValueError, match="results"):
        asyncio.run(
            llm.match_items_batch(
                category="分类A",
                entries=_build_kb().by_category("分类A"),
                chunks=[(1, "abc")],
            )
        )


def test_match_items_batch_raises_for_non_list_matches_row() -> None:
    llm = StubChatMatcherLLM(payload={"results": [{"chunk_id": 1, "matches": "bad"}]})

    with pytest.raises(ValueError, match="matches"):
        asyncio.run(
            llm.match_items_batch(
                category="分类A",
                entries=_build_kb().by_category("分类A"),
                chunks=[(1, "abc")],
            )
        )


def test_match_items_batch_raises_for_boolean_response_chunk_id() -> None:
    llm = StubChatMatcherLLM(
        payload={
            "results": [
                {
                    "chunk_id": True,
                    "matches": [
                        {
                            "entry_id": "分类A-1",
                            "reason": "命中",
                            "evidence_sentence_index": 0,
                            "evidence_sentence_text": "First sentence.",
                        }
                    ],
                }
            ]
        }
    )

    with pytest.raises(ValueError, match="chunk_id"):
        asyncio.run(
            llm.match_items_batch(
                category="分类A",
                entries=_build_kb().by_category("分类A"),
                chunks=[(1, "First sentence.")],
            )
        )


def test_chat_json_raises_clear_error_for_empty_choices(monkeypatch: pytest.MonkeyPatch) -> None:
    payload = {"choices": []}

    monkeypatch.setattr(
        llm_client_module.httpx,
        "AsyncClient",
        lambda timeout: FakeAsyncClient(payload, timeout=timeout),
    )

    llm = OpenAICompatibleMatcherLLM(base_url="https://example.test", api_key="token", model="demo")

    with pytest.raises(ValueError, match="choices"):
        asyncio.run(llm._chat_json([{"role": "user", "content": "{}"}]))


def test_chat_json_raises_clear_error_for_invalid_content_shape(monkeypatch: pytest.MonkeyPatch) -> None:
    payload = {"choices": [{"message": {"content": {"unexpected": True}}}]}

    monkeypatch.setattr(
        llm_client_module.httpx,
        "AsyncClient",
        lambda timeout: FakeAsyncClient(payload, timeout=timeout),
    )

    llm = OpenAICompatibleMatcherLLM(base_url="https://example.test", api_key="token", model="demo")

    with pytest.raises(ValueError, match="content"):
        asyncio.run(llm._chat_json([{"role": "user", "content": "{}"}]))


def test_chat_json_raises_clear_error_for_invalid_json_content(monkeypatch: pytest.MonkeyPatch) -> None:
    payload = {"choices": [{"message": {"content": "not-json"}}]}

    monkeypatch.setattr(
        llm_client_module.httpx,
        "AsyncClient",
        lambda timeout: FakeAsyncClient(payload, timeout=timeout),
    )

    llm = OpenAICompatibleMatcherLLM(base_url="https://example.test", api_key="token", model="demo")

    with pytest.raises(ValueError, match="valid JSON"):
        asyncio.run(llm._chat_json([{"role": "user", "content": "{}"}]))
