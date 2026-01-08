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

st.sidebar.markdown("---")
st.sidebar.markdown("### 📊 Project Metrics")

# Mock metrics - would be real in production
st.sidebar.metric("Reports Generated", "12")
st.sidebar.metric("Avg Time Saved", "70%")
st.sidebar.metric("Avg Cost/Report", "$0.08")

st.sidebar.markdown("---")
st.sidebar.markdown("### ℹ️ About")
st.sidebar.markdown("""
This system automates ESG compliance reporting by:
- Extracting data from utility bills
- Calculating emissions (EPA factors)
- Categorizing to GRI/SASB standards
- Generating compliance reports
- Identifying cost-saving opportunities
""")

st.sidebar.markdown("---")
st.sidebar.markdown("**Built with:** Claude API + Streamlit")
st.sidebar.markdown("[GitHub](https://github.com/yourusername/esg-automation-system)")

# Tabs
tab1, tab2, tab3, tab4, tab5 = st.tabs(["📄 Extract Data", "📊 Calculate Emissions", "🏷️ Categorize", "📚 ESG Standards", "📈 Operational Insights"])

with tab1:
    st.header("📄 Extract Utility Bill Data")
    
    bill_text = st.text_area(
        "Paste utility bill text:",
        height=300,
        placeholder="Paste your utility bill text here..."
    )
    
    region = st.selectbox(
        "Region (for emissions calculation):",
        ["US_AVERAGE", "ARKANSAS", "CALIFORNIA", "TEXAS", "NEW_YORK", "FLORIDA"]
    )
    
    if st.button("Extract & Calculate", type="primary"):
        if bill_text:
            with st.spinner("Processing bill..."):
                from src.extract import extract_and_calculate_emissions
                
                result = extract_and_calculate_emissions(bill_text, region=region)
                
                if result["success"]:
                    st.success("✅ Extraction successful!")
                    
                    # Show warnings if any
                    if result["warnings"]:
                        for warning in result["warnings"]:
                            st.warning(warning)
                    
                    # Display extracted data
                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric(
                            "Usage",
                            f"{result['extraction']['total_kwh']:.0f} kWh"
                        )
                        st.caption(result['extraction'].get('unit_conversion_applied', 'No conversion'))
                    
                    with col2:
                        st.metric(
                            "Cost",
                            f"${result['extraction']['total_cost']:.2f}"
                        )
                        st.caption(f"Rate: ${result['extraction'].get('calculated_rate_per_kwh', 0):.3f}/kWh")
                    
                    # Display emissions
                    st.subheader("📊 Calculated Emissions")
                    col3, col4 = st.columns(2)
                    with col3:
                        st.metric(
                            "CO2 Emissions",
                            f"{result['emissions']['data']['emissions_kg_co2e']} kg"
                        )
                    with col4:
                        st.metric(
                            "Metric Tons CO2e",
                            f"{result['emissions']['data']['emissions_mtco2e']}"
                        )
                    
                    # Update session state
                    st.session_state.total_cost += result['combined_cost']
                    st.session_state.kwh = result['extraction']['total_kwh']
                    
                    # Show full details in expander
                    with st.expander("View Full Details"):
                        st.json(result)
                else:
                    st.error(f"❌ {result['error']}")
                    if result.get('warnings'):
                        for w in result['warnings']:
                            st.warning(w)
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

with tab4:
    st.header("📚 Query ESG Standards")
    st.markdown("Ask questions about GRI and SASB standards. Answers are sourced from official documentation.")
    
    question = st.text_input(
        "Ask about ESG standards:",
        placeholder="e.g., What are Scope 2 emissions? How should companies report electricity?"
    )
    
    if st.button("Search Standards", type="primary"):
        if question:
            with st.spinner("Searching ESG standards documentation..."):
                from src.rag import ESGStandardsRAG
                
                # Initialize RAG system
                rag = ESGStandardsRAG()
                
                # Query
                result = rag.query(question)
                
                # Track cost (you'll need to add cost tracking to RAG)
                # For now, estimate ~$0.02 per query
                st.session_state.total_cost += 0.02
                
                # Display answer
                st.success("Answer from ESG Standards:")
                st.markdown(result['answer'])
                
                # Display sources
                with st.expander("📖 Sources"):
                    for source in set(result['sources']):
                        st.caption(f"• {source}")
                
                st.info("💡 This answer was generated using RAG (Retrieval-Augmented Generation) over official GRI and SASB standards.")
        else:
            st.warning("Please enter a question first")

with tab5:
    st.header("📈 Operational Insights")
    
    # Mock data for now - in real version, load from database
    monthly_data = {
        "November": {"kwh": 920, "cost": 138.50, "co2_kg": 673},
        "December": {"kwh": 850, "cost": 127.50, "co2_kg": 622}
    }
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        kwh_change = ((850 - 920) / 920) * 100
        st.metric(
            "kWh Usage",
            "850 kWh",
            f"{kwh_change:.1f}% vs last month",
            delta_color="inverse"
        )
    
    with col2:
        cost_change = ((127.50 - 138.50) / 138.50) * 100
        st.metric(
            "Cost",
            "$127.50",
            f"{cost_change:.1f}% vs last month",
            delta_color="inverse"
        )
    
    with col3:
        co2_change = ((622 - 673) / 673) * 100
        st.metric(
            "CO2 Emissions",
            "622 kg",
            f"{co2_change:.1f}% vs last month",
            delta_color="inverse"
        )
    
    st.subheader("💡 Cost-Saving Opportunities")
    
    # Use Claude to generate insights
    if st.button("Generate Insights"):
        prompt = """Analyze this energy usage data and provide 3 specific cost-saving recommendations:

Current Month: 850 kWh, $127.50, 622 kg CO2
Previous Month: 920 kWh, $138.50, 673 kg CO2
Region: Arkansas

Format as bullet points, each with:
- Recommendation
- Estimated savings
- Implementation difficulty"""

        from src.utils import call_claude_with_cost
        insights, cost = call_claude_with_cost(prompt)
        
        st.markdown(insights)
        st.caption(f"Analysis cost: ${cost['total_cost']:.4f}")
            
# Footer
st.markdown("---")
col1, col2, col3 = st.columns(3)
with col1:
    st.markdown("Built with Claude API + Streamlit")
with col2:
    st.markdown("[GitHub](https://github.com/yourusername/esg-automation-system)")
with col3:
    st.markdown("[Documentation](https://github.com/yourusername/esg-automation-system#readme)")