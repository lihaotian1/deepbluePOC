import assert from "node:assert/strict";
import test from "node:test";

import {
  STANDARD_KB_FILE_NAME,
  TENDER_KB_FILE_NAME,
  buildFilterModelForKnowledgeBase,
  invalidateCompareStateAfterChunkEdit,
  toggleKnowledgeBaseSelection,
} from "../src/pages/homePageCompareState.ts";
import type { ChunkCompareResult } from "../src/types";


function buildResult(chunkId: number, typeCode = "P", category = "分类A"): ChunkCompareResult {
  return {
    chunk_id: chunkId,
    heading: `Chunk ${chunkId}`,
    content: "original",
    categories: [category],
    matches: [
      {
        entry_id: `kb-${chunkId}`,
        category,
        text: "符合 API 610",
        type_code: typeCode,
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
    resultsByKb: {
      [STANDARD_KB_FILE_NAME]: {
        1: buildResult(1),
        2: buildResult(2),
      },
      [TENDER_KB_FILE_NAME]: {
        1: buildResult(1, "非强制-报价行动", "非强制-报价行动"),
      },
    },
    activeFilter: "P",
  });

  assert.deepEqual(state.resultsByKb, {});
  assert.equal(state.activeFilter, "ALL");
});


test("editing with no compare results keeps the filter stable", () => {
  const state = invalidateCompareStateAfterChunkEdit({
    resultsByKb: {},
    activeFilter: "ALL",
  });

  assert.deepEqual(state.resultsByKb, {});
  assert.equal(state.activeFilter, "ALL");
});


test("standard knowledge-base filters keep P/A/B/C ordering", () => {
  const model = buildFilterModelForKnowledgeBase(STANDARD_KB_FILE_NAME, {
    1: buildResult(1, "P"),
    2: buildResult(2, "A"),
    3: {
      ...buildResult(3, "P"),
      matches: [],
      categories: [],
      label: "其他",
    },
  }, 3);

  assert.deepEqual(model.order, ["ALL", "P", "A", "B", "C", "OTHER"]);
  assert.equal(model.labels.P, "P");
  assert.equal(model.counts.P, 1);
  assert.equal(model.counts.A, 1);
  assert.equal(model.counts.OTHER, 1);
});


test("tender knowledge-base filters expose fixed display labels including zero-count required deviation", () => {
  const model = buildFilterModelForKnowledgeBase(TENDER_KB_FILE_NAME, {
    1: buildResult(1, "非强制-报价行动", "非强制-报价行动"),
    2: buildResult(2, "强制-澄清", "强制-澄清"),
  }, 2);

  assert.deepEqual(model.order, ["ALL", "强制-必须偏离", "强制-澄清", "非强制-报价参考", "非强制-报价行动", "OTHER"]);
  assert.equal(model.labels["强制-必须偏离"], "强制-必须偏离");
  assert.equal(model.counts["强制-必须偏离"], 0);
  assert.equal(model.counts["强制-澄清"], 1);
  assert.equal(model.counts["非强制-报价行动"], 1);
});


test("knowledge-base selection stays locked while compare is running", () => {
  const selected = toggleKnowledgeBaseSelection([STANDARD_KB_FILE_NAME], TENDER_KB_FILE_NAME, [STANDARD_KB_FILE_NAME, TENDER_KB_FILE_NAME], true);

  assert.deepEqual(selected, [STANDARD_KB_FILE_NAME]);
});
