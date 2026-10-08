# Extraction Workbench

A full-stack application for extracting structured data from support tickets using AI, with human-in-the-loop review and correction.

> **⚠️ Note for Evaluators:** The backend is deployed on Render's free tier, which may sleep after 15 minutes of inactivity. **First request may take 30-60 seconds** while the server wakes up. Subsequent requests are fast. This is normal behavior for free-tier deployments and does not affect functionality.

---

## Overview

**Problem:** Support teams receive tickets as unstructured text (emails, chats, call transcripts). Downstream systems need structured data.

**Solution:** This tool uses an AI model for initial extraction, then provides a review interface for humans to verify and correct the results.

### Key Features

- ✅ **Batch Processing**: Select multiple tickets and process them concurrently
- ✅ **AI Extraction**: Mock rule-based provider extracts 8 structured fields from ticket text
- ✅ **Automatic Retry**: Failed extractions retry once with validation error feedback
- ✅ **Human Review**: Side-by-side interface shows original ticket and extracted fields
- ✅ **Inline Editing**: Edit any field with validation, track which fields are human-edited
- ✅ **Needs Review Queue**: Tickets that failed validation twice are flagged for human attention
- ✅ **CSV Export**: Download reviewed records with proper formatting

### Extracted Fields

From each support ticket, the system extracts:

| Field | Type | Description |
|-------|------|-------------|
| `company` | string | Company name (from email domain or body) |
| `product` | enum | One of 5 Zen products (Orchestrator, Studio, Connect, Insights, Vault) |
| `category` | enum | Ticket category (outage, billing, bug, feature_request, how_to, churn_risk) |
| `severity` | enum | Severity level (low, medium, high, critical) |
| `requested_action` | enum | Action requested (refund, credit, fix, callback, information, none) |
| `refund_amount` | number | Refund amount in USD (optional) |
| `deadline` | date | Deadline mentioned in ticket (optional) |
| `escalated` | boolean | Whether ticket is escalated to leadership |

---

## Architecture

### Technology Stack

**Backend:**
- FastAPI (Python web framework)
- Pydantic (data validation)
- Asyncio (concurrent processing)
- Pytest (testing)

**Frontend:**
- Next.js 14 (React framework with App Router)
- TypeScript (type safety)
- Tailwind CSS (styling)

**Data:**
- In-memory storage (Python dictionaries)
- 150 real support tickets (JSONL format)

### System Flow

```
┌─────────────┐
│   User      │ Selects tickets
└─────┬───────┘
      │
      ▼
┌─────────────────────────────────────────────┐
│            Frontend (Next.js)               │
│  - Ticket list with search/filter           │
│  - Job creation interface                   │
│  - Real-time progress tracking              │
│  - Side-by-side review UI                   │
└─────────────┬───────────────────────────────┘
              │ HTTP/REST API
              ▼
┌─────────────────────────────────────────────┐
│         Backend (FastAPI)                   │
│  ┌────────────────────────────────────┐    │
│  │  Job Manager (Background Tasks)    │    │
│  │  - Concurrent processing (max 5)   │    │
│  │  - Retry logic on validation fail  │    │
│  │  - Progress tracking               │    │
│  └───────┬────────────────────────────┘    │
│          │                                  │
│  ┌───────▼────────────┐  ┌──────────────┐ │
│  │  Mock AI Provider  │  │   Storage    │ │
│  │  - Rule-based      │  │  (In-memory) │ │
│  │  - Deterministic   │  │  - Jobs      │ │
│  │  - Intentional     │  │  - Records   │ │
│  │    failures        │  │  - Tickets   │ │
│  └────────────────────┘  └──────────────┘ │
└─────────────────────────────────────────────┘
              │
              ▼
        Validation (Pydantic)
              │
     ┌────────┴────────┐
     │                 │
  Success          Failure
     │                 │
  Save Record     Retry Once
                       │
                  ┌────┴────┐
                  │         │
              Success   Failure
                  │         │
              Save     needs_review
```

---

## Project Structure

```
extraction_workbench/
├── backend/                    # Python FastAPI backend
│   ├── main.py                # API endpoints
│   ├── models.py              # Pydantic data models
│   ├── storage.py             # In-memory data store
│   ├── mock_provider.py       # Mock AI extraction
│   ├── job_manager.py         # Background job processing
│   ├── requirements.txt       # Python dependencies
│   ├── .env.example           # Environment variables template
│   ├── README.md              # Backend-specific docs
│   └── tests/
│       ├── test_validation.py  # Validation & retry tests
│       ├── test_progress.py    # Progress tracking tests
│       └── test_job_manager.py # Job manager tests
│
├── frontend/                   # Next.js frontend
│   ├── app/
│   │   ├── page.tsx           # Home page (ticket list)
│   │   ├── layout.tsx         # Root layout
│   │   └── jobs/
│   │       └── [id]/
│   │           └── page.tsx   # Job detail & review page
│   ├── lib/
│   │   ├── types.ts           # TypeScript interfaces
│   │   └── api.ts             # API client functions
│   ├── package.json           # Node dependencies
│   ├── .env.example           # Environment variables template
│   └── .env.local             # Local environment config
│
├── context/                    # Dataset
│   ├── tickets.jsonl          # 150 support tickets
│   ├── README.md              # Dataset documentation
│   └── DATA.md                # Data format specification
│
├── README.md                   # This file
├── DECISIONS.md                # Architecture decisions
└── .gitignore                  # Git ignore rules
```

