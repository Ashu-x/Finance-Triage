"""
FastAPI Web Server for Finance Triage Agent
Provides REST API and serves HTML frontend
"""

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse
import os
import json
import time
from datetime import datetime
from pathlib import Path
import logging

from dotenv import load_dotenv
load_dotenv()

from triage_models import TriageReport
from classifier import classify
from entity_extractor import extract_entities
from response_writer import generate
from database import init_db, save_triage_record, get_all_records, get_records_by_status, get_records_by_urgency, get_record_by_id, update_record_status, export_to_csv, get_statistics


# Create FastAPI app
app = FastAPI(title="Finance Triage Agent", version="1.0")

# Initialize database on startup
try:
    init_db()
except Exception as e:
    print(f"ERROR: Database initialization failed: {e}")
    print("Make sure DATABASE_URL is correctly configured in .env")

# Configure Python logging - database only, no files
logging.basicConfig(
    level=logging.WARNING,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)

# Suppress verbose logging from external libraries
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("uvicorn").setLevel(logging.WARNING)
logging.getLogger("sqlalchemy").setLevel(logging.WARNING)



@app.get("/")
async def get_homepage():
    """Serve the HTML frontend"""
    return FileResponse("index.html")


@app.post("/api/triage")
async def triage_endpoint(request_data: dict):
    """
    API endpoint for triage processing - saves to database only.
    
    Expected request:
    {
        "message": "Customer support message"
    }
    
    Returns:
    {
        "success": bool,
        "record_id": int,
        "classification": {...},
        "entities": {...},
        "response": "...",
        "processing_time_ms": float
    }
    """
    
    try:
        message = request_data.get("message", "").strip()
        
        if not message:
            logger.warning("Empty message received")
            raise HTTPException(status_code=400, detail="Message cannot be empty")
        
        start_time = time.time()
        
        # Step 1: Classify
        classification = classify(message)
        
        # Step 2: Extract entities
        entities = extract_entities(message)
        
        # Step 3: Generate response
        response = generate(
            message_text=message,
            urgency=classification.urgency,
            intent=classification.intent,
            transaction_ids=entities.transaction_ids,
            amounts=entities.amounts,
            dates=entities.dates
        )
        
        # Create triage report
        processing_time = (time.time() - start_time) * 1000
        report = TriageReport(
            original_message=message,
            classification=classification,
            extracted_entities=entities,
            draft_response=response,
            processing_time_ms=processing_time
        )
        
        # Save to DATABASE only
        record_id = None
        try:
            db_record = save_triage_record(
                customer_message=message,
                urgency=classification.urgency,
                intent=classification.intent,
                confidence=float(classification.confidence),
                transaction_ids=entities.transaction_ids,
                amounts=entities.amounts,
                dates=entities.dates,
                account_numbers=entities.account_numbers,
                ai_response=response,
                processing_time_ms=processing_time
            )
            record_id = db_record.id
        except Exception as db_error:
            logger.error(f"Database save failed: {db_error}")
        
        # Return response
        return {
            "success": True,
            "record_id": record_id,
            "classification": {
                "urgency": classification.urgency,
                "intent": classification.intent,
                "confidence": float(classification.confidence)
            },
            "entities": {
                "transaction_ids": entities.transaction_ids,
                "amounts": entities.amounts,
                "dates": entities.dates,
                "account_numbers": entities.account_numbers
            },
            "response": response,
            "processing_time_ms": float(processing_time)
        }
    
    except HTTPException:
        raise
    except Exception as e:
        error_msg = f"Triage failed: {str(e)}"
        logger.error(error_msg)
        raise HTTPException(status_code=500, detail=error_msg)



@app.get("/api/database/records")
async def get_database_records(skip: int = 0, limit: int = 50):
    """
    Get all triage records from the database.
    Supports pagination.
    """
    try:
        records = get_all_records(skip=skip, limit=limit)
        return {
            "success": True,
            "total": len(records),
            "records": [
                {
                    "id": r.id,
                    "timestamp": r.timestamp.isoformat() if r.timestamp else None,
                    "customer_message": r.customer_message[:150] + "..." if len(r.customer_message) > 150 else r.customer_message,
                    "urgency": r.urgency,
                    "intent": r.intent,
                    "confidence": float(r.confidence) if r.confidence else None,
                    "transaction_ids": r.transaction_ids,
                    "amounts": r.amounts,
                    "status": r.status,
                    "processing_time_ms": r.processing_time_ms
                }
                for r in records
            ]
        }
    except Exception as e:
        logger.error(f"Failed to get database records: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve records")


