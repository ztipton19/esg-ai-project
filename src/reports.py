"""Generate ESG compliance reports with validation"""
from src.utils import call_claude_with_cost
from src.validation import validate_emissions_data, verify_report_accuracy, validate_report_completeness
import json
from datetime import datetime

def generate_gri_report_section(emissions_data, scope="Scope 2", previous_period_data=None):
    """
    Generate GRI 305-compliant report section with validation and audit trail
    
    Args:
        emissions_data: Dict with emissions calculations (must include audit trail)
        scope: Which scope to report on
        previous_period_data: Optional dict with prior period data for comparison
        
    Returns:
        dict: {
            "report_text": str,
            "cost": float,
            "validation_passed": bool,
            "warnings": list,
            "audit_trail": dict
        }
    """
    
    # Step 1: PRE-CALL VALIDATION
    is_valid, error_msg = validate_emissions_data(emissions_data)
    if not is_valid:
        return {
            "report_text": None,
            "cost": 0,
            "validation_passed": False,
            "warnings": [f"Validation Error: {error_msg}"],
            "audit_trail": None
        }
    
    # Step 2: ENHANCED PROMPTING
    system_prompt = """You are a Senior Sustainability Consultant specializing in GRI Standards. 
Your task is to draft a technical, precise disclosure for GRI 305 (Emissions).

CRITICAL REQUIREMENTS:
- Use EXACT numbers from the provided data - do not calculate or estimate
- Cite the specific emission factor source provided
- Include the calculation methodology verbatim
- Maintain objective, neutral tone appropriate for audited reports
- Format as professional report prose, not conversational text"""

    # Build comparison context if available
    comparison_text = ""
    if previous_period_data:
        # ENHANCED: Handle None and missing values
        prev_mt = previous_period_data.get("metric_tons_co2")
        current_mt = emissions_data.get("metric_tons_co2")
        
        # Only calculate change if both values exist and previous is non-zero
        if prev_mt is not None and current_mt is not None and prev_mt > 0:
            change_pct = ((current_mt - prev_mt) / prev_mt * 100)
            change_abs = current_mt - prev_mt
            
            comparison_text = f"""
Previous Period Comparison:
- Prior period: {prev_mt} metric tons CO2e
- Current period: {current_mt} metric tons CO2e
- Absolute change: {change_abs:+.4f} metric tons CO2e
- Percentage change: {change_pct:+.1f}%
"""
        elif prev_mt is not None and current_mt is not None and prev_mt == 0:
            # Previous period was zero - show as new baseline
            comparison_text = f"""
Previous Period Comparison:
- Prior period: {prev_mt} metric tons CO2e (baseline period)
- Current period: {current_mt} metric tons CO2e
- Note: Prior period had zero emissions - this is the first period with measurable activity
"""
        else:
            # Incomplete data - mention but don't calculate
            comparison_text = f"""
Previous Period Note:
- Historical comparison data incomplete or unavailable
- Current period: {current_mt if current_mt is not None else 'N/A'} metric tons CO2e
"""

    user_prompt = f"""Generate a GRI 305-{2 if scope == "Scope 2" else 1} compliant disclosure.

Emissions Data:
{json.dumps(emissions_data, indent=2)}

{comparison_text}

Required Sections:
1. Reporting Period and Scope
2. Total Emissions (in metric tons CO2e) - USE EXACT VALUE: {emissions_data['metric_tons_co2']}
3. Calculation Methodology (cite: {emissions_data['emission_factor_source']})
4. Data Quality and Limitations
5. Year-over-year comparison (if previous data provided)

Format as a single professional disclosure section suitable for inclusion in a sustainability report."""

    # Step 3: API CALL WITH ERROR HANDLING
    try:
        response, cost = call_claude_with_cost(
            user_prompt,
            max_tokens=1024,
            system_prompt=system_prompt  # Note: your utils.py needs to support system prompts
        )
        
    except Exception as e:
        return {
            "report_text": None,
            "cost": 0,
            "validation_passed": False,
            "warnings": [f"API Error: {str(e)}"],
            "audit_trail": None
        }

    # Step 4: POST-CALL VERIFICATION
    warnings = []
    
    # Accuracy check with percentage tolerance
    is_accurate, warning_msg = verify_report_accuracy(
        response, 
        emissions_data,
        tolerance_percent=0.1  # 0.1% tolerance for audit compliance
    )
    if not is_accurate or warning_msg:
        warnings.append(warning_msg)
    
    # Completeness check
    is_complete, missing_sections = validate_report_completeness(response)
    if not is_complete:
        warnings.append(f"⚠️ Report missing required sections: {', '.join(missing_sections)}")
    
    # Check if report is suspiciously short
    if len(response) < 200:
        warnings.append("⚠️ Warning: Generated report is unusually short (< 200 characters)")
    
    # Step 5: BUILD AUDIT TRAIL
    audit_trail = {
        "generation_timestamp": datetime.now().isoformat(),
        "source_data": emissions_data,
        "model_used": "claude-sonnet-4-20250514",
        "validation_passed": is_accurate and len(warnings) == 1,  # Only length warning is minor
        "warnings": warnings,
        "cost": cost['total_cost']
    }
    
    return {
        "report_text": response,
        "cost": cost['total_cost'],
        "validation_passed": len([w for w in warnings if "hallucination" in w.lower()]) == 0,
        "warnings": warnings,
        "audit_trail": audit_trail
    }


