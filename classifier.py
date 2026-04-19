"""
Classifier Agent - Classifies support messages by urgency and intent
Uses Groq API for fast, reliable classification
"""

import os
import json
from groq import Groq
from triage_models import ClassificationResult

client = Groq(api_key=os.getenv("GROQ_API_KEY"))


def safe_parse_json(response_text):
    """
    Safely extract and parse JSON from LLM response.
    """
    try:
        response_text = response_text.strip()
        print(f"[PARSE] Input: {response_text[:80]}...")
        
        if response_text.startswith("```json"):
            response_text = response_text[7:]
        if response_text.startswith("```"):
            response_text = response_text[3:]
        if response_text.endswith("```"):
            response_text = response_text[:-3]

        start = response_text.find("{")
        end = response_text.rfind("}") + 1
        if start == -1 or end == 0:
            print(f"[PARSE] No JSON braces found")
            return None
        json_str = response_text[start:end]
        print(f"[PARSE] Extracted: {json_str}")
        result = json.loads(json_str)
        print(f"[PARSE] Parsed successfully: {result}")
        return result
    except Exception as e:
        print(f"[PARSE] JSON parsing error: {type(e).__name__}: {e}")
        return None


def classify(message_text: str, retry_count=0) -> ClassificationResult:
    """
    Classify a finance support message by urgency and intent.
    """

    prompt = f"""You are a finance support classifier. Your ONLY job is to return valid JSON.

Analyze this message: {message_text}

Return ONLY this JSON format, nothing else:
{{"urgency": "CRITICAL", "intent": "fraud_alert", "confidence": 0.95}}

Rules for urgency:
- CRITICAL: fraud, unauthorized charges, payroll failure, system outage, emergency
- HIGH: large failed transaction, account locked, can't access funds, immediate need
- MEDIUM: refund request, payment dispute, transaction issue
- LOW: password help, general question, documentation request

Rules for intent:
- fraud_alert: unauthorized/fraudulent activity
- transaction_failed: payment didn't go through
- refund_request: customer wants money back
- account_locked: can't access account
- payment_dispute: disagrees with charge
- general_inquiry: other questions

Rules for confidence:
- 0.9-1.0: Very clear intent and urgency
- 0.7-0.9: Clear but some ambiguity
- 0.5-0.7: Some uncertainty
- Below 0.5: Very unclear

Output ONLY the JSON object. No markdown. No explanation. No extra text."""

    try:
        print(f"[CLASSIFY] Calling Groq API with model: llama-3.1-8b-instant")
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            max_tokens=200,
            messages=[{"role": "user", "content": prompt}]
        )

        response_text = response.choices[0].message.content
        print(f"[CLASSIFY] Raw response: {response_text[:100]}...")

        result = safe_parse_json(response_text)
        print(f"[CLASSIFY] Parsed result: {result}")

        if result is None and retry_count == 0:
            print(f"[CLASSIFY] First parse failed, retrying...")
            return classify(message_text, retry_count=1)

        if result is None:
            print(f"[CLASSIFY] Second parse failed, using fallback")
            return ClassificationResult(
                urgency="MEDIUM",
                intent="general_inquiry",
                confidence=0.5
            )

        # Validate urgency value
        valid_urgencies = ["CRITICAL", "HIGH", "MEDIUM", "LOW"]
        if result.get("urgency", "").upper() not in valid_urgencies:
            result["urgency"] = "MEDIUM"

        # Validate intent value
        valid_intents = [
            "fraud_alert", "transaction_failed", "refund_request",
            "account_locked", "payment_dispute", "general_inquiry"
        ]
        if result.get("intent", "") not in valid_intents:
            result["intent"] = "general_inquiry"

        # Ensure urgency is uppercase
        result["urgency"] = result["urgency"].upper()

        print(f"[CLASSIFY] Success: {result['urgency']}/{result['intent']}")
        return ClassificationResult(**result)

    except Exception as e:
        print(f"[CLASSIFY] ERROR: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        if retry_count == 0:
            return classify(message_text, retry_count=1)

        return ClassificationResult(
            urgency="MEDIUM",
            intent="general_inquiry",
            confidence=0.5
        )