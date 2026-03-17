export interface ChunkCardViewState {
  leftContentMode: "truncated" | "full";
  rightContentMode: "tags-only" | "details";
}

export interface ChunkCardViewStateOptions {
  expanded: boolean;
}

export interface ChunkCardHeightOptions {
  expanded: boolean;
  leftFullContentHeight: number;
  rightDetailHeight: number;
  measuredTagHeight: number;
  tagRowHeight: number;
  tagRowGap?: number;
  minCollapsedTagRows?: number;
}

export interface ChunkCardOuterHeightOptions {
  synchronizedContentHeight: number;
  panelVerticalInset: number;
}

export interface ChunkCardCollapsedLineClampOptions {
  synchronizedContentHeight: number;
  lineHeight: number;
  minCollapsedLines?: number;
}

const DUPLICATE_NUMERIC_PREFIX_PATTERN = /^\d+\.\s+((?:\d{1,2}(?:\.\d+)+|\d{1,2})\s+.+)$/;
const DEFAULT_MIN_COLLAPSED_TAG_ROWS = 3;
const DEFAULT_MIN_COLLAPSED_SOURCE_LINES = 3;

export function getChunkCardViewState({ expanded }: ChunkCardViewStateOptions): ChunkCardViewState {
  if (expanded) {
    return {
      leftContentMode: "full",
      rightContentMode: "details",
    };
  }

  return {
    leftContentMode: "truncated",
    rightContentMode: "tags-only",
  };
}

export function formatChunkCardTitle(title: string): string {
  const duplicatedPrefixMatch = title.match(DUPLICATE_NUMERIC_PREFIX_PATTERN);

  return duplicatedPrefixMatch ? duplicatedPrefixMatch[1] : title;
}

export function resolveChunkCardSynchronizedHeight({
  expanded,
  leftFullContentHeight,
  rightDetailHeight,
  measuredTagHeight,
  tagRowHeight,
  tagRowGap = 0,
  minCollapsedTagRows = DEFAULT_MIN_COLLAPSED_TAG_ROWS,
}: ChunkCardHeightOptions): number {
  if (expanded) {
    return Math.max(leftFullContentHeight, rightDetailHeight);
  }

  const collapsedMinimumHeight = tagRowHeight * minCollapsedTagRows + tagRowGap * Math.max(0, minCollapsedTagRows - 1);

  return Math.max(measuredTagHeight, collapsedMinimumHeight);
}

export function resolveChunkCardPanelOuterHeight({
  synchronizedContentHeight,
  panelVerticalInset,
}: ChunkCardOuterHeightOptions): number {
  return synchronizedContentHeight + panelVerticalInset;
}

export function resolveChunkCardCollapsedLineClamp({
  synchronizedContentHeight,
  lineHeight,
  minCollapsedLines = DEFAULT_MIN_COLLAPSED_SOURCE_LINES,
}: ChunkCardCollapsedLineClampOptions): number {
  return Math.max(minCollapsedLines, Math.floor(synchronizedContentHeight / lineHeight));
}
