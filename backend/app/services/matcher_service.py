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
        category_contexts = _build_category_contexts(self.kb)
        for chunk_batch in _iter_batches(chunks, batch_size):
            batch_payload = [(chunk.chunk_id, chunk.content) for chunk in chunk_batch]
            sentence_map = {
                chunk.chunk_id: split_sentences(chunk.content)
                for chunk in chunk_batch
            }
            classified_map = await self.llm.classify_categories_batch(
                chunks=batch_payload,
                category_keys=self.kb.categories,
                category_contexts=category_contexts,
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

            await self._match_category_batches(
                category_chunks=category_chunks,
                sentence_map=sentence_map,
                traces=traces,
                match_rows=match_rows,
                normalized_map=normalized_map,
                trace_event="category_match",
                add_category_on_hit=False,
            )

            fallback_category_chunks: dict[str, list[Chunk]] = {}
            for chunk in chunk_batch:
                if not _needs_fallback_match(match_rows[chunk.chunk_id]):
                    continue
                tried_categories = set(normalized_map[chunk.chunk_id])
                for category in self.kb.categories:
                    if category in tried_categories:
                        continue
                    fallback_category_chunks.setdefault(category, []).append(chunk)

            await self._match_category_batches(
                category_chunks=fallback_category_chunks,
                sentence_map=sentence_map,
                traces=traces,
                match_rows=match_rows,
                normalized_map=normalized_map,
                trace_event="category_match",
                add_category_on_hit=True,
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

    async def _match_category_batches(
        self,
        *,
        category_chunks: dict[str, list[Chunk]],
        sentence_map: dict[int, list[str]],
        traces: dict[int, list[dict]],
        match_rows: dict[int, list[MatchItem]],
        normalized_map: dict[int, list[str]],
        trace_event: str,
        add_category_on_hit: bool,
    ) -> None:
        for category, assigned_chunks in category_chunks.items():
            entries = self.kb.by_category(category)
            if not entries:
                continue

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
                        "event": trace_event,
                        "chunk_id": chunk.chunk_id,
                        "category": category,
                        "hit_count": len(hit_rows),
                    }
                )
                starting_count = len(match_rows[chunk.chunk_id])
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

                if (
                    add_category_on_hit
                    and len(match_rows[chunk.chunk_id]) > starting_count
                    and category not in normalized_map[chunk.chunk_id]
                ):
                    normalized_map[chunk.chunk_id].append(category)


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


def _needs_fallback_match(matches: list[MatchItem]) -> bool:
    if not matches:
        return True
    return all(_is_conflict_match(match) for match in matches)


def _is_conflict_match(match: MatchItem) -> bool:
    normalized_reason = match.reason.strip()
    return normalized_reason.startswith("强关联但冲突")


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


def _build_category_contexts(kb: KnowledgeBase, sample_limit: int = 3) -> list[dict[str, object]]:
    contexts: list[dict[str, object]] = []
    for category in kb.categories:
        sample_entries = _select_representative_entry_texts(kb.by_category(category), sample_limit)
        contexts.append({"category": category, "sample_entries": sample_entries})
    return contexts


def _select_representative_entry_texts(entries, sample_limit: int) -> list[str]:
    if sample_limit <= 0 or not entries:
        return []
    if len(entries) <= sample_limit:
        return [entry.text for entry in entries]
    if sample_limit == 1:
        return [entries[0].text]

    last_index = len(entries) - 1
    selected_indices: list[int] = []
    for position in range(sample_limit):
        candidate_index = round(position * last_index / (sample_limit - 1))
        if selected_indices and candidate_index <= selected_indices[-1]:
            candidate_index = selected_indices[-1] + 1

        remaining_slots = sample_limit - position - 1
        max_index = last_index - remaining_slots
        if candidate_index > max_index:
            candidate_index = max_index

        selected_indices.append(candidate_index)

    return [entries[index].text for index in selected_indices]


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
