export interface ComparePanelActionButton {
  key: "compare" | "export" | "submit-review";
  label: string;
  className: string;
}

export function buildComparePanelActionButtons(comparing: boolean): ComparePanelActionButton[] {
  return [
    {
      key: "compare",
      label: comparing ? "智能分析中..." : "开始智能分析",
      className: "btn btn-primary compare-panel__action-btn",
    },
    {
      key: "export",
      label: "导出 Excel",
      className: "btn btn-secondary compare-panel__action-btn",
    },
    {
      key: "submit-review",
      label: "提交审核",
      className: "btn btn-review compare-panel__action-btn",
    },
  ];
}

export function getVisibleComparePanelLogs(logs: string[]) {
  return logs;
}

export function resolveComparePanelProgressPercent(current: number, total: number) {
  if (total <= 0 || current <= 0) {
    return 0;
  }

  return Math.min(100, Math.max(0, Math.round((current / total) * 100)));
}

interface ComparePanelLogMetrics {
  scrollTop: number;
  clientHeight: number;
  scrollHeight: number;
}

export function shouldKeepComparePanelLogPinnedToBottom(metrics: ComparePanelLogMetrics) {
  const distanceFromBottom = metrics.scrollHeight - (metrics.scrollTop + metrics.clientHeight);
  return distanceFromBottom <= 12;
}
