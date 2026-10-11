import re
import logging
from datetime import datetime, timezone
from typing import Optional

from playwright.async_api import async_playwright, TimeoutError as PWTimeoutError

logger = logging.getLogger(__name__)

NAV_TIMEOUT_MS = 25_000
SELECTOR_TIMEOUT_MS = 8_000

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

BLOCK_MARKERS = [
    "enter the characters you see below",
    "sorry, we just need to make sure you're not a robot",
    "api-services-support@amazon.com",
    "to discuss automated access to amazon data",
]


class ScrapeResult:
    def __init__(self, status: str, **kwargs):
        self.status = status
        self.title = kwargs.get("title")
        self.rating = kwargs.get("rating")
        self.review_count = kwargs.get("review_count")


async def scrape_product(url: str, asin: str) -> ScrapeResult:
    browser = None
    context = None
    try:
        async with async_playwright() as pw:
            browser = await pw.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-gpu",
                ],
            )
            context = await browser.new_context(
                user_agent=USER_AGENT,
                viewport={"width": 1366, "height": 900},
                locale="en-US",
            )
            page = await context.new_page()

            try:
                await page.goto(url, timeout=NAV_TIMEOUT_MS, wait_until="domcontentloaded")
            except PWTimeoutError:
                logger.warning("Navigation timeout for %s", url)
                return ScrapeResult("failed")

            try:
                await page.wait_for_selector(
                    "#productTitle, #averageCustomerReviews",
                    timeout=SELECTOR_TIMEOUT_MS,
                )
            except PWTimeoutError:
                pass

            html = await page.content()

            if _looks_blocked(html):
                logger.info("Block page detected for %s", url)
                return ScrapeResult("unavailable")

            title = await _extract_title(page)
            rating = await _extract_rating(page)
            review_count = await _extract_review_count(page)

            if title is None and rating is None and review_count is None:
                return ScrapeResult("unavailable")

            return ScrapeResult(
                status="success",
                title=title,
                rating=rating,
                review_count=review_count,
            )

    except Exception as exc:
        logger.exception("Scrape failed: %s", exc)
        return ScrapeResult("failed")
    finally:
        try:
            if context is not None:
                await context.close()
        except Exception:
            pass
        try:
            if browser is not None:
                await browser.close()
        except Exception:
            pass


def _looks_blocked(html: str) -> bool:
    lowered = html.lower()
    return any(marker in lowered for marker in BLOCK_MARKERS)


async def _extract_title(page) -> Optional[str]:
    for selector in ("#productTitle", "h1#title", "span#title"):
        try:
            el = await page.query_selector(selector)
            if el:
                text = (await el.inner_text()).strip()
                if text:
                    return text
        except Exception:
            continue
    return None


async def _extract_rating(page) -> Optional[float]:
    selectors = [
        "#acrPopover .a-icon-alt",
        "#averageCustomerReviews .a-icon-alt",
    ]
    for selector in selectors:
        try:
            el = await page.query_selector(selector)
            if not el:
                continue
            text = (await el.inner_text()).strip() or (await el.get_attribute("textContent") or "")
            value = _parse_rating_text(text)
            if value is not None:
                return value
        except Exception:
            continue

    try:
        el = await page.query_selector("#acrPopover")
        if el:
            title = await el.get_attribute("title")
            value = _parse_rating_text(title or "")
            if value is not None:
                return value
    except Exception:
        pass

    return None


def _parse_rating_text(text: str) -> Optional[float]:
    if not text:
        return None
    match = re.search(r"([0-5](?:\.\d+)?)\s*out of\s*5", text, re.IGNORECASE)
    if not match:
        return None
    try:
        value = float(match.group(1))
    except ValueError:
        return None
    if 0.0 <= value <= 5.0:
        return value
    return None


async def _extract_review_count(page) -> Optional[int]:
    try:
        el = await page.query_selector("#acrCustomerReviewText")
        if not el:
            return None

        candidates = []
        aria = await el.get_attribute("aria-label")
        if aria:
            candidates.append(aria)
        text = await el.inner_text()
        if text:
            candidates.append(text)

        for candidate in candidates:
            value = _parse_review_count(candidate)
            if value is not None:
                return value
    except Exception:
        pass
    return None


def _parse_review_count(text: str) -> Optional[int]:
    if not text:
        return None
    match = re.search(r"([\d.,]+)", text)
    if not match:
        return None
    raw = match.group(1).replace(",", "").replace(".", "")
    if not raw.isdigit():
        return None
    try:
        value = int(raw)
    except ValueError:
        return None
    return value if value >= 0 else None


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
