from __future__ import annotations

import sys
from pathlib import Path
from typing import Callable
from uuid import uuid4

from app.schemas import Chunk


ROOT_DIR = Path(__file__).resolve().parents[3]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from chapter_splitter import extract_text_from_file, split_text_engineering, split_text_with_gpt  # noqa: E402


RawChunk = dict[str, object]
ExtractTextFn = Callable[[Path], str]
EngineeringSplitter = Callable[[str, str], list[RawChunk]]
GPTSplitter = Callable[..., list[RawChunk]]


class SplitterService:
    def __init__(
        self,
        temp_dir: Path,
        *,
        extract_text_fn: ExtractTextFn = extract_text_from_file,
        engineering_splitter: EngineeringSplitter = split_text_engineering,
        gpt_splitter: GPTSplitter = split_text_with_gpt,
        api_key: str = "",
        base_url: str = "https://api.openai.com/v1",
        model: str = "gpt-4.1-mini",
        timeout: int = 120,
    ) -> None:
        self.temp_dir = temp_dir
        self.extract_text_fn = extract_text_fn
        self.engineering_splitter = engineering_splitter
        self.gpt_splitter = gpt_splitter
        self.api_key = api_key
        self.base_url = base_url
        self.model = model
        self.timeout = timeout
        self.temp_dir.mkdir(parents=True, exist_ok=True)

    def split_upload(self, *, file_name: str, payload: bytes) -> list[Chunk]:
        suffix = Path(file_name).suffix or ".txt"
        temp_file = self.temp_dir / f"{uuid4()}{suffix}"
        temp_file.write_bytes(payload)
        try:
            text = self.extract_text_fn(temp_file)
            raw_chunks = self._split_text(text=text, source_name=file_name)
        finally:
            if temp_file.exists():
                temp_file.unlink(missing_ok=True)

        chunks: list[Chunk] = []
        for row in raw_chunks:
            chunks.append(
                Chunk(
                    chunk_id=int(row.get("chunk_id", 0)),
                    source=str(row.get("source", file_name)),
                    heading=str(row.get("heading", "")),
                    level=int(row.get("level", 0)),
                    line_no=int(row.get("line_no", 1)),
                    content=str(row.get("content", "")),
                )
            )
        return chunks

    def _split_text(self, *, text: str, source_name: str) -> list[RawChunk]:
        if self.api_key:
            raw_chunks = self._try_gpt_split(text=text, source_name=source_name)
            if raw_chunks is not None:
                return raw_chunks
        return self.engineering_splitter(text, source_name=source_name)

    def _try_gpt_split(self, *, text: str, source_name: str) -> list[RawChunk] | None:
        try:
            raw_chunks = self.gpt_splitter(
                text=text,
                source_name=source_name,
                api_key=self.api_key,
                base_url=self.base_url,
                model=self.model,
                timeout=self.timeout,
            )
        except Exception:
            return None

        if not self._is_valid_raw_chunks(raw_chunks):
            return None
        return raw_chunks

    @staticmethod
    def _is_valid_raw_chunks(raw_chunks: object) -> bool:
        return isinstance(raw_chunks, list) and bool(raw_chunks) and all(isinstance(row, dict) for row in raw_chunks)
