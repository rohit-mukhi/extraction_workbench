"""
Job manager for background processing of extraction jobs.
Handles concurrent processing with retry logic and validation.
"""
import asyncio
import logging
from typing import Optional
from datetime import datetime
from pydantic import ValidationError

from models import (
    ExtractedRecord,
    JobStatus,
    RecordStatus,
    Ticket
)
from storage import Storage
from mock_provider import MockAIProvider


logger = logging.getLogger(__name__)


class JobManager:
    """
    Manages background job processing with concurrency control.
    """
    
    def __init__(self, storage: Storage, max_concurrent: int = 5):
        """
        Initialize job manager.
        
        Args:
            storage: Storage instance
            max_concurrent: Maximum concurrent extractions
        """
        self.storage = storage
        self.max_concurrent = max_concurrent
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.ai_provider = MockAIProvider()
    
    async def process_job(self, job_id: str) -> None:
        """
        Process all tickets in a job with concurrent extraction.
        
        Args:
            job_id: Job ID to process
        """
        job = self.storage.get_job(job_id)
        if not job:
            logger.error(f"Job {job_id} not found")
            return
        
        logger.info(f"Starting job {job_id} with {len(job.ticket_ids)} tickets")
        
        # Update job status to running
        self.storage.update_job_status(job_id, JobStatus.RUNNING)
        
        try:
            # Create tasks for all tickets
            tasks = []
            for ticket_id in job.ticket_ids:
                task = asyncio.create_task(
                    self._process_ticket(job_id, ticket_id)
                )
                tasks.append(task)
            
            # Wait for all tasks to complete
            await asyncio.gather(*tasks, return_exceptions=True)
            
            # Update job status to completed
            self.storage.update_job_status(job_id, JobStatus.COMPLETED)
            logger.info(f"Job {job_id} completed successfully")
        
        except Exception as e:
            logger.error(f"Job {job_id} failed: {e}")
            self.storage.update_job_status(job_id, JobStatus.FAILED)
            job.error_message = str(e)
    
    async def _process_ticket(self, job_id: str, ticket_id: str) -> None:
        """
        Process a single ticket with retry logic.
        
        Args:
            job_id: Job ID
            ticket_id: Ticket ID to process
        """
        # Acquire semaphore to limit concurrency
        async with self.semaphore:
            job = self.storage.get_job(job_id)
            if not job:
                return
            
            # Check if job was cancelled
            if job.cancelled:
                logger.info(f"Job {job_id} was cancelled, skipping ticket {ticket_id}")
                self._mark_skipped(job, ticket_id)
                return
            
            # Update progress: queued -> running
            job.progress.queued -= 1
            job.progress.running += 1
            job.updated_at = datetime.utcnow()
            
            try:
                # Get ticket
                ticket = self.storage.get_ticket(ticket_id)
                if not ticket:
                    logger.error(f"Ticket {ticket_id} not found")
                    self._mark_failed(job, ticket_id)
                    return
                
                # First extraction attempt
                logger.info(f"Processing ticket {ticket_id} (attempt 1)")
                record = await self._extract_with_validation(ticket)
                
                if record:
                    # Success on first attempt
                    self.storage.create_record(record)
                    self._mark_completed(job, ticket_id)
                    logger.info(f"Ticket {ticket_id} extracted successfully")
                else:
                    # First attempt failed, try retry with validation error
                    logger.warning(f"First attempt failed for {ticket_id}, retrying...")
                    record = await self._retry_extraction(ticket)
                    
                    if record:
                        # Success on retry
                        self.storage.create_record(record)
                        self._mark_completed(job, ticket_id)
                        logger.info(f"Ticket {ticket_id} extracted successfully on retry")
                    else:
                        # Both attempts failed, mark needs_review
                        logger.warning(f"Both attempts failed for {ticket_id}, marking needs_review")
                        needs_review_record = self._create_needs_review_record(ticket)
                        self.storage.create_record(needs_review_record)
                        self._mark_completed(job, ticket_id)
            
            except Exception as e:
                logger.error(f"Error processing ticket {ticket_id}: {e}")
                self._mark_failed(job, ticket_id)
    
    async def _extract_with_validation(
        self,
        ticket: Ticket,
        validation_error: Optional[str] = None
    ) -> Optional[ExtractedRecord]:
        """
        Extract data and validate against schema.
        
        Args:
            ticket: Ticket to extract
            validation_error: Previous validation error (for retry)
        
        Returns:
            ExtractedRecord if valid, None if validation fails
        """
        try:
            # Call AI provider
            raw_output = await self.ai_provider.extract(ticket, validation_error)
            
            # Validate against Pydantic model
            record = ExtractedRecord(
                ticket_id=ticket.id,
                company=raw_output.get("company", ""),
                product=raw_output.get("product", ""),
                category=raw_output.get("category", ""),
                severity=raw_output.get("severity", ""),
                requested_action=raw_output.get("requested_action", ""),
                refund_amount=raw_output.get("refund_amount"),
                deadline=raw_output.get("deadline"),
                escalated=raw_output.get("escalated", False),
                confidence_scores=raw_output.get("confidence_scores", {}),
                status=RecordStatus.COMPLETED
            )
            
            return record
        
        except ValidationError as e:
            logger.warning(f"Validation failed for ticket {ticket.id}: {e}")
            return None
        
        except Exception as e:
            logger.error(f"Extraction failed for ticket {ticket.id}: {e}")
            return None
    
    async def _retry_extraction(self, ticket: Ticket) -> Optional[ExtractedRecord]:
        """
        Retry extraction with validation error feedback.
        
        Args:
            ticket: Ticket to extract
        
        Returns:
            ExtractedRecord if valid, None if validation fails again
        """
        # First, get the validation error from the first attempt
        try:
            raw_output = await self.ai_provider.extract(ticket, None)
            
            # Try to validate to get the error
            try:
                ExtractedRecord(
                    ticket_id=ticket.id,
                    company=raw_output.get("company", ""),
                    product=raw_output.get("product", ""),
                    category=raw_output.get("category", ""),
                    severity=raw_output.get("severity", ""),
                    requested_action=raw_output.get("requested_action", ""),
                    refund_amount=raw_output.get("refund_amount"),
                    deadline=raw_output.get("deadline"),
                    escalated=raw_output.get("escalated", False)
                )
            except ValidationError as e:
                validation_error = str(e)
        except Exception:
            validation_error = "Unknown validation error"
        
        # Now retry with the error feedback
        return await self._extract_with_validation(ticket, validation_error)
    
    def _create_needs_review_record(self, ticket: Ticket) -> ExtractedRecord:
        """
        Create a needs_review record when extraction fails twice.
        
        Args:
            ticket: Original ticket
        
        Returns:
            ExtractedRecord with needs_review status
        """
        # Create record with placeholder/default values
        record = ExtractedRecord(
            ticket_id=ticket.id,
            company="Unknown",
            product="Zen Connect",  # Default product
            category="how_to",  # Default category
            severity="medium",  # Default severity
            requested_action="information",  # Default action
            refund_amount=None,
            deadline=None,
            escalated=False,
            confidence_scores={},
            status=RecordStatus.NEEDS_REVIEW,
            raw_output="Extraction failed after 2 attempts"
        )
        
        return record
    
    def _mark_completed(self, job, ticket_id: str) -> None:
        """
        Mark a ticket as completed in job progress.
        
        Args:
            job: Job object
            ticket_id: Ticket ID
        """
        job.progress.running -= 1
        job.progress.completed += 1
        job.updated_at = datetime.utcnow()
        
        logger.debug(f"Progress for job {job.id}: {job.progress.completed}/{job.progress.total}")
    
    def _mark_failed(self, job, ticket_id: str) -> None:
        """
        Mark a ticket as failed in job progress and create a needs_review record.
        
        Args:
            job: Job object
            ticket_id: Ticket ID
        """
        job.progress.running -= 1
        job.progress.failed += 1
        job.updated_at = datetime.utcnow()
        
        # Create a needs_review record for the failed ticket
        ticket = self.storage.get_ticket(ticket_id)
        if ticket:
            needs_review_record = self._create_needs_review_record(ticket)
            self.storage.create_record(needs_review_record)
        
        logger.warning(f"Ticket {ticket_id} marked as failed in job {job.id}")

    def _mark_skipped(self, job, ticket_id: str) -> None:
        """
        Mark a ticket as skipped when job is cancelled.
        
        Args:
            job: Job object
            ticket_id: Ticket ID
        """
        job.progress.queued -= 1
        job.updated_at = datetime.utcnow()
        
        logger.info(f"Ticket {ticket_id} skipped due to job cancellation")
