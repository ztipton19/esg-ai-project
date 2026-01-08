"""Validation layer for ESG data with audit-grade checks"""
import re
from datetime import datetime
from typing import Tuple, Optional

def validate_emissions_data(emissions_data: dict) -> Tuple[bool, Optional[str]]:
    """
    Validate emissions data has all required fields for GRI reporting
    with audit-grade checks
    
    Args:
        emissions_data: Dict with emissions calculations
        
    Returns:
        tuple: (is_valid, error_message)
    """
    required_keys = [
        "reporting_period",
        "metric_tons_co2",
        "emission_factor_used",
        "emission_factor_source",
        "calculation_method"
    ]
    
    # Check for missing keys
    missing_keys = [k for k in required_keys if k not in emissions_data]
    if missing_keys:
        return False, f"Missing required fields: {', '.join(missing_keys)}"
    
    # Validate data types
    if not isinstance(emissions_data["metric_tons_co2"], (int, float)):
        return False, "metric_tons_co2 must be numeric"
    
    # Non-negative emissions
    if emissions_data["metric_tons_co2"] < 0:
        return False, "Emissions cannot be negative"
    
    # === NEW: DATE RANGE VALIDATION ===
    service_start = emissions_data.get("service_start_date")
    service_end = emissions_data.get("service_end_date")
    
    if service_start and service_end:
        try:
            # Parse dates if they're strings
            if isinstance(service_start, str):
                start_date = datetime.strptime(service_start, "%Y-%m-%d")
            else:
                start_date = service_start
                
            if isinstance(service_end, str):
                end_date = datetime.strptime(service_end, "%Y-%m-%d")
            else:
                end_date = service_end
            
            # Validate chronological order
            if end_date <= start_date:
                return False, f"End date ({service_end}) must be after start date ({service_start})"
            
            # Check if date range is reasonable (not more than 3 months for utility bills)
            days_diff = (end_date - start_date).days
            if days_diff > 100:  # ~3 months
                return False, f"Reporting period too long ({days_diff} days). Utility bills typically cover 1 month."
            
            if days_diff < 1:
                return False, "Reporting period must be at least 1 day"
                
        except ValueError as e:
            return False, f"Invalid date format: {e}"
    
    # === NEW: EMISSION FACTOR RANGE CHECK ===
    # Sanity check: US electricity factors typically 0.2 - 1.2 kg CO2e/kWh
    factor = emissions_data.get("emission_factor_used")
    if factor and isinstance(factor, (int, float)):
        if factor < 0.05 or factor > 2.0:
            return False, f"Emission factor {factor} outside expected range (0.05-2.0 kg CO2e/kWh)"
    
    return True, None


