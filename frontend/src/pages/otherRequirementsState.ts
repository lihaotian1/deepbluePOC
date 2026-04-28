import type { OtherRequirementRow } from "../types";

export const OTHER_REQUIREMENTS_PAGE_SIZE = 10;

export interface OtherRequirementsPageModel {
  rows: OtherRequirementRow[];
  page: number;
  totalItems: number;
  totalPages: number;
}

function sortOtherRequirements(rows: OtherRequirementRow[]): OtherRequirementRow[] {
  return [...rows].sort((left, right) => {
    if (left.source_order !== right.source_order) {
      return left.source_order - right.source_order;
    }
    return left.row_id.localeCompare(right.row_id, "zh-CN");
  });
}

export function mergeOtherRequirementRow(
  rows: OtherRequirementRow[],
  nextRow: OtherRequirementRow,
): OtherRequirementRow[] {
  const existingIndex = rows.findIndex((row) => row.row_id === nextRow.row_id);
  if (existingIndex === -1) {
    return sortOtherRequirements([...rows, nextRow]);
  }

  const nextRows = [...rows];
  nextRows[existingIndex] = nextRow;
  return sortOtherRequirements(nextRows);
}

export function buildOtherRequirementsPageModel(
  rows: OtherRequirementRow[],
  requestedPage: number,
  pageSize: number = OTHER_REQUIREMENTS_PAGE_SIZE,
): OtherRequirementsPageModel {
  const sortedRows = sortOtherRequirements(rows);
  const totalItems = sortedRows.length;
  const totalPages = Math.max(1, Math.ceil(totalItems / pageSize));
  const page = Math.min(Math.max(requestedPage, 1), totalPages);
  const start = (page - 1) * pageSize;

  return {
    rows: sortedRows.slice(start, start + pageSize),
    page,
    totalItems,
    totalPages,
  };
}

export function canOpenOtherRequirements(rows: OtherRequirementRow[], comparing: boolean): boolean {
  return !comparing && rows.length > 0;
}
