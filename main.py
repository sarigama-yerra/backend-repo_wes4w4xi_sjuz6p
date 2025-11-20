import os
import time
from typing import Dict
import requests
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from database import get_documents

COUNTRIES = {
    "NL": {"code": "NL", "name": "Nederland"},
    "AE": {"code": "AE", "name": "Dubai"},
    "BH": {"code": "BH", "name": "Bahrein"},
}

app = FastAPI(title="BirthdayDeals API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Simple in-process rate limiting (per IP per route)
RateKey = str
_rate_store: Dict[RateKey, Dict[str, float]] = {}

def check_rate_limit(request: Request, limit: int, window_seconds: int) -> bool:
    ip = request.client.host if request.client else "unknown"
    path = request.url.path
    key = f"{ip}:{path}:{window_seconds}"
    now = time.time()
    entry = _rate_store.get(key)
    if not entry:
        _rate_store[key] = {"count": 1, "reset": now + window_seconds}
        return True
    if now > entry["reset"]:
        _rate_store[key] = {"count": 1, "reset": now + window_seconds}
        return True
    if entry["count"] >= limit:
        return False
    entry["count"] += 1
    return True

@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    # default soft limit for all routes
    if not check_rate_limit(request, limit=120, window_seconds=60):
        return JSONResponse(status_code=429, content={"detail": "Rate limit exceeded"})
    return await call_next(request)

class RecaptchaRequest(BaseModel):
    token: str

@app.get("/")
async def read_root(request: Request):
    if not check_rate_limit(request, limit=5, window_seconds=1):
        return JSONResponse(status_code=429, content={"detail": "Rate limit exceeded"})
    return {"message": "BirthdayDeals Backend Running"}

@app.get("/api/health")
async def health(request: Request):
    if not check_rate_limit(request, limit=10, window_seconds=1):
        return JSONResponse(status_code=429, content={"detail": "Rate limit exceeded"})
    return {"status": "ok", "countries": list(COUNTRIES.values())}

@app.get("/api/countries")
async def get_countries(request: Request):
    if not check_rate_limit(request, limit=20, window_seconds=60):
        return JSONResponse(status_code=429, content={"detail": "Rate limit exceeded"})
    return list(COUNTRIES.values())

@app.get("/api/banners")
async def get_banners(request: Request, country: str):
    if not check_rate_limit(request, limit=60, window_seconds=60):
        return JSONResponse(status_code=429, content={"detail": "Rate limit exceeded"})
    code = country.upper()
    if code not in COUNTRIES:
        raise HTTPException(status_code=400, detail="Unsupported country")
    docs = get_documents("banner", {"country_code": code, "is_active": True})
    docs.sort(key=lambda x: x.get("position", 0))
    for d in docs:
        if "_id" in d:
            d["id"] = str(d.pop("_id"))
    return docs

@app.post("/api/verify-recaptcha")
async def verify_recaptcha(request: Request, payload: RecaptchaRequest):
    if not check_rate_limit(request, limit=30, window_seconds=60):
        return JSONResponse(status_code=429, content={"detail": "Rate limit exceeded"})
    secret = os.getenv("RECAPTCHA_SECRET")
    if not payload.token:
        raise HTTPException(status_code=400, detail="Missing token")
    if not secret:
        return {"success": False, "skipped": True, "reason": "No secret configured"}
    try:
        resp = requests.post(
            "https://www.google.com/recaptcha/api/siteverify",
            data={"secret": secret, "response": payload.token},
            timeout=5,
        )
        data = resp.json()
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Recaptcha verify failed: {str(e)[:100]}")

@app.get("/test")
async def test_database(request: Request):
    if not check_rate_limit(request, limit=10, window_seconds=60):
        return JSONResponse(status_code=429, content={"detail": "Rate limit exceeded"})
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }
    try:
        from database import db
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Configured"
            response["database_name"] = db.name if hasattr(db, 'name') else "✅ Connected"
            response["connection_status"] = "Connected"
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"
    except ImportError:
        response["database"] = "❌ Database module not found (run enable-database first)"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"
    response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
    response["database_name"] = "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set"
    return response

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
