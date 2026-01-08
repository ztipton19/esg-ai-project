"""Extract data from utility bills using Claude with robust error handling"""
import json
import re
from datetime import datetime
from src.utils import call_claude_with_cost

def extract_utility_bill_data(bill_text):
    """
    Extract structured data from utility bill text with validation
    
    Args:
        bill_text: Raw text from utility bill
        
    Returns:
        dict: Extracted data (kwh, cost, dates, etc.) or None if failed
    """
    
    # === ENHANCED PROMPT ===
    prompt = f"""Extract the following information from this utility bill and return as valid JSON:

Required fields:
- account_number (string)
- service_start_date (YYYY-MM-DD format)
- service_end_date (YYYY-MM-DD format)
- total_usage (number - the actual value shown on bill)
- usage_unit (string - "kWh", "MWh", "therms", etc.)
- total_cost (number - dollars, no $ symbol)

Utility Bill:
{bill_text}

CRITICAL: Return ONLY the raw JSON object with no markdown formatting, no backticks, no explanatory text.
If a field is not found, use null."""

    try:
        response, cost = call_claude_with_cost(prompt, max_tokens=512, temperature=0)
        
        # === JSON CLEANING WITH REGEX ===
        # Remove markdown formatting if present
        json_match = re.search(r'\{.*\}', response, re.DOTALL)
        if not json_match:
            print(f"Warning: No JSON object found in response: {response[:200]}")
            return None
        
        json_str = json_match.group()
        
        # Parse JSON
        data = json.loads(json_str)
        
        # === UNIT CONVERSION ===
        usage_unit = data.get("usage_unit", "").upper()
        total_usage = data.get("total_usage")
        
        if total_usage is None:
            print("Warning: No usage value extracted")
            return None
        
        # Convert to kWh if needed
        if usage_unit == "MWH":
            data["total_kwh"] = total_usage * 1000
            data["unit_conversion_applied"] = "MWh to kWh (×1000)"
        elif usage_unit == "KWH":
            data["total_kwh"] = total_usage
            data["unit_conversion_applied"] = "None (already kWh)"
        elif usage_unit == "THERMS":
            # Don't convert therms to kWh - they're for natural gas
            data["total_therms"] = total_usage
            data["unit_conversion_applied"] = "None (natural gas)"
        else:
            # Unknown unit - flag for review
            data["total_kwh"] = total_usage
            data["unit_conversion_applied"] = f"Warning: Unknown unit '{usage_unit}'"
        
        # === DATE VALIDATION ===
        for date_field in ["service_start_date", "service_end_date"]:
            date_str = data.get(date_field)
            if date_str:
                try:
                    # Attempt to parse the date to validate format
                    parsed_date = datetime.strptime(date_str, "%Y-%m-%d")
                    # Check if date is reasonable (not in future, not before 1990)
                    current_year = datetime.now().year
                    if parsed_date.year > current_year or parsed_date.year < 1990:
                        data[f"{date_field}_warning"] = f"Unusual year: {parsed_date.year}"
                except ValueError:
                    # Try common alternative formats
                    alternative_formats = ["%m/%d/%Y", "%m/%d/%y", "%Y/%m/%d"]
                    parsed = False
                    for fmt in alternative_formats:
                        try:
                            parsed_date = datetime.strptime(date_str, fmt)
                            data[date_field] = parsed_date.strftime("%Y-%m-%d")
                            data[f"{date_field}_converted"] = True
                            parsed = True
                            break
                        except ValueError:
                            continue
                    
                    if not parsed:
                        data[f"{date_field}_warning"] = f"Could not parse date: {date_str}"
        
        # === SANITY CHECK ON RATE ===
        total_cost = data.get("total_cost")
        total_kwh = data.get("total_kwh")
        
        if total_cost and total_kwh and total_kwh > 0:
            rate_per_kwh = total_cost / total_kwh
            data["calculated_rate_per_kwh"] = round(rate_per_kwh, 4)
            
            # Typical US residential rates: $0.08 - $0.40/kWh
            # Commercial can be $0.05 - $0.50/kWh
            if rate_per_kwh < 0.03 or rate_per_kwh > 0.60:
                data["rate_warning"] = (
                    f"Unusual rate: ${rate_per_kwh:.4f}/kWh. "
                    f"Typical range: $0.05-0.50/kWh. Please verify extraction."
                )
        
        # === ADD METADATA ===
        data['extraction_cost'] = cost['total_cost']
        data['extraction_timestamp'] = datetime.now().isoformat()
        data['validation_passed'] = "rate_warning" not in data and all(
            f"{field}_warning" not in data 
            for field in ["service_start_date", "service_end_date"]
        )
        
        return data
        
    except json.JSONDecodeError as e:
        print(f"JSON parsing error: {e}")
        print(f"Response was: {response[:500]}")
        return None
    except Exception as e:
        print(f"Extraction error: {e}")
        return None


