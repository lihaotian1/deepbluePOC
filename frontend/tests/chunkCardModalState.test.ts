import assert from "node:assert/strict";
import test from "node:test";

import { getChunkCardModalState } from "../src/components/chunkCardModalState.ts";

test("opening review modal locks the background scroll and uses the base layer", () => {
  const state = getChunkCardModalState({
    isReviewModalOpen: true,
    isAddModalOpen: false,
  });

  assert.equal(state.hasAnyModalOpen, true);
  assert.equal(state.shouldLockBackgroundScroll, true);
  assert.equal(state.reviewBackdropClassName, "modal-backdrop");
});

test("opening add modal keeps it above the review modal", () => {
  const state = getChunkCardModalState({
    isReviewModalOpen: true,
    isAddModalOpen: true,
  });

  assert.equal(state.hasAnyModalOpen, true);
  assert.equal(state.addBackdropClassName, "modal-backdrop modal-backdrop--stacked");
  assert.equal(state.isReviewModalInert, true);
  assert.equal(state.activeModalKey, "add");
});

test("no open modal leaves the page unlocked", () => {
  const state = getChunkCardModalState({
    isReviewModalOpen: false,
    isAddModalOpen: false,
  });

  assert.equal(state.hasAnyModalOpen, false);
  assert.equal(state.shouldLockBackgroundScroll, false);
});
