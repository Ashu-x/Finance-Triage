"""
Database module for Finance Triage Agent
Stores triage records in PostgreSQL for human review and analysis
"""

import os
import csv
from datetime import datetime
from pathlib import Path
from sqlalchemy import create_engine, Column, String, Float, DateTime, Integer, Text, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

load_dotenv()

# Database configuration
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://user:password@localhost:5432/finance_triage"
)

# Create database engine with connection pooling for cloud databases like Neon
# For Neon DB, we need to handle SSL and connection pool settings
engine = create_engine(
    DATABASE_URL,
    echo=False,  # Set to True only for debugging
    connect_args={
        "connect_timeout": 10,
        "keepalives": 1,
        "keepalives_idle": 30,
    },
    pool_pre_ping=True,  # Test connections before using them
    pool_size=5,
    max_overflow=10
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class TriageRecord(Base):
    """
    Database model for storing triage records.
    Each record represents one customer complaint/inquiry processed by the agent.
    """
    __tablename__ = "triage_records"

    id = Column(Integer, primary_key=True, index=True)
    
    # Timestamp and metadata
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    request_ip = Column(String(50), nullable=True)
    
    # Customer input
    customer_message = Column(Text, nullable=False)
    message_length = Column(Integer)
    
    # Classification results
    urgency = Column(String(20), nullable=False, index=True)  # CRITICAL, HIGH, MEDIUM, LOW
    intent = Column(String(50), nullable=False, index=True)  # fraud_alert, refund_request, etc.
    confidence = Column(Float)  # 0.0 to 1.0
    
    # Extracted entities (stored as JSON for flexibility)
    transaction_ids = Column(JSON)  # List of TXN IDs
    amounts = Column(JSON)  # List of amounts
    dates = Column(JSON)  # List of dates
    account_numbers = Column(JSON)  # List of account numbers
    
    # Generated response
    ai_response = Column(Text, nullable=False)
    
    # Processing details
    processing_time_ms = Column(Float)  # How long did processing take?
    
    # Human review tracking
    status = Column(String(50), default="PENDING_REVIEW", index=True)
    # Status options: PENDING_REVIEW, REVIEWED, ESCALATED, RESOLVED, CLOSED


def init_db():
    """Create all database tables"""
    try:
        Base.metadata.create_all(bind=engine)
        print("INFO: Database initialized successfully")
    except Exception as e:
        print(f"ERROR: Database initialization failed: {e}")
        raise


def get_db():
    """Get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def save_triage_record(
    customer_message: str,
    urgency: str,
    intent: str,
    confidence: float,
    transaction_ids: list,
    amounts: list,
    dates: list,
    account_numbers: list,
    ai_response: str,
    processing_time_ms: float,
    request_ip: str = "127.0.0.1"
) -> TriageRecord:
    """
    Save a triage record to the database.
    
    Args:
        customer_message: Original customer message
        urgency: Classification urgency level
        intent: Classification intent
        confidence: Confidence score (0-1)
        transaction_ids: List of extracted transaction IDs
        amounts: List of extracted amounts
        dates: List of extracted dates
        account_numbers: List of extracted account numbers
        ai_response: Generated AI response
        processing_time_ms: Processing time in milliseconds
        request_ip: Client IP address
    
    Returns:
        The saved TriageRecord object
    """
    db = SessionLocal()
    try:
        record = TriageRecord(
            customer_message=customer_message,
            message_length=len(customer_message),
            urgency=urgency,
            intent=intent,
            confidence=confidence,
            transaction_ids=transaction_ids,
            amounts=amounts,
            dates=dates,
            account_numbers=account_numbers,
            ai_response=ai_response,
            processing_time_ms=processing_time_ms,
            request_ip=request_ip,
            status="PENDING_REVIEW"
        )
        db.add(record)
        db.commit()
        db.refresh(record)
        return record
    finally:
        db.close()


def get_all_records(skip: int = 0, limit: int = 100):
    """Fetch all triage records with pagination"""
    db = SessionLocal()
    try:
        records = db.query(TriageRecord).offset(skip).limit(limit).all()
        return records
    finally:
        db.close()


def get_records_by_status(status: str, skip: int = 0, limit: int = 100):
    """Fetch records by status (for filtering in UI)"""
    db = SessionLocal()
    try:
        records = db.query(TriageRecord).filter(
            TriageRecord.status == status
        ).offset(skip).limit(limit).all()
        return records
    finally:
        db.close()


def get_records_by_urgency(urgency: str, skip: int = 0, limit: int = 100):
    """Fetch records by urgency level"""
    db = SessionLocal()
    try:
        records = db.query(TriageRecord).filter(
            TriageRecord.urgency == urgency
        ).offset(skip).limit(limit).all()
        return records
    finally:
        db.close()


def get_record_by_id(record_id: int):
    """Fetch a specific record by ID"""
    db = SessionLocal()
    try:
        record = db.query(TriageRecord).filter(
            TriageRecord.id == record_id
        ).first()
        return record
    finally:
        db.close()


def update_record_status(record_id: int, status: str, notes: str = None, reviewed_by: str = None):
    """Update record status"""
    db = SessionLocal()
    try:
        record = db.query(TriageRecord).filter(
            TriageRecord.id == record_id
        ).first()
        if record:
            record.status = status
            db.commit()
        return record
    finally:
        db.close()


def export_to_csv(output_path: str = "triage_export.csv", status_filter: str = None):
    """
    Export triage records to CSV file for human review in Excel
    
    Args:
        output_path: Where to save the CSV file
        status_filter: Optional filter by status (e.g., "PENDING_REVIEW")
    """
    db = SessionLocal()
    try:
        if status_filter:
            records = db.query(TriageRecord).filter(
                TriageRecord.status == status_filter
            ).all()
        else:
            records = db.query(TriageRecord).all()
        
        if not records:
            return None
        
        # CSV columns
        with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = [
                'ID', 'Timestamp', 'Customer Message', 'Urgency', 'Intent',
                'Confidence', 'Transaction IDs', 'Amounts', 'Dates', 'Account Numbers',
                'AI Response', 'Processing Time (ms)', 'Status', 'Reviewer Notes',
                'Reviewed At', 'Reviewed By'
            ]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            
            for record in records:
                writer.writerow({
                    'ID': record.id,
                    'Timestamp': record.timestamp.isoformat() if record.timestamp else '',
                    'Customer Message': record.customer_message[:100] + '...' if len(record.customer_message) > 100 else record.customer_message,
                    'Urgency': record.urgency,
                    'Intent': record.intent,
                    'Confidence': f"{record.confidence:.2f}" if record.confidence else '',
                    'Transaction IDs': ', '.join(record.transaction_ids) if record.transaction_ids else '',
                    'Amounts': ', '.join(record.amounts) if record.amounts else '',
                    'Dates': ', '.join(record.dates) if record.dates else '',
                    'Account Numbers': ', '.join(record.account_numbers) if record.account_numbers else '',
                    'AI Response': record.ai_response[:100] + '...' if len(record.ai_response) > 100 else record.ai_response,
                    'Processing Time (ms)': f"{record.processing_time_ms:.0f}",
                    'Status': record.status,
                    'Reviewer Notes': record.reviewer_notes or '',
                    'Reviewed At': record.reviewed_at.isoformat() if record.reviewed_at else '',
                    'Reviewed By': record.reviewed_by or ''
                })
        
        return output_path
    finally:
        db.close()


def get_statistics():
    """Get statistics about triage records for dashboard"""
    db = SessionLocal()
    try:
        total = db.query(TriageRecord).count()
        pending = db.query(TriageRecord).filter(
            TriageRecord.status == "PENDING_REVIEW"
        ).count()
        critical = db.query(TriageRecord).filter(
            TriageRecord.urgency == "CRITICAL"
        ).count()
        high = db.query(TriageRecord).filter(
            TriageRecord.urgency == "HIGH"
        ).count()
        
        return {
            "total_records": total,
            "pending_review": pending,
            "critical_urgency": critical,
            "high_urgency": high
        }
    finally:
        db.close()
