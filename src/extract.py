# PDF/document extraction

"""Extract data from utility bills using Claude"""
import json
from src.utils import call_claude_with_cost

def extract_utility_bill_data(bill_text):
    """
    Extract structured data from utility bill text
    
    Args:
        bill_text: Raw text from utility bill
        
    Returns:
        dict: Extracted data (kwh, cost, dates, etc.)
    """
    prompt = f"""Extract the following information from this utility bill and return as valid JSON:
- account_number (string)
- service_start_date (YYYY-MM-DD format)
- service_end_date (YYYY-MM-DD format)
- total_kwh (number)
- total_cost (number, dollars)

IMPORTANT INSTRUCTIONS:
- Only extract values that are explicitly present in the document
- If a field cannot be found, use null (not a made-up value)
- Do not make assumptions or infer missing data
- If you're uncertain about a value, use null

Utility Bill:
{bill_text}

Return ONLY raw JSON, no other text.
- Do not wrap in markdown code blocks.
- Do not include the word "json" before the response.
- Start directly with the opening brace."""

    response, cost = call_claude_with_cost(prompt, max_tokens=512)

    # Strip markdown code fences if present
    response = response.strip()
    if response.startswith("```json"):
        response = response[7:]  # Remove ```json
    if response.startswith("```"):
        response = response[3:]   # Remove ```
    if response.endswith("```"):
        response = response[:-3]  # Remove trailing ```
    response = response.strip()
    
    # Parse JSON response
    try:
        data = json.loads(response)
        data['extraction_cost'] = cost['total_cost']
        
        # Log missing fields
        missing = [k for k, v in data.items() if v is None and k != 'extraction_cost']
        if missing:
            print(f"Warning: Missing fields: {missing}")
        
        return data
    except json.JSONDecodeError:
        print(f"Failed to parse JSON: {response}")
        return None

if __name__ == "__main__":
    try:
        with open("data/test_bills/sample_electric_bill.txt", "r") as f:
            bill_text = f.read()
        result = extract_utility_bill_data(bill_text)
        print(json.dumps(result, indent=2))
    except FileNotFoundError:
        print("Error: File not found.")