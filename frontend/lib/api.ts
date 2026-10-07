/**
 * API client for Extraction Workbench backend.
 * All API calls go through these functions.
 */

import type {
  Ticket,
  Job,
  ExtractedRecord,
  JobCreateRequest,
  JobCreateResponse,
  RecordUpdateRequest,
  APIError,
} from "./types";

// Get API URL from environment variable
const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

/**
 * Base fetch wrapper with error handling
 */
async function apiFetch<T>(
  endpoint: string,
  options?: RequestInit
): Promise<T> {
  const url = `${API_URL}${endpoint}`;

  try {
    const response = await fetch(url, {
      ...options,
      headers: {
        "Content-Type": "application/json",
        ...options?.headers,
      },
    });

    // Handle non-OK responses
    if (!response.ok) {
      const error: APIError = await response.json().catch(() => ({
        detail: `HTTP ${response.status}: ${response.statusText}`,
      }));
      throw new Error(error.detail || "API request failed");
    }

    return await response.json();
  } catch (error) {
    if (error instanceof Error) {
      throw error;
    }
    throw new Error("Unknown error occurred");
  }
}

// ============================================================================
// Ticket API
// ============================================================================

/**
 * Get all tickets
 */
export async function getTickets(params?: {
  limit?: number;
  search?: string;
}): Promise<Ticket[]> {
  const queryParams = new URLSearchParams();
  if (params?.limit) queryParams.append("limit", params.limit.toString());
  if (params?.search) queryParams.append("search", params.search);

  const query = queryParams.toString();
  const endpoint = `/api/tickets${query ? `?${query}` : ""}`;

  return apiFetch<Ticket[]>(endpoint);
}

// ============================================================================
// Job API
// ============================================================================

/**
 * Create a new extraction job
 */
export async function createJob(
  ticketIds: string[]
): Promise<JobCreateResponse> {
  const body: JobCreateRequest = { ticket_ids: ticketIds };

  return apiFetch<JobCreateResponse>("/api/jobs", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

/**
 * Get job status and progress
 */
export async function getJob(jobId: string): Promise<Job> {
  return apiFetch<Job>(`/api/jobs/${jobId}`);
}

/**
 * Get job results (extracted records)
 */
export async function getJobResults(jobId: string): Promise<ExtractedRecord[]> {
  return apiFetch<ExtractedRecord[]>(`/api/jobs/${jobId}/results`);
}

/**
 * Export job results as CSV
 * Returns the download URL
 */
export function getExportURL(jobId: string): string {
  return `${API_URL}/api/jobs/${jobId}/export.csv`;
}

/**
 * Download CSV file
 */
export async function downloadCSV(jobId: string): Promise<void> {
  const url = getExportURL(jobId);
  
  // Open download in new tab
  window.open(url, "_blank");
}

// ============================================================================
// Record API
// ============================================================================

/**
 * Update a record field with human correction
 */
export async function updateRecord(
  recordId: string,
  field: string,
  value: string | number | boolean | null
): Promise<ExtractedRecord> {
  const body: RecordUpdateRequest = { field, value };

  return apiFetch<ExtractedRecord>(`/api/records/${recordId}`, {
    method: "PATCH",
    body: JSON.stringify(body),
  });
}

// ============================================================================
// Helper Functions
// ============================================================================

/**
 * Check if backend is reachable
 */
export async function healthCheck(): Promise<boolean> {
  try {
    const response = await fetch(`${API_URL}/`);
    return response.ok;
  } catch {
    return false;
  }
}

/**
 * Poll job status until completion
 * Calls onUpdate with job data on each poll
 */
export async function pollJobStatus(
  jobId: string,
  onUpdate: (job: Job) => void,
  options?: {
    interval?: number; // milliseconds
    maxAttempts?: number;
  }
): Promise<Job> {
  const interval = options?.interval || 2000; // 2 seconds default
  const maxAttempts = options?.maxAttempts || 300; // 10 minutes max

  let attempts = 0;

  return new Promise((resolve, reject) => {
    const poll = async () => {
      try {
        const job = await getJob(jobId);
        onUpdate(job);

        // Check if job is complete
        if (job.status === "completed" || job.status === "failed") {
          resolve(job);
          return;
        }

        // Check max attempts
        attempts++;
        if (attempts >= maxAttempts) {
          reject(new Error("Polling timeout"));
          return;
        }

        // Schedule next poll
        setTimeout(poll, interval);
      } catch (error) {
        reject(error);
      }
    };

    // Start polling
    poll();
  });
}