def verify_report_accuracy(
    report_text: str, 
    emissions_data: dict,
    tolerance_percent: float = 0.1
) -> Tuple[bool, Optional[str]]:
    """
    Verify that the generated report contains the correct emissions value
    with keyword proximity checks and percentage-based tolerance
    
    Args:
        report_text: Generated report text
        emissions_data: Source data used to generate report
        tolerance_percent: Acceptable percentage deviation (default 0.1%)
        
    Returns:
        tuple: (is_accurate, warning_message)
    """
    expected_value = emissions_data["metric_tons_co2"]
    
    # === ENHANCED: KEYWORD PROXIMITY CHECK ===
    # Look for the emissions value near relevant keywords
    # This prevents false positives (e.g., account number = kWh value)
    
    emission_keywords = [
        r"emissions?",
        r"co2e?",
        r"metric\s+tons?",
        r"mtco2e",
        r"carbon",
        r"greenhouse\s+gas",
        r"ghg"
    ]
    
    # Build patterns that look for number near keywords
    # Format: "emissions: 0.622" or "0.622 metric tons" or "total of 0.622"
    proximity_patterns = []
    
    # Pattern 1: keyword followed by number
    for kw in emission_keywords:
        proximity_patterns.append(
            rf"{kw}[:\s]+(\d+\.?\d*)"
        )
    
    # Pattern 2: number followed by keyword
    for kw in emission_keywords:
        proximity_patterns.append(
            rf"(\d+\.?\d*)\s+{kw}"
        )
    
    found_values = []
    for pattern in proximity_patterns:
        matches = re.finditer(pattern, report_text, re.IGNORECASE)
        for match in matches:
            try:
                value = float(match.group(1))
                found_values.append(value)
            except (ValueError, IndexError):
                continue
    
    if not found_values:
        # Fallback: look for ANY number (old behavior)
        all_numbers = re.findall(r'\d+\.?\d*', report_text)
        found_values = [float(n) for n in all_numbers if n]
        
        if not found_values:
            return False, "⚠️ No numeric values found in report"
    
    # === ENHANCED: PERCENTAGE-BASED TOLERANCE ===
    # Instead of fixed 0.01 tolerance, use percentage
    # Example: 0.622 ± 0.1% = 0.62162 to 0.62238
    
    absolute_tolerance = abs(expected_value * tolerance_percent / 100)
    min_acceptable = expected_value - absolute_tolerance
    max_acceptable = expected_value + absolute_tolerance
    
    # Check if any found value is within tolerance
    matches = [
        v for v in found_values 
        if min_acceptable <= v <= max_acceptable
    ]
    
    if matches:
        # Found exact match or within tolerance
        closest_match = min(matches, key=lambda x: abs(x - expected_value))
        deviation_pct = abs((closest_match - expected_value) / expected_value * 100)
        
        if deviation_pct == 0:
            return True, None
        else:
            return True, f"ℹ️ Report value {closest_match} differs by {deviation_pct:.3f}% from source {expected_value}"
    
    # === UNIT CONSISTENCY CHECK ===
    # Check if the report mentions the value but with wrong unit
    # e.g., source says "0.622 metric tons" but report says "622 kg"
    
    # Common conversions
    kg_value = expected_value * 1000  # metric tons to kg
    lb_value = expected_value * 2204.62  # metric tons to pounds
    
    unit_variants = [
        (kg_value, "kg", "kilograms"),
        (lb_value, "lb", "pounds"),
        (expected_value * 1000000, "g", "grams")
    ]
    
    for variant_value, unit_short, unit_long in unit_variants:
        variant_tolerance = abs(variant_value * tolerance_percent / 100)
        if any(abs(v - variant_value) <= variant_tolerance for v in found_values):
            return False, (
                f"⚠️ UNIT ERROR: Report contains {variant_value:.2f} (likely {unit_short}), "
                f"but source data is {expected_value} metric tons CO2e. "
                f"This is a {unit_short}-to-metric-tons conversion error."
            )
    
    # No match found
    closest_value = min(found_values, key=lambda x: abs(x - expected_value)) if found_values else None
    
    if closest_value:
        deviation = abs(closest_value - expected_value)
        deviation_pct = abs((deviation / expected_value) * 100)
        return False, (
            f"⚠️ HALLUCINATION DETECTED: Expected {expected_value} metric tons CO2e, "
            f"but report contains {closest_value} (deviation: {deviation_pct:.1f}%). "
            f"LLM may have calculated incorrectly or used wrong source value."
        )
    else:
        return False, f"⚠️ Expected value {expected_value} not found in report text"


def validate_report_completeness(report_text: str, required_sections: list = None) -> Tuple[bool, list]:
    """
    Check if report contains all required GRI disclosure sections
    Uses semantic keyword matching to verify completeness
    
    Args:
        report_text: Generated report text
        required_sections: Optional list of required topics
        
    Returns:
        tuple: (is_complete, missing_sections)
    """
    if required_sections is None:
        # Default GRI 305 requirements with multiple keyword options per topic
        required_topics = {
            "reporting_period": ["reporting period", "period", "2024", "2025", "december", "january"],
            "emissions_value": ["metric tons", "mtco2e", "co2e", "emissions", "tonnes"],
            "methodology": ["methodology", "calculation", "formula", "method", "approach"],
            "emission_factor": ["emission factor", "egrid", "epa", "factor", "coefficient"],
            "data_quality": ["quality", "limitation", "uncertainty", "assumption", "exclusion"]
        }
    else:
        # User-provided sections as simple keyword list
        required_topics = {section: [section] for section in required_sections}
    
    missing = []
    for topic, keywords in required_topics.items():
        # Check if ANY of the keywords for this topic appear in the report
        found = any(keyword.lower() in report_text.lower() for keyword in keywords)
        if not found:
            missing.append(topic)
    
    return len(missing) == 0, missing


