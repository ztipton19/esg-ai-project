"""
ESG Automation System - Utility Functions
Production-grade PDF extraction with dual-path strategy

VERSION: 2.0
- Meter reading calculation (handles Oklahoma EC, Eversource formats)
- Data validation layer
- Enhanced Claude prompts with examples
- Cost tracking and confidence scoring
"""

import os
from dotenv import load_dotenv
import anthropic
import base64
from io import BytesIO
from datetime import datetime
import time

# Load environment variables
load_dotenv()

# ============================================================================
# DATA VALIDATION
# ============================================================================

def validate_extraction(data):
    """
    Check for logical consistency in ESG data
    
    Args:
        data: Dict with extracted bill data
        
    Returns:
        tuple: (is_valid: bool, issues: list)
    """
    issues = []
    
    # Check 1: Service dates make sense
    if data.get('service_start_date') and data.get('service_end_date'):
        try:
            start = datetime.strptime(data['service_start_date'], '%Y-%m-%d')
            end = datetime.strptime(data['service_end_date'], '%Y-%m-%d')
            
            if end <= start:
                issues.append("End date must be after start date")
            
            # Check billing period isn't too long (>60 days unusual)
            days = (end - start).days
            if days > 60:
                issues.append(f"Billing period of {days} days is unusually long")
        except (ValueError, TypeError):
            issues.append("Invalid date format")
    
    # Check 2: Cost per unit isn't impossible
    if data.get('total_usage') and data.get('total_cost'):
        try:
            usage = float(data['total_usage'])
            cost = float(data['total_cost'])
            
            if usage > 0:
                unit_price = cost / usage
                
                # Residential electricity typically $0.08-$0.40 per kWh
                if unit_price > 5.0:
                    issues.append(f"Unit price ${unit_price:.2f}/kWh is unusually high")
                elif unit_price < 0.01:
                    issues.append(f"Unit price ${unit_price:.4f}/kWh is unusually low")
        except (ValueError, TypeError, ZeroDivisionError):
            pass
    
    # Check 3: Usage amount is reasonable
    if data.get('total_usage'):
        try:
            usage = float(data['total_usage'])
            
            # Residential typically 200-2000 kWh/month
            if usage < 10:
                issues.append(f"Usage of {usage} kWh is unusually low")
            elif usage > 50000:
                issues.append(f"Usage of {usage} kWh is unusually high")
        except (ValueError, TypeError):
            pass
    
    is_valid = len(issues) == 0
    return is_valid, issues


# ============================================================================
# COST TRACKING
# ============================================================================

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
        temperature: Randomness (0=deterministic). Default 0 for data extraction
        
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
# AI-POWERED PDF EXTRACTION (Claude Vision)
# ============================================================================

