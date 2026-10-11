from typing import List, Optional
from pydantic import BaseModel, Field


class ScrapeRequest(BaseModel):
    # Accept 1–20 ASINs per request to keep Chromium memory in check.
    asins: List[str] = Field(..., min_length=1, max_length=20)


class ProductData(BaseModel):
    asin: str
    title: Optional[str] = None
    rating: Optional[float] = None
    review_count: Optional[int] = None
    product_url: str
    scraped_at: str
    status: str          # "success" | "unavailable" | "failed"
    error: Optional[str] = None


class ScrapeResponse(BaseModel):
    success: bool
    results: List[ProductData] = []
    error: Optional[str] = None