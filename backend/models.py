"""
Pydantic models for the Extraction Workbench.
Defines all data structures and validation schemas.
"""
from pydantic import BaseModel, Field, validator
from typing import Optional, List, Set, Dict, Literal
from datetime import datetime, date
from enum import Enum
import uuid


# Enums for constrained fields
class ProductType(str, Enum):
    """Valid product types."""
    ZEN_ORCHESTRATOR = "Zen Orchestrator"
    ZEN_STUDIO = "Zen Studio"
    ZEN_CONNECT = "Zen Connect"
    ZEN_INSIGHTS = "Zen Insights"
    ZEN_VAULT = "Zen Vault"


class CategoryType(str, Enum):
    """Valid ticket categories."""
    OUTAGE = "outage"
    BILLING = "billing"
    BUG = "bug"
    FEATURE_REQUEST = "feature_request"
    HOW_TO = "how_to"
    CHURN_RISK = "churn_risk"


class SeverityLevel(str, Enum):
    """Valid severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RequestedAction(str, Enum):
    """Valid requested actions."""
    REFUND = "refund"
    CREDIT = "credit"
    FIX = "fix"
    CALLBACK = "callback"
    INFORMATION = "information"
    NONE = "none"


class RecordStatus(str, Enum):
    """Status of an extracted record."""
    COMPLETED = "completed"
    NEEDS_REVIEW = "needs_review"
    FAILED = "failed"


class JobStatus(str, Enum):
    """Status of a job."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


# Input ticket model
class Ticket(BaseModel):
    """Raw ticket from tickets.jsonl."""
    id: str
    subject: str
    body: str
    channel: str
    received_at: str
    from_email: str
    attachments: int

    class Config:
        json_schema_extra = {
            "example": {
                "id": "tkt_0001",
                "subject": "Question about setup",
                "body": "Quick one - does Zen Orchestrator count a retried run?",
                "channel": "web_form",
                "received_at": "2026-08-04T11:56:28Z",
                "from_email": "user@example.com",
                "attachments": 0
            }
        }


# Extracted record model
class ExtractedRecord(BaseModel):
    """
    Structured record extracted from a ticket.
    This is validated against the schema requirements.
    """
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    ticket_id: str
    
    # Required fields
    company: str = Field(..., min_length=1, description="Company name extracted from email or ticket")
    product: ProductType = Field(..., description="Product mentioned in ticket")
    category: CategoryType = Field(..., description="Ticket category")
    severity: SeverityLevel = Field(..., description="Severity level")
    requested_action: RequestedAction = Field(..., description="Action requested by customer")
    
    # Optional fields
    refund_amount: Optional[float] = Field(None, ge=0, description="Refund amount in USD")
    deadline: Optional[date] = Field(None, description="Deadline mentioned in ticket")
    
    # Required boolean
    escalated: bool = Field(default=False, description="Whether ticket is escalated")
    
    # Metadata fields
    confidence_scores: Dict[str, float] = Field(
        default_factory=dict,
        description="Confidence score per field (0.0 to 1.0)"
    )
    human_edited_fields: Set[str] = Field(
        default_factory=set,
        description="Set of field names that were edited by a human"
    )
    status: RecordStatus = Field(
        default=RecordStatus.COMPLETED,
        description="Status of the record"
    )
    raw_output: Optional[str] = Field(
        None,
        description="Raw AI output if validation failed"
    )
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    @validator('refund_amount')
    def validate_refund_amount(cls, v):
        """Validate refund amount is positive."""
        if v is not None and v < 0:
            raise ValueError("Refund amount must be non-negative")
        return v

    class Config:
        use_enum_values = True
        json_schema_extra = {
            "example": {
                "id": "rec_123",
                "ticket_id": "tkt_0001",
                "company": "Castlerock Mining",
                "product": "Zen Orchestrator",
                "category": "how_to",
                "severity": "low",
                "requested_action": "information",
                "refund_amount": None,
                "deadline": None,
                "escalated": False,
                "confidence_scores": {"company": 0.95, "product": 0.99},
                "human_edited_fields": [],
                "status": "completed"
            }
        }


# Job progress tracking
class JobProgress(BaseModel):
    """Progress statistics for a job."""
    total: int = 0
    queued: int = 0
    running: int = 0
    completed: int = 0
    failed: int = 0

    def is_complete(self) -> bool:
        """Check if job is complete."""
        return (self.completed + self.failed) == self.total


# Job model
class Job(BaseModel):
    """Extraction job containing multiple tickets."""
    id: str = Field(default_factory=lambda: f"job_{uuid.uuid4().hex[:8]}")
    ticket_ids: List[str]
    record_ids: List[str] = Field(default_factory=list)
    status: JobStatus = Field(default=JobStatus.PENDING)
    progress: JobProgress = Field(default_factory=JobProgress)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    error_message: Optional[str] = None

    def model_post_init(self, __context):
        """Initialize progress after model creation."""
        if self.progress.total == 0:
            self.progress.total = len(self.ticket_ids)
            self.progress.queued = len(self.ticket_ids)


# API request/response models
class JobCreate(BaseModel):
    """Request to create a new job."""
    ticket_ids: List[str] = Field(..., min_length=1, description="List of ticket IDs to process")

    @validator('ticket_ids')
    def validate_ticket_ids(cls, v):
        """Validate ticket IDs list is not empty and has no duplicates."""
        if not v:
            raise ValueError("ticket_ids cannot be empty")
        if len(v) != len(set(v)):
            raise ValueError("ticket_ids must be unique")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "ticket_ids": ["tkt_0001", "tkt_0002", "tkt_0003"]
            }
        }


class JobResponse(BaseModel):
    """Response after creating a job."""
    job_id: str
    status: JobStatus

    class Config:
        json_schema_extra = {
            "example": {
                "job_id": "job_abc123",
                "status": "pending"
            }
        }


class RecordUpdate(BaseModel):
    """Request to update a record field."""
    field: str = Field(..., description="Field name to update")
    value: Optional[str | float | bool | date] = Field(..., description="New value for the field")

    @validator('field')
    def validate_field(cls, v):
        """Validate field name is a valid record field."""
        allowed_fields = {
            'company', 'product', 'category', 'severity',
            'requested_action', 'refund_amount', 'deadline', 'escalated'
        }
        if v not in allowed_fields:
            raise ValueError(f"Field must be one of: {allowed_fields}")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "field": "severity",
                "value": "high"
            }
        }


# Model for AI provider output (before validation)
class ExtractionOutput(BaseModel):
    """Raw output from AI provider before validation."""
    company: str
    product: str
    category: str
    severity: str
    requested_action: str
    refund_amount: Optional[float] = None
    deadline: Optional[str] = None
    escalated: bool = False
    confidence_scores: Optional[Dict[str, float]] = None

    class Config:
        json_schema_extra = {
            "example": {
                "company": "Castlerock Mining",
                "product": "Zen Orchestrator",
                "category": "how_to",
                "severity": "low",
                "requested_action": "information",
                "refund_amount": None,
                "deadline": None,
                "escalated": False,
                "confidence_scores": {"company": 0.95}
            }
        }