@app.get("/api/database/records/{record_id}")
async def get_database_record_detail(record_id: int):
    """
    Get full details of a specific triage record from the database.
    """
    try:
        record = get_record_by_id(record_id)
        if not record:
            raise HTTPException(status_code=404, detail="Record not found")
        
        return {
            "success": True,
            "record": {
                "id": record.id,
                "timestamp": record.timestamp.isoformat() if record.timestamp else None,
                "customer_message": record.customer_message,
                "urgency": record.urgency,
                "intent": record.intent,
                "confidence": float(record.confidence) if record.confidence else None,
                "transaction_ids": record.transaction_ids,
                "amounts": record.amounts,
                "dates": record.dates,
                "account_numbers": record.account_numbers,
                "ai_response": record.ai_response,
                "processing_time_ms": record.processing_time_ms,
                "status": record.status
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get database record: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve record")


@app.get("/api/database/records/status/{status}")
async def get_records_by_status_endpoint(status: str, skip: int = 0, limit: int = 50):
    """
    Get triage records filtered by status.
    Statuses: PENDING_REVIEW, REVIEWED, ESCALATED, RESOLVED, CLOSED
    """
    try:
        records = get_records_by_status(status=status, skip=skip, limit=limit)
        return {
            "success": True,
            "status": status,
            "total": len(records),
            "records": [
                {
                    "id": r.id,
                    "timestamp": r.timestamp.isoformat() if r.timestamp else None,
                    "customer_message": r.customer_message[:150] + "..." if len(r.customer_message) > 150 else r.customer_message,
                    "urgency": r.urgency,
                    "intent": r.intent,
                    "status": r.status
                }
                for r in records
            ]
        }
    except Exception as e:
        logger.error(f"Failed to get records by status: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve records")


@app.post("/api/database/records/{record_id}/update")
async def update_record_endpoint(record_id: int, update_data: dict):
    """
    Update the status of a triage record.
    
    Expected input:
    {
        "status": "REVIEWED" | "ESCALATED" | "RESOLVED" | "CLOSED"
    }
    """
    try:
        status = update_data.get("status")
        
        if not status:
            raise HTTPException(status_code=400, detail="Status is required")
        
        record = update_record_status(record_id, status)
        if not record:
            raise HTTPException(status_code=404, detail="Record not found")
        
        logger.info(f"Updated record {record_id} status to {status}")
        
        return {
            "success": True,
            "message": f"Record {record_id} updated successfully",
            "record_id": record_id,
            "status": status
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update record: {e}")
        raise HTTPException(status_code=500, detail="Failed to update record")


@app.get("/api/database/export")
async def export_database_to_csv(status_filter: str = None):
    """
    Export triage records to CSV format for human review.
    Returns CSV data directly without saving to disk.
    
    Query parameters:
    - status_filter: Optional, filter by status (e.g., PENDING_REVIEW)
    """
    try:
        records = get_records_by_status(status_filter) if status_filter else get_all_records(limit=10000)
        
        if not records:
            raise HTTPException(status_code=404, detail="No records to export")
        
        # Build CSV data in memory
        import io
        output = io.StringIO()
        writer = __import__('csv').DictWriter(output, fieldnames=[
            'id', 'timestamp', 'customer_message', 'urgency', 'intent', 'confidence',
            'transaction_ids', 'amounts', 'dates', 'account_numbers', 
            'ai_response', 'processing_time_ms', 'status'
        ])
        writer.writeheader()
        
        for r in records:
            writer.writerow({
                'id': r.id,
                'timestamp': r.timestamp.isoformat() if r.timestamp else '',
                'customer_message': r.customer_message,
                'urgency': r.urgency,
                'intent': r.intent,
                'confidence': r.confidence,
                'transaction_ids': json.dumps(r.transaction_ids) if r.transaction_ids else '',
                'amounts': json.dumps(r.amounts) if r.amounts else '',
                'dates': json.dumps(r.dates) if r.dates else '',
                'account_numbers': json.dumps(r.account_numbers) if r.account_numbers else '',
                'ai_response': r.ai_response,
                'processing_time_ms': r.processing_time_ms,
                'status': r.status
            })
        
        csv_data = output.getvalue()
        return JSONResponse({
            "success": True,
            "format": "csv",
            "data": csv_data,
            "filename": f"triage_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        })
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to export CSV: {e}")
        raise HTTPException(status_code=500, detail="Failed to export data")


@app.get("/api/database/statistics")
async def get_database_statistics():
    """
    Get statistics about all triage records in the database.
    """
    try:
        stats = get_statistics()
        return {
            "success": True,
            "statistics": stats
        }
    except Exception as e:
        logger.error(f"Failed to get database statistics: {e}")
        raise HTTPException(status_code=500, detail="Failed to get statistics")


if __name__ == "__main__":
    import uvicorn
    logger.info("Starting Finance Triage Agent Web Server...")
    logger.info("Open browser: http://localhost:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000)
