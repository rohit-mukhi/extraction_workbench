# Extraction Workbench - Backend

FastAPI backend service for ticket data extraction and review.

---

## Overview

This backend provides REST API endpoints for:
- Loading support tickets from JSONL files
- Running extraction jobs with mock AI provider
- Validating extracted data with automatic retry logic
- Managing human corrections to extracted records
- Exporting reviewed records as CSV

---

## Prerequisites

- **Python 3.9 or higher**
- **pip** (Python package manager)
- **Git** (for cloning the repository)

---

## Installation

### Step 1: Clone the Repository

```bash
# Clone the repository
git clone <your-repo-url>
cd extraction_workbench/backend
```

### Step 2: Create Virtual Environment

**On macOS/Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

**On Windows:**
```bash
python -m venv venv
venv\Scripts\activate
```

Your terminal should now show `(venv)` prefix.

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

This installs:
- FastAPI (web framework)
- Uvicorn (ASGI server)
- Pydantic (data validation)
- Pytest (testing framework)

### Step 4: Set Up Environment Variables

```bash
# Copy the example env file
cp .env.example .env

# Edit .env if needed (optional - defaults work fine)
# Default settings:
# - AI_PROVIDER=mock
# - MAX_CONCURRENT_JOBS=5
# - PORT=8000
# - CORS_ORIGINS=http://localhost:3000
```

---

## Running the Backend

### Option 1: Using Python Directly

```bash
python main.py
```

### Option 2: Using Uvicorn (Recommended for Development)

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

The `--reload` flag enables auto-restart on code changes.

### Expected Output

```
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Loaded 150 tickets
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000
```

---

## Verify It's Working

### Method 1: Browser

Open: http://localhost:8000

You should see:
```json
{
  "status": "running",
  "service": "Extraction Workbench API",
  "tickets_loaded": 150
}
```

### Method 2: API Documentation

Open: http://localhost:8000/docs

This shows interactive Swagger UI with all API endpoints.

### Method 3: Command Line

```bash
curl http://localhost:8000
```

---

## Running Tests

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/test_validation.py

# Run with coverage report
pytest --cov=. tests/
```

**Expected output:**
```
======================== test session starts =========================
tests/test_job_manager.py ..........
tests/test_progress.py .......
tests/test_validation.py .....

======================== 23 passed in 3.2s ==========================
```

---

## API Endpoints

### Core Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | Health check |
| `GET` | `/api/tickets` | List all tickets |
| `POST` | `/api/jobs` | Create extraction job |
| `GET` | `/api/jobs/{job_id}` | Get job status and progress |
| `GET` | `/api/jobs/{job_id}/results` | Get extracted records |
| `PATCH` | `/api/records/{record_id}` | Update record with human edit |
| `GET` | `/api/jobs/{job_id}/export.csv` | Export job results as CSV |

### Example: Create a Job

```bash
curl -X POST http://localhost:8000/api/jobs \
  -H "Content-Type: application/json" \
  -d '{"ticket_ids": ["tkt_0001", "tkt_0002", "tkt_0003"]}'
```

**Response:**
```json
{
  "job_id": "job_abc123",
  "status": "pending"
}
```

### Example: Check Job Progress

```bash
curl http://localhost:8000/api/jobs/job_abc123
```

**Response:**
```json
{
  "id": "job_abc123",
  "status": "running",
  "progress": {
    "total": 3,
    "queued": 1,
    "running": 1,
    "completed": 1,
    "failed": 0
  }
}
```

---

## Project Structure

```
backend/
├── main.py                 # FastAPI app and API routes
├── models.py               # Pydantic data models
├── storage.py              # In-memory data storage
├── mock_provider.py        # Mock AI extraction logic
├── job_manager.py          # Background job processing
├── requirements.txt        # Python dependencies
├── .env.example            # Environment variables template
├── README.md               # This file
└── tests/
    ├── __init__.py
    ├── test_validation.py  # Validation & retry tests
    ├── test_progress.py    # Progress arithmetic tests
    └── test_job_manager.py # Job manager tests
```

---

## How It Works

### 1. Startup
- Server starts and loads 150 tickets from `../context/tickets.jsonl`
- Initializes in-memory storage (jobs and records)
- Sets up mock AI provider

### 2. Job Creation
- User selects tickets via frontend
- POST request creates a job with those ticket IDs
- Job starts processing in background (non-blocking)
- Returns immediately with job ID

### 3. Extraction Process
```
For each ticket:
  ├─ Extract data using mock AI provider (0.5-2s delay)
  ├─ Validate against Pydantic schema
  ├─ If validation fails:
  │   ├─ Retry once with validation error feedback
  │   └─ If still fails: mark as needs_review
  └─ Update job progress (queued → running → completed)
