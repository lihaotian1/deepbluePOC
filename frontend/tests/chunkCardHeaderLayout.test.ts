import assert from "node:assert/strict";
import test from "node:test";

import { buildChunkCardHeaderActionGroups } from "../src/components/chunkCardHeaderViewState.ts";

test("preview and edit controls belong to the top header row and use the same base button style", () => {
  const groups = buildChunkCardHeaderActionGroups({
    mode: "preview",
    isReviewed: false,
  });

  assert.equal(groups.length, 2);
  assert.deepEqual(groups[0]?.actions.map((action) => action.label), ["预览", "编辑"]);
  assert.deepEqual(groups[1]?.actions.map((action) => action.label), ["修改", "审核"]);
  assert.equal(groups[0]?.className, "chunk-card__switcher chunk-card__switcher--source");
  assert.equal(groups[1]?.className, "chunk-card__switcher chunk-card__switcher--review");
  assert.equal(groups[0]?.actions[0]?.className, "btn btn-lite is-active");
  assert.equal(groups[0]?.actions[1]?.className, "btn btn-lite");
  assert.equal(groups[0]?.containerClassName, "chunk-card__header-primary");
  assert.equal(groups[1]?.containerClassName, "chunk-card__header-secondary");
  assert.equal(groups[0]?.titleContainerClassName, "chunk-card__title-wrap");
  assert.equal(groups[0]?.titleGapPx, 40);
});
