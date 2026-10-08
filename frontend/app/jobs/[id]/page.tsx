"use client";

import { useState, useEffect, use } from "react";
import { useRouter } from "next/navigation";
import { getJob, getJobResults, getTickets, updateRecord, downloadCSV } from "@/lib/api";
import type { Job, ExtractedRecord, Ticket } from "@/lib/types";
import {
  PRODUCT_OPTIONS,
  CATEGORY_OPTIONS,
  SEVERITY_OPTIONS,
  REQUESTED_ACTION_OPTIONS,
  CATEGORY_LABELS,
  SEVERITY_LABELS,
  ACTION_LABELS,
  SEVERITY_COLORS,
  STATUS_COLORS,
} from "@/lib/types";

interface PageProps {
  params: Promise<{ id: string }>;
}

export default function JobDetailPage({ params }: PageProps) {
  const resolvedParams = use(params);
  const jobId = resolvedParams.id;
  const router = useRouter();

  const [job, setJob] = useState<Job | null>(null);
  const [records, setRecords] = useState<ExtractedRecord[]>([]);
  const [tickets, setTickets] = useState<Map<string, Ticket>>(new Map());
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedRecordId, setSelectedRecordId] = useState<string | null>(null);
  const [showOnlyEdited, setShowOnlyEdited] = useState(false);

  // Load job and poll for updates
  useEffect(() => {
    loadJobData();
    const interval = setInterval(() => {
      if (job?.status === "running" || job?.status === "pending") {
        loadJobData();
      }
    }, 2000); // Poll every 2 seconds

    return () => clearInterval(interval);
  }, [jobId, job?.status]);

  async function loadJobData() {
    try {
      setError(null);
      const jobData = await getJob(jobId);
      setJob(jobData);

      // Load results if job has started
      if (jobData.record_ids.length > 0) {
        const resultsData = await getJobResults(jobId);
        setRecords(resultsData);

        // Load tickets for records
        const allTickets = await getTickets();
        const ticketMap = new Map(allTickets.map((t) => [t.id, t]));
        setTickets(ticketMap);
      }

      setLoading(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load job");
      setLoading(false);
    }
  }

  async function handleFieldUpdate(
    recordId: string,
    field: string,
    value: string | number | boolean | null
  ) {
    try {
      const updated = await updateRecord(recordId, field, value);
      // Update local state
      setRecords((prev) =>
        prev.map((r) => (r.id === recordId ? updated : r))
      );
    } catch (err) {
      alert(err instanceof Error ? err.message : "Failed to update record");
    }
  }

  function handleExport() {
    downloadCSV(jobId);
  }

  // Selected record for side-by-side view
  const selectedRecord = records.find((r) => r.id === selectedRecordId);
  const selectedTicket = selectedRecord
    ? tickets.get(selectedRecord.ticket_id)
    : null;

  // Progress percentage
  const progressPercent = job
    ? Math.round((job.progress.completed / job.progress.total) * 100)
    : 0;

  // Filter records based on human-edited toggle
  const filteredRecords = showOnlyEdited
    ? records.filter((r) => r.human_edited_fields.length > 0)
    : records;

  // Count of human-edited records
  const editedCount = records.filter((r) => r.human_edited_fields.length > 0).length;

  if (loading && !job) {
    return (
      <div className="min-h-screen bg-[#0a0a0a] flex items-center justify-center">
        <div className="text-center">
          <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-gray-100"></div>
          <p className="mt-4 text-gray-400">Loading job...</p>
        </div>
      </div>
    );
  }

  if (error && !job) {
    return (
      <div className="min-h-screen bg-[#0a0a0a] flex items-center justify-center">
        <div className="text-center">
          <p className="text-red-400 mb-4">{error}</p>
          <button
            onClick={() => router.push("/")}
            className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
          >
            Back to Home
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#0a0a0a]">
      {/* Header */}
      <header className="bg-[#1a1a1a] border-b border-[#333333]">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between">
            <div>
              <button
                onClick={() => router.push("/")}
                className="text-sm text-blue-400 hover:text-blue-300 mb-2"
              >
                ← Back to Tickets
              </button>
              <h1 className="text-2xl font-bold text-gray-100">
                Job {jobId}
              </h1>
              <p className="text-sm text-gray-400 mt-1">
                Processing {job?.progress.total} tickets
              </p>
            </div>

            {job?.status === "completed" && (
              <button
                onClick={handleExport}
                className="px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 font-medium"
              >
                Export CSV
              </button>
            )}
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        {/* Progress Section */}
        <div className="bg-[#1a1a1a] rounded-lg shadow-lg border border-[#333333] p-6 mb-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-gray-100">Progress</h2>
            <span
              className={`px-3 py-1 rounded-full text-sm font-medium ${
                job?.status === "completed"
                  ? "bg-green-950 text-green-300"
                  : job?.status === "running"
                  ? "bg-blue-950 text-blue-300"
                  : job?.status === "failed"
                  ? "bg-red-950 text-red-300"
                  : "bg-[#242424] text-gray-300"
              }`}
            >
              {job?.status.toUpperCase()}
            </span>
          </div>

          {/* Progress Bar */}
          <div className="mb-4">
            <div className="w-full bg-[#242424] rounded-full h-2">
              <div
                className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                style={{ width: `${progressPercent}%` }}
              ></div>
            </div>
            <p className="text-sm text-gray-400 mt-2">{progressPercent}% complete</p>
          </div>

          {/* Progress Stats */}
          <div className="grid grid-cols-2 sm:grid-cols-5 gap-4">
            <div>
              <p className="text-xs text-gray-500">Total</p>
              <p className="text-2xl font-bold text-gray-100">
                {job?.progress.total}
              </p>
            </div>
            <div>
              <p className="text-xs text-gray-500">Queued</p>
              <p className="text-2xl font-bold text-gray-400">
                {job?.progress.queued}
              </p>
            </div>
            <div>
              <p className="text-xs text-gray-500">Running</p>
              <p className="text-2xl font-bold text-blue-400">
                {job?.progress.running}
              </p>
            </div>
            <div>
              <p className="text-xs text-gray-500">Completed</p>
              <p className="text-2xl font-bold text-green-400">
                {job?.progress.completed}
              </p>
            </div>
            <div>
              <p className="text-xs text-gray-500">Failed</p>
              <p className="text-2xl font-bold text-red-400">
                {job?.progress.failed}
              </p>
            </div>
          </div>
        </div>

        {/* Results Section */}
        {records.length > 0 && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Records List */}
            <div className="bg-[#1a1a1a] rounded-lg shadow-lg border border-[#333333] p-4 flex flex-col" style={{height: 'calc(100vh - 400px)', minHeight: '500px'}}>
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-lg font-semibold text-gray-100">
                  Extracted Records
                </h2>
                
                {/* Filter Toggle */}
                <button
                  onClick={() => setShowOnlyEdited(!showOnlyEdited)}
                  className={`flex items-center gap-2 px-3 py-1.5 text-sm rounded-md transition-colors ${
                    showOnlyEdited
                      ? "bg-blue-600 text-white"
                      : "bg-[#242424] text-gray-300 hover:bg-[#2f2f2f]"
                  }`}
                >
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                  </svg>
                  {showOnlyEdited ? `Edited (${editedCount})` : `Show Edited Only (${editedCount})`}
                </button>
              </div>

              <div className="space-y-2 flex-1 overflow-y-auto">
                {filteredRecords.length === 0 ? (
                  <div className="text-center py-12 text-gray-500">
                    {showOnlyEdited 
                      ? "No human-edited records yet" 
                      : "No records available"}
                  </div>
                ) : (
                  filteredRecords.map((record) => (
                  <button
                    key={record.id}
                    onClick={() => setSelectedRecordId(record.id)}
                    className={`w-full text-left p-3 rounded-md border transition-colors ${
                      selectedRecordId === record.id
                        ? "border-blue-500 bg-blue-950/30"
                        : "border-[#333333] hover:border-[#444444] hover:bg-[#242424]"
                    } ${
                      record.status === "needs_review"
                        ? "border-l-4 border-l-yellow-500"
                        : ""
                    } ${
                      record.human_edited_fields.length > 0
                        ? "border-r-4 border-r-green-500"
                        : ""
                    }`}
                  >
                    <div className="flex items-center justify-between mb-1">
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-mono text-gray-500">
                          {record.ticket_id}
                        </span>
                        {record.human_edited_fields.length > 0 && (
                          <span className="text-xs px-2 py-0.5 bg-green-950 text-green-300 rounded flex items-center gap-1">
                            <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                            </svg>
                            Edited
                          </span>
                        )}
                      </div>
                      <span
                        className={`text-xs px-2 py-1 rounded ${
                          STATUS_COLORS[record.status]
                        }`}
                      >
                        {record.status.replace("_", " ")}
                      </span>
                    </div>
                    <p className="text-sm font-medium text-gray-100">
                      {record.company}
                    </p>
                    <p className="text-xs text-gray-400">
                      {record.product} • {CATEGORY_LABELS[record.category]}
                    </p>
                  </button>
                ))}
              </div>
            </div>

            {/* Detail View */}
            <div className="bg-[#1a1a1a] rounded-lg shadow-lg border border-[#333333] p-4 flex flex-col" style={{height: 'calc(100vh - 400px)', minHeight: '500px'}}>
              {selectedRecord && selectedTicket ? (
                <div className="flex flex-col h-full">
                  <h2 className="text-lg font-semibold text-gray-100 mb-4">
                    Review & Edit
                  </h2>

                  <div className="flex-1 overflow-y-auto space-y-4">
                    {/* Original Ticket */}
                    <div className="p-4 bg-[#242424] rounded-md border border-[#333333]">
                      <h3 className="text-sm font-medium text-gray-300 mb-2">
                        Original Ticket
                      </h3>
                      <p className="text-xs text-gray-500 mb-1">
                        {selectedTicket.id} • {selectedTicket.from_email}
                      </p>
                      <p className="text-sm font-medium text-gray-100 mb-2">
                        {selectedTicket.subject}
                      </p>
                      <p className="text-sm text-gray-300 whitespace-pre-wrap max-h-32 overflow-y-auto">
                        {selectedTicket.body}
                      </p>
                    </div>

                    {/* Extracted Fields */}
                    <div className="space-y-4">
                    <RecordField
                      label="Company"
                      field="company"
                      value={selectedRecord.company}
                      type="text"
                      isEdited={selectedRecord.human_edited_fields.includes("company")}
                      onUpdate={(value) =>
                        handleFieldUpdate(selectedRecord.id, "company", value)
                      }
                    />

                    <RecordField
                      label="Product"
                      field="product"
                      value={selectedRecord.product}
                      type="select"
                      options={PRODUCT_OPTIONS}
                      isEdited={selectedRecord.human_edited_fields.includes("product")}
                      onUpdate={(value) =>
                        handleFieldUpdate(selectedRecord.id, "product", value)
                      }
                    />

                    <RecordField
                      label="Category"
                      field="category"
                      value={selectedRecord.category}
                      type="select"
                      options={CATEGORY_OPTIONS}
                      isEdited={selectedRecord.human_edited_fields.includes("category")}
                      onUpdate={(value) =>
                        handleFieldUpdate(selectedRecord.id, "category", value)
                      }
                    />

                    <RecordField
                      label="Severity"
                      field="severity"
                      value={selectedRecord.severity}
                      type="select"
                      options={SEVERITY_OPTIONS}
                      isEdited={selectedRecord.human_edited_fields.includes("severity")}
                      onUpdate={(value) =>
                        handleFieldUpdate(selectedRecord.id, "severity", value)
                      }
                    />

                    <RecordField
                      label="Requested Action"
                      field="requested_action"
                      value={selectedRecord.requested_action}
                      type="select"
                      options={REQUESTED_ACTION_OPTIONS}
                      isEdited={selectedRecord.human_edited_fields.includes(
                        "requested_action"
                      )}
                      onUpdate={(value) =>
                        handleFieldUpdate(selectedRecord.id, "requested_action", value)
                      }
                    />

                    <RecordField
                      label="Refund Amount (USD)"
                      field="refund_amount"
                      value={selectedRecord.refund_amount?.toString() || ""}
                      type="number"
                      isEdited={selectedRecord.human_edited_fields.includes(
                        "refund_amount"
                      )}
                      onUpdate={(value) =>
                        handleFieldUpdate(
                          selectedRecord.id,
                          "refund_amount",
                          value ? parseFloat(value as string) : null
                        )
                      }
                    />

                    <RecordField
                      label="Deadline"
                      field="deadline"
                      value={selectedRecord.deadline || ""}
                      type="date"
                      isEdited={selectedRecord.human_edited_fields.includes("deadline")}
                      onUpdate={(value) =>
                        handleFieldUpdate(selectedRecord.id, "deadline", value || null)
                      }
                    />

                    <RecordField
                      label="Escalated"
                      field="escalated"
                      value={selectedRecord.escalated}
                      type="checkbox"
                      isEdited={selectedRecord.human_edited_fields.includes("escalated")}
                      onUpdate={(value) =>
                        handleFieldUpdate(selectedRecord.id, "escalated", value)
                      }
                    />
                  </div>
                  </div>
                </div>
              ) : (
                <div className="text-center py-12 text-gray-500">
                  Select a record to review
                </div>
              )}
            </div>
          </div>
        )}

        {/* No Results Yet */}
        {records.length === 0 && job?.status === "running" && (
          <div className="text-center py-12 text-gray-500">
            Processing tickets...
          </div>
        )}
      </main>
    </div>
  );
}

