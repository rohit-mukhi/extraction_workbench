"""
Extraction Workbench Backend API
Main entry point for the FastAPI application.
"""
import os
import json
from fastapi import FastAPI, HTTPException, BackgroundTasks, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from typing import List, Optional
from datetime import datetime
import logging
from pydantic import ValidationError

from models import (
    Job,
    JobCreate,
    JobResponse,
    JobProgress,
    ExtractedRecord,
    RecordUpdate,
    Ticket
)
from storage import Storage
from job_manager import JobManager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Extraction Workbench API",
    description="API for ticket data extraction and review",
    version="1.0.0"
)

# Configure CORS
cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize storage and job manager
storage = Storage()
job_manager = JobManager(storage)


@app.on_event("startup")
async def startup_event():
    """Load tickets from JSONL file on startup."""
    logger.info("Starting Extraction Workbench API...")
    try:
        storage.load_tickets()
        logger.info(f"Loaded {len(storage.tickets)} tickets")
    except Exception as e:
        logger.error(f"Failed to load tickets: {e}")
        raise


@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "status": "running",
        "service": "Extraction Workbench API",
        "tickets_loaded": len(storage.tickets)
    }


@app.get("/api/tickets", response_model=List[Ticket])
async def get_tickets(
    limit: Optional[int] = None,
    search: Optional[str] = None
):
    """
    Get all tickets with optional filtering.
    
    Args:
        limit: Maximum number of tickets to return
        search: Search term to filter tickets by subject or body
    
    Returns:
        List of tickets
    """
    tickets = list(storage.tickets.values())
    
    # Apply search filter
    if search:
        search_lower = search.lower()
        tickets = [
            t for t in tickets
            if search_lower in t.subject.lower() or search_lower in t.body.lower()
        ]
    
    # Apply limit
    if limit:
        tickets = tickets[:limit]
    
    return tickets


@app.post("/api/upload-tickets")
async def upload_tickets(file: UploadFile = File(...)):
    """
    Upload a JSONL file containing tickets.
    Validates format and adds new tickets to the system.
    Returns count of tickets added.
    """
    if not file.filename or not file.filename.endswith('.jsonl'):
        raise HTTPException(
            status_code=400,
            detail="File must be a JSONL file (.jsonl extension)"
        )
    
    try:
        # Read file content
        content = await file.read()
        content_str = content.decode('utf-8')
        
        # Parse JSONL
        new_tickets = []
        for line_num, line in enumerate(content_str.strip().split('\n'), 1):
            if not line.strip():
                continue
            
            try:
                ticket_data = json.loads(line)
                # Validate required fields
                required_fields = ['id', 'subject', 'body', 'from_email', 'received_at', 'channel']
                missing = [f for f in required_fields if f not in ticket_data]
                if missing:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Line {line_num}: Missing required fields: {', '.join(missing)}"
                    )
                
                # Create Ticket object
                ticket = Ticket(**ticket_data)
                new_tickets.append(ticket)
                
            except json.JSONDecodeError as e:
                raise HTTPException(
                    status_code=400,
                    detail=f"Line {line_num}: Invalid JSON - {str(e)}"
                )
            except ValidationError as e:
                raise HTTPException(
                    status_code=400,
                    detail=f"Line {line_num}: Validation error - {str(e)}"
                )
        
        if not new_tickets:
            raise HTTPException(
                status_code=400,
                detail="No valid tickets found in file"
            )
        
        # Add tickets to storage
        added_count = 0
        for ticket in new_tickets:
            if ticket.id not in storage.tickets:
                storage.tickets[ticket.id] = ticket
                added_count += 1
        
        storage._save_to_disk()
        
        logger.info(f"Uploaded {added_count} new tickets from {file.filename}")
        
        return {
            "message": f"Successfully uploaded {added_count} new tickets",
            "total_tickets": len(storage.tickets),
            "added": added_count,
            "skipped": len(new_tickets) - added_count
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading tickets: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process file: {str(e)}"
        )


@app.post("/api/jobs", response_model=JobResponse, status_code=202)
async def create_job(job_create: JobCreate, background_tasks: BackgroundTasks):
    """
    Create a new extraction job.
    
    Args:
        job_create: Job creation request with ticket IDs
        background_tasks: FastAPI background tasks
    
    Returns:
        Job response with job ID
    """
    # Validate ticket IDs exist
    invalid_ids = [
        tid for tid in job_create.ticket_ids
        if tid not in storage.tickets
    ]
    
    if invalid_ids:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid ticket IDs: {invalid_ids}"
        )
    
    # Create job
    job = storage.create_job(job_create.ticket_ids)
    logger.info(f"Created job {job.id} with {len(job_create.ticket_ids)} tickets")
    
    # Start processing in background
    background_tasks.add_task(job_manager.process_job, job.id)
    
    return JobResponse(job_id=job.id, status=job.status)


@app.get("/api/jobs/{job_id}", response_model=Job)
async def get_job(job_id: str):
    """
    Get job status and progress.
    
    Args:
        job_id: Job ID
    
    Returns:
        Job object with current status and progress
    """
    job = storage.get_job(job_id)
    
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    
    return job


@app.get("/api/jobs/{job_id}/results", response_model=List[ExtractedRecord])
async def get_job_results(job_id: str):
    """
    Get extraction results for a job.
    
    Args:
        job_id: Job ID
    
    Returns:
        List of extracted records
    """
    job = storage.get_job(job_id)
    
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    
    # Get all records for this job
    records = [
        storage.get_record(record_id)
        for record_id in job.record_ids
    ]
    
    # Filter out None values (shouldn't happen, but defensive)
    records = [r for r in records if r is not None]
    
    # Sort: needs_review first, then by ticket_id
    records.sort(
        key=lambda r: (
            0 if r.status == "needs_review" else 1,
            r.ticket_id
        )
    )
    
    return records


@app.patch("/api/records/{record_id}", response_model=ExtractedRecord)
async def update_record(record_id: str, update: RecordUpdate):
    """
    Update a record field with human correction.
    
    Args:
        record_id: Record ID
        update: Field update with validation
    
    Returns:
        Updated record
    """
    record = storage.get_record(record_id)
    
    if not record:
        raise HTTPException(status_code=404, detail=f"Record {record_id} not found")
    
    try:
        updated_record = storage.update_record(record_id, update)
        logger.info(f"Updated record {record_id}: {update.field} = {update.value}")
        return updated_record
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/jobs/{job_id}/export.csv")
async def export_job_csv(job_id: str):
    """
    Export job results as CSV.
    
    Args:
        job_id: Job ID
    
    Returns:
        CSV file download
    """
    job = storage.get_job(job_id)
    
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    
    # Get all records
    records = [
        storage.get_record(record_id)
        for record_id in job.record_ids
    ]
    records = [r for r in records if r is not None]
    
    if not records:
        raise HTTPException(status_code=404, detail="No records found for this job")
    
    # Generate CSV content
    import csv
    import io
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write header
    writer.writerow([
        "ticket_id",
        "company",
        "product",
        "category",
        "severity",
        "requested_action",
        "refund_amount",
        "deadline",
        "escalated",
        "status",
        "human_edited"
    ])
    
    # Write data
    for record in records:
        writer.writerow([
            record.ticket_id,
            record.company,
            record.product,
            record.category,
            record.severity,
            record.requested_action,
            record.refund_amount if record.refund_amount is not None else "",
            record.deadline.isoformat() if record.deadline else "",
            record.escalated,
            record.status,
            "yes" if record.human_edited_fields else "no"
        ])
    
    # Return as streaming response
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=job_{job_id}_export.csv"
        }
    )


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
