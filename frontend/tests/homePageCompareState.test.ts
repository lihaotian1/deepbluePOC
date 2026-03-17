import assert from "node:assert/strict";
import test from "node:test";

import { invalidateCompareStateAfterChunkEdit } from "../src/pages/homePageCompareState.ts";
import type { ChunkCompareResult } from "../src/types";


function buildResult(chunkId: number): ChunkCompareResult {
  return {
    chunk_id: chunkId,
    heading: `Chunk ${chunkId}`,
    content: "original",
    categories: ["分类A"],
    matches: [
      {
        entry_id: `kb-${chunkId}`,
        category: "分类A",
        text: "符合 API 610",
        type_code: "P",
        reason: "命中原句",
        evidence_sentence_index: 0,
        evidence_sentence_text: "original",
      },
    ],
    label: "命中",
  };
}


test("editing a chunk clears stale compare state", () => {
  const state = invalidateCompareStateAfterChunkEdit({
    resultMap: {
      1: buildResult(1),
      2: buildResult(2),
    },
    activeFilter: "P",
  });

  assert.deepEqual(state.resultMap, {});
  assert.equal(state.activeFilter, "ALL");
});


test("editing with no compare results keeps the filter stable", () => {
  const state = invalidateCompareStateAfterChunkEdit({
    resultMap: {},
    activeFilter: "ALL",
  });

  assert.deepEqual(state.resultMap, {});
  assert.equal(state.activeFilter, "ALL");
});
