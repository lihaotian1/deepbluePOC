import type { ChunkCompareResult, ResultFilterType, TypeCode } from "../types";

export const STANDARD_KB_FILE_NAME = "标准化配套知识库.json";
export const TENDER_KB_FILE_NAME = "投标说明知识库.json";
export const DEFAULT_COMPARE_KB_FILES = [STANDARD_KB_FILE_NAME, TENDER_KB_FILE_NAME] as const;

const STANDARD_FILTER_ORDER = ["ALL", "P", "A", "B", "C", "OTHER"];
const TENDER_FILTER_ORDER = [
  "ALL",
  "强制-必须偏离",
  "强制-澄清",
  "非强制-报价参考",
  "非强制-报价行动",
  "OTHER",
];

const STANDARD_FILTER_LABELS: Record<string, string> = {
  ALL: "ALL",
  P: "P",
  A: "A",
  B: "B",
  C: "C",
  OTHER: "其他",
};

interface HomePageCompareState {
  resultsByKb: Record<string, Record<number, ChunkCompareResult>>;
  activeFilter: ResultFilterType;
}

interface FilterModel {
  order: ResultFilterType[];
  labels: Record<string, string>;
  counts: Record<string, number>;
}

export function invalidateCompareStateAfterChunkEdit(state: HomePageCompareState): HomePageCompareState {
  if (!Object.keys(state.resultsByKb).length && state.activeFilter === "ALL") {
    return state;
  }

  return {
    resultsByKb: {},
    activeFilter: "ALL",
  };
}

export function mergeChunkCompareResult(
  resultsByKb: Record<string, Record<number, ChunkCompareResult>>,
  kbFile: string,
  result: ChunkCompareResult,
): Record<string, Record<number, ChunkCompareResult>> {
  return {
    ...resultsByKb,
    [kbFile]: {
      ...(resultsByKb[kbFile] ?? {}),
      [result.chunk_id]: result,
    },
  };
}

export function buildFilterModelForKnowledgeBase(
  kbFile: string,
  resultMap: Record<number, ChunkCompareResult>,
  totalCount: number,
): FilterModel {
  const order = kbFile === TENDER_KB_FILE_NAME ? TENDER_FILTER_ORDER : STANDARD_FILTER_ORDER;
  const labels = buildFilterLabels(order);
  const counts: Record<string, number> = Object.fromEntries(order.map((key) => [key, key === "ALL" ? totalCount : 0]));

  for (const result of Object.values(resultMap)) {
    for (const typeCode of collectTypeCodes(result)) {
      counts[typeCode] = (counts[typeCode] ?? 0) + 1;
    }
  }

  return { order, labels, counts };
}

export function collectTypeCodes(result: ChunkCompareResult): TypeCode[] {
  if (result.label === "其他" || result.matches.length === 0) {
    return ["OTHER"];
  }

  return Array.from(new Set(result.matches.map((item) => item.type_code)));
}

export function toggleKnowledgeBaseSelection(
  current: string[],
  fileName: string,
  orderedFileNames: string[],
  comparing: boolean,
): string[] {
  if (comparing) {
    return current;
  }

  if (current.includes(fileName)) {
    if (current.length === 1) {
      return current;
    }
    return current.filter((item) => item !== fileName);
  }

  const next = new Set([...current, fileName]);
  return orderedFileNames.filter((item) => next.has(item));
}

function buildFilterLabels(order: readonly string[]): Record<string, string> {
  return Object.fromEntries(
    order.map((key) => {
      if (key in STANDARD_FILTER_LABELS) {
        return [key, STANDARD_FILTER_LABELS[key]];
      }
      if (key === "OTHER") {
        return [key, "其他"];
      }
      return [key, key];
    }),
  );
}
