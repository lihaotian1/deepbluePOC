import type { TypeCode } from "../types";

interface ResultTagProps {
  code: TypeCode;
}

function ResultTag({ code }: ResultTagProps) {
  const normalized = code.trim().toUpperCase();
  const variant = ["P", "A", "B", "C", "OTHER"].includes(normalized)
    ? `result-tag--${normalized.toLowerCase()}`
    : "result-tag--named";

  return <span className={`result-tag ${variant}`}>{code}</span>;
}

export default ResultTag;
