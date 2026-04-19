"""
Entity Extractor - Extracts financial entities using regex and spaCy
Identifies transaction IDs, amounts, dates, and account numbers
"""

import re
from triage_models import ExtractedEntities

try:
    import spacy
    # Load spaCy model for NER
    nlp = spacy.load("en_core_web_sm")
except OSError:
    nlp = None


def extract_transaction_ids(text: str) -> list:
    """
    Extract transaction IDs (common formats: TXN, TX, REF followed by numbers/alphanumerics)
    Examples: TXN123456, TX-789ABC, REF-2024-001
    """
    patterns = [
        r'TXN[A-Z0-9\-]{5,}',
        r'TX[#\-]?[A-Z0-9]{6,}',
        r'REF[#\-]?[A-Z0-9]{4,}',
        r'[A-Z]{3}\d{8,}'  # 3 letters + 8+ digits
    ]
    
    matches = []
    for pattern in patterns:
        matches.extend(re.findall(pattern, text, re.IGNORECASE))
    
    return list(set(matches))  # Remove duplicates


def extract_amounts(text: str) -> list:
    """
    Extract monetary amounts (various formats: $1000, 1000 USD, £500.99, etc.)
    """
    patterns = [
        r'\$[\d,]+(?:\.\d{2})?',  # $1,000.00
        r'£[\d,]+(?:\.\d{2})?',   # £500.99
        r'€[\d,]+(?:\.\d{2})?',   # €250.50
        r'[\d,]+\s*(USD|EUR|GBP|INR)',  # 1000 USD
        r'[\d,]+(?:\.\d{2})?\s*(?:dollars|euros|pounds)',
    ]
    
    matches = []
    for pattern in patterns:
        matches.extend(re.findall(pattern, text, re.IGNORECASE))
    
    return list(set(matches))  # Remove duplicates


def extract_dates(text: str) -> list:
    """
    Extract dates in common formats: MM/DD/YYYY, DD-MM-YYYY, YYYY-MM-DD, Month DD, YYYY
    """
    patterns = [
        r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}',  # MM/DD/YYYY or DD-MM-YYYY
        r'\d{4}[/-]\d{1,2}[/-]\d{1,2}',    # YYYY-MM-DD
        r'(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{1,2},?\s+\d{4}',  # Month DD, YYYY
    ]
    
    matches = []
    for pattern in patterns:
        matches.extend(re.findall(pattern, text, re.IGNORECASE))
    
    return list(set(matches))  # Remove duplicates


def extract_account_numbers(text: str) -> list:
    """
    Extract account numbers (last 4 digits format or full account patterns)
    Examples: ****1234, Account ending in 5678
    """
    patterns = [
        r'\*{3,4}\d{4}',  # ****1234
        r'(?:account|acct).*?(\d{4,})',  # account 123456789
        r'acc(?:ount)?\s*#?\s*(\d{6,})',  # acc# 123456
    ]
    
    matches = []
    for pattern in patterns:
        found = re.findall(pattern, text, re.IGNORECASE)
        matches.extend(found)
    
    return list(set(matches))  # Remove duplicates


def extract_entities(message_text: str) -> ExtractedEntities:
    """
    Main function: Extract all financial entities from message.
    Uses regex for structured data and spaCy for NER as fallback.
    
    Args:
        message_text: The customer message to analyze
    
    Returns:
        ExtractedEntities with lists of identified financial entities
    """
    
    # Extract using regex patterns
    transaction_ids = extract_transaction_ids(message_text)
    amounts = extract_amounts(message_text)
    dates = extract_dates(message_text)
    account_numbers = extract_account_numbers(message_text)
    
    # Optional: Use spaCy NER as additional context if model is loaded
    if nlp:
        try:
            doc = nlp(message_text)
            # spaCy can identify MONEY, DATE, CARDINAL entities
            for ent in doc.ents:
                if ent.label_ == "MONEY" and ent.text not in amounts:
                    amounts.append(ent.text)
                elif ent.label_ == "DATE" and ent.text not in dates:
                    dates.append(ent.text)
        except Exception:
            pass
    
    return ExtractedEntities(
        transaction_ids=transaction_ids,
        amounts=amounts,
        dates=dates,
        account_numbers=account_numbers
    )