---

## Prerequisites

- **Python 3.9+** (for backend)
- **Node.js 18+** (for frontend)
- **npm** or **yarn** (package manager)
- **Git** (version control)

---

## Installation & Setup

### Step 1: Clone the Repository

```bash
git clone <your-repo-url>
cd extraction_workbench
```

### Step 2: Backend Setup

```bash
# Navigate to backend
cd backend

# Create virtual environment
python3 -m venv venv

# Activate virtual environment
# On macOS/Linux:
source venv/bin/activate
# On Windows:
# venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy environment template
cp .env.example .env

# (Optional) Edit .env if needed - defaults work fine
```

### Step 3: Frontend Setup

```bash
# Navigate to frontend (from repo root)
cd frontend

# Install dependencies
npm install

# Copy environment template
cp .env.example .env.local

# (Optional) Edit .env.local to point to your backend
# Default: NEXT_PUBLIC_API_URL=http://localhost:8000
```

---

## Running the Application

### Terminal 1: Start Backend

```bash
cd backend

# Make sure virtual environment is activated
source venv/bin/activate  # macOS/Linux
# venv\Scripts\activate   # Windows

# Start the server
python main.py

# OR use uvicorn directly (auto-reload on changes)
uvicorn main:app --reload
```

**Backend runs at:** `http://localhost:8000`

**API Documentation:** `http://localhost:8000/docs` (Swagger UI)

### Terminal 2: Start Frontend

```bash
cd frontend

# Start development server
npm run dev
```

**Frontend runs at:** `http://localhost:3000`

---

## Using the Application

### Step 1: View Tickets

1. Open `http://localhost:3000` in your browser
2. You'll see a list of 150 support tickets
3. Use the search bar to filter tickets
4. Browse tickets to understand the data

### Step 2: Create an Extraction Job

1. Select tickets using checkboxes (or "Select All")
2. Click "Start Extraction" button
3. You'll be redirected to the job detail page
4. Job starts processing in the background

### Step 3: Monitor Progress

1. Progress bar shows real-time completion percentage
2. Stats show: total, queued, running, completed, failed
3. Page auto-refreshes every 2 seconds
4. Records appear in the left panel as they complete

### Step 4: Review & Edit Records

1. Click on any record in the left panel
2. Original ticket appears on the right
3. Extracted fields shown below with "Edit" buttons
4. Click "Edit" on any field to modify it
5. Save changes - field is marked "Human Edited"
6. Records with `needs_review` status appear at the top with yellow border

### Step 5: Export Results

1. When job is complete, "Export CSV" button appears
2. Click to download CSV file
3. CSV includes all fields plus human-edited indicators

---

## Testing

### Backend Tests

```bash
cd backend

# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/test_validation.py

# Run with coverage
pytest --cov=. tests/
```

**Required tests included:**
1. ✅ Validation failure triggers retry with error feedback
2. ✅ Double failure results in `needs_review` status
3. ✅ Progress arithmetic is accurate throughout job lifecycle

### Manual Testing Checklist

- [ ] Backend starts without errors
- [ ] Frontend starts without errors
- [ ] Tickets load on home page
- [ ] Search/filter works
- [ ] Ticket selection works
- [ ] Job creation redirects to job page
- [ ] Progress updates in real-time
- [ ] Records appear as they complete
- [ ] Clicking record shows detail view
- [ ] Editing fields works and saves
- [ ] `needs_review` items are visually distinct
- [ ] CSV export downloads correctly
- [ ] CSV contains all expected data

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | Health check |
| `GET` | `/api/tickets` | List all tickets (with optional search) |
| `POST` | `/api/jobs` | Create extraction job (returns 202) |
| `GET` | `/api/jobs/{id}` | Get job status and progress |
| `GET` | `/api/jobs/{id}/results` | Get extracted records |
| `PATCH` | `/api/records/{id}` | Update record field |
| `GET` | `/api/jobs/{id}/export.csv` | Export job as CSV |

See `backend/README.md` for detailed API documentation with examples.

---

## Configuration

### Backend Environment Variables

Located in `backend/.env`:

```bash
AI_PROVIDER=mock              # AI provider (mock or real)
MAX_CONCURRENT_JOBS=5         # Max concurrent extractions
CORS_ORIGINS=http://localhost:3000  # Allowed frontend origins
PORT=8000                     # Server port
```

### Frontend Environment Variables

Located in `frontend/.env.local`:

```bash
NEXT_PUBLIC_API_URL=http://localhost:8000  # Backend API URL
```

---

## Deployment

### Backend Deployment (Render/Railway)

1. Create new Web Service
2. Connect GitHub repository
3. Set root directory: `backend`
4. Set build command: `pip install -r requirements.txt`
5. Set start command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
6. Set environment variables:
   - `AI_PROVIDER=mock`
   - `CORS_ORIGINS=<your-frontend-url>`
