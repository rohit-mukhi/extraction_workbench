# Architecture Decisions

This document covers key design decisions made during the implementation of the Extraction Workbench.

---

## 1. Data Persistence Strategy

**Decision:** In-memory storage with future consideration for restart persistence.

**Reasoning:**
The requirements specified that "in-memory state that survives for the life of the process is fine." For this prototype, I implemented storage using Python dictionaries to meet the deadline efficiently. However, I recognized that deployment on free-tier platforms (Render, Railway) involves frequent server restarts due to auto-sleep and redeployment.

**Trade-offs:**
- ✅ **Pros:** Fast development, no database setup complexity, meets stated requirements
- ⚠️ **Cons:** Data loss on server restart, not suitable for production use

**Production Approach:**
In a production system, I would implement PostgreSQL with SQLAlchemy for:
- ACID compliance for concurrent user access
- Data persistence across restarts
- Query optimization and indexing
- Connection pooling for performance
- Proper migrations for schema changes

**Mitigation for Demo:**
If time permits before submission, I will add simple pickle serialization to persist jobs and records between restarts, ensuring the deployed demo remains functional even with platform restarts.

---

## 2. Missing Field Values (Severity, Amounts, Deadlines)

**Decision:** Model makes best-effort extraction; missing optional fields return `None`; required fields use sensible defaults with low confidence scores.

**Product Decision Reasoning:**
When a ticket lacks explicit information (e.g., no severity mentioned), there are three options:

1. **Guess/infer** - Model makes its best prediction
2. **Leave empty** - Return None/null for the field
3. **Flag as needs_review** - Force human review

**I chose Option 1 (guess with confidence tracking)** because:

- **User efficiency:** Most tickets have implicit severity (e.g., "URGENT" in subject → critical). Making humans fill obvious fields wastes time.
- **Review workflow:** Low-confidence fields are highlighted in the UI, so humans can quickly verify questionable extractions.
- **Fail-safe:** If the model truly cannot determine a value, the record goes to `needs_review` status after validation failure.

**Implementation:**
- Required fields (company, product, category, severity, requested_action) always have values
- Optional fields (refund_amount, deadline) return `None` when not found
- Confidence scores highlight uncertain extractions for human review
- Validation failures trigger retry, then `needs_review` status

---

## 3. Currency Conversion (EUR to USD)

**Decision:** Approximate EUR-to-USD conversion (1 EUR = 1.10 USD) with flagging for human review.

**Context:**
Ticket `tkt_0058` is in French and mentions "4 820 EUR". The schema requires `refund_amount` in USD.

**Approach:**
1. Mock AI provider detects EUR amounts using regex
2. Applies approximate conversion rate (1.10) for USD equivalent
3. Returns converted amount with **low confidence score** (0.6)
4. Frontend highlights this field for human verification

**Why This Works:**
- ✅ Provides useful starting point (better than blank)
- ✅ Human reviewer sees low confidence and can verify/adjust
- ✅ Avoids blocking extraction on currency detection

**Production Improvement:**
Use a live currency API (e.g., exchangerate-api.io) for real-time conversion rates and store original currency + amount in metadata for audit trail.

---

## 4. Multi-Issue Tickets (Multiple Categories)

**Decision:** Extract the **primary/most urgent** issue; add note in confidence scores.

**Context:**
Ticket `tkt_0089` contains three separate problems:
1. Export bug (category: bug)
2. Billing discrepancy (category: billing)
3. SSO delay + renewal threat (category: churn_risk)

The schema allows only one category per record.

**Approach:**
- Select category based on **severity and urgency**: churn_risk (renewal threat) takes precedence
- Set `escalated: true` flag to indicate multiple issues
- Lower confidence score for category field (0.7 instead of 0.9+)
- In `raw_output` or notes, mention "Multiple issues detected"

**Why Single Category:**
- Schema constraint cannot be changed without breaking validation
- Escalation flag signals complexity
- Low confidence prompts human review
- Human can create separate tickets if needed

**Production Improvement:**
Allow multi-select categories or create linked sub-tickets for complex issues.

---

## 5. Minimal/Unclear Tickets (Empty Bodies)

**Decision:** Send all tickets to the model; create `needs_review` records for extraction failures.

**Context:**
- Ticket `tkt_0004`: body = "please advise"
- Ticket `tkt_0020`: body = "?" with empty subject

**Options Considered:**

1. **Skip AI processing entirely** - Fast but loses potential context
2. **Send to AI anyway** - Model might extract useful info from metadata (email domain, channel)
3. **Auto-flag for human review** - Skip AI, go straight to manual review

**I chose Option 2 (send to AI)** because:

- ✅ Email domain reveals company name
- ✅ Channel and metadata provide context
- ✅ Model can make educated guesses (e.g., company from `@castlerock.com`)
- ✅ Validation will catch if output is too sparse
- ✅ Failed validation → `needs_review` (same outcome as Option 3, but tried AI first)

