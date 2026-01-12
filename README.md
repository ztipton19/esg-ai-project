# ESG Automation System

**Automate ESG compliance reporting with AI - 3-tier extraction strategy for 94% cost savings**

[![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?style=for-the-badge&logo=Streamlit&logoColor=white)](https://streamlit.io)
[![Claude](https://img.shields.io/badge/Claude-000000?style=for-the-badge&logo=anthropic&logoColor=white)](https://www.anthropic.com)

## 🌍 Overview

An intelligent ESG (Environmental, Social, Governance) compliance system that extracts data from utility bills, calculates emissions, and generates GRI-compliant reports. Built with a production-grade 3-tier extraction strategy that saves 94% on costs compared to AI-only approaches.

### Key Features

- **📄 3-Tier PDF Extraction** - Docling → Tesseract OCR → Claude Vision API
- **⚡ Cost Optimization** - ~$0.50-1.00/month vs $10-20/month for 1,000 bills (95%+ savings)
- **📊 Emissions Calculator** - EPA eGRID emission factors by region
- **📋 GRI Report Generator** - Automated GRI 305-2 compliant reports
- **🔍 Full Audit Trail** - Complete validation and verification
- **💰 Real-time Cost Tracking** - Track API costs per session

## 🚀 Quick Start

### Prerequisites

- Python 3.9+
- Anthropic API key ([get one here](https://console.anthropic.com/))
- Tesseract OCR (for local installations)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/esg-ai-project.git
   cd esg-ai-project
   ```

2. **Install Python dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Install Tesseract OCR** (for Tier 2 extraction)

   **Windows:**
   - Download installer from [UB-Mannheim/tesseract](https://github.com/UB-Mannheim/tesseract/wiki)
   - Install to default location: `C:\Program Files\Tesseract-OCR`
   - Add to PATH or the app will auto-detect it

   **Linux/Mac:**
   ```bash
   # Ubuntu/Debian
   sudo apt-get install tesseract-ocr poppler-utils

   # macOS
   brew install tesseract poppler
   ```

4. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env and add your ANTHROPIC_API_KEY
   ```

5. **Run the app**
   ```bash
   streamlit run app.py
   ```

## 💡 How It Works

### 3-Tier Extraction Strategy

```
┌─────────────────────────────────────────────┐
│  TIER 1: Docling (Text-based PDFs)         │
│  Cost: $0 (local) | Success: 85%           │
│  ↓ If confidence < 70%                      │
├─────────────────────────────────────────────┤
│  TIER 2: Tesseract OCR (Scanned PDFs)      │
│  Cost: $0 (local) | Success: 10%           │
│  ↓ If confidence < 70%                      │
├─────────────────────────────────────────────┤
│  TIER 3: Claude Vision API (Complex)       │
│  Cost: ~$0.01-0.02/bill | Success: 5%      │
└─────────────────────────────────────────────┘
```

### Cost Comparison

| Approach | Cost/1000 Bills | Annual Cost |
|----------|----------------|-------------|
| **3-Tier (Ours)** | ~$0.50-1.00/month | ~$6-12/year |
| Claude-only | $10-20/month | $120-240/year |
| **Savings** | **95%+** | **$114-228/year** |

## 📊 Usage

### 1. Extract Utility Bill Data

**Option A: Upload PDF**
- Drag and drop a PDF utility bill
- Select your region for emissions calculation
- Click "Extract from PDF"

**Option B: Paste Text**
- Copy text from a utility bill
- Paste into the text area
- Click "Extract & Calculate"

### 2. Calculate Emissions

Automatically calculates:
- CO2 emissions (kg and metric tons)
- Uses EPA eGRID emission factors by region
- Provides complete audit trail

### 3. Generate GRI Report

Click "Generate GRI 305-2 Report" to create:
- Professional compliance disclosure
- Year-over-year comparisons
- Calculation methodology
- Data quality notes
- Downloadable report file

## 🏗️ Architecture

```
esg-ai-project/
├── app.py                      # Main Streamlit interface
├── src/
│   ├── extract.py              # 3-tier extraction engine
│   ├── calculate.py            # Emissions calculations
│   ├── reports.py              # GRI report generation
│   ├── validation.py           # Data validation
│   ├── categorize.py           # Scope categorization
│   ├── rag.py                  # ESG standards RAG
│   └── utils.py                # Utilities & API calls
├── data/
│   └── test_bills/             # Sample bills
├── requirements.txt            # Python dependencies
├── packages.txt                # System dependencies
└── .streamlit/
    └── config.toml             # Streamlit config
```

## 🔧 Configuration

### Environment Variables

Create a `.env` file:

```env
ANTHROPIC_API_KEY=your_api_key_here
```

### Streamlit Secrets (for deployment)

For Streamlit Cloud, add to secrets:

```toml
ANTHROPIC_API_KEY = "your_api_key_here"
```

## 📈 Features in Detail

### Supported Utility Types
- ✅ Electricity bills (kWh, MWh)
- ✅ Text-based PDFs
- ✅ Scanned/image PDFs
- ✅ Auto-converts units

### Emission Factor Sources
- EPA eGRID 2024
- Regional factors for:
  - US Average
  - Arkansas
  - California
  - Texas
  - New York
  - Florida

### Validation & Quality
- ✅ Pre-call data validation
- ✅ Post-call accuracy verification
- ✅ Hallucination detection
- ✅ Completeness checks
- ✅ Rate sanity checks

## 🚢 Deployment

### Streamlit Cloud

1. Push to GitHub
2. Connect to [Streamlit Cloud](https://streamlit.io/cloud)
3. Add `ANTHROPIC_API_KEY` to secrets
4. Deploy!

The `packages.txt` file ensures Tesseract is installed automatically.

### Docker

```dockerfile
FROM python:3.9-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy app
COPY . /app
WORKDIR /app

EXPOSE 8501

CMD ["streamlit", "run", "app.py"]
```

## 📊 Performance

- **Extraction Speed**: 2-3s (Docling), 3-5s (OCR), 2-4s (Claude)
- **Accuracy**: 85-90% (Docling), 70-85% (OCR), 95%+ (Claude)
- **Cost per Complete Workflow**: ~$0.006-0.011 (extraction + report)

## 🤝 Contributing

Contributions welcome! Please feel free to submit a Pull Request.

## 📄 License

MIT License - See LICENSE file for details

## 🙏 Acknowledgments

- [Docling](https://github.com/DS4SD/docling) - IBM's document AI
- [Anthropic Claude](https://www.anthropic.com) - AI extraction & report generation
- [EPA eGRID](https://www.epa.gov/egrid) - Emission factors
- [GRI Standards](https://www.globalreporting.org/) - Reporting framework

## 📞 Support

For issues or questions, please open a GitHub issue.

---

**Built with Docling + Claude API + Streamlit** | v1.0 - 3-Tier Extraction
