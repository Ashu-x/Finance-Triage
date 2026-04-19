# Finance Support Triage Agent - Database Setup Guide

## Overview

The Finance Triage Agent now supports **PostgreSQL database storage** for persistent record-keeping and human evaluation. Instead of just text files, all triage results are saved to a PostgreSQL database with full tracking of status, reviewer notes, and evaluation history.

## Features

✅ **Persistent Storage** - All complaints stored in PostgreSQL database  
✅ **Status Tracking** - Mark records as PENDING_REVIEW, REVIEWED, ESCALATED, RESOLVED, CLOSED  
✅ **Reviewer Notes** - Add comments and evaluation feedback  
✅ **CSV Export** - Download records for Excel review  
✅ **REST API** - Full API access to database records  
✅ **Statistics** - Dashboard with urgency and intent distribution  
✅ **Backward Compatible** - Text files still saved alongside database  

---

## Installation & Setup

### Step 1: Install PostgreSQL

**Windows:**
- Download from: https://www.postgresql.org/download/windows/
- Run the installer
- Remember the password you set for the `postgres` user
- PostgreSQL will start automatically

**macOS:**
```bash
brew install postgresql
brew services start postgresql
```

**Linux (Ubuntu/Debian):**
```bash
sudo apt-get install postgresql postgresql-contrib
sudo systemctl start postgresql
```

---

### Step 2: Create Database and User

Open PostgreSQL command line (psql):

**Windows:** Search for "SQL Shell" in Start Menu  
**Mac/Linux:** Run `psql postgres`

Execute these commands:

```sql
-- Create database
CREATE DATABASE finance_triage;

-- Create user
CREATE USER triage_user WITH PASSWORD 'your_secure_password_here';

-- Grant permissions
ALTER ROLE triage_user SET client_encoding TO 'utf8';
ALTER ROLE triage_user SET default_transaction_isolation TO 'read committed';
ALTER ROLE triage_user SET default_transaction_deferrable TO on;
GRANT ALL PRIVILEGES ON DATABASE finance_triage TO triage_user;

-- Connect to database
\c finance_triage

-- Grant schema permissions
GRANT ALL ON SCHEMA public TO triage_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO triage_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO triage_user;
```

---

### Step 3: Update .env File

Edit `.env` in your project root:

```env
GROQ_API_KEY=your_groq_api_key_here

# PostgreSQL Configuration
DATABASE_URL=postgresql://triage_user:your_secure_password_here@localhost:5432/finance_triage
```

**Format:** `postgresql://username:password@host:port/database_name`

---

### Step 4: Install Python Dependencies

```bash
pip install -r requirements.txt
```

This will install `psycopg2-binary` (PostgreSQL Python driver) and `sqlalchemy` (ORM).

---

### Step 5: Start the Server

```bash
python app.py
```

The database will be initialized automatically on first run.

---

## Database Schema

The `triage_records` table stores:

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer | Primary key, auto-incremented |
| `timestamp` | DateTime | When the complaint was received |
| `request_ip` | String | Customer IP address |
| `customer_message` | Text | Original complaint/inquiry |
| `message_length` | Integer | Length of customer message |
| `urgency` | String | CRITICAL, HIGH, MEDIUM, LOW |
| `intent` | String | fraud_alert, refund_request, etc. |
| `confidence` | Float | 0.0 to 1.0 classification confidence |
| `transaction_ids` | JSON | List of extracted transaction IDs |
| `amounts` | JSON | List of extracted amounts |
| `dates` | JSON | List of extracted dates |
| `account_numbers` | JSON | List of extracted account numbers |
| `ai_response` | Text | Generated AI response |
| `processing_time_ms` | Float | Milliseconds to process |
| `status` | String | PENDING_REVIEW, REVIEWED, ESCALATED, RESOLVED, CLOSED |
| `reviewer_notes` | Text | Human reviewer comments |
| `reviewed_at` | DateTime | When human reviewed it |
| `reviewed_by` | String | Name of reviewer |

---

## API Endpoints

### View Records

**Get all records (paginated):**
```bash
GET /api/database/records?skip=0&limit=50
```

