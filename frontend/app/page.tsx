"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { getTickets, createJob } from "@/lib/api";
import type { Ticket } from "@/lib/types";

export default function HomePage() {
  const router = useRouter();
  const [tickets, setTickets] = useState<Ticket[]>([]);
  const [selectedTickets, setSelectedTickets] = useState<Set<string>>(new Set());
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");

  // Load tickets on mount
  useEffect(() => {
    loadTickets();
  }, []);

  async function loadTickets() {
    try {
      setLoading(true);
      setError(null);
      const data = await getTickets();
      setTickets(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load tickets");
    } finally {
      setLoading(false);
    }
  }

  // Toggle ticket selection
  function toggleTicket(ticketId: string) {
    const newSelected = new Set(selectedTickets);
    if (newSelected.has(ticketId)) {
      newSelected.delete(ticketId);
    } else {
      newSelected.add(ticketId);
    }
    setSelectedTickets(newSelected);
  }

  // Select all tickets
  function selectAll() {
    const filtered = getFilteredTickets();
    setSelectedTickets(new Set(filtered.map((t) => t.id)));
  }

  // Clear selection
  function clearSelection() {
    setSelectedTickets(new Set());
  }

  // Create extraction job
  async function handleCreateJob() {
    if (selectedTickets.size === 0) {
      alert("Please select at least one ticket");
      return;
    }

    try {
      setCreating(true);
      const response = await createJob(Array.from(selectedTickets));
      // Redirect to job detail page
      router.push(`/jobs/${response.job_id}`);
    } catch (err) {
      alert(err instanceof Error ? err.message : "Failed to create job");
      setCreating(false);
    }
  }

  // Filter tickets by search query
  function getFilteredTickets(): Ticket[] {
    if (!searchQuery.trim()) {
      return tickets;
    }

    const query = searchQuery.toLowerCase();
    return tickets.filter(
      (ticket) =>
        ticket.subject.toLowerCase().includes(query) ||
        ticket.body.toLowerCase().includes(query) ||
        ticket.from_email.toLowerCase().includes(query) ||
        ticket.id.toLowerCase().includes(query)
    );
  }

  const filteredTickets = getFilteredTickets();

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <h1 className="text-3xl font-bold text-gray-900">
            Extraction Workbench
          </h1>
          <p className="mt-1 text-sm text-gray-500">
            Select tickets to extract structured data
          </p>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Error Message */}
        {error && (
          <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-md">
            <p className="text-sm text-red-800">{error}</p>
            <button
              onClick={loadTickets}
              className="mt-2 text-sm text-red-600 hover:text-red-800 underline"
            >
              Retry
            </button>
          </div>
        )}

        {/* Controls */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4 mb-6">
          <div className="flex flex-col sm:flex-row gap-4 items-start sm:items-center justify-between">
            {/* Search */}
            <div className="flex-1 w-full sm:w-auto">
              <input
                type="text"
                placeholder="Search tickets by subject, body, or email..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            {/* Actions */}
            <div className="flex gap-2 w-full sm:w-auto">
              <button
                onClick={selectAll}
                disabled={filteredTickets.length === 0}
                className="px-4 py-2 text-sm text-gray-700 bg-gray-100 rounded-md hover:bg-gray-200 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Select All
              </button>
              <button
                onClick={clearSelection}
                disabled={selectedTickets.size === 0}
                className="px-4 py-2 text-sm text-gray-700 bg-gray-100 rounded-md hover:bg-gray-200 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Clear
              </button>
            </div>
          </div>

          {/* Selection Count */}
          <div className="mt-4 flex items-center justify-between">
            <p className="text-sm text-gray-600">
              {selectedTickets.size} of {filteredTickets.length} tickets selected
              {searchQuery && ` (filtered from ${tickets.length} total)`}
            </p>
            <button
              onClick={handleCreateJob}
              disabled={selectedTickets.size === 0 || creating}
              className="px-6 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed font-medium"
            >
              {creating ? "Creating Job..." : "Start Extraction"}
            </button>
          </div>
        </div>

        {/* Loading State */}
        {loading && (
          <div className="text-center py-12">
            <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-gray-900"></div>
            <p className="mt-2 text-sm text-gray-600">Loading tickets...</p>
          </div>
        )}

        {/* Ticket List */}
        {!loading && filteredTickets.length === 0 && (
          <div className="text-center py-12">
            <p className="text-gray-500">
              {searchQuery ? "No tickets match your search" : "No tickets found"}
            </p>
          </div>
        )}

        {!loading && filteredTickets.length > 0 && (
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 divide-y divide-gray-200">
            {filteredTickets.map((ticket) => (
              <div
                key={ticket.id}
                className={`p-4 hover:bg-gray-50 cursor-pointer transition-colors ${
                  selectedTickets.has(ticket.id) ? "bg-blue-50" : ""
                }`}
                onClick={() => toggleTicket(ticket.id)}
              >
                <div className="flex items-start gap-4">
                  {/* Checkbox */}
                  <input
                    type="checkbox"
                    checked={selectedTickets.has(ticket.id)}
                    onChange={() => toggleTicket(ticket.id)}
                    className="mt-1 h-4 w-4 text-blue-600 rounded border-gray-300 focus:ring-blue-500"
                    onClick={(e) => e.stopPropagation()}
                  />

                  {/* Ticket Content */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-xs font-mono text-gray-500">
                        {ticket.id}
                      </span>
                      <span className="text-xs px-2 py-1 bg-gray-100 text-gray-700 rounded">
                        {ticket.channel}
                      </span>
                      {ticket.attachments > 0 && (
                        <span className="text-xs px-2 py-1 bg-blue-100 text-blue-700 rounded">
                          {ticket.attachments} attachment{ticket.attachments > 1 ? "s" : ""}
                        </span>
                      )}
                    </div>

                    <h3 className="text-sm font-medium text-gray-900 mb-1">
                      {ticket.subject || "(No subject)"}
                    </h3>

                    <p className="text-sm text-gray-600 line-clamp-2 mb-2">
                      {ticket.body}
                    </p>

                    <div className="flex items-center gap-4 text-xs text-gray-500">
                      <span>{ticket.from_email}</span>
                      <span>
                        {new Date(ticket.received_at).toLocaleDateString()}
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </main>
    </div>
  );
}