def extract_from_pdf_with_ai(pdf_file):
    """
    Extract utility bill data using Claude's native PDF vision
    
    Cost: ~$0.02-$0.03 per PDF
    Accuracy: 95%+ (handles complex layouts, scanned images)
    Use case: Fallback when Docling confidence < 85%
    
    Args:
        pdf_file: Streamlit UploadedFile object
        
    Returns:
        dict: Extraction results with cost tracking
    """
    try:
        # Read PDF as base64
        pdf_content = pdf_file.read()
        pdf_base64 = base64.b64encode(pdf_content).decode('utf-8')
        
        # Reset file pointer for potential future reads
        pdf_file.seek(0)
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to read PDF: {str(e)}",
            "cost": 0
        }
    
    # Enhanced system prompt - VERY explicit for image/scanned bills
    system_prompt = """You are an expert utility bill data extractor. You read electricity, gas, and water bills and extract structured data.

You ALWAYS return valid JSON in this exact format:
{
  "account_number": "string or null",
  "service_start_date": "YYYY-MM-DD or null",
  "service_end_date": "YYYY-MM-DD or null", 
  "total_usage": number or null,
  "usage_unit": "kWh|MWh|therms|CCF or null",
  "total_cost": number or null
}

CRITICAL RULES FOR METER READINGS (READ THIS TWICE):
1. If you see "Previous Reading" and "Present Reading" or "Current Reading"
2. YOU MUST CALCULATE: Present/Current - Previous = Usage
3. DO NOT just report one of the readings as usage
4. DO NOT report the difference from a graph
5. DO THE SUBTRACTION YOURSELF

For total_usage:
- Find BILLED usage for CURRENT period ONLY
- NEVER use "average monthly usage" or historical totals
- If you see meter readings, CALCULATE the difference
- Look for: "Billed Usage", "Current Charges", "Usage This Period", or the last column labeled "Usage"

Return ONLY raw JSON - no markdown, no backticks, no explanatory text.

EXAMPLES - STUDY THESE:

Example 1 - Direct Usage (Easy):
INPUT: "Service Period: 11/01/2024 - 11/30/2024, Current Charges: 850 kWh, Amount Due: $127.50"
OUTPUT: {"account_number": null, "service_start_date": "2024-11-01", "service_end_date": "2024-11-30", "total_usage": 850, "usage_unit": "kWh", "total_cost": 127.50}

Example 2 - Meter Readings in Table (CALCULATE!):
INPUT: Table showing:
| Service Description | Previous Reading | Present Reading | Usage |
| 12345 MAIN ST | 12258 | 12512 | 254 |

THOUGHT PROCESS:
- I see Previous Reading: 12258
- I see Present Reading: 12512
- I see Usage column showing: 254
- The correct answer is 254 kWh (already calculated in the Usage column)
- OR if Usage column is blank, calculate: 12512 - 12258 = 254

OUTPUT: {"account_number": null, "service_start_date": null, "service_end_date": null, "total_usage": 254, "usage_unit": "kWh", "total_cost": null}

Example 3 - Meter Readings WITHOUT Usage Column Shown:
INPUT: "Previous Reading: 45004, Current Reading: 45426"
CALCULATION: 45426 - 45004 = 422 kWh
OUTPUT: {"account_number": null, "service_start_date": null, "service_end_date": null, "total_usage": 422, "usage_unit": "kWh", "total_cost": null}

Example 4 - Complete Bill:
INPUT: "Account: 962-642-734-1-6, Service 11/05/25 - 12/05/25, Usage: 282 kWh, Amount Due: $46.84"
OUTPUT: {"account_number": "962-642-734-1-6", "service_start_date": "2025-11-05", "service_end_date": "2025-12-05", "total_usage": 282, "usage_unit": "kWh", "total_cost": 46.84}

COMMON MISTAKES TO AVOID:
❌ Reporting one meter reading as usage (e.g., reporting 12512 instead of 254)
❌ Reporting a graph value instead of the calculated/stated usage
❌ Reporting average usage instead of current period
✅ Looking for a "Usage" column in tables FIRST
✅ If no Usage column, calculating Present - Previous yourself
✅ Double-checking your math"""

    # Simplified user prompt
    user_prompt = "Extract the utility bill data from this PDF and return as JSON. If you see meter readings, calculate the usage difference."
    
    try:
        client = get_claude_client()
        
        # Call Claude with PDF document
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            temperature=0,
            system=system_prompt,
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
                            "text": user_prompt
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
        
        # Validate extracted data
        is_valid, issues = validate_extraction(data)
        
        return {
            "success": True,
            "data": data,
            "cost": extraction_cost,
            "method": "AI-powered (Claude PDF vision)",
            "validation_issues": issues if not is_valid else None
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": f"AI extraction failed: {str(e)}",
            "cost": 0
        }


# ============================================================================
# TIER 2: OCR EXTRACTION (Tesseract for Scanned/Image PDFs)
# ============================================================================

