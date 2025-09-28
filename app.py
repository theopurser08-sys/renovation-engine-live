import os
import requests
from typing import List, Optional, Dict, Any
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from fastapi.middleware.cors import CORSMiddleware

# ---- Config ----
SERPAPI_KEY = os.getenv("SERPAPI_KEY")

app = FastAPI(title="Renovation Price Finder Live", version="1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---- Models ----
class ItemRequest(BaseModel):
    name: str
    brand: Optional[str] = None
    material: Optional[str] = None
    color: Optional[str] = None

class SearchRequest(BaseModel):
    items: List[ItemRequest]
    country: str = "uk"
    language: str = "en"
    num_results: int = 24

class Product(BaseModel):
    title: str
    price: Optional[float]
    price_str: Optional[str]
    link: str
    source: Optional[str]
    thumbnail: Optional[str]

class SearchResponse(BaseModel):
    results: Dict[str, List[Product]]

# ---- Helpers ----
def call_serpapi(query: str, gl: str, hl: str, num: int):
    if not SERPAPI_KEY:
        raise HTTPException(status_code=500, detail="SERPAPI_KEY not set")
    params = {
        "engine": "google_shopping",
        "q": query,
        "gl": gl,
        "hl": hl,
        "num": num,
        "api_key": SERPAPI_KEY,
    }
    r = requests.get("https://serpapi.com/search.json", params=params, timeout=20)
    if r.status_code != 200:
        raise HTTPException(status_code=502, detail=f"SerpAPI error {r.text}")
    return r.json()

def normalize(entry) -> Product:
    return Product(
        title=entry.get("title",""),
        price=entry.get("extracted_price"),
        price_str=entry.get("price"),
        link=entry.get("link",""),
        source=entry.get("source"),
        thumbnail=entry.get("thumbnail")
    )

# ---- Endpoints ----
@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/search_live", response_model=SearchResponse)
def search_live(req: SearchRequest):
    output = {}
    for item in req.items:
        q = item.name
        if item.brand: q = f"{item.brand} {q}"
        if item.material: q = f"{item.material} {q}"
        if item.color: q = f"{item.color} {q}"
        data = call_serpapi(q, req.country, req.language, req.num_results)
        products = [normalize(e) for e in data.get("shopping_results", []) if e.get("extracted_price")]
        products.sort(key=lambda x: x.price or 999999)
        output[q] = products
    return SearchResponse(results=output)
