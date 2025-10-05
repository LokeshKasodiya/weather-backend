# main.py
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import probability, locations, air_quality, simple_forecast

# Routers (ensure routers/__init__.py exists and these files define `router = APIRouter()`)
from routers import probability, locations, air_quality

# Load environment variables if any (e.g., API keys, config)
load_dotenv()

app = FastAPI(
    title="NASA Weather & Air Quality Analytics API",
    description=(
        "Historical probability-based weather analytics (NASA POWER) with polygon/region support, "
        "histograms, trends, and a NASA-derived air-quality proxy endpoint"
    ),
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS for local dev and easy frontend integration; tighten in production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],     # Replace with your frontend domain(s) in prod
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount feature routers under /api
app.include_router(probability.router, prefix="/api", tags=["Extreme Weather Probability"])
app.include_router(locations.router,   prefix="/api", tags=["Location Services"])
app.include_router(air_quality.router, prefix="/api", tags=["Air Quality"])
app.include_router(simple_forecast.router, prefix="/api", tags=["Simple forecast"])
# Simple health and root endpoints
@app.get("/")
def root():
    return {"message": "OK", "docs": "/docs", "redoc": "/redoc"}

@app.get("/health")
def health():
    return {"status": "healthy"}

# Run locally:
# uvicorn main:app --reload
