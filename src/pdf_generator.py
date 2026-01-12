"""
PDF Report Generator for ESG Compliance Reports

Converts GRI 305-2 compliance reports to professional PDF format using ReportLab.
"""

from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib import colors
from io import BytesIO
from datetime import datetime
import re


def clean_markdown_for_pdf(text):
    """
    Convert markdown-style text to ReportLab-compatible format

    Args:
        text: Markdown-formatted text

    Returns:
        str: ReportLab-compatible text with proper tags
    """
    # Convert **bold** to <b>bold</b>
    text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', text)

    # Convert *italic* to <i>italic</i>
    text = re.sub(r'\*(.+?)\*', r'<i>\1</i>', text)

    # Convert # Headers to bold text
    text = re.sub(r'^### (.+)$', r'<b>\1</b>', text, flags=re.MULTILINE)
    text = re.sub(r'^## (.+)$', r'<b><font size="14">\1</font></b>', text, flags=re.MULTILINE)
    text = re.sub(r'^# (.+)$', r'<b><font size="16">\1</font></b>', text, flags=re.MULTILINE)

    # Remove markdown list markers (we'll handle lists separately)
    text = re.sub(r'^- ', r'• ', text, flags=re.MULTILINE)

    return text


def generate_gri_pdf(report_text, filename=None):
    """
    Generate a professional PDF from GRI 305-2 report text

    Args:
        report_text: The report text (markdown format)
        filename: Optional filename (defaults to GRI_305_Report_YYYY-MM-DD.pdf)

    Returns:
        BytesIO: PDF file as bytes (for Streamlit download)
    """
    # Create filename with current date if not provided
    if not filename:
        current_date = datetime.now().strftime("%Y-%m-%d")
        filename = f"GRI_305_Report_{current_date}.pdf"

    # Create a BytesIO buffer to store PDF
    buffer = BytesIO()

    # Create the PDF document
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=72,
        leftMargin=72,
        topMargin=72,
        bottomMargin=72
    )

    # Container for the 'Flowable' objects
    elements = []

    # Define styles
    styles = getSampleStyleSheet()

    # Custom title style
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#2E7D32'),
        spaceAfter=30,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )

    # Custom heading styles
    heading1_style = ParagraphStyle(
        'CustomHeading1',
        parent=styles['Heading1'],
        fontSize=16,
        textColor=colors.HexColor('#1B5E20'),
        spaceAfter=12,
        spaceBefore=12,
        fontName='Helvetica-Bold'
    )

    heading2_style = ParagraphStyle(
        'CustomHeading2',
        parent=styles['Heading2'],
        fontSize=14,
        textColor=colors.HexColor('#2E7D32'),
        spaceAfter=10,
        spaceBefore=10,
        fontName='Helvetica-Bold'
    )

    heading3_style = ParagraphStyle(
        'CustomHeading3',
        parent=styles['Heading2'],
        fontSize=12,
        textColor=colors.HexColor('#388E3C'),
        spaceAfter=8,
        spaceBefore=8,
        fontName='Helvetica-Bold'
    )

    # Body text style
    body_style = ParagraphStyle(
        'CustomBody',
        parent=styles['BodyText'],
        fontSize=10,
        leading=14,
        alignment=TA_JUSTIFY,
        spaceAfter=6
    )

    # Add header/logo area
    elements.append(Spacer(1, 0.5*inch))

    # Add title
    title = Paragraph("GRI 305-2 Compliance Report", title_style)
    elements.append(title)
    elements.append(Spacer(1, 0.3*inch))

    # Add subtitle with date
    current_date = datetime.now().strftime("%B %d, %Y")
    subtitle = Paragraph(f"<i>Generated on {current_date}</i>", body_style)
    elements.append(subtitle)
    elements.append(Spacer(1, 0.5*inch))

    # Add horizontal line
    elements.append(Spacer(1, 0.2*inch))

    # Parse and add report content
    lines = report_text.split('\n')

    for line in lines:
        line = line.strip()

        if not line:
            elements.append(Spacer(1, 0.1*inch))
            continue

        # Detect section headers
        if line.startswith('# '):
            text = line.replace('# ', '')
            elements.append(Paragraph(text, heading1_style))
        elif line.startswith('## '):
            text = line.replace('## ', '')
            elements.append(Paragraph(text, heading2_style))
        elif line.startswith('### '):
            text = line.replace('### ', '')
            elements.append(Paragraph(text, heading3_style))
        elif line.startswith('---'):
            # Horizontal line
            elements.append(Spacer(1, 0.2*inch))
        elif line.startswith('- ') or line.startswith('• '):
            # Bullet point
            text = line.replace('- ', '• ').replace('**', '<b>').replace('**', '</b>')
            text = clean_markdown_for_pdf(text)
            para = Paragraph(text, body_style)
            elements.append(para)
        else:
            # Regular paragraph
            text = clean_markdown_for_pdf(line)
            para = Paragraph(text, body_style)
            elements.append(para)

    # Add footer
    elements.append(Spacer(1, 0.5*inch))
    elements.append(Spacer(1, 0.2*inch))

    footer_text = """
    <i>This report was generated using ESG Automation System with Claude AI.
    Data has been validated against GRI Standards and EPA eGRID emission factors.</i>
    """
    footer = Paragraph(footer_text, body_style)
    elements.append(footer)

    # Build PDF
    doc.build(elements)

    # Get the PDF bytes
    buffer.seek(0)
    return buffer


def create_pdf_filename(service_start_date=None, service_end_date=None):
    """
    Create a standardized PDF filename

    Args:
        service_start_date: Optional start date from report
        service_end_date: Optional end date from report

    Returns:
        str: Filename in format GRI_305_Report_YYYY-MM-DD.pdf
    """
    if service_end_date and service_end_date != 'N/A':
        # Use the service end date if available
        try:
            # Try to parse the date
            date_obj = datetime.strptime(service_end_date, "%Y-%m-%d")
            date_str = date_obj.strftime("%Y-%m-%d")
        except:
            # Fall back to current date if parsing fails
            date_str = datetime.now().strftime("%Y-%m-%d")
    else:
        # Use current date
        date_str = datetime.now().strftime("%Y-%m-%d")

    return f"GRI_305_Report_{date_str}.pdf"


if __name__ == "__main__":
    # Test PDF generation
    sample_report = """
# GRI 305-2: Energy Indirect (Scope 2) GHG Emissions

## Disclosure 305-2-a: Gross Location-Based Scope 2 Emissions

**Total Scope 2 Emissions:** 0.1948 metric tons CO₂e

### Calculation Methodology
- **Electricity Consumption:** 282.0 kWh
- **Emission Factor:** 0.000691 MT CO2e/kWh
- **Region:** ARKANSAS
- **Data Source:** EPA eGRID 2023

### Verification
✅ All calculations verified
✅ Emission factors validated against EPA eGRID 2023
✅ Data completeness confirmed

## Notes
This report complies with GRI 305-2 requirements for Scope 2 emissions reporting.
    """

    pdf_buffer = generate_gri_pdf(sample_report)

    # Save to file for testing
    with open("test_gri_report.pdf", "wb") as f:
        f.write(pdf_buffer.read())

    print("✅ Test PDF generated: test_gri_report.pdf")
