import json
from pathlib import Path

from app.schemas import KnowledgeBaseCategory, KnowledgeBaseDocument, KnowledgeBaseItem
from app.services.knowledge_base_manager import KnowledgeBaseManager


def test_manager_lists_reads_and_saves_knowledge_base_files(tmp_path: Path) -> None:
    kb_dir = tmp_path / "kb"
    kb_dir.mkdir()
    file_path = kb_dir / "demo.json"
    file_path.write_text(
        json.dumps(
            {
                "分类A": [{"条目1": "P"}],
                "分类B": [{"条目2": "A"}],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    manager = KnowledgeBaseManager(kb_dir)

    files = manager.list_files()
    assert [item.file_name for item in files] == ["demo.json"]

    document = manager.read_file("demo.json")
    assert document.file_name == "demo.json"
    assert document.format == "grouped"
    assert [category.name for category in document.categories] == ["分类A", "分类B"]
    assert document.categories[0].items[0].text == "条目1"
    assert document.categories[0].items[0].value == "P"

    updated_document = KnowledgeBaseDocument(
        file_name="demo.json",
        display_name="demo",
        format="grouped",
        categories=[
            KnowledgeBaseCategory(
                name="分类A",
                items=[KnowledgeBaseItem(text="条目1", value="C")],
            ),
            KnowledgeBaseCategory(
                name="新分类",
                items=[KnowledgeBaseItem(text="新增条目", value="B")],
            ),
        ],
    )

    manager.save_file("demo.json", updated_document)

    saved_payload = json.loads(file_path.read_text(encoding="utf-8"))
    assert saved_payload == {
        "分类A": [{"条目1": "C"}],
        "新分类": [{"新增条目": "B"}],
    }


def test_manager_supports_flat_key_value_format_and_file_lifecycle(tmp_path: Path) -> None:
    kb_dir = tmp_path / "kb"
    kb_dir.mkdir()
    file_path = kb_dir / "api610.json"
    file_path.write_text(
        json.dumps({"6.1.1": "Clause 6.1.1 text", "6.1.2": "Clause 6.1.2 text"}, ensure_ascii=False),
        encoding="utf-8",
    )

    manager = KnowledgeBaseManager(kb_dir)

    document = manager.read_file("api610.json")
    assert document.format == "flat_key_value"
    assert [category.name for category in document.categories] == ["6.1.1", "6.1.2"]
    assert document.categories[0].items[0].text == "Clause 6.1.1 text"
    assert document.categories[0].items[0].value == ""

    updated_document = KnowledgeBaseDocument(
        file_name="api610.json",
        display_name="api610",
        format="flat_key_value",
        categories=[
            KnowledgeBaseCategory(
                name="6.1.1",
                items=[KnowledgeBaseItem(text="Updated clause", value="")],
            ),
            KnowledgeBaseCategory(
                name="6.1.3",
                items=[KnowledgeBaseItem(text="New clause", value="")],
            ),
        ],
    )

    manager.save_file("api610.json", updated_document)

    saved_payload = json.loads(file_path.read_text(encoding="utf-8"))
    assert saved_payload == {"6.1.1": "Updated clause", "6.1.3": "New clause"}

    manager.save_file(
        "api610.json",
        KnowledgeBaseDocument(
            file_name="api610.json",
            display_name="api610",
            format="flat_key_value",
            categories=[],
        ),
    )
    empty_payload = json.loads(file_path.read_text(encoding="utf-8"))
    assert empty_payload == {"1": ""}
    reloaded_document = manager.read_file("api610.json")
    assert reloaded_document.format == "flat_key_value"
    assert reloaded_document.categories[0].name == "1"
    assert reloaded_document.categories[0].items[0].text == ""

    manager.create_file("created.json", format_type="grouped")
    assert (kb_dir / "created.json").exists()
    created_payload = json.loads((kb_dir / "created.json").read_text(encoding="utf-8"))
    assert created_payload == {"新分类": [{"新条目": "P"}]}

    manager.delete_file("created.json")
    assert not (kb_dir / "created.json").exists()
