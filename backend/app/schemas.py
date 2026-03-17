from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


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


class MatchItem(BaseModel):
    entry_id: str
    category: str
    text: str
    type_code: Literal["P", "A", "B", "C", "OTHER"]
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


class DocumentSession(BaseModel):
    doc_id: str
    source_file_name: str
    chunks: list[Chunk] = Field(default_factory=list)
    compare_results: list[ChunkCompareResult] = Field(default_factory=list)


class DocumentUploadResponse(BaseModel):
    doc_id: str
    source_file_name: str
    chunks: list[Chunk]


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
