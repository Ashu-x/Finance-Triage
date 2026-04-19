# Finance Support Triage Agent

Automated triage system for finance support messages. Uses AI to classify urgency/intent, extract financial entities, and generate professional responses. All data stored in PostgreSQL.

## Features

- **AI Classification** - Analyzes urgency (CRITICAL/HIGH/MEDIUM/LOW) and intent (fraud_alert, refund_request, etc.)
- **Entity Extraction** - Identifies transaction IDs, amounts, dates, and account numbers using regex + spaCy
- **Response Generation** - Generates context-specific professional responses based on classification
- **REST API** - FastAPI web server with endpoints for processing, querying, and exporting records
- **Database Storage** - PostgreSQL (Neon) for persistent record storage and human review
- **Web Interface** - Clean HTML frontend for message submission and result viewing

## Tech Stack

- **Python 3.10+**
- **Groq API** (llama-3.1-8b-instant model)
- **FastAPI** + uvicorn
- **SQLAlchemy** ORM
- **PostgreSQL** (via Neon DB)
- **spaCy** for NLP
- **pydantic** for validation

## Setup

### 1. Clone and Install

```bash
git clone <your-repo-url>
cd financeTriage
pip install -r requirements.txt
python -m spacy download en_core_web_sm
```

### 2. Configure Environment

Create `.env` file with:

```
GROQ_API_KEY=your_groq_api_key_here
DATABASE_URL=postgresql://username:password@host:port/database?sslmode=require
```

### 3. Run

Start the web server:

```bash
python app.py
```

Open browser: **http://localhost:8000**

Or run CLI pipeline:

```bash
python main.py
```

## API Endpoints

### Process Message
`POST /api/triage`
```json
{
  "message": "I was charged $500 for transaction TXN123 that never went through..."
}
```

### View Records
- `GET /api/database/records` - List all triage records
- `GET /api/database/records/{id}` - Get record details
- `GET /api/database/records/status/{status}` - Filter by status

### Update Record Status
`POST /api/database/records/{id}/update`
```json
{
  "status": "REVIEWED" | "ESCALATED" | "RESOLVED" | "CLOSED"
}
```

### Export Records
`GET /api/database/export` - Export to CSV format

### Statistics
`GET /api/database/statistics` - Get processing stats

## Project Structure

```
financeTriage/
├── app.py                 # FastAPI web server + REST API
├── main.py               # CLI pipeline entry point
├── classifier.py         # LLM classification (urgency/intent)
├── entity_extractor.py   # Regex + spaCy entity extraction
├── response_writer.py    # LLM response generation
├── database.py           # SQLAlchemy ORM + database functions
├── triage_models.py      # Pydantic data models
├── index.html            # Web frontend
├── requirements.txt      # Python dependencies
├── .env                  # Configuration (not in git)
└── .gitignore           # Git ignore rules
```

## How It Works

1. **Input** - User submits customer support message via web or API
2. **Classify** - Groq LLM analyzes and assigns urgency + intent + confidence
3. **Extract** - Regex patterns + spaCy identify financial entities
4. **Generate** - Groq LLM creates context-specific response
5. **Save** - Record stored in PostgreSQL with all analysis results
6. **Review** - Human reviewers can view, update status, and export for further action

## Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `GROQ_API_KEY` | Groq API authentication key | `gsk_...` |
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://user:pass@host/db?sslmode=require` |

## Classification Details

**Urgency Levels:**
- CRITICAL: Fraud, unauthorized charges, payroll failure, emergency
- HIGH: Large failed transactions, account locked, can't access funds
- MEDIUM: Refund requests, payment disputes, transaction issues
- LOW: Password help, general questions, documentation

**Intent Types:**
- fraud_alert
- transaction_failed
- refund_request
- account_locked
- payment_dispute
- general_inquiry

**Record Status Values:**
- PENDING_REVIEW - New record awaiting human review
- REVIEWED - Human has reviewed the record
- ESCALATED - Escalated to specialist team
- RESOLVED - Issue has been resolved
- CLOSED - Case is closed

## Development

### Debug Logging

The app prints classification logs with prefixes for debugging:
- `[CLASSIFY]` - Classification process logs
- `[GENERATE]` - Response generation logs
- `[PARSE]` - JSON parsing logs

## License

MIT