def extract_from_pdf_with_ocr(pdf_file):
    """
    Extract utility bill data using Tesseract OCR
    
    Cost: ~$0.001 per PDF (essentially free, local processing)
    Accuracy: 70-85% for scanned documents
    Speed: 3-5 seconds per PDF
    Use case: Scanned PDFs, image-based bills (Oklahoma EC type)
    
    Args:
        pdf_file: Streamlit UploadedFile object
        
    Returns:
        dict: Extraction results with confidence score
    """
    start_time = time.time()
    
    try:
        import pytesseract
        from pdf2image import convert_from_bytes
        from PIL import Image
        import tempfile
        import os
        
        print("\n📸 Starting OCR extraction (Tesseract)...")
        
        # Read PDF bytes
        pdf_bytes = pdf_file.read()
        pdf_file.seek(0)  # Reset for potential future reads
        
        # Convert PDF to images (one per page)
        print("   Converting PDF to images...")
        images = convert_from_bytes(pdf_bytes, dpi=300)  # High DPI for better OCR
        
        print(f"   Found {len(images)} page(s)")
        
        # Extract text from each page
        full_text = ""
        for i, image in enumerate(images, 1):
            print(f"   OCR processing page {i}/{len(images)}...")
            
            # Tesseract OCR (without restrictive config)
            page_text = pytesseract.image_to_string(image)
            full_text += page_text + "\n\n"
        
        print(f"   Extracted {len(full_text)} characters")
        
        # Now parse the OCR text using same extraction functions
        data = {
            "account_number": extract_account_number(full_text),
            "service_start_date": extract_service_dates(full_text)[0],
            "service_end_date": extract_service_dates(full_text)[1],
            "total_usage": extract_usage_value(full_text),
            "usage_unit": extract_usage_unit(full_text),
            "total_cost": extract_total_cost(full_text)
        }
        
        # Calculate confidence
        confidence = calculate_extraction_confidence(data)
        
        # Validate data
        is_valid, issues = validate_extraction(data)
        
        # Adjust confidence based on validation
        if not is_valid:
            print(f"⚠️  Validation warnings: {', '.join(issues)}")
            penalty = min(len(issues) * 0.10, 0.30)
            original_confidence = confidence
            confidence = max(0, confidence - penalty)
            print(f"   Confidence adjusted from {original_confidence:.0%} to {confidence:.0%}")
        
        elapsed_time = time.time() - start_time
        
        return {
            "success": True,
            "data": data,
            "confidence": confidence,
            "validation_issues": issues if not is_valid else None,
            "method": "OCR (Tesseract)",
            "cost": 0.001,  # Essentially free, but track nominal cost
            "processing_time": round(elapsed_time, 2),
            "ocr_text_length": len(full_text),
            "raw_text": full_text[:1000]  # First 1000 chars for debugging
        }
        
    except ImportError as e:
        return {
            "success": False,
            "confidence": 0.0,
            "error": f"OCR libraries not installed: {str(e)}. Install with: pip install pytesseract pdf2image"
        }
    except Exception as e:
        return {
            "success": False,
            "confidence": 0.0,
            "error": f"OCR extraction failed: {str(e)}"
        }


# ============================================================================
# TIER 1: DOCLING PDF EXTRACTION (Production-Grade Local Processing)
# ============================================================================

def extract_from_pdf_with_docling(pdf_file):
    """
    Extract utility bill data using Docling (IBM's document AI)
    
    Cost: ~$0.0001 per PDF (200x cheaper than Claude API)
    Accuracy: 85-90% for standard utility bills
    Speed: 2-3 seconds per PDF
    
    Args:
        pdf_file: Streamlit UploadedFile object
        
    Returns:
        dict: Extraction results with confidence score
    """
    start_time = time.time()
    
    try:
        from docling.document_converter import DocumentConverter
        import tempfile
        
        # Write to temp file (Docling needs file path)
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp:
            tmp.write(pdf_file.read())
            tmp_path = tmp.name
        
        # Reset file pointer
        pdf_file.seek(0)
        
        # Convert PDF
        converter = DocumentConverter()
        result = converter.convert(tmp_path)
        
        # Extract text
        text = result.document.export_to_markdown()
        
        # Clean up temp file
        import os
        os.unlink(tmp_path)
        
        # Parse utility bill data using enhanced extractors
        data = {
            "account_number": extract_account_number(text),
            "service_start_date": extract_service_dates(text)[0],
            "service_end_date": extract_service_dates(text)[1],
            "total_usage": extract_usage_value(text),
            "usage_unit": extract_usage_unit(text),
            "total_cost": extract_total_cost(text)
        }
        
        # Calculate confidence score
        confidence = calculate_extraction_confidence(data)
        
        # Validate data consistency
        is_valid, issues = validate_extraction(data)
        
        # Adjust confidence based on validation
        if not is_valid:
            print(f"⚠️  Validation warnings: {', '.join(issues)}")
            penalty = min(len(issues) * 0.10, 0.30)
            original_confidence = confidence
            confidence = max(0, confidence - penalty)
            print(f"   Confidence adjusted from {original_confidence:.0%} to {confidence:.0%}")
        
        elapsed_time = time.time() - start_time
        
        return {
            "success": True,
            "data": data,
            "confidence": confidence,
            "validation_issues": issues if not is_valid else None,
            "method": "Docling (local)",
            "cost": 0.0001,
            "processing_time": round(elapsed_time, 2),
            "raw_text": text[:1000]  # First 1000 chars for debugging
        }
        
    except ImportError:
        return {
            "success": False,
            "confidence": 0.0,
            "error": "Docling not installed. Install with: pip install docling"
        }
    except Exception as e:
        return {
            "success": False,
            "confidence": 0.0,
            "error": f"Docling extraction failed: {str(e)}"
        }


