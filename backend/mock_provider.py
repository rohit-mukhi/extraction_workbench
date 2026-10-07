"""
Mock AI provider for ticket data extraction.
Uses rule-based logic to extract structured data from tickets.
Deterministic and includes artificial delays for observable progress.
"""
import re
import asyncio
import random
from typing import Dict, Any, Optional
from datetime import date, timedelta

from models import Ticket, ExtractionOutput


class MockAIProvider:
    """
    Mock AI provider that extracts data using simple rules.
    Deterministic for the same input, with intentional failures for testing.
    """
    
    # Tickets that should return invalid data to test retry logic
    INVALID_TICKETS = ["tkt_0013", "tkt_0042", "tkt_0089"]
    
    def __init__(self):
        """Initialize the mock provider."""
        self.retry_count: Dict[str, int] = {}
    
    async def extract(
        self,
        ticket: Ticket,
        validation_error: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Extract structured data from a ticket.
        
        Args:
            ticket: Input ticket
            validation_error: Previous validation error (for retry)
        
        Returns:
            Extracted data dictionary
        """
        # Artificial delay to simulate AI processing
        delay = self._get_delay(ticket.id)
        await asyncio.sleep(delay)
        
        # Track retry attempts
        retry_attempt = self.retry_count.get(ticket.id, 0)
        
        # For specific tickets, return invalid data on first attempt
        if ticket.id in self.INVALID_TICKETS and retry_attempt == 0:
            self.retry_count[ticket.id] = retry_attempt + 1
            return self._generate_invalid_output(ticket)
        
        # For retry attempts, try to fix based on validation error
        if validation_error:
            self.retry_count[ticket.id] = retry_attempt + 1
            # On second attempt, return valid data
            return self._extract_data(ticket)
        
        # Normal extraction
        return self._extract_data(ticket)
    
    def _get_delay(self, ticket_id: str) -> float:
        """
        Get deterministic delay based on ticket ID.
        
        Args:
            ticket_id: Ticket ID
        
        Returns:
            Delay in seconds (0.5 to 2.0)
        """
        # Use ticket ID hash for deterministic random delay
        seed = hash(ticket_id) % 1000
        random.seed(seed)
        return random.uniform(0.5, 2.0)
    
    def _extract_data(self, ticket: Ticket) -> Dict[str, Any]:
        """
        Extract structured data using rule-based logic.
        
        Args:
            ticket: Input ticket
        
        Returns:
            Extracted data dictionary
        """
        body_lower = ticket.body.lower()
        subject_lower = ticket.subject.lower()
        combined = (subject_lower + " " + body_lower).strip()
        
        # Extract company from email domain
        company = self._extract_company(ticket.from_email, ticket.body)
        
        # Extract product
        product = self._extract_product(combined)
        
        # Extract category
        category = self._extract_category(combined, subject_lower)
        
        # Extract severity
        severity = self._extract_severity(combined, subject_lower)
        
        # Extract requested action
        requested_action = self._extract_requested_action(combined, category)
        
        # Extract refund amount
        refund_amount = self._extract_refund_amount(ticket.body)
        
        # Extract deadline
        deadline = self._extract_deadline(ticket.body)
        
        # Determine if escalated
        escalated = self._is_escalated(combined, subject_lower)
        
        # Generate confidence scores
        confidence_scores = self._generate_confidence_scores(ticket)
        
        return {
            "company": company,
            "product": product,
            "category": category,
            "severity": severity,
            "requested_action": requested_action,
            "refund_amount": refund_amount,
            "deadline": deadline,
            "escalated": escalated,
            "confidence_scores": confidence_scores
        }
    
    def _extract_company(self, email: str, body: str) -> str:
        """Extract company name from email domain or body."""
        # Try to extract from email domain
        if "@" in email:
            domain = email.split("@")[1].split(".")[0]
            # Capitalize first letter
            company = domain.capitalize()
            
            # Check if company name appears in body with better formatting
            company_matches = [
                "Castlerock Mining", "Panacea Labs", "Nordvale Bank",
                "Sunbelt Utilities", "Orchid Hospitality", "Kestrel Motors",
                "Vireo Health", "Meridian Logistics", "Ferrolane Steel",
                "Halcyon Foods", "Bluepeak Retail", "Trident Pharma"
            ]
            
            for match in company_matches:
                if match.lower() in body.lower() or domain in match.lower():
                    return match
            
            return company
        
        return "Unknown Company"
    
    def _extract_product(self, text: str) -> str:
        """Extract product name from text."""
        products = {
            "zen orchestrator": "Zen Orchestrator",
            "zen studio": "Zen Studio",
            "zen connect": "Zen Connect",
            "zen insights": "Zen Insights",
            "zen vault": "Zen Vault"
        }
        
        for key, value in products.items():
            if key in text:
                return value
        
        # Default to most common product
        return "Zen Connect"
    
    def _extract_category(self, text: str, subject: str) -> str:
        """Extract category from text."""
        # Outage keywords
        if any(word in text for word in ["down", "unavailable", "502", "504", "failed", "failing", "outage"]):
            return "outage"
        
        # Billing keywords
        if any(word in text for word in ["billed", "invoice", "charge", "refund", "credit", "billing", "payment", "duplicate"]):
            return "billing"
        
        # Churn risk keywords
        if any(word in text for word in ["non-renewal", "not renew", "lapse", "terminate", "termination", "cancel"]):
            return "churn_risk"
        
        # Bug keywords
        if any(word in text for word in ["bug", "error", "broken", "apostrophe", "drops rows", "serial number"]):
            return "bug"
        
        # Feature request keywords
        if any(word in text for word in ["sso", "feature", "roadmap", "bulk re-run", "row-level permission"]):
            return "feature_request"
        
        # How-to keywords (default for questions)
        if any(word in subject for word in ["how", "question", "help", "where"]):
            return "how_to"
        
        return "how_to"
    
    def _extract_severity(self, text: str, subject: str) -> str:
        """Extract severity level."""
        # Critical indicators
        if any(word in text for word in ["urgent", "completely down", "sitting idle", "critical"]) or "URGENT" in subject.upper():
            return "critical"
        
        # High severity
        if any(word in text for word in ["escalat", "cto", "leadership", "third time", "board demo"]):
            return "high"
        
        # Medium severity
        if any(word in text for word in ["reliability", "issue", "problem", "concern"]):
            return "medium"
        
        # Low severity (default for questions, feature requests)
        return "low"
    
    def _extract_requested_action(self, text: str, category: str) -> str:
        """Extract requested action."""
        # Refund keywords
        if "refund" in text and "duplicate" in text:
            return "refund"
        
        # Credit keywords
        if "credit" in text or "cancelled two seats" in text:
            return "credit"
        
        # Callback keywords
        if any(word in text for word in ["call me", "please call", "ask for a call"]):
            return "callback"
        
        # Fix for bugs and outages
        if category in ["bug", "outage"]:
            return "fix"
        
        # Information for how-to and feature requests
        if category in ["how_to", "feature_request"]:
            return "information"
        
        return "none"
    
    def _extract_refund_amount(self, body: str) -> Optional[float]:
        """Extract refund amount from text."""
        # Look for dollar amounts
        dollar_pattern = r'\$([0-9,]+(?:\.[0-9]{2})?)'
        matches = re.findall(dollar_pattern, body)
        
        if matches:
            # If multiple amounts, look for context
            if "refund" in body.lower() or "credit" in body.lower() or "duplicate" in body.lower():
                # Take the first amount mentioned
                try:
                    amount_str = matches[0].replace(",", "")
                    return float(amount_str)
                except ValueError:
                    pass
        
        # Look for EUR amounts and convert to USD (approximate)
        eur_pattern = r'([0-9\s]+)\s*EUR'
        eur_matches = re.findall(eur_pattern, body)
        if eur_matches:
            try:
                amount_str = eur_matches[0].replace(" ", "")
                eur_amount = float(amount_str)
                # Approximate conversion EUR to USD (1.1 rate)
                return round(eur_amount * 1.1, 2)
            except ValueError:
                pass
        
        # Look for spoken amounts in transcripts
        if "nine thousand" in body.lower():
            return 9000.0
        
        return None
    
    def _extract_deadline(self, body: str) -> Optional[str]:
        """Extract deadline from text."""
        # Look for specific dates with "the Xth" pattern
        date_pattern = r'the (\d+)(?:st|nd|rd|th)'
        matches = re.findall(date_pattern, body)
        
        if matches:
            try:
                day = int(matches[0])
                # Assume current month/year (August 2026 based on tickets)
                if 1 <= day <= 31:
                    return f"2026-08-{day:02d}"
            except ValueError:
                pass
        
        # Look for "before quarter end"
        if "quarter end" in body.lower():
            return "2026-09-30"
        
        # Look for relative dates like "Thursday" or "next week"
        if "thursday" in body.lower() or "next week" in body.lower():
            # Return a date 3-7 days from ticket received
            return "2026-08-15"
        
        return None
    
    def _is_escalated(self, text: str, subject: str) -> bool:
        """Determine if ticket is escalated."""
        escalation_keywords = [
            "escalat", "cto", "leadership", "vp", "cfo",
            "invoke", "termination clause", "copying in"
        ]
        
        return any(keyword in text for keyword in escalation_keywords)
    
    def _generate_confidence_scores(self, ticket: Ticket) -> Dict[str, float]:
        """Generate mock confidence scores for fields."""
        # Use ticket ID for deterministic scores
        seed = hash(ticket.id) % 100
        base_confidence = 0.75 + (seed / 100 * 0.2)  # 0.75 to 0.95
        
        return {
            "company": min(0.95, base_confidence + 0.05),
            "product": min(0.99, base_confidence + 0.10),
            "category": min(0.90, base_confidence),
            "severity": min(0.85, base_confidence - 0.05),
            "requested_action": min(0.80, base_confidence - 0.10)
        }
    
    def _generate_invalid_output(self, ticket: Ticket) -> Dict[str, Any]:
        """
        Generate intentionally invalid output for testing retry logic.
        
        Args:
            ticket: Input ticket
        
        Returns:
            Invalid data that will fail Pydantic validation
        """
        if ticket.id == "tkt_0013":
            # Invalid product
            return {
                "company": "Panacea Labs",
                "product": "Zen InvalidProduct",  # Invalid enum value
                "category": "billing",
                "severity": "medium",
                "requested_action": "refund",
                "refund_amount": 4820.0,
                "deadline": None,
                "escalated": False,
                "confidence_scores": {"company": 0.8}
            }
        
        elif ticket.id == "tkt_0042":
            # Invalid category
            return {
                "company": "Trident Pharma",
                "product": "Zen Connect",
                "category": "invalid_category",  # Invalid enum value
                "severity": "low",
                "requested_action": "information",
                "refund_amount": None,
                "deadline": None,
                "escalated": False,
                "confidence_scores": {"company": 0.9}
            }
        
        elif ticket.id == "tkt_0089":
            # Invalid severity
            return {
                "company": "Ferrolane Steel",
                "product": "Zen Insights",
                "category": "churn_risk",
                "severity": "super_critical",  # Invalid enum value
                "requested_action": "callback",
                "refund_amount": None,
                "deadline": "2026-08-19",
                "escalated": True,
                "confidence_scores": {"company": 0.95}
            }
        
        # Default invalid output
        return {
            "company": "",  # Invalid: empty string
            "product": "Unknown",
            "category": "unknown",
            "severity": "low",
            "requested_action": "none",
            "refund_amount": None,
            "deadline": None,
            "escalated": False,
            "confidence_scores": {}
        }