**Implementation:**
```python
# Even minimal tickets get processed
if body in ["?", "please advise", ""]:
    # AI extracts what it can from email, subject, metadata
    # If validation fails → needs_review
    # No special case needed
```

**Cost:** Minimal (mock provider has ~0.5s delay regardless)

---

## 6. Progress Reporting: Polling vs. Streaming

**Decision:** HTTP polling every 2 seconds.

**Options:**

| Approach | Pros | Cons |
|----------|------|------|
| **Polling** | Simple, works everywhere, no connection management | Extra HTTP requests, 2-second delay |
| **Server-Sent Events (SSE)** | Real-time updates, efficient | More complex, some proxies block |
| **WebSockets** | Bi-directional, real-time | Overkill for one-way updates, complex deployment |

**Why Polling:**
- ✅ **Simplicity:** 5 lines of code (`setInterval` in frontend)
- ✅ **Reliability:** Works through all proxies and load balancers
- ✅ **Deployment:** No special server configuration needed
- ✅ **Acceptable latency:** 2-second delay is fine for batch jobs (not real-time chat)

**Cost Analysis:**
- 150 tickets × 1.5s average = ~3.75 minutes job duration
- 3.75 min ÷ 2s polling = ~112 requests
- Minimal bandwidth (JSON payload ~500 bytes)
- No measurable performance impact

**Production Consideration:**
For high-frequency updates or many concurrent users, SSE would be better. For this use case (single user reviewing batches), polling is pragmatic.

---

## 7. Additional Observations from Ticket Data

### Patterns Noticed:

1. **Reply chains:** ~30% of tickets include quoted email threads with support responses
2. **Signatures:** Most emails have legal footers ("This email and any attachments...")
3. **Amounts:** Inconsistent formatting: "$4,820", "4 820 EUR", "nine thousand something"
4. **Dates:** Relative ("the 14th", "Thursday") and absolute formats
5. **Escalation language:** Keywords like "CTO", "leadership", "termination clause"

### Mock AI Approach:

Used **keyword-based extraction** with regex patterns:
- Product: Search for "Zen X" literal strings
- Category: Keyword matching (e.g., "down"/"502" → outage, "invoice"/"billed" → billing)
- Severity: Urgency keywords ("URGENT", "completely down" → critical)
- Amounts: Regex for `$X,XXX` and `X XXX EUR`
- Escalation: Presence of executive titles or termination language

**Confidence Scores:** Deterministic based on ticket ID hash (0.75-0.95 range) to simulate AI uncertainty.

---

## 8. What I Would Build Next

If I had another day, I would add:

1. **Pickle persistence** for restart resilience (15 minutes)
2. **Keyboard navigation** in review UI (Tab to next field, Enter to save)
3. **Batch edit** mode (apply same change to multiple records)
4. **Audit log** (track all human edits with timestamps)
5. **Export filters** (only export human-reviewed records)
6. **Job cancellation** (stop running jobs)
7. **Re-run single ticket** (after fixing prompt or model)

---

## 9. Parts I'm Least Happy With

### Technical Debt:

1. **All routes in main.py:** Should be split into `routes/` modules for better organization
2. **No connection pooling:** If we add a database, would need proper connection management  
3. **CSV generation in memory:** Large exports (1000+ records) could hit memory limits
4. **No rate limiting:** API has no protection against abuse
5. **Basic error messages:** User-facing errors could be more helpful

### Testing Gaps:

1. Only 3 backend tests (meets requirement, but more would be better)
2. No integration tests (API endpoint → database → response)
3. No load testing (how many concurrent jobs can it handle?)

### Would Fix With More Time:

- Refactor routes into separate files
- Add Redis for job queue (better than in-memory task management)
- Implement proper logging with structured output (JSON logs)
- Add API request validation middleware
- Create admin dashboard for job monitoring

---

## 10. Technology Choices Rationale

### Backend: FastAPI
- ✅ Async support for concurrent job processing
- ✅ Automatic API documentation (Swagger UI)
- ✅ Pydantic integration for validation
- ✅ Fast development speed

### Frontend: Next.js 14 (App Router)
- ✅ Server-side rendering for better SEO
- ✅ Built-in routing
- ✅ TypeScript support
- ✅ Easy deployment to Vercel

### Mock Provider: Rule-Based
- ✅ Deterministic (same input → same output)
- ✅ No API costs or rate limits
- ✅ Fast (<2s per ticket)
- ✅ Testable with known failure cases

---

## Summary

These decisions prioritized:
1. **Meeting requirements** (all "Must Build" features)
2. **Time efficiency** (deliver working product by deadline)
3. **User experience** (helpful defaults, clear review UI)
4. **Interview readiness** (can explain every choice)

All trade-offs were made consciously with production improvements documented.
