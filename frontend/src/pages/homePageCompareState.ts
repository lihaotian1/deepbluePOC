import type { CompareRow, ResultFilterType } from "../types";

export const STANDARD_KB_FILE_NAME = "标准化配套知识库.json";
export const TENDER_KB_FILE_NAME = "投标说明知识库.json";
export const TYPE_FILTER_ORDER = ["ALL", "P", "A", "B", "C"] as const;

interface TypeFilterModel {
  order: ResultFilterType[];
  labels: Record<string, string>;
  counts: Record<string, number>;
}

export function buildTypeFilterModel(rows: CompareRow[]): TypeFilterModel {
  const counts: Record<string, number> = Object.fromEntries(TYPE_FILTER_ORDER.map((key) => [key, key === "ALL" ? rows.length : 0]));
  for (const row of rows) {
    counts[row.type_code] = (counts[row.type_code] ?? 0) + 1;
  }

  return {
    order: [...TYPE_FILTER_ORDER],
    labels: Object.fromEntries(TYPE_FILTER_ORDER.map((key) => [key, key])),
    counts,
  };
}

export function filterCompareRowsByType(rows: CompareRow[], filterType: ResultFilterType): CompareRow[] {
  if (filterType === "ALL") {
    return rows;
  }

  return rows.filter((row) => row.type_code === filterType);
}

export function mergeCompareRow(rows: CompareRow[], nextRow: CompareRow): CompareRow[] {
  const existingIndex = rows.findIndex((row) => row.row_id === nextRow.row_id);
  if (existingIndex === -1) {
    return [...rows, nextRow];
  }

  const nextRows = [...rows];
  nextRows[existingIndex] = nextRow;
  return nextRows;
}
