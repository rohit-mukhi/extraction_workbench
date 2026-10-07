/**
 * TypeScript types for Extraction Workbench frontend.
 * These match the backend Pydantic models.
 */

// ============================================================================
// Enums
// ============================================================================

export type ProductType =
  | "Zen Orchestrator"
  | "Zen Studio"
  | "Zen Connect"
  | "Zen Insights"
  | "Zen Vault";

export type CategoryType =
  | "outage"
  | "billing"
  | "bug"
  | "feature_request"
  | "how_to"
  | "churn_risk";

export type SeverityLevel = "low" | "medium" | "high" | "critical";

export type RequestedAction =
  | "refund"
  | "credit"
  | "fix"
  | "callback"
  | "information"
  | "none";

export type RecordStatus = "completed" | "needs_review" | "failed";

export type JobStatus = "pending" | "running" | "completed" | "failed";

// ============================================================================
// Core Data Types
// ============================================================================

export interface Ticket {
  id: string;
  subject: string;
  body: string;
  channel: string;
  received_at: string;
  from_email: string;
  attachments: number;
}

export interface ExtractedRecord {
  id: string;
  ticket_id: string;
  
  // Required fields
  company: string;
  product: ProductType;
  category: CategoryType;
  severity: SeverityLevel;
  requested_action: RequestedAction;
  
  // Optional fields
  refund_amount: number | null;
  deadline: string | null; // ISO date string
  
  // Boolean
  escalated: boolean;
  
  // Metadata
  confidence_scores: Record<string, number>;
  human_edited_fields: string[];
  status: RecordStatus;
  raw_output: string | null;
  created_at: string;
  updated_at: string;
}

export interface JobProgress {
  total: number;
  queued: number;
  running: number;
  completed: number;
  failed: number;
}

export interface Job {
  id: string;
  ticket_ids: string[];
  record_ids: string[];
  status: JobStatus;
  progress: JobProgress;
  created_at: string;
  updated_at: string;
  error_message: string | null;
}

// ============================================================================
// API Request/Response Types
// ============================================================================

export interface JobCreateRequest {
  ticket_ids: string[];
}

export interface JobCreateResponse {
  job_id: string;
  status: JobStatus;
}

export interface RecordUpdateRequest {
  field: string;
  value: string | number | boolean | null;
}

// ============================================================================
// UI-Specific Types
// ============================================================================

export interface TicketWithSelection extends Ticket {
  selected: boolean;
}

export interface RecordWithTicket {
  record: ExtractedRecord;
  ticket: Ticket;
}

// ============================================================================
// API Error Types
// ============================================================================

export interface APIError {
  detail: string;
}

// ============================================================================
// Field Metadata (for form validation)
// ============================================================================

export const PRODUCT_OPTIONS: ProductType[] = [
  "Zen Orchestrator",
  "Zen Studio",
  "Zen Connect",
  "Zen Insights",
  "Zen Vault",
];

export const CATEGORY_OPTIONS: CategoryType[] = [
  "outage",
  "billing",
  "bug",
  "feature_request",
  "how_to",
  "churn_risk",
];

export const SEVERITY_OPTIONS: SeverityLevel[] = [
  "low",
  "medium",
  "high",
  "critical",
];

export const REQUESTED_ACTION_OPTIONS: RequestedAction[] = [
  "refund",
  "credit",
  "fix",
  "callback",
  "information",
  "none",
];

// Human-readable labels for enum values
export const CATEGORY_LABELS: Record<CategoryType, string> = {
  outage: "Outage",
  billing: "Billing",
  bug: "Bug",
  feature_request: "Feature Request",
  how_to: "How-to",
  churn_risk: "Churn Risk",
};

export const SEVERITY_LABELS: Record<SeverityLevel, string> = {
  low: "Low",
  medium: "Medium",
  high: "High",
  critical: "Critical",
};

export const ACTION_LABELS: Record<RequestedAction, string> = {
  refund: "Refund",
  credit: "Credit",
  fix: "Fix",
  callback: "Callback",
  information: "Information",
  none: "None",
};

// CSS classes for severity levels
export const SEVERITY_COLORS: Record<SeverityLevel, string> = {
  low: "bg-blue-100 text-blue-800",
  medium: "bg-yellow-100 text-yellow-800",
  high: "bg-orange-100 text-orange-800",
  critical: "bg-red-100 text-red-800",
};

// CSS classes for record status
export const STATUS_COLORS: Record<RecordStatus, string> = {
  completed: "bg-green-100 text-green-800",
  needs_review: "bg-yellow-100 text-yellow-800",
  failed: "bg-red-100 text-red-800",
};
