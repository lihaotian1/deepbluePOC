import json

from app.services.kb_loader import KnowledgeEntry
from app.services.prompt_builder import (
    DOCUMENT_COMPARE_PIPELINE_VERSION,
    build_candidate_adjudication_messages,
    build_document_candidate_messages,
    build_other_requirement_messages,
)


def test_document_candidate_prompt_extracts_distinct_requirement_candidates() -> None:
    messages = build_document_candidate_messages(document_title="demo.pdf", document_text="source")

    system_prompt = messages[0]["content"]
    user_payload = json.loads(messages[1]["content"])

    assert "候选要求片段提取助手" in system_prompt
    assert "提取可能需要供应商响应、澄清、确认或偏差判断的候选要求片段" in system_prompt
    assert "只提取需要深蓝实际响应的技术要求" in system_prompt
    assert "排除招标流程、资质套话、泛化承诺、背景介绍、空洞规范引用" in system_prompt
    assert "source_excerpt 必须裁剪到最小可用原文" in system_prompt
    assert "不要返回整段上下文或无关前后缀" in system_prompt
    assert "只保留一条最完整、最有代表性的片段" in system_prompt
    assert "按文档原始顺序输出" in system_prompt
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
    assert "source_excerpt 必须直接复用 candidate_excerpts 中的最小可用原文" in system_prompt
    assert "不要改写、扩写或拼接成长句" in system_prompt
    assert "如果两条询价要求本质上是同一件事的重复表达，只保留一条" in system_prompt
    assert "如果同一 entry_id 下既出现直接满足又出现存在冲突，则只保留存在冲突结果" in system_prompt
    assert user_payload["document_title"] == "demo.pdf"
    assert user_payload["candidate_excerpts"][0]["source_excerpt"] == "source"
    assert user_payload["kb_entries"][0]["entry_id"] == "kb-1"


def test_other_requirement_prompt_only_allows_unmatched_candidates_and_summary_output() -> None:
    messages = build_other_requirement_messages(
        document_title="demo.pdf",
        candidate_excerpts=[
            {"chapter_title": "1 总则", "source_excerpt": "Pump flow shall be 120 m3/h."},
        ],
        matched_excerpts=[
            {"chapter_title": "2 文件", "source_excerpt": "Vendor shall provide drawings."},
        ],
    )

    system_prompt = messages[0]["content"]
    user_payload = json.loads(messages[1]["content"])

    assert DOCUMENT_COMPARE_PIPELINE_VERSION in system_prompt
    assert "未匹配技术要求清单整理助手" in system_prompt
    assert "只允许从 candidate_excerpts 中挑选未被标准化配套覆盖的项" in system_prompt
    assert "不要输出 matched_excerpts 中已经命中的内容" in system_prompt
    assert "source_excerpt 必须直接复用 candidate_excerpts 中的最小可用原文" in system_prompt
    assert "\"summary\":\"string\"" in system_prompt
    assert "summary 必须是中文一句话总结" in system_prompt
    assert user_payload["document_title"] == "demo.pdf"
    assert user_payload["candidate_excerpts"][0]["source_excerpt"] == "Pump flow shall be 120 m3/h."
    assert user_payload["matched_excerpts"][0]["source_excerpt"] == "Vendor shall provide drawings."
