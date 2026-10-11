import logging
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.models import ScrapeRequest, ScrapeResponse, ProductData
from app.scraper import scrape_product, now_iso
from app.validators import validate_asin, asin_to_url, InvalidASINError

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "static"

app = FastAPI(title="Amazon Product Scraper", version="1.1.0")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/")
async def index():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/healthz")
async def healthz():
    return {"ok": True}


@app.post("/api/scrape", response_model=ScrapeResponse)
async def api_scrape(payload: ScrapeRequest):
    # De-duplicate while preserving order.
    seen = set()
    unique_raw = []
    for raw in payload.asins:
        key = (raw or "").strip().upper()
        if key and key not in seen:
            seen.add(key)
            unique_raw.append(raw)

    if not unique_raw:
        raise HTTPException(status_code=400, detail="No ASINs provided.")

    results: list[ProductData] = []

    # Sequential scraping — never parallel. One Chromium at a time.
    for raw in unique_raw:
        try:
            asin = validate_asin(raw)
        except InvalidASINError as exc:
            results.append(
                ProductData(
                    asin=(raw or "").strip().upper() or "—",
                    title=None,
                    rating=None,
                    review_count=None,
                    product_url="",
                    scraped_at=now_iso(),
                    status="failed",
                    error=str(exc),
                )
            )
            continue

        url = asin_to_url(asin)
        scraped_at = now_iso()

        try:
            result = await scrape_product(url, asin)
        except Exception:
            logger.exception("Unexpected error scraping %s", asin)
            results.append(
                ProductData(
                    asin=asin,
                    title=None,
                    rating=None,
                    review_count=None,
                    product_url=url,
                    scraped_at=scraped_at,
                    status="failed",
                    error="Unexpected server error while scraping this ASIN.",
                )
            )
            continue

        if result.status == "failed":
            results.append(
                ProductData(
                    asin=asin,
                    title=None,
                    rating=None,
                    review_count=None,
                    product_url=url,
                    scraped_at=scraped_at,
                    status="failed",
                    error="Could not retrieve the product page.",
                )
            )
        elif result.status == "unavailable":
            results.append(
                ProductData(
                    asin=asin,
                    title=None,
                    rating=None,
                    review_count=None,
                    product_url=url,
                    scraped_at=scraped_at,
                    status="unavailable",
                    error=(
                        "Amazon did not return a readable product page "
                        "(blocked, CAPTCHA, or product unavailable)."
                    ),
                )
            )
        else:
            results.append(
                ProductData(
                    asin=asin,
                    title=result.title,
                    rating=result.rating,
                    review_count=result.review_count,
                    product_url=url,
                    scraped_at=scraped_at,
                    status="success",
                    error=None,
                )
            )

    any_success = any(r.status == "success" for r in results)
    return ScrapeResponse(success=any_success, results=results, error=None)