def extract_and_calculate_emissions(bill_text, bill_type="electricity", region="US_AVERAGE"):
    """
    Extract data from bill and calculate emissions in one step
    
    Returns complete audit-ready result with warnings
    """
    # Extract data
    extracted = extract_utility_bill_data(bill_text)
    
    if not extracted:
        return {
            "success": False,
            "error": "Failed to extract data from bill",
            "extraction": None,
            "emissions": None
        }
    
    # Check for warnings
    warnings = []
    if not extracted.get("validation_passed"):
        if "rate_warning" in extracted:
            warnings.append(extracted["rate_warning"])
        for field in ["service_start_date", "service_end_date"]:
            if f"{field}_warning" in extracted:
                warnings.append(extracted[f"{field}_warning"])
    
    # Calculate emissions using production function
    try:
        from src.calculate import calculate_electricity_emissions
        
        # Determine reporting period
        start = extracted.get("service_start_date", "Unknown")
        end = extracted.get("service_end_date", "Unknown")
        reporting_period = f"{start} to {end}"
        
        emissions_result = calculate_electricity_emissions(
            kwh=extracted.get("total_kwh", 0),
            region=region,
            reporting_period=reporting_period
        )
        
        return {
            "success": True,
            "warnings": warnings,
            "extraction": extracted,
            "emissions": emissions_result,
            "combined_cost": extracted.get("extraction_cost", 0)
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": f"Emissions calculation failed: {str(e)}",
            "warnings": warnings,
            "extraction": extracted,
            "emissions": None
        }


# ============================================================================
# TEST / DEMO
# ============================================================================

if __name__ == "__main__":
    print("="*70)
    print("UTILITY BILL EXTRACTION - PRODUCTION VERSION")
    print("="*70)
    
    # Test Case 1: Standard kWh bill
    print("\n[TEST 1] Standard kWh Bill")
    print("-"*70)
    test_bill_1 = """
    ELECTRIC COMPANY
    Account #: 123456789
    Service Period: December 1 - December 31, 2024
    
    Usage Summary:
    Total Usage: 850 kWh
    
    Charges:
    Energy Charge: $102.00
    Delivery Charge: $25.50
    Total Amount Due: $127.50
    """
    
    result = extract_utility_bill_data(test_bill_1)
    if result:
        print(f"✅ Extraction successful")
        print(f"   kWh: {result.get('total_kwh')}")
        print(f"   Cost: ${result.get('total_cost')}")
        print(f"   Rate: ${result.get('calculated_rate_per_kwh')}/kWh")
        print(f"   Validation: {'PASS' if result.get('validation_passed') else 'WARNING'}")
        if not result.get('validation_passed'):
            print(f"   ⚠️  {result.get('rate_warning', 'Date warnings present')}")
    
    # Test Case 2: MWh bill (should auto-convert)
    print("\n[TEST 2] MWh Bill (Auto-conversion)")
    print("-"*70)
    test_bill_2 = """
    COMMERCIAL ELECTRIC
    Account: 987654321
    Period: 11/01/2024 - 11/30/2024
    
    Usage: 1.2 MWh
    Total: $180.00
    """
    
    result = extract_utility_bill_data(test_bill_2)
    if result:
        print(f"✅ Extraction successful")
        print(f"   Original: {result.get('total_usage')} {result.get('usage_unit')}")
        print(f"   Converted: {result.get('total_kwh')} kWh")
        print(f"   Conversion: {result.get('unit_conversion_applied')}")
    
    # Test Case 3: Full pipeline with emissions
    print("\n[TEST 3] Full Pipeline (Extract → Calculate)")
    print("-"*70)
    full_result = extract_and_calculate_emissions(test_bill_1, region="ARKANSAS")
    
    if full_result["success"]:
        print(f"✅ Pipeline successful")
        print(f"   Emissions: {full_result['emissions']['data']['emissions_mtco2e']} metric tons CO2e")
        print(f"   Cost: ${full_result['combined_cost']:.4f}")
        if full_result["warnings"]:
            print(f"   Warnings: {len(full_result['warnings'])}")
            for w in full_result["warnings"]:
                print(f"      - {w}")
    else:
        print(f"❌ Pipeline failed: {full_result['error']}")