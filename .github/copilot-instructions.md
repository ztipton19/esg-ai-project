# Copilot Instructions for ESG Automation System

## Overview
This project automates ESG compliance reporting using a three-tier extraction strategy, leveraging AI for data extraction and emissions calculation. The architecture consists of several components that interact to provide a seamless user experience.

## Architecture
- **Main Components**: The core components include `app.py` for the Streamlit interface, `src/` for utility functions and data processing, and `tests/` for unit testing.
- **Data Flow**: Data is extracted from utility bills (PDFs or text), processed to calculate emissions, and then formatted into compliance reports. The flow is as follows:
  1. **Data Extraction**: Handled in `src/extract.py` using AI models (e.g., Claude API).
  2. **Emissions Calculation**: Performed in `src/calculate.py` using EPA factors.
  3. **Report Generation**: Managed in `src/reports.py`, which formats the data into GRI-compliant reports.

## Developer Workflows
- **Running the Application**: Use `streamlit run app.py` to start the application. Ensure all dependencies are installed via `pip install -r requirements.txt`.
- **Testing**: Run tests located in the `tests/` directory using `pytest`. Ensure to check for coverage reports in `.coverage` files.
- **Debugging**: Utilize print statements or logging within the `src/` files to trace data flow and identify issues.

## Project-Specific Conventions
- **File Naming**: Use snake_case for Python files and functions (e.g., `calculate_emissions.py`).
- **Documentation**: Each function should have a docstring explaining its purpose, parameters, and return values.
- **Error Handling**: Implement try-except blocks around API calls to handle potential failures gracefully.

## Integration Points
- **External Dependencies**: The project relies on several libraries, including `streamlit`, `anthropic`, and `docling`. Ensure these are included in `requirements.txt`.
- **Cross-Component Communication**: Data is passed between components using function calls. For example, `app.py` calls functions from `src/` to process data and generate reports.

## Examples
- **Extracting Data**: Use the `extract_from_pdf_with_ai` function in `src/utils.py` to extract data from PDFs. Ensure to handle the output correctly to avoid common mistakes.
- **Calculating Emissions**: The `calculate_electricity_emissions` function in `src/calculate.py` takes kWh and region as inputs to return emissions data.

## Conclusion
This document serves as a guide for AI agents to understand the structure and workflows of the ESG Automation System. For further details, refer to the README.md and individual module documentation.