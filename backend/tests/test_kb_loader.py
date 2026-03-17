from pathlib import Path

from app.services.kb_loader import KnowledgeBase, infer_type_code, load_knowledge_base


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
