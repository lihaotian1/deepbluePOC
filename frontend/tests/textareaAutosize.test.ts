import assert from "node:assert/strict";
import test from "node:test";

import { autosizeTextarea } from "../src/utils/textareaAutosize.ts";

function createFakeTextarea(initialContentHeight: number) {
  const heightWrites: string[] = [];
  let currentHeight = "0px";
  let intrinsicHeight = initialContentHeight;

  const style = {
    get height() {
      return currentHeight;
    },
    set height(value: string) {
      currentHeight = value;
      heightWrites.push(value);
    },
  } satisfies Pick<CSSStyleDeclaration, "height">;

  const textarea = {
    get scrollHeight() {
      if (currentHeight === "auto") {
        return intrinsicHeight;
      }

      const renderedHeight = Number.parseInt(currentHeight, 10);

      return Number.isNaN(renderedHeight) ? intrinsicHeight : Math.max(intrinsicHeight, renderedHeight);
    },
    style,
  };

  return {
    textarea,
    heightWrites,
    setIntrinsicHeight(nextHeight: number) {
      intrinsicHeight = nextHeight;
    },
  };
}

test("respects the minimum height when content is shorter", () => {
  const { textarea } = createFakeTextarea(32);

  autosizeTextarea(textarea, 44);

  assert.equal(textarea.style.height, "44px");
});

test("grows to scrollHeight when content is taller than the minimum", () => {
  const { textarea } = createFakeTextarea(120);

  autosizeTextarea(textarea, 44);

  assert.equal(textarea.style.height, "120px");
});

test("resets height to auto before applying the measured height", () => {
  const { textarea, heightWrites } = createFakeTextarea(88);

  autosizeTextarea(textarea, 44);

  assert.deepEqual(heightWrites, ["auto", "88px"]);
});

test("shrinks on repeated calls after content becomes shorter", () => {
  const { textarea, heightWrites, setIntrinsicHeight } = createFakeTextarea(120);

  autosizeTextarea(textarea, 44);
  setIntrinsicHeight(32);
  autosizeTextarea(textarea, 44);

  assert.equal(textarea.style.height, "44px");
  assert.deepEqual(heightWrites, ["auto", "120px", "auto", "44px"]);
});
