import type { ChunkCompareResult, CompareRow, MatchItem, ReviewStatus } from "../types";

export function normalizeCompareRow(row: Omit<CompareRow, "review_status"> & { review_status?: ReviewStatus }): CompareRow {
  return {
    ...row,
    review_status: row.review_status ?? "未审",
  };
}

export function markCompareRowReviewed(row: CompareRow): CompareRow {
  return {
    ...row,
    review_status: "已审",
  };
}

export function updateCompareRowReviewComment(row: CompareRow, reviewComment: string): CompareRow {
  return {
    ...row,
    review_comment: reviewComment,
    review_status: "未审",
  };
}

export function removeCompareRow(rows: CompareRow[], rowId: string): CompareRow[] {
  return rows.filter((row) => row.row_id !== rowId);
}

const DEFAULT_OTHER_REASON = "未命中知识库条目，归类为其他。";

interface ManualReviewMatchInput {
  entryId: string;
  category: string;
  text: string;
  typeCode: string;
  reason: string;
}

export function normalizeReviewResult(result: Omit<ChunkCompareResult, "review_status"> & { review_status?: ReviewStatus }): ChunkCompareResult {
  return {
    ...result,
    review_status: result.review_status ?? "未审",
  };
}

export function markChunkReviewed(result: ChunkCompareResult): ChunkCompareResult {
  return {
    ...result,
    review_status: "已审",
  };
}

export function updateReviewMatchReason(
  result: ChunkCompareResult,
  entryId: string,
  reason: string,
): ChunkCompareResult {
  return withUnreviewedMatches(
    result,
    result.matches.map((match) =>
      match.entry_id === entryId ? { ...match, reason } : match,
    ),
  );
}

export function removeReviewMatch(result: ChunkCompareResult, entryId: string): ChunkCompareResult {
  return withUnreviewedMatches(
    result,
    result.matches.filter((match) => match.entry_id !== entryId),
  );
}

export function addManualReviewMatch(result: ChunkCompareResult, match: MatchItem): ChunkCompareResult {
  const nextMatches =
    match.type_code === "OTHER"
      ? [...result.matches.filter((existingMatch) => existingMatch.type_code !== "OTHER"), match]
      : [...result.matches.filter((existingMatch) => existingMatch.type_code !== "OTHER"), match];

  return withUnreviewedMatches(result, nextMatches);
}

export function setOtherReviewOpinion(result: ChunkCompareResult, reason: string): ChunkCompareResult {
  return withUnreviewedMatches(result, [
    buildManualReviewMatch({
      entryId: "manual-other",
      category: "其他",
      text: DEFAULT_OTHER_REASON,
      typeCode: "OTHER",
      reason,
    }),
  ]);
}

export function buildManualReviewMatch(input: ManualReviewMatchInput): MatchItem {
  const trimmedReason = input.reason.trim();
  return {
    entry_id: input.entryId,
    category: input.category,
    text: input.text,
    type_code: input.typeCode,
    reason: trimmedReason || (input.category === "其他" ? DEFAULT_OTHER_REASON : ""),
    evidence_sentence_index: null,
    evidence_sentence_text: "",
  };
}

export function getDefaultOtherReason() {
  return DEFAULT_OTHER_REASON;
}

function withUnreviewedMatches(result: ChunkCompareResult, matches: MatchItem[]): ChunkCompareResult {
  const nextCategories = Array.from(new Set(matches.map((match) => match.category).filter((category) => category && category !== "其他")));
  const hasKnowledgeBaseHit = matches.some((match) => match.category !== "其他" && match.type_code !== "OTHER");

  return {
    ...result,
    matches,
    categories: nextCategories,
    label: hasKnowledgeBaseHit ? "命中" : "其他",
    review_status: "未审",
  };
}