// Reusable field editor component
function RecordField({
  label,
  field,
  value,
  type,
  options,
  isEdited,
  onUpdate,
}: {
  label: string;
  field: string;
  value: string | number | boolean;
  type: "text" | "select" | "number" | "date" | "checkbox";
  options?: readonly string[];
  isEdited: boolean;
  onUpdate: (value: string | number | boolean) => void;
}) {
  const [editing, setEditing] = useState(false);
  const [localValue, setLocalValue] = useState(value);

  function handleSave() {
    onUpdate(localValue);
    setEditing(false);
  }

  function handleCancel() {
    setLocalValue(value);
    setEditing(false);
  }

  return (
    <div className="border border-[#333333] rounded-md p-3 bg-[#242424]">
      <div className="flex items-center justify-between mb-2">
        <label className="text-sm font-medium text-gray-300">{label}</label>
        {isEdited && (
          <span className="text-xs px-2 py-1 bg-green-950 text-green-300 rounded">
            Human Edited
          </span>
        )}
      </div>

      {!editing ? (
        <div className="flex items-center justify-between">
          <span className="text-sm text-gray-100">
            {type === "checkbox"
              ? value
                ? "Yes"
                : "No"
              : value || "(empty)"}
          </span>
          <button
            onClick={() => setEditing(true)}
            className="text-xs text-blue-400 hover:text-blue-300"
          >
            Edit
          </button>
        </div>
      ) : (
        <div>
          {type === "select" && options ? (
            <select
              value={localValue as string}
              onChange={(e) => setLocalValue(e.target.value)}
              className="w-full px-3 py-2 bg-[#1f1f1f] border border-[#333333] text-gray-100 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              {options.map((opt) => (
                <option key={opt} value={opt}>
                  {opt}
                </option>
              ))}
            </select>
          ) : type === "checkbox" ? (
            <input
              type="checkbox"
              checked={localValue as boolean}
              onChange={(e) => setLocalValue(e.target.checked)}
              className="h-4 w-4 text-blue-600 rounded border-gray-600 bg-[#1f1f1f]"
            />
          ) : (
            <input
              type={type}
              value={localValue as string}
              onChange={(e) => setLocalValue(e.target.value)}
              className="w-full px-3 py-2 bg-[#1f1f1f] border border-[#333333] text-gray-100 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          )}

          <div className="flex gap-2 mt-2">
            <button
              onClick={handleSave}
              className="px-3 py-1 bg-blue-600 text-white text-xs rounded-md hover:bg-blue-700"
            >
              Save
            </button>
            <button
              onClick={handleCancel}
              className="px-3 py-1 bg-[#333333] text-gray-300 text-xs rounded-md hover:bg-[#444444]"
            >
              Cancel
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
