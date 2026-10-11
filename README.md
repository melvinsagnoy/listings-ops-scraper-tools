# Amazon Product Scraper

A FastAPI + Playwright web app that extracts the title, star rating, and
review count from an Amazon product page.

## Local setup (Windows)

1. Install Python 3.11+ from python.org.
2. In PowerShell:

   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   playwright install chromium

3. Run:

   uvicorn app.main:app --reload

4. Open http://127.0.0.1:8000

## Test URL

https://www.amazon.com/HMCITY-Outdoor-Lights-Lighting-Waterproof/dp/B0DT95J4QC/

## Deploy on Render

1. Push to GitHub.
2. Render -> New -> Web Service -> Build from Dockerfile.
3. Free tier: 512 MB RAM, service sleeps after ~15 min idle, outbound IPs
   frequently blocked by Amazon.
