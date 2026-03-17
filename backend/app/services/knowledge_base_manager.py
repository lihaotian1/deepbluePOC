from __future__ import annotations

import json
from pathlib import Path
from typing import Literal, cast

from app.schemas import (
    KnowledgeBaseCategory,
    KnowledgeBaseDocument,
    KnowledgeBaseFileSummary,
    KnowledgeBaseItem,
)


class KnowledgeBaseManager:
    def __init__(self, kb_dir: Path) -> None:
        self.kb_dir = kb_dir
        self.kb_dir.mkdir(parents=True, exist_ok=True)

    def list_files(self) -> list[KnowledgeBaseFileSummary]:
        files = sorted(self.kb_dir.glob("*.json"), key=lambda path: path.name.lower())
        return [
            KnowledgeBaseFileSummary(file_name=file_path.name, display_name=file_path.stem)
            for file_path in files
        ]

    def read_file(self, file_name: str) -> KnowledgeBaseDocument:
        file_path = self._resolve_existing_file(file_name)
        payload = json.loads(file_path.read_text(encoding="utf-8"))
        format_type = self._detect_format(payload)
        categories: list[KnowledgeBaseCategory] = []
        if format_type == "grouped":
            for category_name, rows in payload.items():
                items: list[KnowledgeBaseItem] = []
                if isinstance(rows, list):
                    for row in rows:
                        if not isinstance(row, dict) or not row:
                            continue
                        text, value = next(iter(row.items()))
                        items.append(KnowledgeBaseItem(text=str(text), value=str(value)))
                categories.append(KnowledgeBaseCategory(name=str(category_name), items=items))
        else:
            for category_name, text_value in payload.items():
                categories.append(
                    KnowledgeBaseCategory(
                        name=str(category_name),
                        items=[KnowledgeBaseItem(text=str(text_value), value="")],
                    )
                )

        return KnowledgeBaseDocument(
            file_name=file_path.name,
            display_name=file_path.stem,
            format=cast(Literal["grouped", "flat_key_value"], format_type),
            categories=categories,
        )

    def save_file(self, file_name: str, document: KnowledgeBaseDocument) -> Path:
        file_path = self._resolve_existing_file(file_name)
        if document.format == "flat_key_value":
            serialized_payload = _build_flat_payload(document)
        else:
            serialized_payload = _build_grouped_payload(document)
        file_path.write_text(json.dumps(serialized_payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return file_path

    def create_file(self, file_name: str, format_type: str) -> Path:
        file_path = self._resolve_new_file(file_name)
        if format_type == "flat_key_value":
            serialized_payload = {"1": ""}
        else:
            serialized_payload = {"新分类": [{"新条目": "P"}]}
        file_path.write_text(json.dumps(serialized_payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return file_path

    def delete_file(self, file_name: str) -> None:
        file_path = self._resolve_existing_file(file_name)
        file_path.unlink(missing_ok=False)

    def _resolve_existing_file(self, file_name: str) -> Path:
        file_path = (self.kb_dir / file_name).resolve()
        kb_root = self.kb_dir.resolve()
        if file_path.suffix.lower() != ".json" or kb_root not in file_path.parents:
            raise ValueError("Invalid knowledge base file")
        if not file_path.exists():
            raise FileNotFoundError(file_name)
        return file_path

    def _resolve_new_file(self, file_name: str) -> Path:
        file_path = (self.kb_dir / file_name).resolve()
        kb_root = self.kb_dir.resolve()
        if file_path.suffix.lower() != ".json" or kb_root not in file_path.parents:
            raise ValueError("Invalid knowledge base file")
        if file_path.exists():
            raise FileExistsError(file_name)
        return file_path

    @staticmethod
    def _detect_format(payload: dict) -> Literal["grouped", "flat_key_value"]:
        for value in payload.values():
            if isinstance(value, list):
                return "grouped"
            if isinstance(value, str):
                return "flat_key_value"
        return "grouped"


def _build_flat_payload(document: KnowledgeBaseDocument) -> dict[str, str]:
    payload: dict[str, str] = {}
    for category in document.categories:
        if not category.name:
            continue
        payload[category.name] = category.items[0].text if category.items else ""
    return payload or {"1": ""}


def _build_grouped_payload(document: KnowledgeBaseDocument) -> dict[str, list[dict[str, str]]]:
    payload: dict[str, list[dict[str, str]]] = {}
    for category in document.categories:
        if not category.name:
            continue
        payload[category.name] = [{item.text: item.value} for item in category.items if item.text]
    return payload
