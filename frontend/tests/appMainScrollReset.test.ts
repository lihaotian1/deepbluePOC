import assert from "node:assert/strict";
import test from "node:test";

import { getAppMainScrollResetKey, resetScrollableRegionToTop } from "../src/layouts/appMainScrollReset.ts";

test("uses scrollTo when the scroll region supports it", () => {
  const calls: Array<{ top: number }> = [];
  const scroller = {
    scrollTop: 120,
    scrollTo(options: { top: number }) {
      calls.push(options);
    },
  };

  resetScrollableRegionToTop(scroller);

  assert.deepEqual(calls, [{ top: 0 }]);
});

test("falls back to scrollTop when scrollTo is unavailable", () => {
  const scroller = { scrollTop: 240 };

  resetScrollableRegionToTop(scroller);

  assert.equal(scroller.scrollTop, 0);
});

test("changes the shell reset key when the selected KB file changes", () => {
  const firstKey = getAppMainScrollResetKey("knowledge-base", "alpha.json");
  const secondKey = getAppMainScrollResetKey("knowledge-base", "beta.json");

  assert.notEqual(firstKey, secondKey);
});
