"""
Test validation and retry logic.
Tests that malformed AI output triggers retry mechanism.
"""
import pytest
import asyncio
from datetime import datetime
from pydantic import ValidationError

from models import ExtractedRecord, Ticket, RecordStatus
from mock_provider import MockAIProvider
from storage import Storage
from job_manager import JobManager


@pytest.fixture
def mock_provider():
    """Create a mock AI provider instance."""
    return MockAIProvider()


@pytest.fixture
def storage():
    """Create a storage instance with test data."""
    storage = Storage()
    # Add test tickets
    storage.tickets = {
        "tkt_test_valid": Ticket(
            id="tkt_test_valid",
            subject="Test ticket",
            body="Test body for Zen Connect",
            channel="email",
            received_at="2026-08-04T11:56:28Z",
            from_email="test@example.com",
            attachments=0
        ),
        "tkt_0013": Ticket(
            id="tkt_0013",
            subject="Invoice query",
            body="We were billed twice",
            channel="chat",
            received_at="2026-08-07T13:22:10Z",
            from_email="m.feld@panacea.com",
            attachments=0
        )
    }
    return storage


def test_valid_extraction_passes_validation(mock_provider):
    """
    Test that valid AI output passes Pydantic validation.
    """
    # Create a valid output
    valid_output = {
        "company": "Example Corp",
        "product": "Zen Connect",
        "category": "billing",
        "severity": "medium",
        "requested_action": "refund",
        "refund_amount": 100.0,
        "deadline": None,
        "escalated": False,
        "confidence_scores": {"company": 0.95}
    }
    
    # Should not raise ValidationError
    try:
        record = ExtractedRecord(
            ticket_id="tkt_test_valid",
            **valid_output
        )
        assert record.company == "Example Corp"
        assert record.product == "Zen Connect"
        assert record.status == RecordStatus.COMPLETED
    except ValidationError:
        pytest.fail("Valid output should not raise ValidationError")


def test_invalid_output_raises_validation_error():
    """
    Test that invalid AI output raises Pydantic ValidationError.
    This is the first step in the retry mechanism.
    """
    # Create invalid output (wrong enum value)
    invalid_output = {
        "company": "Example Corp",
        "product": "Zen InvalidProduct",  # Invalid enum value
        "category": "billing",
        "severity": "medium",
        "requested_action": "refund",
        "refund_amount": 100.0,
        "deadline": None,
        "escalated": False
    }
    
    # Should raise ValidationError
    with pytest.raises(ValidationError) as exc_info:
        record = ExtractedRecord(
            ticket_id="tkt_test_valid",
            **invalid_output
        )
    
    # Verify error details
    error = exc_info.value
    assert "product" in str(error)
    assert len(error.errors()) > 0


@pytest.mark.asyncio
async def test_retry_happens_on_validation_failure(mock_provider, storage):
    """
    Test that retry logic is triggered when validation fails.
    This is the core requirement: feed validation error back to AI and retry.
    """
    # Use tkt_0013 which is configured to return invalid data on first attempt
    ticket = storage.get_ticket("tkt_0013")
    
    # First attempt - should return invalid data
    first_output = await mock_provider.extract(ticket, validation_error=None)
    
    # Try to validate first output - should fail
    with pytest.raises(ValidationError) as exc_info:
        ExtractedRecord(
            ticket_id=ticket.id,
            **first_output
        )
    
    # Capture the validation error
    validation_error = str(exc_info.value)
    assert len(validation_error) > 0
    
    # Retry with validation error feedback
    # This simulates the retry mechanism in job_manager
    second_output = await mock_provider.extract(ticket, validation_error=validation_error)
    
    # Second attempt should succeed (mock provider fixes it)
    try:
        record = ExtractedRecord(
            ticket_id=ticket.id,
            **second_output
        )
        # Verify second attempt produced valid record
        assert record.company is not None
        assert record.product in ["Zen Orchestrator", "Zen Studio", "Zen Connect", "Zen Insights", "Zen Vault"]
        assert record.status == RecordStatus.COMPLETED
    except ValidationError:
        pytest.fail("Second attempt should succeed after retry")
    
    # Verify retry count was tracked
    assert mock_provider.retry_count.get("tkt_0013", 0) >= 1


@pytest.mark.asyncio
async def test_extraction_with_validation_flow(mock_provider, storage):
    """
    Test the complete extraction-validation flow.
    Simulates what job_manager does: extract → validate → retry if needed.
    """
    ticket = storage.get_ticket("tkt_test_valid")
    
    # Simulate job_manager._extract_with_validation
    raw_output = await mock_provider.extract(ticket, validation_error=None)
    
    try:
        # Attempt to create validated record
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
        
        # Assertions
        assert record is not None
        assert record.ticket_id == "tkt_test_valid"
        assert record.status == RecordStatus.COMPLETED
        assert isinstance(record.confidence_scores, dict)
        
    except ValidationError as e:
        # If validation fails, this is where retry would be triggered
        pytest.fail(f"Validation failed for valid ticket: {e}")


def test_negative_refund_amount_validation():
    """
    Test that negative refund amounts are rejected by validation.
    """
    invalid_output = {
        "company": "Example Corp",
        "product": "Zen Connect",
        "category": "billing",
        "severity": "medium",
        "requested_action": "refund",
        "refund_amount": -100.0,  # Invalid: negative
        "deadline": None,
        "escalated": False
    }
    
    with pytest.raises(ValidationError) as exc_info:
        record = ExtractedRecord(
            ticket_id="tkt_test",
            **invalid_output
        )
    
    error = exc_info.value
    assert "refund_amount" in str(error)


def test_empty_company_validation():
    """
    Test that empty company name is rejected by validation.
    """
    invalid_output = {
        "company": "",  # Invalid: empty string
        "product": "Zen Connect",
        "category": "billing",
        "severity": "medium",
        "requested_action": "refund",
        "refund_amount": 100.0,
        "deadline": None,
        "escalated": False
    }
    
    with pytest.raises(ValidationError) as exc_info:
        record = ExtractedRecord(
            ticket_id="tkt_test",
            **invalid_output
        )
    
    error = exc_info.value
    assert "company" in str(error)
