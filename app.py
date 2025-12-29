# Streamlit main app
"""ESG Automation System - Streamlit Interface"""
import streamlit as st
import json
from src.extract import extract_utility_bill_data
from src.calculate import calculate_electricity_emissions
from src.categorize import categorize_to_scope

# Page config (add at very top)
st.set_page_config(
    page_title="ESG Automation System",
    page_icon="🌍",
    layout="wide"
)

st.title("🌍 ESG Automation System")
st.markdown("Automate ESG compliance reporting with AI")

# Sidebar for cost tracking
st.sidebar.markdown("### 💰 Session Costs")
if 'total_cost' not in st.session_state:
    st.session_state.total_cost = 0.0

st.sidebar.metric("Total API Cost", f"${st.session_state.total_cost:.4f}")

# Add reset button
if st.sidebar.button("Reset Costs"):
    st.session_state.total_cost = 0.0
    st.rerun()

# Tabs
tab1, tab2, tab3 = st.tabs(["📄 Extract Data", "📊 Calculate Emissions", "🏷️ Categorize"])

with tab1:
    st.header("Extract Utility Bill Data")
    
    bill_text = st.text_area(
        "Paste utility bill text:",
        height=300,
        placeholder="Paste your utility bill text here..."
    )
    
    if st.button("Extract Data", type="primary", key="extract_btn"):
        if bill_text:
            with st.spinner("Extracting data..."):
                result = extract_utility_bill_data(bill_text)
                
                if result:
                    st.session_state.total_cost += result.get('extraction_cost', 0)
                    
                    st.success("Data extracted successfully!")
                    
                    # Display key metrics in columns
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("kWh Usage", result.get('total_kwh', 'N/A'))
                    with col2:
                        st.metric("Total Cost", f"${result.get('total_cost', 0):.2f}")
                    with col3:
                        st.metric("API Cost", f"${result.get('extraction_cost', 0):.4f}")
                    
                    # Show full data
                    with st.expander("View Full Extracted Data"):
                        st.json(result)
                    
                    # Store for next tab
                    st.session_state.kwh = result.get('total_kwh', 0)
                else:
                    st.error("Failed to extract data")
        else:
            st.warning("Please paste bill text first")

with tab2:
    st.header("Calculate Emissions")
    
    kwh = st.number_input(
        "kWh Usage:",
        min_value=0.0,
        value=float(st.session_state.get('kwh', 0)),
        step=10.0
    )
    
    region = st.selectbox(
        "Region:",
        ["US_AVERAGE", "ARKANSAS", "CALIFORNIA", "TEXAS"],
        index=0
    )
    
    if st.button("Calculate Emissions", type="primary", key="calc_btn"):
        if kwh > 0:
            try:
                result = calculate_electricity_emissions(kwh, region)
                
                st.success("Emissions calculated!")
                
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("CO2 Emissions", f"{result['kg_co2']} kg")
                with col2:
                    st.metric("Metric Tons CO2", f"{result['metric_tons_co2']} MT")
                
                with st.expander("View Calculation Details"):
                    st.json(result)
                    
            except ValueError as e:
                st.error(f"Error: {e}")
        else:
            st.warning("Enter kWh value first")

with tab3:
    st.header("Categorize Activity")
    
    activity = st.text_input(
        "Activity description:",
        placeholder="e.g., Purchased electricity from grid"
    )
    
    if st.button("Categorize", type="primary", key="cat_btn"):
        if activity:
            with st.spinner("Categorizing..."):
                result = categorize_to_scope(activity)
                st.session_state.total_cost += result.get('categorization_cost', 0)
                
                # Display result
                scope_color = {
                    "Scope 1": "🔴",
                    "Scope 2": "🟡", 
                    "Scope 3": "🟢",
                    "Unknown": "⚪"
                }
                
                st.success(f"{scope_color.get(result['scope'], '⚪')} **{result['scope']}**")
                st.info(result['reasoning'])
                
                # Show API cost
                st.caption(f"API Cost: ${result.get('categorization_cost', 0):.4f}")
        else:
            st.warning("Enter activity description first")

# Footer
st.markdown("---")
col1, col2, col3 = st.columns(3)
with col1:
    st.markdown("Built with Claude API + Streamlit")
with col2:
    st.markdown("[GitHub](https://github.com/yourusername/esg-automation-system)")
with col3:
    st.markdown("[Documentation](https://github.com/yourusername/esg-automation-system#readme)")