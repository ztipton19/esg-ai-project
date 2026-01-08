"""Utility functions for ESG automation system"""
import os
from dotenv import load_dotenv
import anthropic
import PyPDF2
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
        
    Returns:
        tuple: (response_text, cost_info_dict)
    """
    client = get_claude_client()
    
    # Build API call parameters
    api_params = {
        "model": model,
        "max_tokens": max_tokens,
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
# PDF UTILITIES
# ============================================================================

def extract_text_from_pdf(pdf_file):
    """
    Extract text from uploaded PDF file with robust error handling
    
    Args:
        pdf_file: Streamlit UploadedFile object
        
    Returns:
        str: Extracted text from all pages
    """
    try:
        # Read PDF from uploaded file
        pdf_reader = PyPDF2.PdfReader(BytesIO(pdf_file.read()))
        
        # Extract text from all pages
        text = ""
        for page_num, page in enumerate(pdf_reader.pages):
            try:
                page_text = page.extract_text()
                
                # Handle NullObject or None
                if page_text and page_text.strip():
                    text += page_text + "\n\n"
                else:
                    # Page might be scanned or empty
                    text += f"[Page {page_num + 1}: No extractable text]\n\n"
                    
            except Exception as page_error:
                # Skip problematic pages but continue
                text += f"[Page {page_num + 1}: Error extracting text - {str(page_error)}]\n\n"
                continue
        
        # Check if we got any usable text
        if not text.strip() or len(text.strip()) < 50:
            raise ValueError(
                "Could not extract readable text from PDF. "
                "This might be a scanned document (image-based PDF). "
                "Please try copying the text manually or use a different PDF."
            )
        
        return text.strip()
        
    except Exception as e:
        # More helpful error message
        error_msg = str(e)
        if "NullObject" in error_msg:
            raise ValueError(
                "This PDF appears to have formatting issues or is password-protected. "
                "Try: (1) Copy-paste the text manually, or (2) Save the PDF from your email/browser again."
            )
        elif "decrypt" in error_msg.lower():
            raise ValueError("This PDF is password-protected. Please use an unprotected version.")
        else:
            raise ValueError(f"Failed to extract text from PDF: {error_msg}")


def validate_pdf_content(text, min_length=50):
    """
    Validate that extracted text is usable
    
    Args:
        text: Extracted text
        min_length: Minimum character length
        
    Returns:
        bool: True if valid, False otherwise
    """
    if not text or len(text) < min_length:
        return False
    
    # Check for common utility bill keywords (case-insensitive)
    utility_keywords = [
        "account", "bill", "kwh", "usage", "electric",
        "water", "gas", "service", "charge", "total",
        "meter", "billing", "due", "payment", "amount",
        "current", "balance", "customer"
    ]
    
    text_lower = text.lower()
    found_keywords = sum(1 for kw in utility_keywords if kw in text_lower)
    
    # Only need 2 keywords now (less strict)
    if found_keywords >= 2:
        return True
    
    # Also check for numeric patterns common in bills
    import re
    has_dollar_amounts = bool(re.search(r'\$\s*\d+\.\d{2}', text))
    has_kwh = 'kwh' in text_lower
    has_account = 'account' in text_lower or '#' in text
    
    # If it has money + (kWh or account), it's probably a bill
    return has_dollar_amounts and (has_kwh or has_account)

# Test it
if __name__ == "__main__":
    response, cost = call_claude_with_cost("What is ESG reporting?")
    print(f"Response: {response}")
    print(f"Cost: ${cost['total_cost']:.4f}")