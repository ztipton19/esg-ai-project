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
    Extract text from uploaded PDF file
    
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
        for page in pdf_reader.pages:
            page_text = page.extract_text()
            text += page_text + "\n\n"
        
        return text.strip()
        
    except Exception as e:
        raise ValueError(f"Failed to extract text from PDF: {str(e)}")


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
    
    # Check for common utility bill keywords
    utility_keywords = [
        "account", "bill", "kwh", "usage", "electric",
        "water", "gas", "service", "charge", "total",
        "meter", "billing", "due", "payment"
    ]
    
    text_lower = text.lower()
    found_keywords = sum(1 for kw in utility_keywords if kw in text_lower)
    
    # Should have at least 3 utility-related keywords
    return found_keywords >= 3

# Test it
if __name__ == "__main__":
    response, cost = call_claude_with_cost("What is ESG reporting?")
    print(f"Response: {response}")
    print(f"Cost: ${cost['total_cost']:.4f}")