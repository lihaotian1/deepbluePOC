export type TypeCode = string;
export type ResultFilterType = string;
export type ReviewStatus = "已审" | "未审";

export interface Chunk {
  chunk_id: number;
  source: string;
  heading: string;
  level: number;
  line_no: number;
  content: string;
}

export interface UploadResponse {
  doc_id: string;
  source_file_name: string;
  document_text: string;
}

export interface TranslationResponse {
  translation: string;
}

export interface MatchItem {
  entry_id: string;
  category: string;
  text: string;
  type_code: TypeCode;
  reason: string;
  evidence_sentence_index?: number | null;
  evidence_sentence_text?: string;
}

export interface ChunkCompareResult {
  chunk_id: number;
  heading: string;
  content: string;
  categories: string[];
  matches: MatchItem[];
  label: "命中" | "其他";
  review_status?: ReviewStatus;
}

export interface CompareRow {
  row_id: string;
  chapter_title: string;
  source_excerpt: string;
  kb_entry_id: string;
  kb_entry_text: string;
  difference_summary_brief: string;
  difference_summary: string;
  type_code: "P" | "A" | "B" | "C";
  review_comment: string;
  review_status?: ReviewStatus;
}

export interface KnowledgeBaseFileSummary {
  file_name: string;
  display_name: string;
}

export interface KnowledgeBaseItem {
  text: string;
  value: string;
}

export interface KnowledgeBaseCategory {
  name: string;
  items: KnowledgeBaseItem[];
}

export interface KnowledgeBaseDocument {
  file_name: string;
  display_name: string;
  format: "grouped" | "flat_key_value";
  categories: KnowledgeBaseCategory[];
}

export interface DocumentReviewUpdateRequest {
  compare_rows: CompareRow[];
  submitted_for_review: boolean;
}

export interface DocumentReviewResponse {
  doc_id: string;
  compare_rows: CompareRow[];
  submitted_for_review: boolean;
}

export interface KnowledgeBaseCreateRequest {
  file_name: string;
  format: "grouped" | "flat_key_value";
}

export type AppPage = "home" | "knowledge-base";
