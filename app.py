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

# ============================================================================
# PAGE CONFIG & CUSTOM STYLING
# ============================================================================

st.set_page_config(
    page_title="ESG Automation System",
    page_icon="🌿",
    layout="wide"
)

# Professional styling
st.markdown("""
    <style>
    /* Global Background */
    .stApp { background-color: #f8fafc; }
    
    /* Sidebar Styling */
    [data-testid="stSidebar"] {
        background-color: #0f172a !important;
    }
    [data-testid="stSidebar"] .css-1d391kg, 
    [data-testid="stSidebar"] p,
    [data-testid="stSidebar"] label {
        color: #94a3b8 !important;
    }
    
    /* Emerald Accents for Metrics */
    [data-testid="stMetricValue"] {
        color: #10b981 !important;
        font-weight: 700 !important;
        font-family: 'SF Mono', 'Monaco', 'Inconsolata', monospace;
    }
    
    /* Custom Card Containers */
    .styled-card {
        background: white;
        padding: 1.5rem;
        border-radius: 1rem;
        border: 1px solid #e2e8f0;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        margin-bottom: 1rem;
    }
    
    /* Button Styling */
    .stButton > button {
        border-radius: 0.5rem;
        font-weight: 500;
    }
    
    /* Tab Styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 2rem;
    }
    .stTabs [data-baseweb="tab"] {
        font-weight: 500;
        color: #64748b;
    }
    .stTabs [aria-selected="true"] {
        color: #10b981;
    }
    
    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    </style>
""", unsafe_allow_html=True)

# Header
st.title("ESG Automation System")
st.caption("Automated compliance reporting with intelligent 3-tier extraction")

# ============================================================================
# SIDEBAR
# ============================================================================

