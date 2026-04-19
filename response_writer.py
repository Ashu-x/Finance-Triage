"""
Response Writer Agent - Generates professional draft responses
Uses Groq API to create context-aware support responses
"""

import os
from groq import Groq


# Initialize Groq client
client = Groq(api_key=os.getenv("GROQ_API_KEY"))


def generate(
    message_text: str,
    urgency: str,
    intent: str,
    transaction_ids: list,
    amounts: list,
    dates: list
) -> str:
    """
    Generate a professional draft response based on classification and extracted entities.
    
    Args:
        message_text: Original customer message
        urgency: Urgency level (CRITICAL | HIGH | MEDIUM | LOW)
        intent: Type of support request
        transaction_ids: List of extracted transaction IDs
        amounts: List of extracted monetary amounts
        dates: List of extracted dates
    
    Returns:
        A professional draft response (plain text, no JSON)
    """
    
    # Format entities for prompt
    transaction_ids_str = ", ".join(transaction_ids) if transaction_ids else "None"
    amounts_str = ", ".join(amounts) if amounts else "None"
    dates_str = ", ".join(dates) if dates else "None"
    
    # Build context-specific prompt
    prompt = f"""You are a professional finance support agent. Generate a specific, helpful response.

Customer Issue: {intent.replace('_', ' ').upper()}
Urgency: {urgency}
Message: {message_text}

Extracted Details:
- Transaction IDs: {transaction_ids_str}
- Amounts: {amounts_str}
- Dates: {dates_str}

Guidelines:
1. CRITICAL urgency: Express urgency, escalate immediately, provide specific next steps, mention fraud team/investigation
2. HIGH urgency: Fast response needed, action will be taken soon, provide timeline (4 hours)
3. MEDIUM urgency: Professional and reassuring, mention timeline (24 hours), reference specific details if available
4. LOW urgency: Friendly and helpful, guide them through the process

IMPORTANT: 
- Mention specific transaction IDs, amounts, and dates from the extracted details
- Make the response unique to THIS customer's specific issue
- Do NOT use generic/placeholder text
- Keep under 100 words
- Be specific and actionable
- Include specific transaction IDs if available
- Give concrete timelines or next steps

Write ONLY the response text. No JSON. No explanation. No placeholders like [NAME]."""

    try:
        # Call Groq API
        print(f"[GENERATE] Calling Groq API for {urgency}/{intent}")
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            max_tokens=300,
            messages=[{"role": "user", "content": prompt}]
        )
        
        draft_response = response.choices[0].message.content.strip()
        print(f"[GENERATE] Response length: {len(draft_response)} chars")
        
        # Validate response is not empty
        if not draft_response:
            print(f"[GENERATE] Empty response, using fallback")
            return get_fallback_response(urgency)
        
        print(f"[GENERATE] Success")
        return draft_response
    
    except Exception as e:
        print(f"[GENERATE] ERROR: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return get_fallback_response(urgency)


def get_fallback_response(urgency: str) -> str:
    """
    Return a fallback response based on urgency level.
    Used when LLM call fails or returns invalid output.
    """
    fallback_responses = {
        "CRITICAL": (
            "Thank you for reporting this critical issue. We are treating this as top priority "
            "and our fraud investigation team will contact you within 1 hour. Please do not make "
            "any transactions until we investigate further."
        ),
        "HIGH": (
            "Thank you for contacting us about this urgent matter. We have flagged your case for "
            "immediate review by our specialist team. You can expect an update within 4 hours."
        ),
        "MEDIUM": (
            "Thank you for contacting finance support. We have received your message and will review "
            "it carefully. You can expect a response within 24 hours."
        ),
        "LOW": (
            "Thank you for reaching out! We're here to help. We'll get back to you as soon as possible, "
            "usually within 1-2 business days."
        ),
    }
    
    return fallback_responses.get(urgency, fallback_responses["MEDIUM"])
