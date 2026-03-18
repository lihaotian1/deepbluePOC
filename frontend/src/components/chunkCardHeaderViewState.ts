export interface ChunkCardHeaderAction {
  key: string;
  label: string;
  className: string;
}

export interface ChunkCardHeaderActionGroup {
  key: string;
  className: string;
  containerClassName: string;
  actions: ChunkCardHeaderAction[];
  titleContainerClassName?: string;
  titleGapPx?: number;
}

interface ChunkCardHeaderViewStateInput {
  mode: "preview" | "edit";
  isReviewed: boolean;
}

export function buildChunkCardHeaderActionGroups(
  input: ChunkCardHeaderViewStateInput,
): ChunkCardHeaderActionGroup[] {
  return [
    {
      key: "view-mode",
      containerClassName: "chunk-card__header-primary",
      className: "chunk-card__switcher chunk-card__switcher--source",
      titleContainerClassName: "chunk-card__title-wrap",
      titleGapPx: 40,
      actions: [
        {
          key: "preview",
          label: "预览",
          className: `btn btn-lite${input.mode === "preview" ? " is-active" : ""}`,
        },
        {
          key: "edit",
          label: "编辑",
          className: `btn btn-lite${input.mode === "edit" ? " is-active" : ""}`,
        },
      ],
    },
    {
      key: "review-actions",
      containerClassName: "chunk-card__header-secondary",
      className: "chunk-card__switcher chunk-card__switcher--review",
      actions: [
        {
          key: "modify",
          label: "修改",
          className: "btn btn-lite",
        },
        {
          key: "review",
          label: input.isReviewed ? "已审" : "审核",
          className: `btn btn-lite${input.isReviewed ? " btn--success" : ""}`,
        },
      ],
    },
  ];
}