with st.sidebar:
    st.markdown("### ESG Automation")
    st.caption("v1.0 - Production Ready")
    st.markdown("---")
    
    # Session cost tracking
    if 'total_cost' not in st.session_state:
        st.session_state.total_cost = 0.0
    
    # Cost display card
    st.markdown(f"""
        <div style='background:#1e293b; padding:1rem; border-radius:0.75rem; border:1px solid #334155; margin-bottom:1rem;'>
            <span style='color:#94a3b8; font-size:11px; font-weight:600; letter-spacing:0.5px;'>SESSION API COST</span>
            <h2 style='color:#34d399; margin:0.5rem 0 0 0; font-family:monospace;'>${st.session_state.total_cost:.4f}</h2>
        </div>
    """, unsafe_allow_html=True)
    
    if st.button("Reset Session", use_container_width=True):
        st.session_state.total_cost = 0.0
        if 'last_extraction' in st.session_state:
            del st.session_state.last_extraction
        st.rerun()
    
    st.markdown("---")
    
    # System info
    st.markdown("#### System Status")
    st.markdown("""
        <div style='background:#1e293b; padding:0.75rem; border-radius:0.5rem; font-size:0.85rem;'>
            <div style='color:#94a3b8; margin-bottom:0.5rem;'>
                <strong style='color:#10b981;'>●</strong> 3-Tier Extraction Active
            </div>
            <div style='color:#64748b; font-size:0.75rem;'>
                Docling → OCR → Claude Vision
            </div>
        </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Project metrics
    st.markdown("#### Project Metrics")
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Accuracy", "95%")
    with col2:
        st.metric("Savings", "94%")
    
    st.markdown("---")
    
    # Tier info
    st.markdown("#### Extraction Tiers")
    st.markdown("""
        <div style='color:#94a3b8; font-size:0.8rem; line-height:1.6;'>
            <div style='margin-bottom:0.5rem;'>
                <strong style='color:#e2e8f0;'>Tier 1:</strong> Docling (Free)<br/>
                <span style='color:#64748b;'>Text-based PDFs, $0.0001/bill</span>
            </div>
            <div style='margin-bottom:0.5rem;'>
                <strong style='color:#e2e8f0;'>Tier 2:</strong> OCR<br/>
                <span style='color:#64748b;'>Scanned PDFs, $0.001/bill</span>
            </div>
            <div>
                <strong style='color:#e2e8f0;'>Tier 3:</strong> Claude Vision<br/>
                <span style='color:#64748b;'>Complex layouts, $0.02/bill</span>
            </div>
        </div>
    """, unsafe_allow_html=True)

st.sidebar.markdown("---")
st.sidebar.markdown("""
    <div style='text-align:center; color:#64748b; font-size:0.75rem;'>
        Built with Docling + Claude API + Streamlit
    </div>
""", unsafe_allow_html=True)

st.sidebar.markdown("---")
st.sidebar.markdown("**Built with:** Docling + OCR + Claude API")

# ============================================================================
# TABS
# ============================================================================

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "Extract Data", 
    "Calculate Emissions", 
    "Categorize", 
    "ESG Standards", 
    "Operational Insights"
])

# ============================================================================
# TAB 1: EXTRACT DATA
# ============================================================================

with tab1:
    st.header("Extract Utility Bill Data")
    st.caption("3-Tier intelligent extraction: Docling → OCR → Claude Vision")
    
    # ===== SESSION PERSISTENCE =====
    if 'last_extraction' in st.session_state and st.session_state.last_extraction:
        with st.expander("Latest Extraction Results", expanded=False):
            result = st.session_state.last_extraction
            
            st.info(f"Method: {st.session_state.get('extraction_method', 'Unknown')}")
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Usage", f"{result['extraction']['total_kwh']:.0f} kWh")
            with col2:
                st.metric("Cost", f"${result['extraction']['total_cost']:.2f}")
            with col3:
                st.metric("Emissions", f"{result['emissions']['data']['emissions_mtco2e']} MT CO2e")
            
            start = result['extraction'].get('service_start_date', 'N/A')
            end = result['extraction'].get('service_end_date', 'N/A')
            st.caption(f"Period: {start} to {end}")
            st.caption(f"Region: {st.session_state.get('extraction_region', 'Unknown')}")
            
            if st.button("Clear Results"):
                del st.session_state.last_extraction
                if 'extraction_method' in st.session_state:
                    del st.session_state.extraction_method
                st.rerun()
    
    # ===== INPUT METHOD SELECTOR =====
    upload_method = st.radio(
        "Choose input method:",
        ["Upload PDF", "Paste Text"],
        horizontal=True
    )
    
    # ===== PDF UPLOAD MODE =====
    if upload_method == "Upload PDF":
        st.info("**3-Tier Extraction:** Docling (free) → OCR ($0.001) → Claude Vision ($0.02)")
        
        uploaded_files = st.file_uploader(
            "Upload utility bill PDF(s):",
            type=['pdf'],
            accept_multiple_files=True,
            help="Upload multiple bills for batch processing"
        )
        
        region = st.selectbox(
            "Region (for emissions calculation):",
            ["US_AVERAGE", "ARKANSAS", "CALIFORNIA", "TEXAS", "NEW_YORK", "FLORIDA"],
            index=1,
            key="pdf_region"
        )
        
        # Determine if batch mode
        is_batch = uploaded_files and len(uploaded_files) > 1
        
        if is_batch:
            st.success(f"**Batch Mode:** {len(uploaded_files)} bills uploaded")
        
        if uploaded_files and st.button(
            f"Process {'All Bills' if is_batch else 'PDF'}", 
            type="primary"
        ):
            from src.extract import extract_from_pdf_hybrid
            from src.calculate import calculate_electricity_emissions
            
            if is_batch:
                # ===== BATCH PROCESSING MODE =====
                st.markdown("---")
                st.subheader("Batch Processing Results")
                
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                results = []
                tier_counts = {"Tier 1 (Docling)": 0, "Tier 2 (OCR)": 0, "Tier 3 (Claude Vision)": 0}
                total_cost = 0
                
                for idx, uploaded_file in enumerate(uploaded_files):
                    status_text.text(f"Processing {idx + 1}/{len(uploaded_files)}: {uploaded_file.name}")
                    
                    # Extract from PDF
                    extracted = extract_from_pdf_hybrid(uploaded_file, confidence_threshold=0.70)
                    
                    if extracted:
                        # Calculate emissions
                        start = extracted.get("service_start_date", "Unknown")
                        end = extracted.get("service_end_date", "Unknown")
                        reporting_period = f"{start} to {end}"
                        
                        emissions_result = calculate_electricity_emissions(
                            kwh=extracted.get("total_kwh", 0),
                            region=region,
                            reporting_period=reporting_period
                        )
                        
                        result = {
                            "success": True,
                            "filename": uploaded_file.name,
                            "extraction": extracted,
                            "emissions": emissions_result,
                            "cost": extracted.get("extraction_cost", 0)
                        }
                        
                        # Track tier usage
                        method = extracted.get("extraction_method", "")
                        if "Docling" in method:
                            tier_counts["Tier 1 (Docling)"] += 1
                        elif "OCR" in method:
                            tier_counts["Tier 2 (OCR)"] += 1
                        elif "Claude" in method or "Vision" in method:
                            tier_counts["Tier 3 (Claude Vision)"] += 1
                        
                        total_cost += result['cost']
                        results.append(result)
                    else:
                        results.append({
                            "success": False,
                            "filename": uploaded_file.name,
                            "error": "Extraction failed"
                        })
                    
                    progress_bar.progress((idx + 1) / len(uploaded_files))
                
                status_text.empty()
                progress_bar.empty()
                
                # Update session cost
                st.session_state.total_cost += total_cost
                
                # ===== DISPLAY BATCH RESULTS =====
                st.success(f"Processed {len([r for r in results if r['success']])} of {len(uploaded_files)} bills")
                
                # Tier breakdown
                st.markdown("### 3-Tier Cost Optimization")
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Tier 1 (Docling)", f"{tier_counts['Tier 1 (Docling)']} bills", "~$0.0001 each")
                with col2:
                    st.metric("Tier 2 (OCR)", f"{tier_counts['Tier 2 (OCR)']} bills", "~$0.001 each")
                with col3:
                    st.metric("Tier 3 (Claude)", f"{tier_counts['Tier 3 (Claude Vision)']} bills", "~$0.02 each")
                
                # Cost comparison
                claude_only_cost = len(uploaded_files) * 0.02
                savings = claude_only_cost - total_cost
                savings_pct = (savings / claude_only_cost * 100) if claude_only_cost > 0 else 0
                
                st.markdown("### Cost Analysis")
                col4, col5, col6 = st.columns(3)
                with col4:
                    st.metric("Actual Cost", f"${total_cost:.4f}")
                with col5:
                    st.metric("Claude-Only Cost", f"${claude_only_cost:.4f}")
                with col6:
                    st.metric("Savings", f"${savings:.4f}", f"{savings_pct:.1f}%")
                
                # Aggregate emissions
                successful_results = [r for r in results if r['success']]
                if successful_results:
                    st.markdown("### Aggregate Emissions")
                    
                    total_kwh = sum(r['extraction']['total_kwh'] for r in successful_results)
                    total_emissions = sum(r['emissions']['data']['emissions_mtco2e'] for r in successful_results)
                    total_bill_cost = sum(r['extraction'].get('total_cost', 0) for r in successful_results if r['extraction'].get('total_cost'))
                    
                    col7, col8, col9 = st.columns(3)
                    with col7:
                        st.metric("Total Usage", f"{total_kwh:,.0f} kWh")
                    with col8:
                        st.metric("Total Emissions", f"{total_emissions:.4f} MT CO2e")
                    with col9:
                        st.metric("Total Cost", f"${total_bill_cost:,.2f}")
                
                # Individual results table
                with st.expander("Individual Bill Results", expanded=False):
                    for result in results:
                        if result['success']:
                            st.markdown(f"**{result['filename']}**")
                            col_a, col_b, col_c, col_d = st.columns(4)
                            with col_a:
                                st.caption(f"Usage: {result['extraction']['total_kwh']:.0f} kWh")
                            with col_b:
                                st.caption(f"Emissions: {result['emissions']['data']['emissions_mtco2e']} MT")
                            with col_c:
                                st.caption(f"Method: {result['extraction'].get('extraction_method', 'N/A')}")
                            with col_d:
                                st.caption(f"Cost: ${result['cost']:.4f}")
                            st.markdown("---")
                        else:
                            st.error(f" {result['filename']}: {result.get('error', 'Unknown error')}")
            
            else:
                # ===== SINGLE FILE MODE (original code) =====
                uploaded_file = uploaded_files[0]
                
                with st.spinner("Processing PDF with 3-tier extraction..."):
                    # Hybrid extraction (Docling → OCR → Claude fallback)
                    extracted = extract_from_pdf_hybrid(uploaded_file, confidence_threshold=0.70)
                
                if extracted:
                    # Calculate emissions
                    start = extracted.get("service_start_date", "Unknown")
                    end = extracted.get("service_end_date", "Unknown")
                    reporting_period = f"{start} to {end}"
                    
                    emissions_result = calculate_electricity_emissions(
                        kwh=extracted.get("total_kwh", 0),
                        region=region,
                        reporting_period=reporting_period
                    )
                    
                    result = {
                        "success": True,
                        "warnings": [],
                        "extraction": extracted,
                        "emissions": emissions_result,
                        "combined_cost": extracted.get("extraction_cost", 0)
                    }
                else:
                    result = {
                        "success": False,
                        "error": "PDF extraction failed with both methods"
                    }
                
                # DISPLAY RESULTS
                if result["success"]:
                    # Store in session
                    st.session_state.total_cost += result['combined_cost']
                    st.session_state.kwh = result['extraction']['total_kwh']
                    st.session_state.last_extraction = result
                    st.session_state.extraction_method = result['extraction'].get('extraction_method', 'Unknown')
                    st.session_state.extraction_region = region
                    
                    st.success("Extraction successful!")
                    
                    # Show method with cost
                    method = result['extraction'].get('extraction_method', 'Unknown')
                    cost = result['combined_cost']
                    
                    if "Docling" in method:
                        st.info(f"**Cost Savings:** Extracted locally with Docling (~$0.0001)")
                        st.caption(f"{method}")
                    elif "Claude" in method:
                        st.info(f"Extracted with Claude API (~${cost:.4f})")
                        st.caption(f"{method}")
                    
                    # Warnings
                    if result["warnings"]:
                        for warning in result["warnings"]:
                            st.warning(warning)
                    
                    # Extracted data
                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric("Usage", f"{result['extraction']['total_kwh']:.0f} kWh")
                        st.caption(result['extraction'].get('unit_conversion_applied', 'No conversion'))
                    with col2:
                        st.metric("Cost", f"${result['extraction']['total_cost']:.2f}")
                        st.caption(f"Rate: ${result['extraction'].get('calculated_rate_per_kwh', 0):.3f}/kWh")
                    
                    # Emissions
                    st.subheader("Calculated Emissions")
                    col3, col4 = st.columns(2)
                    with col3:
                        st.metric("CO2 Emissions", f"{result['emissions']['data']['emissions_kg_co2e']} kg")
                    with col4:
                        st.metric("Metric Tons CO2e", f"{result['emissions']['data']['emissions_mtco2e']}")
                    
                    # Audit Trail
                    with st.expander("View Audit Trail & Verification"):
                        st.markdown("#### Extraction Details")
                        st.write(f"**Timestamp:** {result['extraction'].get('extraction_timestamp', 'N/A')}")
                        st.write(f"**Method:** {result['extraction'].get('extraction_method', 'N/A')}")
                        st.write(f"**Validation:** {'Passed' if result['extraction'].get('validation_passed') else 'Warnings'}")
                        
                        st.markdown("#### Emissions Calculation")
                        audit = result['emissions']['audit']
                        st.write(f"**Formula:** `{audit['calculation_formula']}`")
                        st.write(f"**Emission Factor:** {audit['emission_factor']} {audit['emission_factor_unit']}")
                        st.write(f"**Source:** {audit['emission_factor_source']}")
                        
                        st.markdown("#### Cost Tracking")
                        st.write(f"**API Cost:** ${result['combined_cost']:.4f}")
                        if "Docling" in method:
                            st.caption("Docling processed locally - essentially free!")
                    
                    with st.expander("View Full JSON (Debug)"):
                        st.json(result)
                else:
                    st.error(f" {result['error']}")
    
    # ===== TEXT PASTE MODE =====
    else:
        col1, col2 = st.columns([3, 1])
        with col2:
            if st.button("Try Demo Bill", help="Load example SWEPCO bill"):
                st.session_state.demo_bill_text = DEMO_BILL_TEXT
        
        default_value = st.session_state.get('demo_bill_text', "")
        
        bill_text = st.text_area(
            "Paste utility bill text:",
            value=default_value,
            height=300,
            placeholder="Paste your utility bill text here..."
        )
        
        if default_value and default_value == DEMO_BILL_TEXT:
            st.success("Demo bill loaded! Click 'Extract & Calculate' below.")
        
        region = st.selectbox(
            "Region (for emissions calculation):",
            ["US_AVERAGE", "ARKANSAS", "CALIFORNIA", "TEXAS", "NEW_YORK", "FLORIDA"],
            index=1,
            key="text_region"
        )
        
        has_bill_text = bill_text and len(bill_text.strip()) > 0
        
        if st.button("Extract & Calculate", type="primary", disabled=not has_bill_text):
            if bill_text:
                with st.spinner("Processing bill..."):
                    result = extract_and_calculate_emissions(bill_text=bill_text, region=region)
                    
                    if result["success"]:
                        # Store in session
                        st.session_state.total_cost += result['combined_cost']
                        st.session_state.kwh = result['extraction']['total_kwh']
                        st.session_state.last_extraction = result
                        st.session_state.extraction_method = result['extraction'].get('extraction_method', 'Text extraction')
                        st.session_state.extraction_region = region
                        
                        st.success("Extraction successful!")
                        
                        # Warnings
                        if result["warnings"]:
                            for warning in result["warnings"]:
                                st.warning(warning)
                        
                        # Extracted data
                        col1, col2 = st.columns(2)
                        with col1:
                            st.metric("Usage", f"{result['extraction']['total_kwh']:.0f} kWh")
                            st.caption(result['extraction'].get('unit_conversion_applied', 'No conversion'))
                        with col2:
                            st.metric("Cost", f"${result['extraction']['total_cost']:.2f}")
                            st.caption(f"Rate: ${result['extraction'].get('calculated_rate_per_kwh', 0):.3f}/kWh")
                        
                        # Emissions
                        st.subheader("Calculated Emissions")
                        col3, col4 = st.columns(2)
                        with col3:
                            st.metric("CO2 Emissions", f"{result['emissions']['data']['emissions_kg_co2e']} kg")
                        with col4:
                            st.metric("Metric Tons CO2e", f"{result['emissions']['data']['emissions_mtco2e']}")
                        
                        # Audit Trail
                        with st.expander("View Audit Trail & Verification"):
                            st.markdown("#### Extraction Details")
                            st.write(f"**Timestamp:** {result['extraction'].get('extraction_timestamp', 'N/A')}")
                            st.write(f"**Method:** {result['extraction'].get('extraction_method', 'N/A')}")
                            
                            st.markdown("#### Emissions Calculation")
                            audit = result['emissions']['audit']
                            st.write(f"**Formula:** `{audit['calculation_formula']}`")
                            st.write(f"**Emission Factor:** {audit['emission_factor']} {audit['emission_factor_unit']}")
                            
                            st.markdown("#### Cost Tracking")
                            st.write(f"**API Cost:** ${result['combined_cost']:.4f}")
                        
                        with st.expander("View Full JSON (Debug)"):
                            st.json(result)
                    else:
                        st.error(f" {result['error']}")

# ============================================================================
# TAB 2: CALCULATE EMISSIONS
# ============================================================================

with tab2:
    st.header("Calculate Emissions")
    
    kwh = st.number_input(
        "kWh Usage:",
        min_value=0.0,
        value=float(st.session_state.get('kwh', 0)),
        step=10.0
    )
    
    default_region = st.session_state.get('extraction_region', 'US_AVERAGE')
    region_options = ["US_AVERAGE", "ARKANSAS", "CALIFORNIA", "TEXAS", "NEW_YORK", "FLORIDA"]
    
    try:
        default_index = region_options.index(default_region)
    except ValueError:
        default_index = 0
    
    region = st.selectbox("Region:", region_options, index=default_index)
    
    # Show indicator if auto-selected
    if default_region and default_region != "US_AVERAGE":
        st.caption(f"ℹ️ Using region from last extraction: {default_region}")
    
    if st.button("Calculate Emissions", type="primary"):
        if kwh > 0:
            result = calculate_electricity_emissions(kwh, region)
            
            st.success("Emissions calculated!")
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric("CO2 Emissions", f"{result['data']['emissions_kg_co2e']} kg")
            with col2:
                st.metric("Metric Tons CO2e", f"{result['data']['emissions_mtco2e']} MT")
            
            st.subheader("Calculation Details")
            st.code(result['audit']['calculation_formula'])
            
            with st.expander("View Complete Audit Trail"):
                st.json(result)
        else:
            st.warning("Enter kWh value first")

# ============================================================================
# TAB 3: CATEGORIZE
# ============================================================================

with tab3:
    st.header("Categorize Activity")
    
    activity = st.text_input(
        "Activity description:",
        placeholder="e.g., Purchased electricity from grid"
    )
    
    if st.button("Categorize", type="primary"):
        if activity:
            with st.spinner("Categorizing..."):
                result = categorize_to_scope(activity)
                st.session_state.total_cost += result.get('categorization_cost', 0)
                
                scope_color = {
                    "Scope 1": "●",
                    "Scope 2": "●",
                    "Scope 3": "●",
                    "Unknown": "⚪"
                }
                
                st.success(f"{scope_color.get(result['scope'], '⚪')} **{result['scope']}**")
                st.info(result['reasoning'])
                st.caption(f"API Cost: ${result.get('categorization_cost', 0):.4f}")
        else:
            st.warning("Enter activity description first")

# ============================================================================
# TAB 4: ESG STANDARDS
# ============================================================================

with tab4:
    st.header("Query ESG Standards")
    st.markdown("Ask questions about GRI and SASB standards.")
    
    question = st.text_input(
        "Ask about ESG standards:",
        placeholder="e.g., What are Scope 2 emissions?"
    )
    
    if st.button("Search Standards", type="primary"):
        if question:
            with st.spinner("Searching ESG standards..."):
                from src.rag import ESGStandardsRAG
                
                rag = ESGStandardsRAG()
                result = rag.query(question)
                
                st.session_state.total_cost += 0.02
                
                st.success("Answer from ESG Standards:")
                st.markdown(result['answer'])
                
                with st.expander("Sources"):
                    for source in set(result['sources']):
                        st.caption(f"• {source}")
        else:
            st.warning("Please enter a question first")

# ============================================================================
# TAB 5: OPERATIONAL INSIGHTS
# ============================================================================

with tab5:
    st.header("Operational Insights")
    
    monthly_data = {
        "November": {"kwh": 920, "cost": 138.50, "co2_kg": 673},
        "December": {"kwh": 850, "cost": 127.50, "co2_kg": 622}
    }
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        kwh_change = ((850 - 920) / 920) * 100
        st.metric("kWh Usage", "850 kWh", f"{kwh_change:.1f}% vs last month", delta_color="inverse")
    
    with col2:
        cost_change = ((127.50 - 138.50) / 138.50) * 100
        st.metric("Cost", "$127.50", f"{cost_change:.1f}% vs last month", delta_color="inverse")
    
    with col3:
        co2_change = ((622 - 673) / 673) * 100
        st.metric("CO2 Emissions", "622 kg", f"{co2_change:.1f}% vs last month", delta_color="inverse")
    
    st.subheader("Cost-Saving Opportunities")
    
    if st.button("Generate Insights"):
        prompt = """Analyze this energy usage data and provide 3 specific cost-saving recommendations:

Current Month: 850 kWh, $127.50, 622 kg CO2
Previous Month: 920 kWh, $138.50, 673 kg CO2
Region: Arkansas

Format as bullet points, each with recommendation, estimated savings, and implementation difficulty."""

        from src.utils import call_claude_with_cost
        insights, cost = call_claude_with_cost(prompt)
        
        st.session_state.total_cost += cost['total_cost']
        
        st.markdown(insights)
        st.caption(f"Analysis cost: ${cost['total_cost']:.4f}")

# ============================================================================
# FOOTER
# ============================================================================

st.markdown("---")
col1, col2, col3 = st.columns(3)
with col1:
    st.markdown("Built with Docling + Claude API + Streamlit")
with col2:
    st.markdown("[GitHub](https://github.com/yourusername/esg-automation)")
with col3:
    st.markdown("v1.0 - Hybrid PDF Extraction")