"""Calculate emissions from energy usage with production-grade audit trails"""
import json
from datetime import datetime
from typing import Dict, Optional, Tuple

def load_epa_factors(filepath: str = "data/epa_factors.json") -> Dict:
    """
    Load EPA emission factors from file
    
    Args:
        filepath: Path to EPA factors JSON file
        
    Returns:
        dict: Complete factors data with metadata
        
    Raises:
        FileNotFoundError: If factors file doesn't exist
        ValueError: If JSON is malformed
    """
    try:
        with open(filepath, "r") as f:
            factors = json.load(f)
            
        # Validate structure
        required_keys = ["version", "data_source", "gwp_reference"]
        missing = [k for k in required_keys if k not in factors]
        if missing:
            raise ValueError(f"EPA factors file missing required keys: {missing}")
            
        return factors
        
    except FileNotFoundError:
        raise FileNotFoundError(f"EPA factors file not found at {filepath}")
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in EPA factors file: {e}")


def calculate_electricity_emissions(
    kwh: float, 
    region: str = "US_AVERAGE",
    factors_data: Optional[Dict] = None,
    reporting_period: Optional[str] = None
) -> Dict:
    """
    Calculate CO2e emissions from electricity usage with full audit trail
    
    This function implements GHG Protocol Scope 2 calculation methodology
    using location-based emission factors from EPA eGRID.
    
    Args:
        kwh: Kilowatt-hours of electricity consumed (must be positive)
        region: EPA eGRID subregion or US_AVERAGE
        factors_data: Optional pre-loaded factors (for batch processing)
        reporting_period: Optional reporting period string (e.g., "December 2024")
        
    Returns:
        dict: Nested structure with metadata, data, and audit trail
        
    Raises:
        TypeError: If kwh is not numeric
        ValueError: If kwh is negative or region not found
        
    Example:
        >>> result = calculate_electricity_emissions(850, "ARKANSAS")
        >>> print(result['data']['emissions_mtco2e'])
        0.6222
    """
    
    # === INPUT VALIDATION ===
    if not isinstance(kwh, (int, float)):
        raise TypeError(f"kWh must be numeric, got {type(kwh).__name__}")
    
    if kwh < 0:
        raise ValueError(f"kWh cannot be negative, got {kwh}")
    
    # === LOAD FACTORS (with caching support) ===
    if factors_data is None:
        factors_data = load_epa_factors()
    
    # === LOOKUP EMISSION FACTOR ===
    try:
        electricity_factors = factors_data["electricity"]["factors"]
        
        if region not in electricity_factors:
            # AUDIT DECISION: Crash instead of defaulting to US_AVERAGE
            # Rationale: In compliance, explicit is better than assumed
            available_regions = ", ".join(electricity_factors.keys())
            raise ValueError(
                f"Region '{region}' not found in EPA factors. "
                f"Available regions: {available_regions}"
            )
        
        emission_factor = electricity_factors[region]
        
    except KeyError as e:
        raise ValueError(f"Malformed EPA factors data structure: {e}")
    
    # === CALCULATE EMISSIONS ===
    kg_co2e = kwh * emission_factor
    metric_tons_co2e = kg_co2e / 1000
    
    # === BUILD CALCULATION STRING ===
    calculation_formula = (
        f"{kwh:,.2f} kWh × {emission_factor} kg CO2e/kWh = "
        f"{kg_co2e:,.2f} kg CO2e = {metric_tons_co2e:.6f} metric tons CO2e"
    )
    
    # === RETURN ENRICHED STRUCTURE ===
    return {
        "metadata": {
            "scope": "Scope 2 (Location-based)",
            "inventory_year": 2024,
            "reporting_period": reporting_period or "Not specified",
            "boundary": "Organizational",
            "standard": "GHG Protocol Corporate Standard",
            "calculation_date": datetime.now().isoformat()
        },
        
        "data": {
            "input_value": kwh,
            "input_unit": "kWh",
            "region": region,
            "emissions_kg_co2e": round(kg_co2e, 2),
            "emissions_mtco2e": round(metric_tons_co2e, 6)
        },
        
        "audit": {
            "emission_factor": emission_factor,
            "emission_factor_unit": factors_data["electricity"]["unit"],
            "emission_factor_source": factors_data["data_source"],
            "gwp_reference": factors_data["gwp_reference"],
            "factors_version": factors_data["version"],
            "calculation_formula": calculation_formula,
            "methodology_note": (
                "Location-based method using grid-average emission factors. "
                "Market-based method would require contractual instrument tracking."
            )
        }
    }


