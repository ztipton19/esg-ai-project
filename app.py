# Streamlit main app
"""ESG Automation System - Streamlit Interface"""
import streamlit as st
import json
from src.extract import extract_utility_bill_data, extract_and_calculate_emissions
from src.calculate import calculate_electricity_emissions
from src.categorize import categorize_to_scope

# ============================================================================
# DEMO DATA
# ============================================================================

DEMO_BILL_TEXT = """
SOUTHWESTERN ELECTRIC POWER COMPANY
Account #000-000-000-0-0

SERVICE ADDRESS: 
555 S George Washington Ln
FAYETTEVILLE, AR 72701-5275

Current bill summary:
Billing from 11/05/25 - 12/05/25 (31 days)

Usage: 282 kWh
Current Charges: $46.84

Line Item Charges:
Rate Billing                        $ 19.52
Customer Charge                       11.97
Formula Rate Review Rider              3.61
Cost of Fuel @ 0.0225120 Per kWh      6.35
Municipal Franchise Adjustment         1.24
Sales Tax                              4.15

Current Balance Due                 $ 46.84
Total Balance Due                   $ 46.84

Amount due on or before January 2, 2026: $46.84
"""

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
    with tab1:
        st.header("📄 Extract Utility Bill Data")
        
        # ===== SESSION PERSISTENCE: SHOW LAST EXTRACTION =====
        if 'last_extraction' in st.session_state and st.session_state.last_extraction:
            with st.expander("📋 Last Extraction Results (Persistent)", expanded=False):
                result = st.session_state.last_extraction
                
                st.info(f"🔄 Method: {st.session_state.get('extraction_method', 'Unknown')}")
                
                # Display key metrics
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Usage", f"{result['extraction']['total_kwh']:.0f} kWh")
                with col2:
                    st.metric("Cost", f"${result['extraction']['total_cost']:.2f}")
                with col3:
                    st.metric("Emissions", f"{result['emissions']['data']['emissions_mtco2e']} MT CO2e")
                
                # Show reporting period
                start = result['extraction'].get('service_start_date', 'N/A')
                end = result['extraction'].get('service_end_date', 'N/A')
                st.caption(f"📅 Period: {start} to {end}")
                
                # Clear button
                if st.button("🗑️ Clear Saved Results"):
                    del st.session_state.last_extraction
                    if 'extraction_method' in st.session_state:
                        del st.session_state.extraction_method
                    st.rerun()
        # ===== END SESSION PERSISTENCE =====
    
    # Upload method selector
    upload_method = st.radio(
        "Choose input method:",
        ["📎 Upload PDF", "📝 Paste Text"],
        horizontal=True
    )
    
    bill_text = None
    pdf_file = None
    
    if upload_method == "📎 Upload PDF":
        st.info("💡 **AI-Powered Extraction:** PDFs are processed using Claude's native document understanding (no OCR libraries needed)")
        
        uploaded_file = st.file_uploader(
            "Upload utility bill PDF:",
            type=['pdf'],
            help="AI will read and extract data directly from your PDF"
        )
        
        region = st.selectbox(
            "Region (for emissions calculation):",
            ["US_AVERAGE", "ARKANSAS", "CALIFORNIA", "TEXAS", "NEW_YORK", "FLORIDA"],
            index=1,  # Default to Arkansas
            key="pdf_region"
        )
        
        if uploaded_file is not None and st.button("🤖 Extract from PDF", type="primary"):
            with st.spinner("🤖 AI is reading your PDF..."):
                from src.extract import extract_and_calculate_emissions
                
                # Use AI-powered PDF extraction
                result = extract_and_calculate_emissions(pdf_file=uploaded_file, region=region)
                
                if result["success"]:
                    # Update costs IMMEDIATELY
                    st.session_state.total_cost += result['combined_cost']
                    st.session_state.kwh = result['extraction']['total_kwh']
                    # Store for persistence
                    st.session_state.last_extraction = result
                    st.session_state.extraction_method = result['extraction'].get('extraction_method', 'Unknown')
                    
                    st.success("✅ AI extraction successful!")
                    
                    # Show extraction method
                    st.info(f"📄 Method: {result['extraction'].get('extraction_method', 'Unknown')}")
                    
                    # Show warnings
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
                    
                    # Audit Trail
                    with st.expander("🔍 View Audit Trail & Verification"):
                        st.markdown("#### Extraction Details")
                        st.write(f"**Timestamp:** {result['extraction'].get('extraction_timestamp', 'N/A')}")
                        st.write(f"**Method:** {result['extraction'].get('extraction_method', 'N/A')}")
                        st.write(f"**Validation Status:** {'✅ Passed' if result['extraction'].get('validation_passed') else '⚠️ Warnings present'}")
                        
                        if result['extraction'].get('unit_conversion_applied'):
                            st.write(f"**Unit Conversion:** {result['extraction']['unit_conversion_applied']}")
                        
                        st.markdown("#### Emissions Calculation")
                        audit = result['emissions']['audit']
                        st.write(f"**Formula:** `{audit['calculation_formula']}`")
                        st.write(f"**Emission Factor:** {audit['emission_factor']} {audit['emission_factor_unit']}")
                        st.write(f"**Source:** {audit['emission_factor_source']}")
                        st.write(f"**GWP Reference:** {audit['gwp_reference']}")
                        st.write(f"**Methodology:** {audit.get('methodology_note', 'N/A')}")
                        
                        st.markdown("#### Compliance Metadata")
                        metadata = result['emissions']['metadata']
                        st.write(f"**Scope:** {metadata['scope']}")
                        st.write(f"**Standard:** {metadata['standard']}")
                        st.write(f"**Reporting Period:** {metadata['reporting_period']}")
                        st.write(f"**Calculation Date:** {metadata['calculation_date']}")
                        
                        st.markdown("#### Cost Tracking")
                        st.write(f"**API Cost (This Operation):** ${result['combined_cost']:.4f}")
                        st.caption("💡 Note: PDF extraction costs ~$0.02-0.04 per document. For high-volume production (>1,000 bills/month), consider hybrid approach with local OCR models (see v2.0 roadmap).")
                    
                    # Full JSON
                    with st.expander("🔧 View Full JSON Response (Debug)"):
                        st.json(result)
                else:
                    st.error(f"❌ {result['error']}")
                    if result.get('warnings'):
                        for w in result['warnings']:
                            st.warning(w)
    
    else:  # Paste Text
        # Demo button
        col1, col2 = st.columns([3, 1])
        with col2:
            if st.button("📋 Try Demo Bill", help="Load example SWEPCO electric bill"):
                st.session_state.demo_bill_loaded = True
        
        # Text area with demo data if button clicked
        bill_text = st.text_area(
            "Paste utility bill text:",
            value=DEMO_BILL_TEXT if st.session_state.get('demo_bill_loaded', False) else "",
            height=300,
            placeholder="Paste your utility bill text here..."
        )
        
        # Clear demo flag after loading
        if 'demo_bill_loaded' in st.session_state and st.session_state.demo_bill_loaded:
            st.success("✅ Demo bill loaded! Click 'Extract & Calculate' below.")
            st.session_state.demo_bill_loaded = False
        
        region = st.selectbox(
            "Region (for emissions calculation):",
            ["US_AVERAGE", "ARKANSAS", "CALIFORNIA", "TEXAS", "NEW_YORK", "FLORIDA"],
            index=1,  # Default to Arkansas
            key="text_region"
        )
        
        has_bill_text = bill_text and len(bill_text.strip()) > 0
        
        if st.button("Extract & Calculate", type="primary", disabled=not has_bill_text):
            if bill_text:
                with st.spinner("🔍 Processing bill..."):
                    from src.extract import extract_and_calculate_emissions
                    
                    result = extract_and_calculate_emissions(bill_text=bill_text, region=region)
                    
                    if result["success"]:
                        # Update costs IMMEDIATELY
                        st.session_state.total_cost += result['combined_cost']
                        st.session_state.kwh = result['extraction']['total_kwh']
                        # Store for persistence
                        st.session_state.last_extraction = result
                        st.session_state.extraction_method = result['extraction'].get('extraction_method', 'Unknown')
                        
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
                        
                        # Audit Trail
                        with st.expander("🔍 View Audit Trail & Verification"):
                            st.markdown("#### Extraction Details")
                            st.write(f"**Timestamp:** {result['extraction'].get('extraction_timestamp', 'N/A')}")
                            st.write(f"**Method:** {result['extraction'].get('extraction_method', 'N/A')}")
                            st.write(f"**Validation Status:** {'✅ Passed' if result['extraction'].get('validation_passed') else '⚠️ Warnings present'}")
                            
                            if result['extraction'].get('unit_conversion_applied'):
                                st.write(f"**Unit Conversion:** {result['extraction']['unit_conversion_applied']}")
                            
                            st.markdown("#### Emissions Calculation")
                            audit = result['emissions']['audit']
                            st.write(f"**Formula:** `{audit['calculation_formula']}`")
                            st.write(f"**Emission Factor:** {audit['emission_factor']} {audit['emission_factor_unit']}")
                            st.write(f"**Source:** {audit['emission_factor_source']}")
                            st.write(f"**GWP Reference:** {audit['gwp_reference']}")
                            st.write(f"**Methodology:** {audit.get('methodology_note', 'N/A')}")
                            
                            st.markdown("#### Compliance Metadata")
                            metadata = result['emissions']['metadata']
                            st.write(f"**Scope:** {metadata['scope']}")
                            st.write(f"**Standard:** {metadata['standard']}")
                            st.write(f"**Reporting Period:** {metadata['reporting_period']}")
                            st.write(f"**Calculation Date:** {metadata['calculation_date']}")
                            
                            st.markdown("#### Cost Tracking")
                            st.write(f"**API Cost (This Operation):** ${result['combined_cost']:.4f}")
                        
                        # Full JSON
                        with st.expander("🔧 View Full JSON Response (Debug)"):
                            st.json(result)
                    else:
                        st.error(f"❌ {result['error']}")
                        if result.get('warnings'):
                            for w in result['warnings']:
                                st.warning(w)
            else:
                st.warning("⚠️ Please provide bill data first")