# In src/reports.py, update the __main__ section:

if __name__ == "__main__":
    print("="*70)
    print("GRI REPORT GENERATION - PRODUCTION VERSION")
    print("="*70)
    
    # Test case 1: Standard report (no comparison)
    print("\n[TEST 1] Standard Report")
    print("-"*70)
    test_data = {
        "reporting_period": "December 2024",
        "service_start_date": "2024-12-01",
        "service_end_date": "2024-12-31",
        "total_kwh": 850,
        "region": "Arkansas",
        "metric_tons_co2": 0.6222,
        "emission_factor_used": 0.732,
        "emission_factor_source": "EPA eGRID 2024",
        "emission_factor_unit": "kg CO2e per kWh",
        "gwp_source": "IPCC AR5",
        "calculation_method": "850 kWh × 0.732 kg CO2e/kWh = 622.2 kg CO2e"
    }
    
    result = generate_gri_report_section(test_data, "Scope 2")
    
    print(f"Status: {'✅ PASS' if result['validation_passed'] else '❌ FAIL'}")
    print(f"Cost: ${result['cost']:.4f}")
    print(f"Warnings: {len(result['warnings'])}")
    
    if result['warnings']:
        for w in result['warnings']:
            print(f"  - {w}")
    
# Test case 2: With year-over-year comparison
    print("\n[TEST 2] Report with YoY Comparison")
    print("-"*70)
    prev_data = {"metric_tons_co2": 0.673}
    
    result = generate_gri_report_section(test_data, "Scope 2", prev_data)
    
    print(f"Status: {'✅ PASS' if result['validation_passed'] else '❌ FAIL'}")
    
    # Add safety check for None
    if result['report_text']:
        print(f"YoY in report: {'Yes' if 'previous period' in result['report_text'].lower() else 'No'}")
    else:
        print(f"YoY in report: N/A (report generation failed)")
    
    # Test case 3: Comparison with zero previous period
    print("\n[TEST 3] Comparison with Zero Baseline")
    print("-"*70)
    zero_prev = {"metric_tons_co2": 0}
    
    result = generate_gri_report_section(test_data, "Scope 2", zero_prev)
    
    print(f"Status: {'✅ PASS' if result['validation_passed'] else '❌ FAIL'}")
    
    # Add safety check
    if result['report_text']:
        print(f"Handled zero baseline: {'Yes' if 'baseline' in result['report_text'].lower() else 'No'}")
    else:
        print(f"Handled zero baseline: N/A (report generation failed)")
    
    # Test case 4: Missing previous data
    print("\n[TEST 4] Incomplete Comparison Data")
    print("-"*70)
    incomplete_prev = {}  # Empty dict
    
    result = generate_gri_report_section(test_data, "Scope 2", incomplete_prev)
    
    print(f"Status: {'✅ PASS' if result['validation_passed'] else '❌ FAIL'}")
    print(f"Handled gracefully: {'Yes' if result['report_text'] else 'No'}")
    
    # Show one full report (only if it exists)
    if result['report_text']:
        print("\n[SAMPLE REPORT]")
        print("="*70)
        print(result['report_text'])
        print("="*70)
    else:
        print("\n[SAMPLE REPORT]")
        print("="*70)
        print("Report generation failed - see warnings above")
        print("="*70)