# ============================================================================
# HELPER FUNCTIONS FOR STRUCTURED EXTRACTION
# ============================================================================

def extract_account_number(text):
    """Extract account number using regex patterns"""
    import re
    patterns = [
        r'Account\s*#?\s*:?\s*([\d\-]+)',
        r'Acct\s*#?\s*:?\s*([\d\-]+)',
        r'Account\s+Number\s*:?\s*([\d\-]+)',
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1).strip()
    return None


def extract_service_dates(text):
    """Extract service period dates"""
    import re
    
    # Look for date ranges
    date_patterns = [
        r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\s*[-–to]+\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
        r'Service\s+Period:?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\s*[-–to]+\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
        r'Billing\s+from\s+(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\s*[-–to]+\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
    ]
    
    for pattern in date_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            try:
                start = parse_flexible_date(match.group(1))
                end = parse_flexible_date(match.group(2))
                return start, end
            except:
                continue
    
    return None, None


def parse_flexible_date(date_str):
    """Parse date from various formats"""
    formats = [
        "%m/%d/%Y", "%m/%d/%y",
        "%m-%d-%Y", "%m-%d-%y",
        "%d/%m/%Y", "%d/%m/%y",
    ]
    
    for fmt in formats:
        try:
            date_obj = datetime.strptime(date_str, fmt)
            return date_obj.strftime("%Y-%m-%d")
        except ValueError:
            continue
    
    return None