def calculate_natural_gas_emissions(
    therms: float,
    factors_data: Optional[Dict] = None,
    reporting_period: Optional[str] = None
) -> Dict:
    """
    Calculate CO2e emissions from natural gas combustion (Scope 1)
    
    Args:
        therms: Natural gas consumption in therms
        factors_data: Optional pre-loaded factors
        reporting_period: Optional reporting period string
        
    Returns:
        dict: Nested structure with metadata, data, and audit trail
    """
    
    # Input validation
    if not isinstance(therms, (int, float)):
        raise TypeError(f"Therms must be numeric, got {type(therms).__name__}")
    
    if therms < 0:
        raise ValueError(f"Therms cannot be negative, got {therms}")
    
    # Load factors
    if factors_data is None:
        factors_data = load_epa_factors()
    
    # Lookup factor
    try:
        emission_factor = factors_data["natural_gas"]["factors"]["US_AVERAGE"]
    except KeyError as e:
        raise ValueError(f"Natural gas factors not found: {e}")
    
    # Calculate
    kg_co2e = therms * emission_factor
    metric_tons_co2e = kg_co2e / 1000
    
    calculation_formula = (
        f"{therms:,.2f} therms × {emission_factor} kg CO2e/therm = "
        f"{kg_co2e:,.2f} kg CO2e = {metric_tons_co2e:.6f} metric tons CO2e"
    )
    
    return {
        "metadata": {
            "scope": "Scope 1 (Direct)",
            "inventory_year": 2024,
            "reporting_period": reporting_period or "Not specified",
            "boundary": "Organizational",
            "standard": "GHG Protocol Corporate Standard",
            "calculation_date": datetime.now().isoformat()
        },
        
        "data": {
            "input_value": therms,
            "input_unit": "therms",
            "emissions_kg_co2e": round(kg_co2e, 2),
            "emissions_mtco2e": round(metric_tons_co2e, 6)
        },
        
        "audit": {
            "emission_factor": emission_factor,
            "emission_factor_unit": factors_data["natural_gas"]["unit"],
            "emission_factor_source": factors_data["data_source"],
            "gwp_reference": factors_data["gwp_reference"],
            "factors_version": factors_data["version"],
            "calculation_formula": calculation_formula,
            "methodology_note": (
                "Direct combustion emission factor for natural gas. "
                "Includes CO2, CH4, and N2O in CO2e using AR5 GWPs."
            )
        }
    }


# ============================================================================
# BATCH PROCESSING HELPER (For efficiency when processing many bills)
# ============================================================================

def batch_calculate_emissions(activities: list) -> Tuple[list, Dict]:
    """
    Calculate emissions for multiple activities efficiently
    
    Args:
        activities: List of dicts with keys: type, value, region (optional)
        
    Returns:
        tuple: (list of results, summary dict)
        
    Example:
        activities = [
            {"type": "electricity", "value": 850, "region": "ARKANSAS"},
            {"type": "electricity", "value": 920, "region": "TEXAS"},
            {"type": "natural_gas", "value": 45}
        ]
    """
    # Load factors once for all calculations
    factors_data = load_epa_factors()
    
    results = []
    total_emissions = 0.0
    errors = []
    
    for i, activity in enumerate(activities):
        try:
            if activity["type"] == "electricity":
                result = calculate_electricity_emissions(
                    activity["value"],
                    activity.get("region", "US_AVERAGE"),
                    factors_data
                )
            elif activity["type"] == "natural_gas":
                result = calculate_natural_gas_emissions(
                    activity["value"],
                    factors_data
                )
            else:
                raise ValueError(f"Unknown activity type: {activity['type']}")
            
            results.append(result)
            total_emissions += result["data"]["emissions_mtco2e"]
            
        except Exception as e:
            errors.append({"activity_index": i, "error": str(e)})
    
    summary = {
        "total_emissions_mtco2e": round(total_emissions, 6),
        "activities_processed": len(results),
        "activities_failed": len(errors),
        "errors": errors
    }
    
    return results, summary


# ============================================================================
# TEST / DEMO
# ============================================================================

if __name__ == "__main__":
    print("="*70)
    print("ESG EMISSIONS CALCULATOR - PRODUCTION VERSION")
    print("="*70)
    
    # Test 1: Single calculation
    print("\n[TEST 1] Single Electricity Calculation")
    print("-"*70)
    result = calculate_electricity_emissions(
        kwh=850,
        region="ARKANSAS",
        reporting_period="December 2024"
    )
    
    print(f"Emissions: {result['data']['emissions_mtco2e']} metric tons CO2e")
    print(f"Formula: {result['audit']['calculation_formula']}")
    print(f"Source: {result['audit']['emission_factor_source']}")
    
    # Test 2: Error handling - invalid region
    print("\n[TEST 2] Error Handling - Invalid Region")
    print("-"*70)
    try:
        result = calculate_electricity_emissions(850, "INVALID_REGION")
    except ValueError as e:
        print(f"✅ Caught error correctly: {e}")
    
    # Test 3: Batch processing
    print("\n[TEST 3] Batch Processing")
    print("-"*70)
    activities = [
        {"type": "electricity", "value": 850, "region": "ARKANSAS"},
        {"type": "electricity", "value": 1200, "region": "TEXAS"},
        {"type": "natural_gas", "value": 45}
    ]
    
    results, summary = batch_calculate_emissions(activities)
    print(f"Total emissions: {summary['total_emissions_mtco2e']} metric tons CO2e")
    print(f"Activities processed: {summary['activities_processed']}")
    
    # Test 4: Full audit trail output
    print("\n[TEST 4] Full Audit Trail (JSON)")
    print("-"*70)
    print(json.dumps(result, indent=2))