**Get specific record:**
```bash
GET /api/database/records/{id}
```

**Get records by status:**
```bash
GET /api/database/records/status/PENDING_REVIEW
GET /api/database/records/status/REVIEWED
GET /api/database/records/status/ESCALATED
```

### Update Records

**Update record status and add reviewer notes:**
```bash
POST /api/database/records/{id}/update

{
    "status": "REVIEWED",
    "notes": "Looks good, responding to customer",
    "reviewed_by": "John Smith"
}
```

### Export Data

**Download CSV file:**
```bash
GET /api/database/export
```

**Export specific status:**
```bash
GET /api/database/export?status_filter=PENDING_REVIEW
```

### Statistics

**Get dashboard statistics:**
```bash
GET /api/database/statistics
```

Returns:
```json
{
    "success": true,
    "statistics": {
        "total_records": 42,
        "pending_review": 15,
        "critical_urgency": 3,
        "high_urgency": 8
    }
}
```

---

## Human Review Workflow

### Step 1: Process Complaint
Customer submits complaint → AI classifies → Response generated → Saved to DB

### Step 2: Review in Database
1. Open: `http://localhost:8000/api/database/records?status_filter=PENDING_REVIEW`
2. Human reviewer examines each record
3. Checks if urgency/intent classification is correct
4. Verifies AI response is appropriate

### Step 3: Update Status

**Option A: Via API**
```bash
curl -X POST http://localhost:8000/api/database/records/1/update \
  -H "Content-Type: application/json" \
  -d '{
    "status": "REVIEWED",
    "notes": "Classification correct, response appropriate",
    "reviewed_by": "Sarah Johnson"
  }'
```

**Option B: Via Frontend** (coming soon)

### Step 4: Export for Excel Analysis
```bash
curl http://localhost:8000/api/database/export > complaints.csv
```

Open in Excel for further analysis, filtering, etc.

---

## Troubleshooting

### "Connection refused" Error

**Problem:** Cannot connect to PostgreSQL  
**Solution:**
1. Check PostgreSQL is running: `sudo systemctl status postgresql` (Linux)
2. Verify DATABASE_URL in .env is correct
3. Test connection: `psql postgresql://user:password@localhost:5432/finance_triage`

### "Authentication failed" Error

**Problem:** Wrong username/password  
**Solution:**
1. Verify DATABASE_URL matches the user created in Step 2
2. Make sure password doesn't have special characters (or escape them)

### "Database does not exist" Error

**Problem:** You created user but not database  
**Solution:**
1. Run the SQL commands from Step 2 again
2. Make sure `CREATE DATABASE finance_triage;` was executed

### "psycopg2 not installed" Error

**Problem:** Missing PostgreSQL driver  
**Solution:**
```bash
pip install psycopg2-binary
```

---

## Fallback Mode (Without Database)

If PostgreSQL is unavailable, the system will:
- Continue running and processing complaints
- Save text files as before (in `logs/` folder)
- Log a warning about database connection failure
- Resume normal operation when database comes back online

This ensures your system is resilient to database outages.

---

## Running Without Database

If you prefer not to use PostgreSQL:

1. Remove `psycopg2-binary` and `sqlalchemy` from requirements.txt
2. Remove import statements for `database` module from app.py
3. Remove database initialization code
4. Comment out database save calls in the triage endpoint

Text files will continue to be saved in the `logs/` folder.

---

## Best Practices

✅ **Regular Backups** - Back up your PostgreSQL database weekly
```bash
pg_dump -U triage_user -d finance_triage > backup_$(date +%Y%m%d).sql
```

✅ **Archive Old Records** - Move reviewed complaints to archive table quarterly

✅ **Monitor Status Distribution** - Check `/api/database/statistics` regularly

✅ **Export for Legal** - Export CRITICAL records monthly for compliance

---

## Next Steps

1. Install PostgreSQL (Step 1)
2. Create database & user (Step 2)
3. Update .env (Step 3)
4. Install dependencies (Step 4)
5. Run `python app.py`
6. Test at http://localhost:8000

Questions? Check the database error logs in `logs/triage_agent.log`
