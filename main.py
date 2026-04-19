"""
Main Triage Pipeline - Orchestrates the entire triage workflow
Combines classification, entity extraction, and response generation
"""

# CRITICAL: Load environment variables BEFORE importing modules that use Groq
import os
from dotenv import load_dotenv
load_dotenv()

import json
import time
from triage_models import TriageReport
from classifier import classify
from entity_extractor import extract_entities
from response_writer import generate


def triage_message(message_text: str) -> TriageReport:
    """
    Main triage function: Analyze a support message end-to-end.
    
    Process:
    1. Classify urgency and intent
    2. Extract financial entities
    3. Generate draft response
    4. Combine into structured report
    
    Args:
        message_text: The customer support message
    
    Returns:
        TriageReport with complete analysis
    """
    
    start_time = time.time()
    
    try:
        # Step 1: Classify the message
        classification = classify(message_text)
        
        # Step 2: Extract entities
        entities = extract_entities(message_text)
        
        # Step 3: Generate response
        draft_response = generate(
            message_text=message_text,
            urgency=classification.urgency,
            intent=classification.intent,
            transaction_ids=entities.transaction_ids,
            amounts=entities.amounts,
            dates=entities.dates
        )
        
        # Step 4: Combine into triage report
        processing_time_ms = (time.time() - start_time) * 1000
        
        triage_report = TriageReport(
            original_message=message_text,
            classification=classification,
            extracted_entities=entities,
            draft_response=draft_response,
            processing_time_ms=processing_time_ms
        )
        
        return triage_report
    
    except Exception as e:
        print(f"ERROR: Triage failed - {e}")
        raise


def print_triage_report(report: TriageReport):
    """
    Pretty-print the triage report in a readable format.
    """
    print("\n" + "="*60)
    print("TRIAGE REPORT")
    print("="*60)
    
    print("\nORIGINAL MESSAGE:")
    print(f"  {report.original_message}\n")
    
    print("CLASSIFICATION:")
    print(f"  Urgency:   {report.classification.urgency}")
    print(f"  Intent:    {report.classification.intent}")
    print(f"  Confidence: {report.classification.confidence:.2f}\n")
    
    print("EXTRACTED ENTITIES:")
    if report.extracted_entities.transaction_ids:
        print(f"  Transaction IDs: {', '.join(report.extracted_entities.transaction_ids)}")
    if report.extracted_entities.amounts:
        print(f"  Amounts: {', '.join(report.extracted_entities.amounts)}")
    if report.extracted_entities.dates:
        print(f"  Dates: {', '.join(report.extracted_entities.dates)}")
    if report.extracted_entities.account_numbers:
        print(f"  Account Numbers: {', '.join(report.extracted_entities.account_numbers)}")
    if not any([
        report.extracted_entities.transaction_ids,
        report.extracted_entities.amounts,
        report.extracted_entities.dates,
        report.extracted_entities.account_numbers
    ]):
        print("  No financial entities found\n")
    else:
        print()
    
    print("DRAFT RESPONSE:")
    print(f"  {report.draft_response}\n")
    
    print(f"Processing Time: {report.processing_time_ms:.0f}ms")
    print("="*60 + "\n")


def print_triage_json(report: TriageReport):
    """
    Output triage report as JSON (for API integration).
    """
    report_dict = report.model_dump()
    print(json.dumps(report_dict, indent=2))


if __name__ == "__main__":
    # Sample test messages
    sample_messages = [
        "I was charged $500 for a transaction TXN123456 that never went through. This happened on 2024-01-15. I need this refunded immediately!",
        "Can you help me reset my password?",
        "There's been fraudulent activity on my account. Multiple unauthorized transactions of $1000, $500, and $250 were made yesterday. Account ending in 4567."
    ]
    
    print("\nFinance Support Triage Agent")
    print("Processing sample message #1...\n")
    
    # Check if API key is set
    if not os.getenv("GROQ_API_KEY") or os.getenv("GROQ_API_KEY") == "your_api_key_here":
        print("ERROR: GROQ_API_KEY not configured in .env file")
        print("Please set GROQ_API_KEY in .env and try again.")
        exit(1)
    
    try:
        # Process the first sample message
        report = triage_message(sample_messages[0])
        
        # Display results
        print_triage_report(report)
        
        # Also show JSON output for reference
        print("\nJSON OUTPUT (for API integration):")
        print_triage_json(report)
        
    except Exception as e:
        print(f"Failed to process message: {e}")
        exit(1)
