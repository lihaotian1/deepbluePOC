import type { ChunkCompareResult, ResultFilterType } from "../types";


interface HomePageCompareState {
  resultMap: Record<number, ChunkCompareResult>;
  activeFilter: ResultFilterType;
}


export function invalidateCompareStateAfterChunkEdit(
  state: HomePageCompareState,
): HomePageCompareState {
  if (!Object.keys(state.resultMap).length && state.activeFilter === "ALL") {
    return state;
  }

  return {
    resultMap: {},
    activeFilter: "ALL",
  };
}