def extract_usage_value(text):
    """
    Extract usage value with METER READING CALCULATION
    
    Priority order:
    1. Direct "Usage" value from tables
    1.5. METER READINGS - Calculate Current - Previous
    2. Billed usage in tables
    3. Explicit "Current Usage" labels
    4. Line-by-line search (skip "average" lines)
    5. Last resort - any kWh value
    """
    import re
    
    print("\n🔍 Docling: Searching for usage value...")
    
    # Priority 1: Look for "Usage" column value in tables
    # OCR output often has: "| 12258 | 12512 | 1 | 54 | 200 | 254"
    # The last number after pipes is typically the usage
    table_usage_patterns = [
        r'\|\s*(\d+)\s*$',  # Simple: last number after pipe at end of line
        r'Reading.*?\|\s*(\d{2,4})\s*$',  # After "Reading", last 2-4 digit number
        r'\|\s*\d+\s*\|\s*\d+\s*\|\s*(\d{2,4})\s*$',  # After two pipes with numbers, get third
    ]
    
    for pattern in table_usage_patterns:
        matches = re.finditer(pattern, text, re.IGNORECASE | re.MULTILINE)
        for match in matches:
            try:
                # Get the first (and usually only) captured group
                usage_value = match.group(1)
                value = float(usage_value)
                if 50 < value < 10000:
                    print(f"✓ Docling: Found usage in table row: {value} kWh")
                    return value
            except (ValueError, IndexError, AttributeError):
                continue
    
    # Priority 1.5: Billed usage in tables
    table_patterns = [
        r'Billed\s+Usage[^\d]*(\d+)\s*kWh',
        r'Usage\s*\|\s*(\d+)\s*\|',
        r'\|\s*(\d+)\s*kWh\s*\|',
    ]
    
    for pattern in table_patterns:
        match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
        if match:
            try:
                value = float(match.group(1))
                if 50 < value < 10000:
                    print(f"✓ Docling: Found billed usage in table: {value} kWh")
                    return value
            except (ValueError, IndexError):
                continue
    
    # Priority 2: METER READINGS - Calculate usage from meter dials
    print("🔍 Docling: Looking for meter readings...")
    
    meter_patterns = [
        # Pattern 1: "Previous Reading: 12258" + "Present Reading: 12512"
        (r'Previous\s+Reading[:\s]+(\d+)', r'(?:Present|Current)\s+Reading[:\s]+(\d+)'),
        # Pattern 2: "Prev Read: 12258" + "Current Read: 12512"
        (r'Prev(?:ious)?\s+Read[:\s]+(\d+)', r'(?:Current|Present)\s+Read[:\s]+(\d+)'),
        # Pattern 3: Simple "Previous: 12258" + "Current: 12512"
        (r'Previous[:\s]+(\d+)', r'Current[:\s]+(\d+)'),
    ]
    
    for prev_pattern, curr_pattern in meter_patterns:
        prev_match = re.search(prev_pattern, text, re.IGNORECASE)
        curr_match = re.search(curr_pattern, text, re.IGNORECASE)
        
        if prev_match and curr_match:
            try:
                previous_reading = int(prev_match.group(1))
                current_reading = int(curr_match.group(1))
                
                # Calculate usage
                usage = current_reading - previous_reading
                
                # Sanity check
                if 50 < usage < 10000:
                    print(f"✓ Docling: CALCULATED from meter readings!")
                    print(f"   Previous: {previous_reading}")
                    print(f"   Current:  {current_reading}")
                    print(f"   Usage:    {usage} kWh")
                    return float(usage)
                else:
                    print(f"⚠ Docling: Meter calc gave unreasonable value: {usage} kWh (skipping)")
            except (ValueError, IndexError) as e:
                print(f"⚠ Docling: Error calculating from meters: {e}")
                continue
    
    print("ℹ️  Docling: No meter readings found, trying other patterns...")
    
    # Priority 3: Explicit "Current" or "Billed" usage labels
    priority_patterns = [
        r'Current\s+(?:bill\s+)?[Uu]sage[:\s]+(\d+\.?\d*)\s*kWh',
        r'Billed\s+[Uu]sage[:\s]+(\d+\.?\d*)\s*kWh',
        r'Usage\s+for\s+this\s+period[:\s]+(\d+\.?\d*)\s*kWh',
        r'This\s+period[:\s]+(\d+\.?\d*)\s*kWh',
        r'Usage:\s*(\d+)\s*kWh',
    ]
    
    for pattern in priority_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            try:
                value = float(match.group(1))
                if 50 < value < 10000:
                    print(f"✓ Docling: Found current period usage: {value} kWh")
                    return value
            except ValueError:
                continue
    
    # Priority 4: Line-by-line search, SKIP "average" lines
    print("🔍 Docling: Searching line-by-line (skipping averages)...")
    lines = text.split('\n')
    for line in lines:
        # Skip lines mentioning average/typical
        if re.search(r'\b(avg|average|typical|historical|past\s+\d+\s+months)\b', line, re.IGNORECASE):
            continue
        
        # Look for kWh on non-average lines
        match = re.search(r'(\d+\.?\d*)\s*kWh', line, re.IGNORECASE)
        if match:
            try:
                value = float(match.group(1))
                if 50 < value < 10000:
                    print(f"✓ Docling: Found usage (non-average line): {value} kWh")
                    return value
            except ValueError:
                continue
    
    # Priority 5: Last resort - any kWh value
    match = re.search(r'(\d+\.?\d*)\s*kWh', text, re.IGNORECASE)
    if match:
        try:
            value = float(match.group(1))
            if 50 < value < 10000:
                print(f"⚠ Docling: Found kWh value (uncertain): {value} kWh")
                return value
        except ValueError:
            pass
    
    print("✗ Docling: No usage value found")
    return None


