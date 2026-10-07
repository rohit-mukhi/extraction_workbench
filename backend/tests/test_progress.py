"""
Test progress tracking arithmetic.
Tests that job progress counters are accurate throughout processing.
"""
import pytest
import asyncio
from datetime import datetime

from models import Job, JobProgress, JobStatus, Ticket
from storage import Storage
from job_manager import JobManager


@pytest.fixture
def storage():
    """Create a storage instance with test tickets."""
    storage = Storage()
    # Create 10 test tickets
    for i in range(10):
        ticket_id = f"tkt_test_{i:03d}"
        storage.tickets[ticket_id] = Ticket(
            id=ticket_id,
            subject=f"Test ticket {i}",
            body=f"Test body for Zen Connect ticket {i}",
            channel="email",
            received_at="2026-08-04T11:56:28Z",
            from_email=f"test{i}@example.com",
            attachments=0
        )
    return storage


@pytest.fixture
def job_manager(storage):
    """Create a job manager instance."""
    return JobManager(storage, max_concurrent=3)


def test_job_progress_initialization():
    """
    Test that job progress is initialized correctly when job is created.
    """
    ticket_ids = ["tkt_001", "tkt_002", "tkt_003"]
    job = Job(ticket_ids=ticket_ids)
    
    # Verify initial progress
    assert job.progress.total == 3
    assert job.progress.queued == 3
    assert job.progress.running == 0
    assert job.progress.completed == 0
    assert job.progress.failed == 0
    assert job.status == JobStatus.PENDING


def test_job_progress_is_complete():
    """
    Test the is_complete() method logic.
    """
    progress = JobProgress(
        total=10,
        queued=0,
        running=0,
        completed=8,
        failed=2
    )
    
    # Should be complete when completed + failed = total
    assert progress.is_complete() is True
    
    # Not complete if still has running items
    progress.running = 1
    progress.completed = 7
    assert progress.is_complete() is False
    
    # Not complete if still has queued items
    progress.running = 0
    progress.queued = 1
    progress.completed = 7
    assert progress.is_complete() is False


def test_progress_arithmetic_manual():
    """
    Test progress arithmetic manually through state transitions.
    This pins the exact math that should happen during processing.
    """
    # Create job with 5 tickets
    job = Job(ticket_ids=["tkt_1", "tkt_2", "tkt_3", "tkt_4", "tkt_5"])
    
    # Initial state
    assert job.progress.total == 5
    assert job.progress.queued == 5
    assert job.progress.running == 0
    assert job.progress.completed == 0
    assert job.progress.failed == 0
    
    # Start processing first ticket
    job.progress.queued -= 1
    job.progress.running += 1
    assert job.progress.queued == 4
    assert job.progress.running == 1
    
    # Start second ticket (concurrent)
    job.progress.queued -= 1
    job.progress.running += 1
    assert job.progress.queued == 3
    assert job.progress.running == 2
    
    # First ticket completes
    job.progress.running -= 1
    job.progress.completed += 1
    assert job.progress.running == 1
    assert job.progress.completed == 1
    
    # Start third ticket
    job.progress.queued -= 1
    job.progress.running += 1
    assert job.progress.queued == 2
    assert job.progress.running == 2
    
    # Second ticket fails
    job.progress.running -= 1
    job.progress.failed += 1
    assert job.progress.running == 1
    assert job.progress.failed == 1
    
    # Continue processing...
    # Third completes
    job.progress.running -= 1
    job.progress.completed += 1
    assert job.progress.completed == 2
    
    # Start fourth
    job.progress.queued -= 1
    job.progress.running += 1
    
    # Fourth completes
    job.progress.running -= 1
    job.progress.completed += 1
    
    # Start fifth
    job.progress.queued -= 1
    job.progress.running += 1
    
    # Fifth completes
    job.progress.running -= 1
    job.progress.completed += 1
    
    # Final state
    assert job.progress.total == 5
    assert job.progress.queued == 0
    assert job.progress.running == 0
    assert job.progress.completed == 4
    assert job.progress.failed == 1
    
    # Verify invariant: total = completed + failed (when done)
    assert job.progress.completed + job.progress.failed == job.progress.total
    assert job.progress.is_complete() is True


def test_progress_invariant():
    """
    Test that progress counters always maintain the invariant:
    queued + running + completed + failed = total
    """
    job = Job(ticket_ids=["tkt_1", "tkt_2", "tkt_3"])
    
    # Helper to check invariant
    def check_invariant(progress):
        return (progress.queued + progress.running + 
                progress.completed + progress.failed == progress.total)
    
    # Initial state
    assert check_invariant(job.progress)
    
    # Simulate state transitions
    job.progress.queued -= 1
    job.progress.running += 1
    assert check_invariant(job.progress)
    
    job.progress.running -= 1
    job.progress.completed += 1
    assert check_invariant(job.progress)
    
    job.progress.queued -= 1
    job.progress.running += 1
    assert check_invariant(job.progress)
    
    job.progress.running -= 1
    job.progress.failed += 1
    assert check_invariant(job.progress)


@pytest.mark.asyncio
async def test_progress_during_actual_processing(storage, job_manager):
    """
    Test progress updates during actual job processing.
    This verifies the job_manager correctly updates progress.
    """
    # Create job with 3 tickets
    ticket_ids = ["tkt_test_000", "tkt_test_001", "tkt_test_002"]
    job = storage.create_job(ticket_ids)
    
    # Initial state
    assert job.progress.total == 3
    assert job.progress.queued == 3
    assert job.progress.completed == 0
    
    # Start processing in background
    task = asyncio.create_task(job_manager.process_job(job.id))
    
    # Wait a bit for processing to start
    await asyncio.sleep(0.1)
    
    # Check that job status changed
    job = storage.get_job(job.id)
    assert job.status == JobStatus.RUNNING
    
    # Wait for completion
    await task
    
    # Final state
    job = storage.get_job(job.id)
    assert job.status == JobStatus.COMPLETED
    assert job.progress.queued == 0
    assert job.progress.running == 0
    assert job.progress.completed + job.progress.failed == job.progress.total
    assert job.progress.is_complete() is True


def test_storage_job_creation_sets_progress(storage):
    """
    Test that storage.create_job properly initializes progress.
    """
    ticket_ids = ["tkt_test_000", "tkt_test_001", "tkt_test_002", "tkt_test_003"]
    job = storage.create_job(ticket_ids)
    
    assert job.progress.total == 4
    assert job.progress.queued == 4
    assert job.progress.running == 0
    assert job.progress.completed == 0
    assert job.progress.failed == 0


def test_job_completion_moment():
    """
    Test the exact moment when a job should flip to complete.
    This pins the completion logic.
    """
    job = Job(ticket_ids=["tkt_1", "tkt_2", "tkt_3"])
    
    # Not complete initially
    assert not job.progress.is_complete()
    
    # Process tickets
    job.progress.queued = 0
    job.progress.running = 2
    job.progress.completed = 1
    assert not job.progress.is_complete()  # Still has running
    
    # One more completes
    job.progress.running = 1
    job.progress.completed = 2
    assert not job.progress.is_complete()  # Still has 1 running
    
    # Last one completes
    job.progress.running = 0
    job.progress.completed = 3
    assert job.progress.is_complete()  # NOW it's complete
    
    # Also complete if some failed
    job.progress.completed = 2
    job.progress.failed = 1
    assert job.progress.is_complete()  # 2 + 1 = 3 (total)
