import type { Chunk, ChunkCompareResult } from "../types";

export interface HomePagePaginationModel {
  chunks: Chunk[];
  page: number;
  totalItems: number;
  totalPages: number;
  pageItemCount: number;
  reviewedCount: number;
}

export function buildHomePagePaginationModel(
  chunks: Chunk[],
  resultMap: Record<number, ChunkCompareResult>,
  requestedPage: number,
  pageSize: number,
): HomePagePaginationModel {
  const totalItems = chunks.length;
  const totalPages = Math.max(1, Math.ceil(totalItems / pageSize));
  const page = Math.min(Math.max(requestedPage, 1), totalPages);
  const start = (page - 1) * pageSize;
  const pagedChunks = chunks.slice(start, start + pageSize);
  const reviewedCount = pagedChunks.filter((chunk) => resultMap[chunk.chunk_id]?.review_status === "已审").length;

  return {
    chunks: pagedChunks,
    page,
    totalItems,
    totalPages,
    pageItemCount: pagedChunks.length,
    reviewedCount,
  };
}
