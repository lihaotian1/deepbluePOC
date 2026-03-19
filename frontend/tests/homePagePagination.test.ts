import assert from "node:assert/strict";
import test from "node:test";

import { buildHomePagePaginationModel } from "../src/pages/homePagePagination.ts";
import type { Chunk, ChunkCompareResult } from "../src/types.ts";

function buildChunks(total: number): Chunk[] {
  return Array.from({ length: total }, (_, index) => ({
    chunk_id: index + 1,
    source: "demo.pdf",
    heading: `${index + 1}`,
    level: 1,
    line_no: index + 1,
    content: `Chunk ${index + 1}`,
  }));
}

function buildReviewedResult(chunkId: number, reviewStatus: "已审" | "未审"): ChunkCompareResult {
  return {
    chunk_id: chunkId,
    heading: `${chunkId}`,
    content: `Chunk ${chunkId}`,
    categories: [],
    matches: [],
    label: "其他",
    review_status: reviewStatus,
  };
}

test("paginates homepage chunks into fixed 10-item pages", () => {
  const model = buildHomePagePaginationModel(buildChunks(11), {}, 1, 10);

  assert.equal(model.totalItems, 11);
  assert.equal(model.totalPages, 2);
  assert.equal(model.page, 1);
  assert.equal(model.pageItemCount, 10);
  assert.equal(model.chunks.length, 10);
  assert.equal(model.chunks[0]?.chunk_id, 1);
  assert.equal(model.chunks[9]?.chunk_id, 10);
});

test("clamps homepage pagination to the last available page", () => {
  const model = buildHomePagePaginationModel(buildChunks(11), {}, 9, 10);

  assert.equal(model.page, 2);
  assert.equal(model.totalPages, 2);
  assert.equal(model.pageItemCount, 1);
  assert.equal(model.chunks.length, 1);
  assert.equal(model.chunks[0]?.chunk_id, 11);
});

test("counts only reviewed chunks that appear on the current page", () => {
  const resultMap = {
    1: buildReviewedResult(1, "已审"),
    2: buildReviewedResult(2, "已审"),
    11: buildReviewedResult(11, "已审"),
    12: buildReviewedResult(12, "未审"),
  };

  const model = buildHomePagePaginationModel(buildChunks(12), resultMap, 2, 10);

  assert.equal(model.page, 2);
  assert.equal(model.pageItemCount, 2);
  assert.equal(model.reviewedCount, 1);
  assert.deepEqual(
    model.chunks.map((chunk) => chunk.chunk_id),
    [11, 12],
  );
});

test("uses the final short page size as the reviewed counter denominator", () => {
  const resultMap = {
    11: buildReviewedResult(11, "已审"),
    12: buildReviewedResult(12, "未审"),
    13: buildReviewedResult(13, "已审"),
  };

  const model = buildHomePagePaginationModel(buildChunks(13), resultMap, 2, 10);

  assert.equal(model.page, 2);
  assert.equal(model.pageItemCount, 3);
  assert.equal(model.reviewedCount, 2);
});
