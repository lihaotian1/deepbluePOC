import type { TypeCode } from "../types";

interface ResultTagProps {
  code: TypeCode;
}

function ResultTag({ code }: ResultTagProps) {
  return <span className={`result-tag result-tag--${code.toLowerCase()}`}>{code}</span>;
}

export default ResultTag;
