import assert from "node:assert/strict";
import test from "node:test";

import {
  createChunkCardTranslationState,
  getChunkCardTranslationView,
  invalidateChunkCardTranslation,
  receiveChunkCardTranslationFailure,
  receiveChunkCardTranslationSuccess,
  startChunkCardTranslation,
  toggleChunkCardTranslationView,
} from "../src/components/chunkCardTranslationState.ts";

test("initial translation view shows source text and translate button", () => {
  const state = createChunkCardTranslationState();

  assert.deepEqual(getChunkCardTranslationView(state, "Pump shall include bearings."), {
    buttonDisabled: false,
    buttonText: "翻译",
    displayText: "Pump shall include bearings.",
    errorMessage: "",
    statusDotMode: "hidden",
  });
});

test("starting a translation request disables the button and animates the pulse dot", () => {
  const nextState = startChunkCardTranslation(createChunkCardTranslationState(), "Pump shall include bearings.");

  assert.deepEqual(getChunkCardTranslationView(nextState, "Pump shall include bearings."), {
    buttonDisabled: true,
    buttonText: "翻译",
    displayText: "Pump shall include bearings.",
    errorMessage: "",
    statusDotMode: "loading",
  });
});

test("blank source text keeps the translate button disabled", () => {
  const state = createChunkCardTranslationState();

  assert.deepEqual(getChunkCardTranslationView(state, "   "), {
    buttonDisabled: true,
    buttonText: "翻译",
    displayText: "   ",
    errorMessage: "",
    statusDotMode: "hidden",
  });
});

test("successful translation switches to chinese text and keeps a static pulse dot", () => {
  const loadingState = startChunkCardTranslation(createChunkCardTranslationState(), "Pump shall include bearings.");
  const nextState = receiveChunkCardTranslationSuccess(loadingState, {
    sourceSnapshot: "Pump shall include bearings.",
    translation: "泵应包括轴承。",
  });

  assert.deepEqual(getChunkCardTranslationView(nextState, "Pump shall include bearings."), {
    buttonDisabled: false,
    buttonText: "原文",
    displayText: "泵应包括轴承。",
    errorMessage: "",
    statusDotMode: "ready",
  });
});

test("toggling back to the original text preserves the cached translation for reuse", () => {
  const loadingState = startChunkCardTranslation(createChunkCardTranslationState(), "Pump shall include bearings.");
  const translatedState = receiveChunkCardTranslationSuccess(loadingState, {
    sourceSnapshot: "Pump shall include bearings.",
    translation: "泵应包括轴承。",
  });
  const sourceViewState = toggleChunkCardTranslationView(translatedState);

  assert.deepEqual(getChunkCardTranslationView(sourceViewState, "Pump shall include bearings."), {
    buttonDisabled: false,
    buttonText: "翻译",
    displayText: "Pump shall include bearings.",
    errorMessage: "",
    statusDotMode: "hidden",
  });

  assert.deepEqual(getChunkCardTranslationView(toggleChunkCardTranslationView(sourceViewState), "Pump shall include bearings."), {
    buttonDisabled: false,
    buttonText: "原文",
    displayText: "泵应包括轴承。",
    errorMessage: "",
    statusDotMode: "ready",
  });
});

test("source edits invalidate cached translations and clear status", () => {
  const loadingState = startChunkCardTranslation(createChunkCardTranslationState(), "Pump shall include bearings.");
  const translatedState = receiveChunkCardTranslationSuccess(loadingState, {
    sourceSnapshot: "Pump shall include bearings.",
    translation: "泵应包括轴承。",
  });
  const nextState = invalidateChunkCardTranslation(translatedState, "Pump shall include bearings. Updated.");

  assert.deepEqual(getChunkCardTranslationView(nextState, "Pump shall include bearings. Updated."), {
    buttonDisabled: false,
    buttonText: "翻译",
    displayText: "Pump shall include bearings. Updated.",
    errorMessage: "",
    statusDotMode: "hidden",
  });
});

test("stale async translation results are ignored after the source text changes", () => {
  const loadingState = startChunkCardTranslation(createChunkCardTranslationState(), "Pump shall include bearings.");
  const invalidatedState = invalidateChunkCardTranslation(loadingState, "Pump shall include bearings. Updated.");
  const nextState = receiveChunkCardTranslationSuccess(invalidatedState, {
    sourceSnapshot: "Pump shall include bearings.",
    translation: "旧翻译",
  });

  assert.deepEqual(getChunkCardTranslationView(nextState, "Pump shall include bearings. Updated."), {
    buttonDisabled: false,
    buttonText: "翻译",
    displayText: "Pump shall include bearings. Updated.",
    errorMessage: "",
    statusDotMode: "hidden",
  });
});

test("failed translation requests restore the original view and expose an inline error", () => {
  const loadingState = startChunkCardTranslation(createChunkCardTranslationState(), "Pump shall include bearings.");
  const nextState = receiveChunkCardTranslationFailure(loadingState, {
    sourceSnapshot: "Pump shall include bearings.",
    message: "翻译失败，请重试",
  });

  assert.deepEqual(getChunkCardTranslationView(nextState, "Pump shall include bearings."), {
    buttonDisabled: false,
    buttonText: "翻译",
    displayText: "Pump shall include bearings.",
    errorMessage: "翻译失败，请重试",
    statusDotMode: "hidden",
  });
});
