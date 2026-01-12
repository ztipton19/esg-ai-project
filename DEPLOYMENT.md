# Deployment Guide

## 🚀 Streamlit Cloud Deployment (Recommended)

### Prerequisites
- GitHub account
- Anthropic API key
- Your repository pushed to GitHub

### Steps

1. **Push to GitHub**
   ```bash
   git add .
   git commit -m "Prepare for deployment"
   git push origin main
   ```

2. **Go to Streamlit Cloud**
   - Visit [share.streamlit.io](https://share.streamlit.io)
   - Sign in with GitHub
   - Click "New app"

3. **Configure App**
   - Repository: `yourusername/esg-ai-project`
   - Branch: `main`
   - Main file path: `app.py`

4. **Add Secrets**
   - Click "Advanced settings"
   - Go to "Secrets" tab
   - Add:
     ```toml
     ANTHROPIC_API_KEY = "sk-ant-api03-your-actual-key"
     ```

5. **Deploy!**
   - Click "Deploy"
   - Wait 2-3 minutes for deployment
   - Your app will be live at: `https://your-app-name.streamlit.app`

### What Happens During Deployment

1. Streamlit installs Python packages from `requirements.txt`
2. System packages (Tesseract, Poppler) are installed from `packages.txt`
3. App starts automatically
4. OCR (Tier 2) works out of the box!

---

## 🐳 Docker Deployment

### Dockerfile

Already included in the repository. To build and run:

```bash
# Build the image
docker build -t esg-automation .

# Run the container
docker run -p 8501:8501 \
  -e ANTHROPIC_API_KEY=your-key-here \
  esg-automation
```

Access at: `http://localhost:8501`

### Docker Compose

Create `docker-compose.yml`:

```yaml
version: '3.8'

services:
  app:
    build: .
    ports:
      - "8501:8501"
    environment:
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
    volumes:
      - ./data:/app/data
```

Run with:
```bash
docker-compose up
```

---

## 🖥️ Local Development

### Setup

1. **Clone & Install**
   ```bash
   git clone https://github.com/yourusername/esg-ai-project.git
   cd esg-ai-project
   pip install -r requirements.txt
   ```

2. **Install Tesseract**
   - **Windows**: [Download installer](https://github.com/UB-Mannheim/tesseract/wiki)
   - **Ubuntu**: `sudo apt-get install tesseract-ocr poppler-utils`
   - **Mac**: `brew install tesseract poppler`

3. **Configure Environment**
   ```bash
   cp .env.example .env
   # Edit .env and add your ANTHROPIC_API_KEY
   ```

4. **Run**
   ```bash
   streamlit run app.py
   ```

---

## 🔐 Security Checklist

Before deploying, ensure:

- [ ] `.env` is in `.gitignore` (✅ Already done)
- [ ] `.streamlit/secrets.toml` is in `.gitignore` (✅ Already done)
- [ ] API keys are not hardcoded in any files
- [ ] Secrets are added via Streamlit Cloud secrets manager
- [ ] Repository is private if handling sensitive data

---

## 📊 Cost Monitoring

After deployment, monitor costs:

1. **Streamlit App**
   - Check "Session Costs" in sidebar
   - Resets when you refresh the page

2. **Anthropic Console**
   - Visit [console.anthropic.com](https://console.anthropic.com)
   - Go to "Usage"
   - Monitor monthly spending

### Expected Costs

For 1,000 bills/month:
- **3-Tier System (Extraction Only)**: ~$0.50-1.00/month (only pays for ~5% using Claude API)
- **With Reports**: ~$6-11/month (includes GRI report generation)
- **Claude Only**: ~$10-20/month (all bills use expensive API)

---

## 🐛 Troubleshooting

### Tesseract Not Found (Streamlit Cloud)

**Problem**: `tesseract: command not found`

**Solution**: Ensure `packages.txt` contains:
```
tesseract-ocr
tesseract-ocr-eng
poppler-utils
```

### Import Errors

**Problem**: `ModuleNotFoundError: No module named 'X'`

**Solution**:
1. Check `requirements.txt` includes the module
2. Redeploy on Streamlit Cloud
3. Locally: `pip install -r requirements.txt`

### API Key Not Working

**Problem**: `ValueError: ANTHROPIC_API_KEY not found`

**Solution**:
- **Streamlit Cloud**: Add to secrets in app settings
- **Local**: Check `.env` file exists with correct key
- **Docker**: Pass via `-e ANTHROPIC_API_KEY=...`

### Slow Performance

**Problem**: App is slow or times out

**Solutions**:
- Reduce confidence threshold (already set to 0.70)
- Check if stuck on Tier 3 (Claude API) for all bills
- Monitor console logs for bottlenecks

---

## 📈 Scaling Tips

### For High Volume (10,000+ bills/month)

1. **Add Caching**
   ```python
   @st.cache_data
   def extract_from_pdf_cached(pdf_bytes):
       # Cache results to avoid re-processing
   ```

2. **Batch Processing**
   - Add bulk upload feature
   - Process multiple PDFs in parallel
   - Store results in database

3. **Database Integration**
   - Store extraction results
   - Enable historical tracking
   - Generate aggregate reports

### For Multiple Users

1. **Add Authentication**
   - Use `streamlit-authenticator`
   - Separate sessions per user
   - Track costs per user

2. **Multi-Tenancy**
   - Add organization/project separation
   - Separate API keys per tenant
   - Cost allocation by tenant

---

## 🔄 Updates & Maintenance

### Updating Dependencies

```bash
# Update all packages
pip install --upgrade -r requirements.txt

# Test locally
streamlit run app.py

# Push changes
git add requirements.txt
git commit -m "Update dependencies"
git push
```

Streamlit Cloud will auto-deploy on push.

### Monitoring

Set up monitoring for:
- [ ] API usage (Anthropic Console)
- [ ] App uptime (Streamlit Cloud dashboard)
- [ ] Error rates (check app logs)
- [ ] User feedback

---

## 🎉 Post-Deployment

After successful deployment:

1. **Test all features**
   - Upload PDF
   - Paste text
   - Generate report
   - Download report

2. **Share with stakeholders**
   - Send app URL
   - Provide user guide
   - Collect feedback

3. **Monitor costs**
   - Check after first week
   - Adjust confidence thresholds if needed
   - Optimize based on usage patterns

---

**Need help?** Open an issue on GitHub or contact support.