7. Deploy

**Example:** `https://extraction-backend.onrender.com`

### Frontend Deployment (Vercel)

1. Create new project
2. Import GitHub repository
3. Set root directory: `frontend`
4. Framework: Next.js (auto-detected)
5. Set environment variable:
   - `NEXT_PUBLIC_API_URL=<your-backend-url>`
6. Deploy

**Example:** `https://extraction-workbench.vercel.app`

### Connecting Frontend & Backend

1. Get backend URL (e.g., `https://extraction-backend.onrender.com`)
2. Update frontend environment in Vercel:
   - `NEXT_PUBLIC_API_URL=https://extraction-backend.onrender.com`
3. Update backend environment in Render:
   - `CORS_ORIGINS=https://extraction-workbench.vercel.app`
4. Redeploy both if needed

---

## Key Design Decisions

See `DECISIONS.md` for detailed rationale on:

1. **Data Persistence**: In-memory vs database
2. **Missing Fields**: How to handle tickets with incomplete data
3. **Currency Conversion**: EUR to USD handling
4. **Multi-Issue Tickets**: How to categorize tickets with multiple problems
5. **Progress Reporting**: Polling vs streaming approach

---

## Data Notes

### Dataset

- 150 support tickets from August 2026
- Mix of emails, web forms, chat logs, phone transcripts
- Real-world variety: typos, signatures, email threads, multiple languages

### Special Tickets

- `tkt_0004`: Minimal body ("please advise")
- `tkt_0020`: Just "?" with no subject
- `tkt_0058`: French ticket with EUR amounts
- `tkt_0089`: Multiple issues in one ticket (tests multi-category handling)
- `tkt_0105`: Heavy typos and shorthand
- `tkt_0131`: Phone transcript with spoken amounts

### Mock AI Behavior

- **Deterministic**: Same ticket always produces same output
- **Artificial delay**: 0.5-2 seconds per ticket (observable progress)
- **Intentional failures**: Returns invalid data for `tkt_0013`, `tkt_0042`, `tkt_0089` to test retry logic

---

## Limitations & Trade-offs

### Current Limitations

- **Data persistence**: All data lost on server restart (in-memory only)
- **Concurrency**: Limited to 5 concurrent extractions (configurable)
- **No authentication**: Single-user application
- **No real AI**: Uses rule-based mock provider

### Production Improvements

If building for production, add:
- PostgreSQL database for data persistence
- Redis for job queue management
- Real LLM integration (OpenAI, Anthropic)
- User authentication and authorization
- API rate limiting
- Comprehensive error logging
- Horizontal scaling support
- WebSocket for real-time updates

---

## Troubleshooting

### Backend won't start

**Error:** "Port 8000 already in use"
```bash
# Find process using port 8000
lsof -i :8000
# Kill it
kill -9 <PID>
```

**Error:** "ModuleNotFoundError"
```bash
# Ensure virtual environment is activated
source venv/bin/activate
# Reinstall dependencies
pip install -r requirements.txt
```

**Error:** "Tickets file not found"
```bash
# Ensure you're in the backend directory
cd backend
# Check file exists
ls ../context/tickets.jsonl
```

### Frontend won't start

**Error:** "Cannot connect to backend"
```bash
# Check backend is running
curl http://localhost:8000
# Check .env.local has correct URL
cat .env.local
```

**Error:** "Module not found"
```bash
# Reinstall dependencies
rm -rf node_modules package-lock.json
npm install
```

### CORS errors

**Symptom:** API calls fail with CORS error in browser console

**Fix:** Update backend `.env`:
```bash
CORS_ORIGINS=http://localhost:3000,http://localhost:3001
```

---

## Development

### Adding More Tickets

Edit `context/tickets.jsonl` and add lines in JSON format:
```json
{"id": "tkt_0151", "subject": "New ticket", "body": "...", "channel": "email", "received_at": "2026-08-31T10:00:00Z", "from_email": "user@example.com", "attachments": 0}
```

Restart backend to reload tickets.

### Modifying Extraction Logic

Edit `backend/mock_provider.py`:
- Update keyword matching in `_extract_category()`
- Modify regex patterns in `_extract_refund_amount()`
- Add new rules in `_extract_data()`

### Adding New Fields

1. Update `backend/models.py` (add field to `ExtractedRecord`)
2. Update `frontend/lib/types.ts` (add to `ExtractedRecord` interface)
3. Update extraction logic in `backend/mock_provider.py`
4. Add field editor in `frontend/app/jobs/[id]/page.tsx`

---

## License

See repository for license information.

---

## Contact

For questions or issues:
1. Check troubleshooting section above
2. Review `DECISIONS.md` for design rationale
3. Check `backend/README.md` for API details
4. Open an issue on GitHub

---

## Acknowledgments

Built as a take-home assignment demonstrating:
- Full-stack development (Python + TypeScript)
- API design (REST, async processing)
- Error handling (validation, retry logic)
- UI/UX design (review workflows)
- Testing (unit tests, integration)
- Deployment (production-ready)
