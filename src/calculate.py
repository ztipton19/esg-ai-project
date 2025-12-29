# Emissions calculations
"""Calculate emissions from energy usage"""
import json

def load_epa_factors():
    """Load EPA emission factors from file"""
    try:
        with open("data/epa_factors.json", "r") as f:
            return json.load(f)
    except FileNotFoundError:
        raise FileNotFoundError(
            "EPA factors file not found. Create data/epa_factors.json"
        )
    except json.JSONDecodeError:
        raise ValueError("Invalid JSON in epa_factors.json")

def calculate_electricity_emissions(kwh, region="US_AVERAGE"):
    """
    Calculate CO2 emissions from electricity usage
    
    Args:
        kwh: Kilowatt-hours used (must be >= 0)
        region: Region for emission factor (default US_AVERAGE)
        
    Returns:
        dict: Emissions in kg CO2 and metric tons CO2
    """
    # Validate input
    if kwh < 0:
        raise ValueError(f"kWh must be non-negative, got {kwh}")
    
    # Load factors
    factors = load_epa_factors()
    
    # Check if region exists
    if region not in factors["electricity"]:
        available = list(factors["electricity"].keys())
        available.remove("unit")  # Don't show "unit" as an option
        raise ValueError(
            f"Region '{region}' not found. Available: {available}"
        )
    
    emission_factor = factors["electricity"][region]
    
    kg_co2 = kwh * emission_factor
    metric_tons_co2 = kg_co2 / 1000
    
    return {
        "kwh": kwh,
        "region": region,
        "emission_factor_used": emission_factor,
        "kg_co2": round(kg_co2, 2),
        "metric_tons_co2": round(metric_tons_co2, 4)
    }

# Test it
if __name__ == "__main__":
    # Test normal case
    result = calculate_electricity_emissions(850, "ARKANSAS")
    print("Normal test:")
    print(json.dumps(result, indent=2))