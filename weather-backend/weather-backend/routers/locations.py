from fastapi import APIRouter, Query, HTTPException
import requests

router = APIRouter()

@router.get("/location/geocode")
async def geocode_location(city: str = Query(..., description="City name (e.g., 'Delhi', 'Mumbai')")):
    """
    Convert city name to latitude/longitude coordinates using OpenStreetMap Nominatim
    """
    url = "https://nominatim.openstreetmap.org/search"
    params = {
        "q": city,
        "format": "json",
        "limit": 1
    }
    headers = {"User-Agent": "WeatherProbabilityApp/1.0"}
    
    try:
        response = requests.get(url, params=params, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if not data:
            raise HTTPException(status_code=404, detail=f"Location '{city}' not found")
        
        return {
            "city": city,
            "latitude": float(data[0]["lat"]),
            "longitude": float(data[0]["lon"]),
            "display_name": data[0]["display_name"]
        }
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail=f"Geocoding service error: {str(e)}")
