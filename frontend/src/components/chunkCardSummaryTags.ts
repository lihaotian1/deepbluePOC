import type { ChunkCompareResult, TypeCode } from "../types";

export function resolveChunkSummaryTags(result?: ChunkCompareResult): TypeCode[] {
  if (!result || result.label === "其他" || result.matches.length === 0) {
    return ["OTHER"];
  }

  return Array.from(new Set(result.matches.map((item) => item.type_code)));
}