def extract_usage_unit(text):
    """Extract usage unit (kWh, MWh, therms, etc.)"""
    text_lower = text.lower()
    
    if 'kwh' in text_lower:
        return "kWh"
    elif 'mwh' in text_lower:
        return "MWh"
    elif 'therm' in text_lower:
        return "therms"
    elif 'ccf' in text_lower:
        return "CCF"
    
    return "kWh"  # Default assumption


def extract_total_cost(text):
    """Extract total cost/amount due"""
    import re
    
    cost_patterns = [
        r'Total\s+Amount\s+Due[:\s]+\$?\s*(\d+[,\.]?\d*)',
        r'Amount\s+Due[:\s]+\$?\s*(\d+[,\.]?\d*)',
        r'Balance\s+Due[:\s]+\$?\s*(\d+[,\.]?\d*)',
        r'Total\s+Charges[:\s]+\$?\s*(\d+[,\.]?\d*)',
        r'Current\s+Charges[:\s]+\$?\s*(\d+[,\.]?\d*)',
    ]
    
    for pattern in cost_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            try:
                # Remove commas and convert to float
                cost_str = match.group(1).replace(',', '')
                cost = float(cost_str)
                if 10 < cost < 10000:  # Sanity check
                    return cost
            except ValueError:
                continue
    
    return None


def calculate_extraction_confidence(data):
    """
    Calculate confidence score based on extracted fields
    
    Returns: float between 0 and 1
    """
    score = 0.0
    weights = {
        "account_number": 0.15,
        "service_start_date": 0.15,
        "service_end_date": 0.15,
        "total_usage": 0.35,  # Most important
        "usage_unit": 0.05,
        "total_cost": 0.15
    }
    
    for field, weight in weights.items():
        if data.get(field) is not None:
            score += weight
    
    return score


# ============================================================================
# MAIN EXTRACTION FUNCTION - 3-TIER STRATEGY
# ============================================================================

