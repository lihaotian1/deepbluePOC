import json

from app.services.kb_loader import KnowledgeEntry
from app.services.prompt_builder import (
    DOCUMENT_COMPARE_PIPELINE_VERSION,
    build_candidate_adjudication_messages,
    build_document_candidate_messages,
)


def test_document_candidate_prompt_extracts_distinct_requirement_candidates() -> None:
    messages = build_document_candidate_messages(document_title="demo.pdf", document_text="source")

    system_prompt = messages[0]["content"]
    user_payload = json.loads(messages[1]["content"])

    assert "候选要求片段提取助手" in system_prompt
    assert "提取可能需要供应商响应、澄清、确认或偏差判断的候选要求片段" in system_prompt
    assert "只保留一条最完整、最有代表性的片段" in system_prompt
    assert "JSON Lines" in system_prompt
    assert user_payload["document_title"] == "demo.pdf"
    assert user_payload["document_text"] == "source"


def test_candidate_adjudication_prompt_uses_two_level_outcome_and_brief_summary() -> None:
    messages = build_candidate_adjudication_messages(
        document_title="demo.pdf",
        candidate_excerpts=[{"chapter_title": "1 总则", "source_excerpt": "source"}],
        entries=[KnowledgeEntry(entry_id="kb-1", category="分类A", text="标准条目", type_code="P", raw_value="P")],
    )

    system_prompt = messages[0]["content"]
    user_payload = json.loads(messages[1]["content"])

    assert DOCUMENT_COMPARE_PIPELINE_VERSION in system_prompt
    assert "只分为两类" in system_prompt
    assert "部分满足" in system_prompt
    assert "全部归入“存在冲突”" in system_prompt
    assert "difference_summary_brief" in system_prompt
    assert "不要加“直接满足：”或“存在冲突：”前缀" in system_prompt
    assert "\"difference_summary_brief\":\"string\"" in system_prompt
    assert "如果两条询价要求本质上是同一件事的重复表达，只保留一条" in system_prompt
    assert "如果同一 entry_id 下既出现直接满足又出现存在冲突，则只保留存在冲突结果" in system_prompt
    assert user_payload["document_title"] == "demo.pdf"
    assert user_payload["candidate_excerpts"][0]["source_excerpt"] == "source"
    assert user_payload["kb_entries"][0]["entry_id"] == "kb-1"
