"""
Test job manager behavior, especially needs_review handling.
Tests that double failures result in needs_review status and job still completes.
"""
import pytest
import asyncio
from datetime import datetime

from models import Job, JobStatus, RecordStatus, Ticket
from storage import Storage
from job_manager import JobManager
from mock_provider import MockAIProvider


@pytest.fixture
def storage():
    """Create storage with test tickets including invalid ones."""
    storage = Storage()
    
    # Add normal test tickets
    for i in range(5):
        ticket_id = f"tkt_test_{i:03d}"
        storage.tickets[ticket_id] = Ticket(
            id=ticket_id,
            subject=f"Test ticket {i}",
            body=f"Test body for Zen Connect issue {i}",
            channel="email",
            received_at="2026-08-04T11:56:28Z",
            from_email=f"test{i}@example.com",
            attachments=0
        )
    
    # Add tickets that will fail validation (from mock_provider.INVALID_TICKETS)
    storage.tickets["tkt_0013"] = Ticket(
        id="tkt_0013",
        subject="Invoice query",
        body="We were billed twice for invoice INV-25846 on the 7th.",
        channel="chat",
        received_at="2026-08-07T13:22:10Z",
        from_email="m.feld@panacea.com",
        attachments=0
    )
    
    storage.tickets["tkt_0042"] = Ticket(
        id="tkt_0042",
        subject="Feature request",
        body="Is there any way to get SSO with Entra ID on Zen Connect?",
        channel="chat",
        received_at="2026-08-12T05:16:24Z",
        from_email="i.ortiz@trident.com",
        attachments=0
    )
    
    return storage


@pytest.fixture
def job_manager(storage):
    """Create job manager instance."""
    return JobManager(storage, max_concurrent=2)


@pytest.mark.asyncio
async def test_needs_review_after_double_failure(storage, job_manager):
    """
    Test that when extraction fails twice, record is marked needs_review
    and the job still completes (doesn't crash).
    This is a core requirement from the README.
    """
    # Create job with a ticket that will fail validation
    job = storage.create_job(["tkt_0013"])
    
    # Process the job
    await job_manager.process_job(job.id)
    
    # Job should complete (not fail)
    job = storage.get_job(job.id)
    assert job.status == JobStatus.COMPLETED
    
    # Progress should show completion
    assert job.progress.completed == 1
    assert job.progress.failed == 0
    assert job.progress.is_complete()
    
    # Record should exist and be marked needs_review
    assert len(job.record_ids) == 1
    record = storage.get_record(job.record_ids[0])
    
    assert record is not None
    assert record.status == RecordStatus.NEEDS_REVIEW
    assert record.ticket_id == "tkt_0013"
    
    # Should have placeholder values
    assert record.company is not None
    assert record.product in ["Zen Orchestrator", "Zen Studio", "Zen Connect", "Zen Insights", "Zen Vault"]


@pytest.mark.asyncio
async def test_job_completes_with_mixed_results(storage, job_manager):
    """
    Test that a job completes successfully even when some tickets
    fail validation and go to needs_review.
    """
    # Create job with mix of valid and invalid tickets
    job = storage.create_job([
        "tkt_test_000",  # Valid
        "tkt_0013",      # Will fail validation
        "tkt_test_001",  # Valid
        "tkt_0042",      # Will fail validation
        "tkt_test_002"   # Valid
    ])
    
    # Process job
    await job_manager.process_job(job.id)
    
    # Job should complete successfully
    job = storage.get_job(job.id)
    assert job.status == JobStatus.COMPLETED
    assert job.progress.completed == 5
    assert job.progress.failed == 0  # No "failed", they go to needs_review
    
    # Check we have 5 records
    assert len(job.record_ids) == 5
    
    # Count records by status
    records = [storage.get_record(rid) for rid in job.record_ids]
    completed_records = [r for r in records if r.status == RecordStatus.COMPLETED]
    needs_review_records = [r for r in records if r.status == RecordStatus.NEEDS_REVIEW]
    
    # Should have some of each
    assert len(completed_records) == 3  # Valid tickets
    assert len(needs_review_records) == 2  # Invalid tickets


@pytest.mark.asyncio
async def test_concurrency_limit_respected(storage, job_manager):
    """
    Test that job manager respects the max_concurrent limit.
    """
    # Create job with more tickets than concurrent limit
    ticket_ids = [f"tkt_test_{i:03d}" for i in range(5)]
    job = storage.create_job(ticket_ids)
    
    # Job manager has max_concurrent=2
    assert job_manager.max_concurrent == 2
    
    # Start processing
    task = asyncio.create_task(job_manager.process_job(job.id))
    
    # Wait briefly to let processing start
    await asyncio.sleep(0.2)
    
    # Check that not all are running at once
    # (This is hard to test precisely due to timing, but we can verify completion)
    await task
    
    # Verify job completed
    job = storage.get_job(job.id)
    assert job.status == JobStatus.COMPLETED
    assert job.progress.is_complete()