def extract_bill_data(pdf_file, confidence_threshold=0.85, enable_ocr=True, enable_ai=True):
    """
    Extract utility bill data with 3-tier fallback strategy
    
    TIER 1: Docling (free, fast, text-based PDFs)
      ↓ if confidence < threshold
    TIER 2: Tesseract OCR (cheap, scanned/image PDFs)
      ↓ if confidence < threshold  
    TIER 3: Claude Vision API (expensive, complex layouts)
    
    Cost optimization:
    - 85% of bills: $0.0001 (Docling)
    - 10% of bills: $0.001  (OCR)
    - 5% of bills:  $0.02   (Claude)
    
    Args:
        pdf_file: Streamlit UploadedFile object
        confidence_threshold: Minimum confidence to accept result (default 0.85)
        enable_ocr: Whether to use OCR fallback (default True)
        enable_ai: Whether to use Claude API fallback (default True)
        
    Returns:
        dict: Extraction results with metadata
    """
    print("="*80)
    print("🚀 STARTING 3-TIER EXTRACTION STRATEGY")
    print("="*80)
    print(f"Confidence threshold: {confidence_threshold:.0%}")
    print(f"OCR enabled: {enable_ocr}")
    print(f"AI fallback enabled: {enable_ai}")
    
    total_cost = 0.0
    
    # ========================================================================
    # TIER 1: DOCLING (Text-Based PDF Extraction)
    # ========================================================================
    print("\n" + "─"*80)
    print("TIER 1: DOCLING (Text Extraction)")
    print("─"*80)
    print("📄 Attempting fast local extraction...")
    
    docling_result = extract_from_pdf_with_docling(pdf_file)
    total_cost += docling_result.get("cost", 0)
    
    if docling_result.get("success"):
        confidence = docling_result.get("confidence", 0)
        print(f"\n✓ Docling extraction successful!")
        print(f"   Confidence: {confidence:.0%}")
        print(f"   Cost: ${docling_result.get('cost', 0):.6f}")
        print(f"   Time: {docling_result.get('processing_time', 0)}s")
        
        if confidence >= confidence_threshold:
            print(f"\n🎯 TIER 1 SUCCESS - Confidence above threshold!")
            print(f"💰 Total cost: ${total_cost:.6f}")
            docling_result['total_cost'] = total_cost
            docling_result['tiers_used'] = ['Docling']
            return docling_result
        else:
            print(f"\n⚠️  Confidence below threshold ({confidence:.0%} < {confidence_threshold:.0%})")
            print("   Moving to Tier 2...")
    else:
        print(f"\n✗ Docling failed: {docling_result.get('error', 'Unknown error')}")
        print("   Moving to Tier 2...")
    
    # ========================================================================
    # TIER 2: TESSERACT OCR (Scanned/Image PDF Extraction)
    # ========================================================================
    if enable_ocr:
        print("\n" + "─"*80)
        print("TIER 2: TESSERACT OCR (Image Processing)")
        print("─"*80)
        print("📸 Attempting OCR extraction...")
        
        ocr_result = extract_from_pdf_with_ocr(pdf_file)
        total_cost += ocr_result.get("cost", 0)
        
        if ocr_result.get("success"):
            confidence = ocr_result.get("confidence", 0)
            print(f"\n✓ OCR extraction successful!")
            print(f"   Confidence: {confidence:.0%}")
            print(f"   Cost: ${ocr_result.get('cost', 0):.6f}")
            print(f"   Time: {ocr_result.get('processing_time', 0)}s")
            print(f"   Text extracted: {ocr_result.get('ocr_text_length', 0)} chars")
            
            if confidence >= confidence_threshold:
                print(f"\n🎯 TIER 2 SUCCESS - Confidence above threshold!")
                print(f"💰 Total cost: ${total_cost:.6f}")
                ocr_result['total_cost'] = total_cost
                ocr_result['tiers_used'] = ['Docling (failed)', 'OCR']
                return ocr_result
            else:
                print(f"\n⚠️  Confidence below threshold ({confidence:.0%} < {confidence_threshold:.0%})")
                print("   Moving to Tier 3...")
        else:
            print(f"\n✗ OCR failed: {ocr_result.get('error', 'Unknown error')}")
            print("   Moving to Tier 3...")
    else:
        print("\n⏭️  OCR disabled, skipping Tier 2")
    
    # ========================================================================
    # TIER 3: CLAUDE VISION API (Complex Layout / Final Fallback)
    # ========================================================================
    if enable_ai:
        print("\n" + "─"*80)
        print("TIER 3: CLAUDE VISION API (AI-Powered Extraction)")
        print("─"*80)
        print("🤖 Attempting Claude Vision extraction...")
        
        ai_result = extract_from_pdf_with_ai(pdf_file)
        total_cost += ai_result.get("cost", 0)
        
        if ai_result.get("success"):
            print(f"\n✓ Claude Vision extraction successful!")
            print(f"   Cost: ${ai_result.get('cost', 0):.4f}")
            print(f"   Method: {ai_result.get('method', 'Claude')}")
            print(f"\n🎯 TIER 3 SUCCESS - Using AI result")
            print(f"💰 Total cost: ${total_cost:.4f}")
            
            ai_result['total_cost'] = total_cost
            
            # Track which tiers were attempted
            tiers_used = ['Docling (failed)']
            if enable_ocr:
                tiers_used.append('OCR (failed)')
            tiers_used.append('Claude Vision')
            ai_result['tiers_used'] = tiers_used
            
            return ai_result
        else:
            print(f"\n✗ Claude Vision failed: {ai_result.get('error', 'Unknown error')}")
    else:
        print("\n⏭️  AI fallback disabled, skipping Tier 3")
    
    # ========================================================================
    # ALL TIERS FAILED
    # ========================================================================
    print("\n" + "="*80)
    print("❌ ALL EXTRACTION TIERS FAILED")
    print("="*80)
    print(f"💰 Total cost: ${total_cost:.4f}")
    
    # Return best result we have (highest confidence)
    results = [docling_result]
    if enable_ocr and 'ocr_result' in locals():
        results.append(ocr_result)
    
    best_result = max(results, key=lambda x: x.get('confidence', 0))
    best_result['total_cost'] = total_cost
    best_result['tiers_used'] = ['Docling', 'OCR', 'Claude Vision'] if enable_ocr and enable_ai else ['Docling', 'Claude Vision']
    best_result['all_tiers_failed'] = True
    
    return best_result