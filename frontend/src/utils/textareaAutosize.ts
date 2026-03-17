export type TextareaLike = Pick<HTMLTextAreaElement, "scrollHeight"> & {
  style: Pick<CSSStyleDeclaration, "height">;
};

export function autosizeTextarea(textarea: TextareaLike, minHeight: number) {
  textarea.style.height = "auto";
  textarea.style.height = `${Math.max(textarea.scrollHeight, minHeight)}px`;
}