```

### 4. Review & Export
- User reviews extracted records via frontend
- Makes corrections via PATCH requests
- Exports final CSV via GET request

---

## Mock AI Provider

The mock provider uses **rule-based extraction**:

- **Company**: Extracted from email domain
- **Product**: Searches for "Zen X" keywords
- **Category**: Keyword matching (e.g., "down" → outage, "invoice" → billing)
- **Severity**: Based on urgency words (URGENT, CTO → critical/high)
- **Refund Amount**: Regex for `$X,XXX` or `X EUR`
- **Escalated**: Looks for keywords like "escalate", "CTO", "termination"

**Intentional Failures**: Tickets `tkt_0013`, `tkt_0042`, `tkt_0089` return invalid data on first attempt to test retry logic.

---

## Troubleshooting

### Issue: "Port 8000 already in use"

**Solution:**
```bash
# Use a different port
uvicorn main:app --reload --port 8001
```

Or kill the existing process:
```bash
# Find process on port 8000
lsof -i :8000

# Kill it
kill -9 <PID>
```

### Issue: "ModuleNotFoundError: No module named 'fastapi'"

**Solution:**
```bash
# Make sure virtual environment is activated
source venv/bin/activate  # macOS/Linux
venv\Scripts\activate     # Windows

# Reinstall dependencies
pip install -r requirements.txt
```

### Issue: "FileNotFoundError: Tickets file not found"

**Solution:**
The backend expects tickets at `../context/tickets.jsonl` (relative to backend directory).

```bash
# Verify file exists
ls ../context/tickets.jsonl

# If missing, make sure you have the complete repository structure
```

### Issue: Tests fail with import errors

**Solution:**
Run tests from the backend directory:
```bash
cd backend
pytest
```

### Issue: CORS errors from frontend

**Solution:**
Update `.env` to include your frontend URL:
```bash
CORS_ORIGINS=http://localhost:3000,https://your-frontend.vercel.app
```

Then restart the server.

---

## Development Tips

### Auto-Reload on Code Changes

```bash
uvicorn main:app --reload
```

The server automatically restarts when you edit `.py` files.

### View Logs

The server logs all operations to console. Look for:
- `INFO` - Normal operations
- `WARNING` - Validation failures, retries
- `ERROR` - Actual errors

### Interactive API Testing

1. Start server
2. Open http://localhost:8000/docs
3. Click "Try it out" on any endpoint
4. Fill in parameters and click "Execute"

### Adding More Tickets

Edit `../context/tickets.jsonl` and add new lines:
```json
{"id": "tkt_0151", "subject": "Test", "body": "...", "channel": "email", "received_at": "2026-08-04T11:56:28Z", "from_email": "test@example.com", "attachments": 0}
```

Restart the server to reload tickets.

---

## Environment Variables Reference

| Variable | Default | Description |
|----------|---------|-------------|
| `AI_PROVIDER` | `mock` | AI provider to use (mock or real) |
| `MAX_CONCURRENT_JOBS` | `5` | Max concurrent ticket extractions |
| `CORS_ORIGINS` | `http://localhost:3000` | Allowed frontend origins (comma-separated) |
| `PORT` | `8000` | Server port |

---

## Production Deployment

### For Render/Railway/Fly.io:

1. **Ensure `requirements.txt` is up to date**
2. **Create start command** (usually auto-detected):
   ```bash
   uvicorn main:app --host 0.0.0.0 --port $PORT
   ```

3. **Set environment variables** on the platform:
   - `AI_PROVIDER=mock`
   - `CORS_ORIGINS=https://your-frontend-url.vercel.app`

4. **Health check endpoint**: `/`

5. **Build command** (if needed):
   ```bash
   pip install -r requirements.txt
   ```

### Platform-Specific Notes:

**Render:**
- Auto-detects Python projects
- Reads `requirements.txt`
- Sets `PORT` automatically

**Railway:**
- Requires `Procfile` or auto-detects
- Set env vars in dashboard

**Fly.io:**
- May need `fly.toml` config
- Deploy with `fly deploy`

---

## Data Persistence Note

**Current Implementation**: All data (jobs, records) is stored in-memory and **lost on restart**.

**What's Preserved**:
- ✅ Tickets (reloaded from `tickets.jsonl` on startup)

**What's Lost**:
- ❌ Jobs created during session
- ❌ Extracted records
- ❌ Human edits

**For Production**: Consider adding SQLite or PostgreSQL for data persistence. See `DECISIONS.md` for details.

---

## Testing the Full Flow

```bash
# 1. Start the backend
python main.py

# 2. Create a job (in another terminal)
curl -X POST http://localhost:8000/api/jobs \
  -H "Content-Type: application/json" \
  -d '{"ticket_ids": ["tkt_0001", "tkt_0002"]}'

# 3. Check progress (use job_id from step 2)
curl http://localhost:8000/api/jobs/job_abc123

# 4. Get results
curl http://localhost:8000/api/jobs/job_abc123/results

# 5. Update a record (use record_id from step 4)
curl -X PATCH http://localhost:8000/api/records/rec_xyz \
  -H "Content-Type: application/json" \
  -d '{"field": "severity", "value": "high"}'

# 6. Export CSV
curl http://localhost:8000/api/jobs/job_abc123/export.csv > results.csv
```

---

## Support

For issues or questions:
1. Check the troubleshooting section above
2. Verify all prerequisites are installed
3. Ensure you're in the correct directory (`backend/`)
4. Make sure virtual environment is activated
5. Check that `../context/tickets.jsonl` exists

---

## License

See repository root for license information.
