import json

from app.services.kb_loader import KnowledgeEntry
from app.services.prompt_builder import build_document_compare_messages


def test_document_compare_prompt_uses_two_level_outcome_and_brief_summary() -> None:
    messages = build_document_compare_messages(
        document_title="demo.pdf",
        document_text="source",
        entries=[KnowledgeEntry(entry_id="kb-1", category="分类A", text="标准条目", type_code="P", raw_value="P")],
    )

    system_prompt = messages[0]["content"]
    user_payload = json.loads(messages[1]["content"])

    assert "只分为两类" in system_prompt
    assert "部分满足" in system_prompt
    assert "全部归入“存在冲突”" in system_prompt
    assert "difference_summary_brief" in system_prompt
    assert "不要加“直接满足：”或“存在冲突：”前缀" in system_prompt
    assert "\"difference_summary_brief\":\"string\"" in system_prompt
    assert "原本“部分满足”的情况，全部归入“存在冲突”" in system_prompt
    assert "如果两条询价要求本质上是同一件事的重复表达，只保留一条" in system_prompt
    assert "如果同一 entry_id 下既出现直接满足又出现存在冲突，则只保留存在冲突结果" in system_prompt
    assert user_payload["document_title"] == "demo.pdf"
    assert user_payload["kb_entries"][0]["entry_id"] == "kb-1"
