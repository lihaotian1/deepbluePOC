from __future__ import annotations

from collections.abc import Iterable

from app.schemas import Chunk, ChunkCompareResult, MatchItem
from app.services.kb_loader import KnowledgeBase
from app.services.sentence_splitter import split_sentences


class MatcherService:
    def __init__(self, kb: KnowledgeBase, llm) -> None:
        self.kb = kb
        self.llm = llm

    async def compare_chunk(self, chunk: Chunk) -> ChunkCompareResult:
        result, _ = await self.compare_chunk_with_trace(chunk)
        return result

    async def compare_chunk_with_trace(self, chunk: Chunk) -> tuple[ChunkCompareResult, list[dict]]:
        batch_result = await self.compare_chunks_with_trace([chunk], batch_size=1)
        return batch_result[0]

    async def compare_chunks_with_trace(
        self,
        chunks: list[Chunk],
        batch_size: int = 10,
    ) -> list[tuple[ChunkCompareResult, list[dict]]]:
        if not chunks:
            return []
        _validate_unique_chunk_ids(chunks)

        output: list[tuple[ChunkCompareResult, list[dict]]] = []
        categories_set = set(self.kb.categories)
        for chunk_batch in _iter_batches(chunks, batch_size):
            batch_payload = [(chunk.chunk_id, chunk.content) for chunk in chunk_batch]
            sentence_map = {
                chunk.chunk_id: split_sentences(chunk.content)
                for chunk in chunk_batch
            }
            classified_map = await self.llm.classify_categories_batch(
                chunks=batch_payload,
                category_keys=self.kb.categories,
            )

            normalized_map: dict[int, list[str]] = {}
            traces: dict[int, list[dict]] = {}
            match_rows: dict[int, list[MatchItem]] = {}
            for chunk in chunk_batch:
                raw_categories = classified_map.get(chunk.chunk_id, [])
                normalized = _dedupe_strings_preserve_order(
                    [name for name in raw_categories if name in categories_set]
                )
                normalized_map[chunk.chunk_id] = normalized
                traces[chunk.chunk_id] = [
                    {
                        "event": "classification",
                        "chunk_id": chunk.chunk_id,
                        "categories": normalized,
                    }
                ]
                match_rows[chunk.chunk_id] = []

            category_chunks: dict[str, list[Chunk]] = {}
            for chunk in chunk_batch:
                for category in normalized_map[chunk.chunk_id]:
                    category_chunks.setdefault(category, []).append(chunk)

            for category, assigned_chunks in category_chunks.items():
                entries = self.kb.by_category(category)
                hit_map = await self.llm.match_items_batch(
                    category=category,
                    entries=entries,
                    chunks=[
                        _build_match_chunk_payload(chunk, sentence_map[chunk.chunk_id])
                        for chunk in assigned_chunks
                    ],
                )
                for chunk in assigned_chunks:
                    hit_rows = hit_map.get(chunk.chunk_id, [])
                    traces[chunk.chunk_id].append(
                        {
                            "event": "category_match",
                            "chunk_id": chunk.chunk_id,
                            "category": category,
                            "hit_count": len(hit_rows),
                        }
                    )
                    for row in hit_rows:
                        entry_id = str(row.get("entry_id", ""))
                        reason = str(row.get("reason", ""))
                        entry = self.kb.find_entry(entry_id)
                        if entry is None:
                            continue
                        evidence_sentence_index, evidence_sentence_text = _sanitize_evidence(
                            sentence_map[chunk.chunk_id],
                            row,
                        )
                        match_rows[chunk.chunk_id].append(
                            MatchItem(
                                entry_id=entry.entry_id,
                                category=entry.category,
                                text=entry.text,
                                type_code=entry.type_code,
                                reason=reason,
                                evidence_sentence_index=evidence_sentence_index,
                                evidence_sentence_text=evidence_sentence_text,
                            )
                        )

            for chunk in chunk_batch:
                deduped_matches = _dedupe_matches(match_rows[chunk.chunk_id])
                label = "命中" if deduped_matches else "其他"
                output.append(
                    (
                        ChunkCompareResult(
                            chunk_id=chunk.chunk_id,
                            heading=chunk.heading,
                            content=chunk.content,
                            categories=normalized_map[chunk.chunk_id],
                            matches=deduped_matches,
                            label=label,
                        ),
                        traces[chunk.chunk_id],
                    )
                )
        return output


def _iter_batches(items: list[Chunk], size: int) -> Iterable[list[Chunk]]:
    if size <= 0:
        size = 10
    for start in range(0, len(items), size):
        yield items[start : start + size]


def _dedupe_matches(matches: list[MatchItem]) -> list[MatchItem]:
    unique_map: dict[str, MatchItem] = {}
    for match in matches:
        if match.entry_id in unique_map:
            continue
        unique_map[match.entry_id] = match
    return list(unique_map.values())


def _dedupe_strings_preserve_order(values: list[str]) -> list[str]:
    seen: set[str] = set()
    output: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        output.append(value)
    return output


def _validate_unique_chunk_ids(chunks: list[Chunk]) -> None:
    seen_chunk_ids: set[int] = set()
    for chunk in chunks:
        if chunk.chunk_id in seen_chunk_ids:
            raise ValueError("Matcher input contains duplicate chunk_id values.")
        seen_chunk_ids.add(chunk.chunk_id)


def _build_match_chunk_payload(chunk: Chunk, sentences: list[str]) -> dict[str, object]:
    return {
        "chunk_id": chunk.chunk_id,
        "content": chunk.content,
        "sentences": [
            {"index": index, "text": sentence}
            for index, sentence in enumerate(sentences)
        ],
    }


def _sanitize_evidence(sentences: list[str], row: dict) -> tuple[int | None, str]:
    evidence_text = _normalize_evidence_text(row.get("evidence_sentence_text"))
    raw_index = row.get("evidence_sentence_index")
    if isinstance(raw_index, bool) or not isinstance(raw_index, int) or raw_index < 0:
        return None, evidence_text

    if raw_index >= len(sentences):
        return None, evidence_text

    return raw_index, sentences[raw_index]


def _normalize_evidence_text(value: object) -> str:
    return value.strip() if isinstance(value, str) else ""


def _split_sentences(text: str) -> list[str]:
    return split_sentences(text)
