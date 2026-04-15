from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator


class Chunk(BaseModel):
    chunk_id: int
    source: str
    heading: str
    level: int
    line_no: int
    content: str


class ChunkUpdate(BaseModel):
    chunk_id: int
    content: str


class ChunkUpdateRequest(BaseModel):
    chunks: list[ChunkUpdate] = Field(default_factory=list)


class CompareRequest(BaseModel):
    knowledge_base_files: list[str] = Field(default_factory=list, min_length=1, max_length=2)

    @field_validator("knowledge_base_files")
    @classmethod
    def validate_unique_files(cls, value: list[str]) -> list[str]:
        normalized = [item.strip() for item in value if item and item.strip()]
        if len(normalized) != len(value):
            raise ValueError("Knowledge base file names must not be empty.")
        if len(set(normalized)) != len(normalized):
            raise ValueError("Knowledge base file names must be unique.")
        return normalized


class MatchItem(BaseModel):
    entry_id: str
    category: str
    text: str
    type_code: str
    reason: str = ""
    evidence_sentence_index: int | None = None
    evidence_sentence_text: str = ""


class ChunkCompareResult(BaseModel):
    chunk_id: int
    heading: str
    content: str
    categories: list[str] = Field(default_factory=list)
    matches: list[MatchItem] = Field(default_factory=list)
    label: Literal["命中", "其他"]
    review_status: Literal["已审", "未审"] = "未审"


class ChunkCompareProgress(BaseModel):
    status: Literal["pending", "running", "succeeded", "failed"] = "pending"
    result: ChunkCompareResult | None = None
    error_message: str = ""


class CompareRow(BaseModel):
    row_id: str
    chapter_title: str
    source_excerpt: str
    kb_entry_id: str
    kb_entry_text: str
    difference_summary: str
    type_code: Literal["P", "A", "B", "C"]
    review_comment: str = ""
    review_status: Literal["已审", "未审"] = "未审"


class DocumentSession(BaseModel):
    doc_id: str
    source_file_name: str
    document_text: str = ""
    compare_rows: list[CompareRow] = Field(default_factory=list)
    chunks: list[Chunk] = Field(default_factory=list)
    compare_results_by_kb: dict[str, list[ChunkCompareResult]] = Field(default_factory=dict)
    compare_progress_by_kb: dict[str, dict[int, ChunkCompareProgress]] = Field(default_factory=dict)
    submitted_for_review: bool = False


class DocumentUploadResponse(BaseModel):
    doc_id: str
    source_file_name: str
    document_text: str


class DocumentReviewUpdateRequest(BaseModel):
    compare_rows: list[CompareRow] = Field(default_factory=list)
    submitted_for_review: bool = False


class DocumentReviewResponse(BaseModel):
    doc_id: str
    compare_rows: list[CompareRow] = Field(default_factory=list)
    submitted_for_review: bool = False


class KnowledgeBaseFileSummary(BaseModel):
    file_name: str
    display_name: str


class KnowledgeBaseItem(BaseModel):
    text: str
    value: str


class KnowledgeBaseCategory(BaseModel):
    name: str
    items: list[KnowledgeBaseItem] = Field(default_factory=list)


class KnowledgeBaseDocument(BaseModel):
    file_name: str
    display_name: str
    format: Literal["grouped", "flat_key_value"]
    categories: list[KnowledgeBaseCategory] = Field(default_factory=list)


class KnowledgeBaseCreateRequest(BaseModel):
    file_name: str
    format: Literal["grouped", "flat_key_value"] = "grouped"


class TranslationRequest(BaseModel):
    text: str = Field(min_length=1)

    @field_validator("text")
    @classmethod
    def validate_non_blank_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Text must not be blank.")
        return normalized


class TranslationResponse(BaseModel):
    translation: str
