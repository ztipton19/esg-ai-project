"""Utility functions for ESG automation system"""
import os
from dotenv import load_dotenv
import anthropic
import base64
from io import BytesIO

# Load environment variables
load_dotenv()

def get_claude_client():
    """Initialize and return Claude API client"""
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY not found in .env file")
    return anthropic.Anthropic(api_key=api_key)

def call_claude_with_cost(prompt, max_tokens=1024, model="claude-sonnet-4-20250514", system_prompt=None, temperature=0):
    """
    Make Claude API call and track costs
    
    Args:
        prompt: Text prompt for Claude
        max_tokens: Maximum tokens in response
        model: Claude model to use
        system_prompt: Optional system-level instructions
        temperature: Randomness (0=deterministic, 1=creative). Default 0 for accuracy
        
    Returns:
        tuple: (response_text, cost_info_dict)
    """
    client = get_claude_client()
    
    # Build API call parameters
    api_params = {
        "model": model,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "messages": [{"role": "user", "content": prompt}]
    }
    
    # Add system prompt if provided
    if system_prompt:
        api_params["system"] = system_prompt
    
    response = client.messages.create(**api_params)
    
    # Extract usage info
    input_tokens = response.usage.input_tokens
    output_tokens = response.usage.output_tokens
    
    # Calculate costs (Claude Sonnet 4 pricing)
    input_cost = (input_tokens / 1_000_000) * 3.00
    output_cost = (output_tokens / 1_000_000) * 15.00
    total_cost = input_cost + output_cost
    
    cost_info = {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_cost": total_cost
    }
    
    return response.content[0].text, cost_info


# ============================================================================
# PDF UTILITIES - AI-POWERED EXTRACTION
# ============================================================================

def pdf_to_base64(pdf_file):
    """
    Convert uploaded PDF to base64 for Claude API
    
    Args:
        pdf_file: Streamlit UploadedFile object
        
    Returns:
        str: Base64 encoded PDF
    """
    pdf_bytes = pdf_file.read()
    return base64.standard_b64encode(pdf_bytes).decode('utf-8')


def extract_from_pdf_with_ai(pdf_file):
    """
    Extract utility bill data directly from PDF using Claude's native PDF support
    
    This uses Claude's document understanding capabilities to read PDFs directly,
    bypassing traditional OCR libraries. More reliable for complex layouts and scanned documents.
    
    Args:
        pdf_file: Streamlit UploadedFile object
        
    Returns:
        dict: Extracted data or error information
        
    Cost: ~$0.02-0.04 per PDF (higher than text extraction, but more reliable)
    
    Note: For production scale (>1,000 bills/month), consider implementing a hybrid
    approach with open-source OCR models (see v2.0 roadmap).
    """
    # Convert PDF to base64
    pdf_base64 = pdf_to_base64(pdf_file)
    
    # Create extraction prompt
    prompt = """Extract utility bill information from this PDF and return as valid JSON.

Extract these fields:
- account_number (string)
- service_start_date (YYYY-MM-DD format)
- service_end_date (YYYY-MM-DD format)
- total_usage (number - the actual value shown on the bill)
- usage_unit (string - "kWh", "MWh", "therms", etc.)
- total_cost (number - dollars, no $ symbol)

CRITICAL: Return ONLY the raw JSON object with no markdown, no backticks, no explanatory text.
If a field is not found, use null.

Example format:
{"account_number": "123456", "service_start_date": "2024-11-01", "service_end_date": "2024-11-30", "total_usage": 850, "usage_unit": "kWh", "total_cost": 127.50}"""

    try:
        client = get_claude_client()
        
        # Call Claude with PDF document
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            temperature=0,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "document",
                            "source": {
                                "type": "base64",
                                "media_type": "application/pdf",
                                "data": pdf_base64
                            }
                        },
                        {
                            "type": "text",
                            "text": prompt
                        }
                    ]
                }
            ]
        )
        
        # Calculate cost
        input_tokens = response.usage.input_tokens
        output_tokens = response.usage.output_tokens
        extraction_cost = (input_tokens / 1_000_000) * 3.00 + (output_tokens / 1_000_000) * 15.00
        
        # Parse response
        response_text = response.content[0].text
        
        # Clean JSON (remove markdown if present)
        import re
        import json
        
        json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
        if not json_match:
            return {
                "success": False,
                "error": "AI could not extract structured data from PDF",
                "cost": extraction_cost
            }
        
        data = json.loads(json_match.group())
        
        # Add metadata
        data['extraction_cost'] = extraction_cost
        data['extraction_method'] = 'AI-powered (Claude PDF vision)'
        
        return {
            "success": True,
            "data": data,
            "cost": extraction_cost
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": f"AI extraction failed: {str(e)}",
            "cost": 0
        }


# ============================================================================
# LEGACY PDF EXTRACTION (Fallback - not recommended)
# ============================================================================

def extract_text_from_pdf_legacy(pdf_file):
    """
    Legacy text extraction using PyPDF2
    
    NOTE: This often fails with complex PDFs. Use extract_from_pdf_with_ai() instead.
    Kept for backwards compatibility only.
    
    Args:
        pdf_file: Streamlit UploadedFile object
        
    Returns:
        str: Extracted text from all pages
    """
    try:
        import PyPDF2
        
        # Read PDF from uploaded file
        pdf_reader = PyPDF2.PdfReader(BytesIO(pdf_file.read()))
        
        # Extract text from all pages
        text = ""
        for page_num, page in enumerate(pdf_reader.pages):
            try:
                page_text = page.extract_text()
                
                if page_text and page_text.strip():
                    text += page_text + "\n\n"
                else:
                    text += f"[Page {page_num + 1}: No extractable text]\n\n"
                    
            except Exception as page_error:
                text += f"[Page {page_num + 1}: Error extracting text - {str(page_error)}]\n\n"
                continue
        
        if not text.strip() or len(text.strip()) < 50:
            raise ValueError(
                "Could not extract readable text from PDF. "
                "Please use AI-powered extraction instead."
            )
        
        return text.strip()
        
    except Exception as e:
        raise ValueError(f"Legacy PDF extraction failed: {str(e)}")


# Test it
if __name__ == "__main__":
    response, cost = call_claude_with_cost("What is ESG reporting?")
    print(f"Response: {response}")
    print(f"Cost: ${cost['total_cost']:.4f}")