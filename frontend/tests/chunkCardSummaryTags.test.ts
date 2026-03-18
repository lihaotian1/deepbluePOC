import assert from "node:assert/strict";
import test from "node:test";

import { resolveChunkSummaryTags } from "../src/components/chunkCardSummaryTags.ts";
import type { ChunkCompareResult } from "../src/types";

test("tender summary tags only show the final matched type code once", () => {
  const result: ChunkCompareResult = {
    chunk_id: 1,
    heading: "3.2 投标说明",
    content: "示例内容",
    categories: ["强制-必须偏离", "强制-澄清", "非强制-报价参考"],
    matches: [
      {
        entry_id: "kb-1",
        category: "非强制-报价参考",
        text: "命中 1",
        type_code: "非强制-报价参考",
        reason: "命中原句",
      },
      {
        entry_id: "kb-2",
        category: "非强制-报价参考",
        text: "命中 2",
        type_code: "非强制-报价参考",
        reason: "命中原句",
      },
    ],
    label: "命中",
  };

  assert.deepEqual(resolveChunkSummaryTags(result), ["非强制-报价参考"]);
});

test("no-hit summary falls back to OTHER tag", () => {
  const result: ChunkCompareResult = {
    chunk_id: 2,
    heading: "3.3 其他",
    content: "示例内容",
    categories: [],
    matches: [],
    label: "其他",
  };

  assert.deepEqual(resolveChunkSummaryTags(result), ["OTHER"]);
});
