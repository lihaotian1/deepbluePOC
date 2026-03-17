import assert from "node:assert/strict";
import test from "node:test";

import {
  formatChunkCardTitle,
  getChunkCardViewState,
  resolveChunkCardCollapsedLineClamp,
  resolveChunkCardPanelOuterHeight,
  resolveChunkCardSynchronizedHeight,
} from "../src/components/chunkCardLayout.ts";

test("collapsed state returns tags-only view metadata", () => {
  assert.deepEqual(getChunkCardViewState({ expanded: false }), {
    leftContentMode: "truncated",
    rightContentMode: "tags-only",
  });
});

test("title formatting removes the extra numeric prefix while preserving plain headings", () => {
  assert.equal(formatChunkCardTitle("1. 1.1 SCOPE"), "1.1 SCOPE");
  assert.equal(formatChunkCardTitle("10. 2 REFERENCE DOCUMENTS"), "2 REFERENCE DOCUMENTS");
  assert.equal(formatChunkCardTitle("2. 2024 UPDATE"), "2. 2024 UPDATE");
  assert.equal(formatChunkCardTitle("General requirements"), "General requirements");
});

test("expanded synchronized height resolves to the larger measured panel", () => {
  assert.equal(
    resolveChunkCardSynchronizedHeight({
      expanded: true,
      leftFullContentHeight: 280,
      rightDetailHeight: 196,
      measuredTagHeight: 40,
      tagRowHeight: 24,
      tagRowGap: 8,
    }),
    280,
  );

  assert.equal(
    resolveChunkCardSynchronizedHeight({
      expanded: true,
      leftFullContentHeight: 168,
      rightDetailHeight: 224,
      measuredTagHeight: 40,
      tagRowHeight: 24,
      tagRowGap: 8,
    }),
    224,
  );
});

test("collapsed synchronized height uses measured tags with a three-row floor including row gaps", () => {
  assert.equal(
    resolveChunkCardSynchronizedHeight({
      expanded: false,
      leftFullContentHeight: 280,
      rightDetailHeight: 196,
      measuredTagHeight: 48,
      tagRowHeight: 24,
      tagRowGap: 8,
    }),
    88,
  );

  assert.equal(
    resolveChunkCardSynchronizedHeight({
      expanded: false,
      leftFullContentHeight: 280,
      rightDetailHeight: 196,
      measuredTagHeight: 96,
      tagRowHeight: 24,
      tagRowGap: 8,
    }),
    96,
  );
});

test("outer panel height preserves the visible collapsed tag-area minimum after padding", () => {
  assert.equal(
    resolveChunkCardPanelOuterHeight({
      synchronizedContentHeight: 88,
      panelVerticalInset: 24,
    }),
    112,
  );
});

test("collapsed excerpt clamp uses the real line height at the four-row boundary", () => {
  assert.equal(
    resolveChunkCardCollapsedLineClamp({
      synchronizedContentHeight: 120,
      lineHeight: 24,
      minCollapsedLines: 3,
    }),
    5,
  );

  assert.equal(
    resolveChunkCardCollapsedLineClamp({
      synchronizedContentHeight: 88,
      lineHeight: 24,
      minCollapsedLines: 3,
    }),
    3,
  );
});
