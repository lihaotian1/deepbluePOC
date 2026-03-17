from pathlib import Path

import json

from app.services.kb_loader import (
    KnowledgeBase,
    infer_type_code,
    load_knowledge_base,
    load_tender_instruction_knowledge_base,
)


def test_infer_type_code_handles_suffix_values() -> None:
    assert infer_type_code("P") == "P"
    assert infer_type_code("C (Contact ADVE)") == "C"
    assert infer_type_code("Unknown") == "OTHER"


def test_load_knowledge_base_flattens_categories() -> None:
    kb_path = Path("data/知识库/标准化配套知识库.json")
    kb = load_knowledge_base(kb_path)

    assert isinstance(kb, KnowledgeBase)
    assert "通用规范General Specification" in kb.categories
    assert any(entry.type_code == "P" for entry in kb.entries)
    assert all(entry.category for entry in kb.entries)


def test_load_tender_instruction_knowledge_base_groups_by_display_label(tmp_path: Path) -> None:
    kb_path = tmp_path / "投标说明知识库.json"
    kb_path.write_text(
        json.dumps(
            {
                "3.2": [
                    {"Clarify mandatory item": "强制-澄清-Mandatory-Clarification"},
                    {"Reference tutorial item": "非强制-报价参考-Tutorial-Info"},
                    {"Action tutorial item": "非强制-报价行动-Tutorial-Action"},
                    {"Deviation item": "强制-必须偏离"},
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    kb = load_tender_instruction_knowledge_base(kb_path)

    assert kb.categories == ["强制-必须偏离", "强制-澄清", "非强制-报价参考", "非强制-报价行动"]
    assert [(entry.text, entry.category, entry.type_code) for entry in kb.entries] == [
        ("Clarify mandatory item", "强制-澄清", "强制-澄清"),
        ("Reference tutorial item", "非强制-报价参考", "非强制-报价参考"),
        ("Action tutorial item", "非强制-报价行动", "非强制-报价行动"),
        ("Deviation item", "强制-必须偏离", "强制-必须偏离"),
    ]
