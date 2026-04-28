export type HomePageStatusTone = "idle" | "running" | "done" | "error";

export function buildCompareDoneMessage(rowCount: number) {
  return `全部解析完毕，已生成 ${Math.max(0, rowCount)} 条结果`;
}

export function resolveHomePageStatusDotClass(tone: HomePageStatusTone) {
  if (tone === "running") {
    return "pulse-dot";
  }

  return "pulse-dot pulse-dot--static";
}