with tab2:
    st.header("📊 Calculate Emissions")
    
    kwh = st.number_input(
        "kWh Usage:",
        min_value=0.0,
        value=float(st.session_state.get('kwh', 0)),
        step=10.0
    )
    
    region = st.selectbox(
        "Region:",
        ["US_AVERAGE", "ARKANSAS", "CALIFORNIA", "TEXAS", "NEW_YORK", "FLORIDA"],
        key="calc_region"
    )
    
    if st.button("Calculate Emissions", type="primary"):
        if kwh > 0:
            from src.calculate import calculate_electricity_emissions
            
            result = calculate_electricity_emissions(kwh, region)
            
            st.success("✅ Emissions calculated!")
            
            # Display results using new structure
            col1, col2 = st.columns(2)
            with col1:
                st.metric(
                    "CO2 Emissions", 
                    f"{result['data']['emissions_kg_co2e']} kg"
                )
            with col2:
                st.metric(
                    "Metric Tons CO2e", 
                    f"{result['data']['emissions_mtco2e']} MT"
                )
            
            # Show calculation details
            st.subheader("Calculation Details")
            st.code(result['audit']['calculation_formula'])
            
            # Show full audit trail
            with st.expander("🔍 View Complete Audit Trail"):
                st.markdown("#### Calculation Metadata")
                st.write(f"**Scope:** {result['metadata']['scope']}")
                st.write(f"**Standard:** {result['metadata']['standard']}")
                st.write(f"**Inventory Year:** {result['metadata']['inventory_year']}")
                
                st.markdown("#### Emission Factor Details")
                st.write(f"**Factor:** {result['audit']['emission_factor']} {result['audit']['emission_factor_unit']}")
                st.write(f"**Source:** {result['audit']['emission_factor_source']}")
                st.write(f"**GWP Reference:** {result['audit']['gwp_reference']}")
                st.write(f"**Methodology:** {result['audit']['methodology_note']}")
                
                st.json(result)
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
        
        # Update session cost IMMEDIATELY
        st.session_state.total_cost += cost['total_cost']
        
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