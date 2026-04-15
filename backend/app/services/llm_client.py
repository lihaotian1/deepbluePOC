from __future__ import annotations

import asyncio
import json
from collections.abc import Sequence
from collections import defaultdict

import httpx

from app.services.kb_loader import KnowledgeEntry
from app.services.prompt_builder import (
    build_batch_category_messages,
    build_document_compare_messages,
    build_batch_item_messages,
    build_category_messages,
    build_item_messages,
)

MAX_CHAT_RETRIES = 2
BASE_RETRY_DELAY_SECONDS = 1.0
FULL_DOCUMENT_MIN_TIMEOUT_SECONDS = 180


class OpenAICompatibleMatcherLLM:
    def __init__(self, *, base_url: str, api_key: str, model: str, timeout: int = 60) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.timeout = timeout

    async def classify_categories(
        self,
        *,
        chunk_text: str,
        category_keys: list[str],
        category_contexts: Sequence[dict[str, object]] | None = None,
    ) -> list[str]:
        if not self.api_key:
            return []
        messages = build_category_messages(
            chunk_text=chunk_text,
            category_keys=category_keys,
            category_contexts=category_contexts,
        )
        payload = await self._chat_json(messages)
        categories = payload.get("categories")
        if not isinstance(categories, list):
            raise ValueError("LLM category response must contain a list in 'categories'.")
        allowed_categories = set(category_keys)
        valid_categories = [str(item) for item in categories if isinstance(item, str) and item in allowed_categories]
        return _dedupe_strings_preserve_order(valid_categories)

    async def classify_categories_batch(
        self,
        *,
        chunks: list[tuple[int, str]],
        category_keys: list[str],
        category_contexts: Sequence[dict[str, object]] | None = None,
    ) -> dict[int, list[str]]:
        _validate_unique_requested_chunk_ids(chunks)
        if not self.api_key:
            return {chunk_id: [] for chunk_id, _ in chunks}

        messages = build_batch_category_messages(
            chunks=chunks,
            category_keys=category_keys,
            category_contexts=category_contexts,
        )
        payload = await self._chat_json(messages)
        raw_results = payload.get("results")
        if not isinstance(raw_results, list):
            raise ValueError("LLM batch category response must contain a list in 'results'.")
        allowed_chunk_ids = {chunk_id for chunk_id, _ in chunks}
        allowed_categories = set(category_keys)
        grouped: dict[int, list[str]] = defaultdict(list)
        seen_chunk_ids: set[int] = set()
        for row in raw_results:
            if not isinstance(row, dict):
                raise ValueError("LLM batch category response rows must be objects.")
            chunk_id = row.get("chunk_id")
            if isinstance(chunk_id, bool) or not isinstance(chunk_id, int):
                raise ValueError("LLM batch category response rows must include integer 'chunk_id'.")
            if chunk_id not in allowed_chunk_ids:
                continue
            if chunk_id in seen_chunk_ids:
                raise ValueError("LLM batch category response contains duplicate in-scope chunk_id rows.")
            seen_chunk_ids.add(chunk_id)
            categories = row.get("categories")
            if not isinstance(categories, list):
                raise ValueError("LLM batch category response rows must include list 'categories'.")
            grouped[chunk_id] = [
                str(item)
                for item in categories
                if isinstance(item, str) and item in allowed_categories
            ]
            grouped[chunk_id] = _dedupe_strings_preserve_order(grouped[chunk_id])

        for chunk_id, _ in chunks:
            grouped.setdefault(chunk_id, [])
        return dict(grouped)

    async def match_items(
        self,
        *,
        chunk_text: str,
        category: str,
        entries: list[KnowledgeEntry],
    ) -> list[dict[str, str]]:
        if not self.api_key:
            return []
        messages = build_item_messages(chunk_text=chunk_text, category=category, entries=entries)
        payload = await self._chat_json(messages)
        rows = payload.get("matches")
        if not isinstance(rows, list):
            raise ValueError("LLM item response must contain a list in 'matches'.")
        allowed_entry_ids = {entry.entry_id for entry in entries}
        clean_rows: list[dict[str, str]] = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            entry_id = str(row.get("entry_id", "")).strip()
            if not entry_id or entry_id not in allowed_entry_ids:
                continue
            reason = str(row.get("reason", "")).strip()
            clean_rows.append({"entry_id": entry_id, "reason": reason})
        return _dedupe_simple_matches_by_entry_id(clean_rows)

    async def match_items_batch(
        self,
        *,
        category: str,
        entries: list[KnowledgeEntry],
        chunks: Sequence[tuple[int, str] | dict[str, object]],
    ) -> dict[int, list[dict[str, object]]]:
        _validate_unique_requested_chunk_ids(chunks)
        if not self.api_key:
            return {_get_chunk_id(chunk): [] for chunk in chunks}

        messages = build_batch_item_messages(
            category=category,
            entries=entries,
            chunks=chunks,
        )
        payload = await self._chat_json(messages)
        raw_results = payload.get("results")
        if not isinstance(raw_results, list):
            raise ValueError("LLM batch item response must contain a list in 'results'.")
        allowed_chunk_ids = {_get_chunk_id(chunk) for chunk in chunks}
        allowed_entry_ids = {entry.entry_id for entry in entries}
        grouped: dict[int, list[dict[str, object]]] = {}
        seen_chunk_ids: set[int] = set()
        for row in raw_results:
            if not isinstance(row, dict):
                raise ValueError("LLM batch item response rows must be objects.")
            chunk_id = row.get("chunk_id")
            if isinstance(chunk_id, bool) or not isinstance(chunk_id, int):
                raise ValueError("LLM batch item response rows must include integer 'chunk_id'.")
            if chunk_id not in allowed_chunk_ids:
                continue
            if chunk_id in seen_chunk_ids:
                raise ValueError("LLM batch item response contains duplicate in-scope chunk_id rows.")
            seen_chunk_ids.add(chunk_id)
            matches = row.get("matches")
            if not isinstance(matches, list):
                raise ValueError("LLM batch item response rows must include list 'matches'.")
            clean_rows: list[dict[str, object]] = []
            for item in matches:
                normalized = _normalize_batch_match(item)
                if normalized is None:
                    continue
                entry_id = normalized.get("entry_id")
                if not isinstance(entry_id, str) or entry_id not in allowed_entry_ids:
                    continue
                clean_rows.append(normalized)
            grouped[chunk_id] = _dedupe_matches_by_entry_id(clean_rows)

        for chunk in chunks:
            grouped.setdefault(_get_chunk_id(chunk), [])
        return dict(grouped)

    async def compare_document_rows(
        self,
        *,
        document_title: str,
        document_text: str,
        entries: list[KnowledgeEntry],
    ) -> list[dict[str, str]]:
        if not self.api_key:
            return []

        messages = build_document_compare_messages(
            document_title=document_title,
            document_text=document_text,
            entries=entries,
        )
        payload = await self._chat_json(messages, timeout_override=max(self.timeout, FULL_DOCUMENT_MIN_TIMEOUT_SECONDS))
        raw_results = payload.get("results")
        if not isinstance(raw_results, list):
            raise ValueError("LLM document compare response must contain a list in 'results'.")

        allowed_entry_ids = {entry.entry_id for entry in entries}
        normalized_results: list[dict[str, str]] = []
        for row in raw_results:
            if not isinstance(row, dict):
                continue

            entry_id = str(row.get("entry_id", "")).strip()
            chapter_title = str(row.get("chapter_title", "")).strip()
            source_excerpt = str(row.get("source_excerpt", "")).strip()
            difference_summary = str(row.get("difference_summary", "")).strip()
            if (
                not entry_id
                or entry_id not in allowed_entry_ids
                or not source_excerpt
                or not difference_summary
            ):
                continue

            normalized_results.append(
                {
                    "entry_id": entry_id,
                    "chapter_title": chapter_title or "未识别标题",
                    "source_excerpt": source_excerpt,
                    "difference_summary": difference_summary,
                }
            )
        return normalized_results

    async def translate_to_chinese(self, *, text: str) -> str:
        if not self.api_key:
            raise ValueError("Translation service is not configured.")

        messages = [
            {
                "role": "system",
                "content": (
                    "You are a technical translator. Translate the user text into simplified Chinese, "
                    "preserve technical meaning, units, and structure, add no explanation, and respond "
                    "with JSON in the shape {\"translation\":\"...\"}."
                ),
            },
            {"role": "user", "content": text},
        ]
        payload = await self._chat_json(messages)
        translation = payload.get("translation")
        if not isinstance(translation, str):
            raise ValueError("LLM translation response must contain string 'translation'.")

        normalized = translation.strip()
        if not normalized:
            raise ValueError("LLM translation response must not be empty.")
        return normalized

    async def _chat_json(self, messages: list[dict[str, str]], timeout_override: int | None = None) -> dict:
        timeout = timeout_override or self.timeout
        data = await self._post_chat_completion(messages, timeout=timeout)
        try:
            content = _extract_json_content(data)
        except ValueError as exc:
            if str(exc) != "LLM returned an empty assistant message.":
                raise
            content = await self._post_chat_completion_stream(messages, timeout=timeout)

        try:
            payload = json.loads(content)
        except json.JSONDecodeError as exc:
            raise ValueError("LLM response content is not valid JSON.") from exc

        if not isinstance(payload, dict):
            raise ValueError("LLM response JSON must be an object.")
        return payload

    async def _post_chat_completion(self, messages: list[dict[str, str]], *, timeout: int) -> dict:
        url = f"{self.base_url}/chat/completions"
        body = {
            "model": self.model,
            "temperature": 0,
            "messages": messages,
            "response_format": {"type": "json_object"},
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        last_error: Exception | None = None
        for attempt in range(MAX_CHAT_RETRIES + 1):
            try:
                async with httpx.AsyncClient(timeout=timeout) as client:
                    response = await client.post(url, headers=headers, json=body)
                if response.status_code == 429 and attempt < MAX_CHAT_RETRIES:
                    await asyncio.sleep(_resolve_retry_delay_seconds(response, attempt))
                    continue

                response.raise_for_status()
                return response.json()
            except httpx.ReadTimeout as exc:
                last_error = exc
                if attempt >= MAX_CHAT_RETRIES:
                    raise
                await asyncio.sleep(_resolve_backoff_delay_seconds(attempt))
            except httpx.HTTPStatusError as exc:
                last_error = exc
                if exc.response.status_code != 429 or attempt >= MAX_CHAT_RETRIES:
                    raise
                await asyncio.sleep(_resolve_retry_delay_seconds(exc.response, attempt))

        assert last_error is not None
        raise last_error

    async def _post_chat_completion_stream(self, messages: list[dict[str, str]], *, timeout: int) -> str:
        url = f"{self.base_url}/chat/completions"
        body = {
            "model": self.model,
            "temperature": 0,
            "messages": messages,
            "response_format": {"type": "json_object"},
            "stream": True,
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        last_error: Exception | None = None
        for attempt in range(MAX_CHAT_RETRIES + 1):
            try:
                async with httpx.AsyncClient(timeout=timeout) as client:
                    async with client.stream("POST", url, headers=headers, json=body) as response:
                        if response.status_code == 429 and attempt < MAX_CHAT_RETRIES:
                            await asyncio.sleep(_resolve_retry_delay_seconds(response, attempt))
                            continue

                        response.raise_for_status()
                        chunks: list[str] = []
                        async for part in response.aiter_text():
                            if part:
                                chunks.append(part)

                content = _extract_streamed_chat_content("".join(chunks))
                if not content:
                    raise ValueError("LLM stream returned no assistant content.")
                return content
            except httpx.ReadTimeout as exc:
                last_error = exc
                if attempt >= MAX_CHAT_RETRIES:
                    raise
                await asyncio.sleep(_resolve_backoff_delay_seconds(attempt))
            except httpx.HTTPStatusError as exc:
                last_error = exc
                if exc.response.status_code != 429 or attempt >= MAX_CHAT_RETRIES:
                    raise
                await asyncio.sleep(_resolve_retry_delay_seconds(exc.response, attempt))

        assert last_error is not None
        raise last_error


def _get_chunk_id(chunk: tuple[int, str] | dict[str, object]) -> int:
    if isinstance(chunk, tuple):
        chunk_id = chunk[0]
        if isinstance(chunk_id, bool) or not isinstance(chunk_id, int):
            raise ValueError("Batch request chunks must include integer chunk_id values.")
        return chunk_id

    chunk_id = chunk.get("chunk_id")
    if isinstance(chunk_id, bool) or not isinstance(chunk_id, int):
        raise ValueError("Batch request chunks must include integer chunk_id values.")
    return chunk_id


def _normalize_batch_match(item: object) -> dict[str, object] | None:
    if not isinstance(item, dict):
        return None

    entry_id = str(item.get("entry_id", "")).strip()
    if not entry_id:
        return None

    reason = str(item.get("reason", "")).strip()
    evidence_text = item.get("evidence_sentence_text")
    return {
        "entry_id": entry_id,
        "reason": reason,
        "evidence_sentence_index": _normalize_evidence_index(item.get("evidence_sentence_index")),
        "evidence_sentence_text": evidence_text.strip() if isinstance(evidence_text, str) else "",
    }


def _normalize_evidence_index(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        stripped = value.strip()
        if stripped.isdigit():
            return int(stripped)
    return None


def _extract_json_content(data: object) -> str:
    if not isinstance(data, dict):
        raise ValueError("LLM response payload must be an object.")

    choices = data.get("choices")
    if not isinstance(choices, list) or not choices:
        raise ValueError("LLM response missing choices.")

    first_choice = choices[0]
    if not isinstance(first_choice, dict):
        raise ValueError("LLM response choices entry must be an object.")

    message = first_choice.get("message")
    if not isinstance(message, dict):
        raise ValueError("LLM response missing message object.")

    content = message.get("content")
    if content is None:
        raise ValueError("LLM returned an empty assistant message.")
    if isinstance(content, str):
        return content

    if isinstance(content, list):
        text_parts = [item.get("text", "") for item in content if isinstance(item, dict)]
        combined = "".join(part for part in text_parts if isinstance(part, str)).strip()
        if combined:
            return combined

    raise ValueError("LLM response has invalid content shape.")


def _extract_streamed_chat_content(stream_text: str) -> str:
    content_parts: list[str] = []
    for block in stream_text.split("\n\n"):
        if not block.strip():
            continue
        for line in block.splitlines():
            if not line.startswith("data: "):
                continue
            data = line[len("data: "):].strip()
            if not data or data == "[DONE]":
                continue
            try:
                payload = json.loads(data)
            except json.JSONDecodeError:
                continue
            choices = payload.get("choices")
            if not isinstance(choices, list) or not choices:
                continue
            first_choice = choices[0]
            if not isinstance(first_choice, dict):
                continue
            delta = first_choice.get("delta")
            if not isinstance(delta, dict):
                continue
            content = delta.get("content")
            if isinstance(content, str):
                content_parts.append(content)
                continue
            if isinstance(content, list):
                for item in content:
                    if not isinstance(item, dict):
                        continue
                    text = item.get("text")
                    if isinstance(text, str):
                        content_parts.append(text)
    return "".join(content_parts).strip()


def _dedupe_strings_preserve_order(values: list[str]) -> list[str]:
    seen: set[str] = set()
    output: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        output.append(value)
    return output


def _dedupe_simple_matches_by_entry_id(matches: list[dict[str, str]]) -> list[dict[str, str]]:
    seen_entry_ids: set[str] = set()
    output: list[dict[str, str]] = []
    for match in matches:
        entry_id = match.get("entry_id")
        if not entry_id or entry_id in seen_entry_ids:
            continue
        seen_entry_ids.add(entry_id)
        output.append(match)
    return output


def _dedupe_matches_by_entry_id(matches: list[dict[str, object]]) -> list[dict[str, object]]:
    seen_entry_ids: set[str] = set()
    output: list[dict[str, object]] = []
    for match in matches:
        entry_id = match.get("entry_id")
        if not isinstance(entry_id, str) or entry_id in seen_entry_ids:
            continue
        seen_entry_ids.add(entry_id)
        output.append(match)
    return output


def _validate_unique_requested_chunk_ids(chunks: Sequence[tuple[int, str] | dict[str, object]]) -> None:
    seen_chunk_ids: set[int] = set()
    for chunk in chunks:
        chunk_id = _get_chunk_id(chunk)
        if chunk_id in seen_chunk_ids:
            raise ValueError("Batch request contains duplicate chunk_id values.")
        seen_chunk_ids.add(chunk_id)


def _resolve_retry_delay_seconds(response: httpx.Response, attempt: int) -> float:
    retry_after = response.headers.get("Retry-After", "").strip()
    if retry_after.isdigit():
        return max(float(retry_after), BASE_RETRY_DELAY_SECONDS)
    return _resolve_backoff_delay_seconds(attempt)


def _resolve_backoff_delay_seconds(attempt: int) -> float:
    return BASE_RETRY_DELAY_SECONDS * (2**attempt)