# ============================================================================
# TEST / DEMO
# ============================================================================

if __name__ == "__main__":
    print("="*70)
    print("ESG VALIDATION LAYER - ENHANCED VERSION")
    print("="*70)
    
    # Test Case 1: Valid data
    print("\n[TEST 1] Valid Emissions Data")
    print("-"*70)
    valid_data = {
        "reporting_period": "December 2024",
        "service_start_date": "2024-12-01",
        "service_end_date": "2024-12-31",
        "metric_tons_co2": 0.622,
        "emission_factor_used": 0.732,
        "emission_factor_source": "EPA eGRID 2024",
        "calculation_method": "850 kWh × 0.732 kg CO2e/kWh"
    }
    
    is_valid, error = validate_emissions_data(valid_data)
    print(f"Result: {'✅ VALID' if is_valid else f'❌ INVALID: {error}'}")
    
    # Test Case 2: Invalid date range
    print("\n[TEST 2] Invalid Date Range (end before start)")
    print("-"*70)
    invalid_dates = valid_data.copy()
    invalid_dates["service_start_date"] = "2024-12-31"
    invalid_dates["service_end_date"] = "2024-12-01"
    
    is_valid, error = validate_emissions_data(invalid_dates)
    print(f"Result: {'✅ VALID' if is_valid else f'❌ INVALID: {error}'}")
    
    # Test Case 3: Keyword proximity check
    print("\n[TEST 3] Keyword Proximity Check")
    print("-"*70)
    
    # Good report - value near emissions keyword
    good_report = """
    GRI 305-2 Disclosure
    Reporting Period: December 2024
    
    Total Scope 2 emissions: 0.622 metric tons CO2e
    
    Calculation: Based on 850 kWh using EPA eGRID factor of 0.732 kg CO2e/kWh.
    """
    
    is_accurate, warning = verify_report_accuracy(good_report, valid_data)
    print(f"Good report: {'✅ ACCURATE' if is_accurate else f'❌ INACCURATE'}")
    if warning:
        print(f"  {warning}")
    
    # Bad report - wrong value near emissions keyword
    bad_report = """
    GRI 305-2 Disclosure
    Reporting Period: December 2024
    
    Total Scope 2 emissions: 0.850 metric tons CO2e
    
    Based on account #622.
    """
    
    is_accurate, warning = verify_report_accuracy(bad_report, valid_data)
    print(f"\nBad report: {'✅ ACCURATE' if is_accurate else f'❌ INACCURATE'}")
    if warning:
        print(f"  {warning}")
    
    # Test Case 4: Unit conversion error
    print("\n[TEST 4] Unit Conversion Error Detection")
    print("-"*70)
    
    unit_error_report = """
    Total Scope 2 emissions: 622 kg CO2e
    (Note: Source data was in metric tons)
    """
    
    is_accurate, warning = verify_report_accuracy(unit_error_report, valid_data)
    print(f"Result: {'✅ ACCURATE' if is_accurate else f'❌ INACCURATE'}")
    if warning:
        print(f"  {warning}")
    
    # Test Case 5: Completeness check
    print("\n[TEST 5] Report Completeness")
    print("-"*70)
    
    incomplete_report = """
    We used electricity.
    """
    
    is_complete, missing = validate_report_completeness(incomplete_report)
    print(f"Result: {'✅ COMPLETE' if is_complete else f'❌ INCOMPLETE'}")
    if missing:
        print(f"  Missing sections: {', '.join(missing)}")