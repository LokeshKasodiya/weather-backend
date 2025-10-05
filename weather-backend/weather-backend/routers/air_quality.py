from fastapi import APIRouter, Query, HTTPException
from typing import Optional
from services.nasa_air_quality import get_air_quality_probability

router = APIRouter()

@router.get("/air-quality/probability", tags=["Air Quality"])
async def get_air_quality_risk(
    lat: float = Query(..., ge=-90, le=90, description="Latitude"),
    lon: float = Query(..., ge=-180, le=180, description="Longitude"),
    month: Optional[int] = Query(None, ge=1, le=12, description="Month (1-12)")
):
    month = month or 6
    result = get_air_quality_probability(lat, lon, month)
    if not result:
        raise HTTPException(status_code=500, detail="Failed to calculate air quality probability")
    p = result["poor_air_quality_probability"]
    risk = "High" if p > 0.5 else ("Moderate" if p > 0.3 else "Low")
    return {
        "location": {"latitude": lat, "longitude": lon},
        "month": month,
        "air_quality_assessment": result,
        "risk_level": risk,
        "advisory": _advice(risk),
        "data_source": "NASA POWER meteorological proxy"
    }

def _advice(level: str) -> str:
    if level == "High":
        return "Poor air quality likely. Limit outdoor activities, especially for sensitive groups."
    if level == "Moderate":
        return "Acceptable air quality. Sensitive individuals should monitor conditions."
    return "Good conditions for outdoor activities"