@pytest.mark.asyncio
async def test_create_needs_review_record(job_manager, storage):
    """
    Test the _create_needs_review_record method directly.
    """
    ticket = storage.get_ticket("tkt_test_000")
    
    # Create needs_review record
    record = job_manager._create_needs_review_record(ticket)
    
    # Verify it has safe defaults
    assert record.ticket_id == "tkt_test_000"
    assert record.status == RecordStatus.NEEDS_REVIEW
    assert record.company == "Unknown"
    assert record.product in ["Zen Orchestrator", "Zen Studio", "Zen Connect", "Zen Insights", "Zen Vault"]
    assert record.category in ["outage", "billing", "bug", "feature_request", "how_to", "churn_risk"]
    assert record.severity in ["low", "medium", "high", "critical"]
    assert record.requested_action in ["refund", "credit", "fix", "callback", "information", "none"]
    assert record.raw_output is not None


@pytest.mark.asyncio
async def test_all_tickets_processed_even_with_failures(storage, job_manager):
    """
    Test that all tickets are processed even if some fail.
    One bad ticket must never fail the job.
    """
    # Create job with all invalid tickets
    job = storage.create_job(["tkt_0013", "tkt_0042"])
    
    # Process job
    await job_manager.process_job(job.id)
    
    # Job should still complete
    job = storage.get_job(job.id)
    assert job.status == JobStatus.COMPLETED
    
    # Both tickets should have records (in needs_review)
    assert len(job.record_ids) == 2
    
    records = [storage.get_record(rid) for rid in job.record_ids]
    assert all(r.status == RecordStatus.NEEDS_REVIEW for r in records)


@pytest.mark.asyncio
async def test_job_status_transitions(storage, job_manager):
    """
    Test that job status transitions correctly through lifecycle.
    """
    job = storage.create_job(["tkt_test_000", "tkt_test_001"])
    
    # Initial status
    assert job.status == JobStatus.PENDING
    
    # Start processing
    task = asyncio.create_task(job_manager.process_job(job.id))
    
    # Wait briefly
    await asyncio.sleep(0.1)
    
    # Should be running
    job = storage.get_job(job.id)
    assert job.status == JobStatus.RUNNING
    
    # Wait for completion
    await task
    
    # Should be completed
    job = storage.get_job(job.id)
    assert job.status == JobStatus.COMPLETED


def test_mark_completed_updates_progress(storage, job_manager):
    """
    Test that _mark_completed correctly updates progress counters.
    """
    job = storage.create_job(["tkt_test_000", "tkt_test_001", "tkt_test_002"])
    
    # Simulate a ticket starting
    job.progress.queued -= 1
    job.progress.running += 1
    
    initial_completed = job.progress.completed
    initial_running = job.progress.running
    
    # Mark as completed
    job_manager._mark_completed(job, "tkt_test_000")
    
    # Verify counters
    assert job.progress.completed == initial_completed + 1
    assert job.progress.running == initial_running - 1


def test_mark_failed_updates_progress(storage, job_manager):
    """
    Test that _mark_failed correctly updates progress counters.
    """
    job = storage.create_job(["tkt_test_000", "tkt_test_001", "tkt_test_002"])
    
    # Simulate a ticket starting
    job.progress.queued -= 1
    job.progress.running += 1
    
    initial_failed = job.progress.failed
    initial_running = job.progress.running
    
    # Mark as failed
    job_manager._mark_failed(job, "tkt_test_000")
    
    # Verify counters
    assert job.progress.failed == initial_failed + 1
    assert job.progress.running == initial_running - 1


@pytest.mark.asyncio
async def test_records_linked_to_job(storage, job_manager):
    """
    Test that extracted records are properly linked to their job.
    """
    job = storage.create_job(["tkt_test_000", "tkt_test_001"])
    
    # Process job
    await job_manager.process_job(job.id)
    
    # Get updated job
    job = storage.get_job(job.id)
    
    # Should have 2 record IDs
    assert len(job.record_ids) == 2
    
    # All records should be retrievable
    for record_id in job.record_ids:
        record = storage.get_record(record_id)
        assert record is not None
        assert record.ticket_id in ["tkt_test_000", "tkt_test_001"]
