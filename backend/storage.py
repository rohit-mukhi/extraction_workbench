"""
In-memory storage layer for tickets, jobs, and records.
Loads tickets from tickets.jsonl and manages all data in memory.
"""
import json
import os
from typing import Dict, Optional, List
from datetime import datetime, date
from pathlib import Path

from models import (
    Ticket,
    Job,
    ExtractedRecord,
    RecordUpdate,
    JobStatus,
    RecordStatus,
    ProductType,
    CategoryType,
    SeverityLevel,
    RequestedAction
)


class Storage:
    """In-memory storage for all data."""
    
    def __init__(self):
        """Initialize empty storage."""
        self.tickets: Dict[str, Ticket] = {}
        self.jobs: Dict[str, Job] = {}
        self.records: Dict[str, ExtractedRecord] = {}
    
    def load_tickets(self) -> None:
        """
        Load tickets from tickets.jsonl file.
        Looks for the file in ../context/tickets.jsonl relative to backend directory.
        """
        # Get path to tickets.jsonl
        backend_dir = Path(__file__).parent
        tickets_path = backend_dir.parent / "context" / "tickets.jsonl"
        
        if not tickets_path.exists():
            raise FileNotFoundError(f"Tickets file not found at {tickets_path}")
        
        # Load tickets from JSONL
        loaded_count = 0
        with open(tickets_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                
                try:
                    ticket_data = json.loads(line)
                    ticket = Ticket(**ticket_data)
                    self.tickets[ticket.id] = ticket
                    loaded_count += 1
                except Exception as e:
                    print(f"Warning: Failed to load ticket from line: {e}")
                    continue
        
        print(f"Loaded {loaded_count} tickets from {tickets_path}")
    
    def get_ticket(self, ticket_id: str) -> Optional[Ticket]:
        """Get a ticket by ID."""
        return self.tickets.get(ticket_id)
    
    def create_job(self, ticket_ids: List[str]) -> Job:
        """
        Create a new job.
        
        Args:
            ticket_ids: List of ticket IDs to process
        
        Returns:
            Created job
        """
        job = Job(ticket_ids=ticket_ids)
        self.jobs[job.id] = job
        return job
    
    def get_job(self, job_id: str) -> Optional[Job]:
        """Get a job by ID."""
        return self.jobs.get(job_id)
    
    def update_job_status(self, job_id: str, status: JobStatus) -> None:
        """Update job status."""
        job = self.jobs.get(job_id)
        if job:
            job.status = status
            job.updated_at = datetime.utcnow()
    
    def create_record(self, record: ExtractedRecord) -> ExtractedRecord:
        """
        Store an extracted record.
        
        Args:
            record: Extracted record to store
        
        Returns:
            Stored record
        """
        self.records[record.id] = record
        
        # Add record ID to the job's record list
        for job in self.jobs.values():
            if record.ticket_id in job.ticket_ids:
                if record.id not in job.record_ids:
                    job.record_ids.append(record.id)
                break
        
        return record
    
    def get_record(self, record_id: str) -> Optional[ExtractedRecord]:
        """Get a record by ID."""
        return self.records.get(record_id)
    
    def update_record(self, record_id: str, update: RecordUpdate) -> ExtractedRecord:
        """
        Update a record field with human correction.
        
        Args:
            record_id: Record ID
            update: Field update
        
        Returns:
            Updated record
        
        Raises:
            ValueError: If validation fails
        """
        record = self.records.get(record_id)
        if not record:
            raise ValueError(f"Record {record_id} not found")
        
        # Validate and convert value based on field type
        field_name = update.field
        value = update.value
        
        try:
            # Type validation and conversion
            if field_name == "company":
                if not isinstance(value, str) or not value.strip():
                    raise ValueError("company must be a non-empty string")
                record.company = value.strip()
            
            elif field_name == "product":
                # Validate against ProductType enum
                try:
                    record.product = ProductType(value)
                except ValueError:
                    valid_products = [p.value for p in ProductType]
                    raise ValueError(f"product must be one of: {valid_products}")
            
            elif field_name == "category":
                # Validate against CategoryType enum
                try:
                    record.category = CategoryType(value)
                except ValueError:
                    valid_categories = [c.value for c in CategoryType]
                    raise ValueError(f"category must be one of: {valid_categories}")
            
            elif field_name == "severity":
                # Validate against SeverityLevel enum
                try:
                    record.severity = SeverityLevel(value)
                except ValueError:
                    valid_severities = [s.value for s in SeverityLevel]
                    raise ValueError(f"severity must be one of: {valid_severities}")
            
            elif field_name == "requested_action":
                # Validate against RequestedAction enum
                try:
                    record.requested_action = RequestedAction(value)
                except ValueError:
                    valid_actions = [a.value for a in RequestedAction]
                    raise ValueError(f"requested_action must be one of: {valid_actions}")
            
            elif field_name == "refund_amount":
                # Validate refund amount
                if value is None or value == "" or value == "null":
                    record.refund_amount = None
                else:
                    try:
                        amount = float(value)
                        if amount < 0:
                            raise ValueError("refund_amount must be non-negative")
                        record.refund_amount = amount
                    except (ValueError, TypeError):
                        raise ValueError("refund_amount must be a valid number")
            
            elif field_name == "deadline":
                # Validate deadline
                if value is None or value == "" or value == "null":
                    record.deadline = None
                else:
                    if isinstance(value, date):
                        record.deadline = value
                    elif isinstance(value, str):
                        # Try to parse date string
                        try:
                            record.deadline = date.fromisoformat(value)
                        except ValueError:
                            raise ValueError("deadline must be a valid ISO date (YYYY-MM-DD)")
                    else:
                        raise ValueError("deadline must be a date string or null")
            
            elif field_name == "escalated":
                # Validate boolean
                if isinstance(value, bool):
                    record.escalated = value
                elif isinstance(value, str):
                    if value.lower() in ["true", "1", "yes"]:
                        record.escalated = True
                    elif value.lower() in ["false", "0", "no"]:
                        record.escalated = False
                    else:
                        raise ValueError("escalated must be true or false")
                else:
                    raise ValueError("escalated must be a boolean")
            
            else:
                raise ValueError(f"Unknown field: {field_name}")
            
            # Mark field as human-edited
            record.human_edited_fields.add(field_name)
            
            # Update timestamp
            record.updated_at = datetime.utcnow()
            
            # If record was in needs_review, change to completed after edit
            if record.status == RecordStatus.NEEDS_REVIEW:
                record.status = RecordStatus.COMPLETED
            
            return record
        
        except Exception as e:
            raise ValueError(f"Validation failed for {field_name}: {str(e)}")
    
    def get_records_by_job(self, job_id: str) -> List[ExtractedRecord]:
        """
        Get all records for a job.
        
        Args:
            job_id: Job ID
        
        Returns:
            List of records for the job
        """
        job = self.jobs.get(job_id)
        if not job:
            return []
        
        records = []
        for record_id in job.record_ids:
            record = self.records.get(record_id)
            if record:
                records.append(record)
        
        return records
    
    def clear_all(self) -> None:
        """Clear all data (useful for testing)."""
        self.tickets.clear()
        self.jobs.clear()
        self.records.clear()
