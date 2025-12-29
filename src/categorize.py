# ESG categorization
"""Categorize activities to ESG frameworks"""
from src.utils import call_claude_with_cost
import json

def categorize_to_scope(activity_description):
    """
    Categorize activity to GHG Protocol Scope (1, 2, or 3)
    
    Args:
        activity_description: Description of the activity
        
    Returns:
        dict: Scope category and reasoning
    """
    # Validate input
    if not activity_description or not activity_description.strip():
        return {
            "scope": "Unknown",
            "reasoning": "No activity description provided",
            "categorization_cost": 0
        }
    
    prompt = f"""Categorize this activity according to GHG Protocol scopes.

Activity: {activity_description}

GHG Protocol definitions:
- Scope 1: Direct emissions from owned/controlled sources (e.g., company vehicles, on-site fuel combustion)
- Scope 2: Indirect emissions from purchased energy (e.g., electricity, steam, heating/cooling)
- Scope 3: All other indirect emissions in value chain (e.g., business travel, employee commuting, purchased goods)

IMPORTANT:
- Only categorize if you're confident based on the description
- If ambiguous or unclear, return "Unknown" with explanation
- Do not make assumptions about ownership or control

Return a JSON object with:
- scope: "Scope 1", "Scope 2", "Scope 3", or "Unknown"
- reasoning: Brief explanation (1-2 sentences max)

Return ONLY valid JSON, no markdown formatting."""

    response, cost = call_claude_with_cost(prompt, max_tokens=256, temperature=0)
    
    # Strip markdown fences if present
    response = response.strip()
    if response.startswith("```json"):
        response = response[7:]
    if response.startswith("```"):
        response = response[3:]
    if response.endswith("```"):
        response = response[:-3]
    response = response.strip()
    
    # Parse JSON
    try:
        data = json.loads(response)
        data['categorization_cost'] = cost['total_cost']
        
        # Validate scope value
        valid_scopes = ["Scope 1", "Scope 2", "Scope 3", "Unknown"]
        if data.get("scope") not in valid_scopes:
            print(f"Warning: Invalid scope '{data.get('scope')}', setting to Unknown")
            data["scope"] = "Unknown"
            data["reasoning"] = f"Invalid categorization: {data.get('reasoning', '')}"
        
        return data
        
    except json.JSONDecodeError:
        print(f"Failed to parse JSON: {response}")
        return {
            "scope": "Unknown",
            "reasoning": "Failed to parse response",
            "categorization_cost": cost['total_cost']
        }

# Test it
if __name__ == "__main__":
    test_cases = [
        "Purchased electricity from grid",
        "Company vehicle fuel consumption",
        "Employee business travel via commercial airline",
        "Office supplies purchase",  # Edge case - could be ambiguous
        "",  # Edge case - empty string
        "Natural gas heating in company-owned facility",  # Clear Scope 1
    ]
    
    for activity in test_cases:
        result = categorize_to_scope(activity)
        print(f"\nActivity: '{activity}'")
        print(f"Scope: {result['scope']}")
        print(f"Reasoning: {result['reasoning']}")
        print(f"API Cost: ${result['categorization_cost']:.6f}")