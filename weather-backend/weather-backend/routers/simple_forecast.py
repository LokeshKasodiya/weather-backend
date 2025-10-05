# routers/simple_forecast.py
"""
Simplified Weather Forecast Endpoint
Based on mentor feedback: User inputs location + date/time, gets W/P/T/H probabilities
No threshold input needed - system uses predefined values
"""

from fastapi import APIRouter, HTTPException, Query
from datetime import datetime
from services.nasa_power import get_nasa_power_data
import statistics
from typing import Dict, List

router = APIRouter(prefix="/api/simple-forecast", tags=["Simple Forecast"])


# Predefined thresholds (no user input)
THRESHOLDS = {
    "rain": 10.0,          # mm/day - moderate rain
    "heavy_rain": 50.0,    # mm/day - heavy rain  
    "high_wind": 10.0,     # m/s - windy
    "high_humidity": 70.0, # % - uncomfortable
    "hot": 35.0,           # °C - hot day
    "very_hot": 40.0       # °C - extreme heat
}


def filter_by_date(data: dict, target_month: int, target_day: int) -> List[float]:
    """Extract values for specific month/day across all years"""
    values = []
    for date_str, value in data.items():
        if value == -999:  # Skip missing data
            continue
        try:
            date_obj = datetime.strptime(date_str, "%Y%m%d")
            if date_obj.month == target_month and date_obj.day == target_day:
                values.append(value)
        except:
            continue
    return values


def calculate_probability(values: List[float], threshold: float, condition: str = "above") -> float:
    """Calculate probability of threshold exceedance"""
    if not values:
        return 0.0
    
    if condition == "above":
        count = sum(1 for v in values if v > threshold)
    else:
        count = sum(1 for v in values if v < threshold)
    
    return round(count / len(values) * 100, 1)  # Return as percentage


@router.get("/")
async def get_simple_forecast(
    lat: float = Query(..., ge=-90, le=90, description="Latitude"),
    lon: float = Query(..., ge=-180, le=180, description="Longitude"),
    date: str = Query(..., description="Date in YYYY-MM-DD format"),
    time: str = Query(default="12:00", description="Time in HH:MM format")
):
    """
    Simple weather forecast endpoint
    
    User inputs: Location (lat/lon) + Date + Time
    System returns: W, P, T, H probabilities with summary
    
    Example: /api/simple-forecast?lat=19.0760&lon=72.8777&date=2025-06-15&time=15:00
    """
    
    # Parse date/time
    try:
        target_datetime = datetime.strptime(f"{date} {time}", "%Y-%m-%d %H:%M")
    except ValueError:
        raise HTTPException(
            status_code=400, 
            detail="Invalid date/time format. Use YYYY-MM-DD and HH:MM"
        )
    
    # Prepare date range for NASA API (same date across past 20 years)
    start_year = target_datetime.year - 20
    end_year = target_datetime.year - 1
    
    start_date = datetime(start_year, target_datetime.month, target_datetime.day)
    end_date = datetime(end_year, target_datetime.month, target_datetime.day)
    
    # Fetch NASA POWER data
    parameters = ["T2M_MAX", "T2M_MIN", "PRECTOTCORR", "WS10M", "RH2M"]
    
    try:
        nasa_data = get_nasa_power_data(
            lat=lat,
            lon=lon,
            start_date=start_date,
            end_date=end_date,
            parameters=parameters
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"NASA API Error: {str(e)}")
    
    if not nasa_data:
        raise HTTPException(status_code=500, detail="Failed to fetch NASA data")
    
    # Extract parameter data
    params = nasa_data.get("properties", {}).get("parameter", {})
    
    # Filter data for target date
    temp_max_data = filter_by_date(params.get("T2M_MAX", {}), target_datetime.month, target_datetime.day)
    temp_min_data = filter_by_date(params.get("T2M_MIN", {}), target_datetime.month, target_datetime.day)
    precip_data = filter_by_date(params.get("PRECTOTCORR", {}), target_datetime.month, target_datetime.day)
    wind_data = filter_by_date(params.get("WS10M", {}), target_datetime.month, target_datetime.day)
    humidity_data = filter_by_date(params.get("RH2M", {}), target_datetime.month, target_datetime.day)
    
    # Calculate statistics
    temp_max = round(max(temp_max_data), 1) if temp_max_data else None
    temp_min = round(min(temp_min_data), 1) if temp_min_data else None
    avg_temp_max = round(statistics.mean(temp_max_data), 1) if temp_max_data else None
    
    # Calculate probabilities (W, P, T, H)
    rain_prob = calculate_probability(precip_data, THRESHOLDS["rain"], "above")
    heavy_rain_prob = calculate_probability(precip_data, THRESHOLDS["heavy_rain"], "above")
    wind_prob = calculate_probability(wind_data, THRESHOLDS["high_wind"], "above")
    hot_prob = calculate_probability(temp_max_data, THRESHOLDS["hot"], "above")
    very_hot_prob = calculate_probability(temp_max_data, THRESHOLDS["very_hot"], "above")
    high_humidity_prob = calculate_probability(humidity_data, THRESHOLDS["high_humidity"], "above")
    
    avg_humidity = round(statistics.mean(humidity_data), 1) if humidity_data else None
    avg_wind = round(statistics.mean(wind_data), 1) if wind_data else None
    
    # Generate summary text
    location_str = f"({lat}, {lon})"
    date_str = target_datetime.strftime("%B %d, %Y")
    time_str = target_datetime.strftime("%I:%M %p")
    
    summary_parts = []
    
    # Temperature summary
    if temp_max and temp_min:
        summary_parts.append(f"Temperature will range from {temp_min}°C to {temp_max}°C")
    
    # Rain summary
    if rain_prob > 60:
        summary_parts.append(f"There is a {rain_prob}% chance of rain")
    elif rain_prob > 30:
        summary_parts.append(f"Moderate {rain_prob}% chance of rain")
    else:
        summary_parts.append(f"Low {rain_prob}% chance of rain")
    
    # Wind summary
    if wind_prob > 50:
        summary_parts.append(f"{wind_prob}% chance of windy conditions")
    
    # Humidity summary
    if avg_humidity:
        summary_parts.append(f"humidity around {avg_humidity}%")
    
    summary = f"Weather forecast for {location_str} on {date_str} at {time_str}: " + ", ".join(summary_parts) + "."
    
    # Return response
    return {
        "location": {
            "latitude": lat,
            "longitude": lon
        },
        "date": date,
        "time": time,
        
        # T - Temperature
        "temperature": {
            "max": temp_max,
            "min": temp_min,
            "average_max": avg_temp_max,
            "hot_probability": hot_prob,
            "very_hot_probability": very_hot_prob,
            "unit": "°C"
        },
        
        # P - Precipitation
        "precipitation": {
            "rain_probability": rain_prob,
            "heavy_rain_probability": heavy_rain_prob,
            "unit": "%"
        },
        
        # W - Wind
        "wind": {
            "high_wind_probability": wind_prob,
            "average_speed": avg_wind,
            "unit": "m/s"
        },
        
        # H - Humidity
        "humidity": {
            "high_humidity_probability": high_humidity_prob,
            "average": avg_humidity,
            "unit": "%"
        },
        
        "summary": summary,
        "data_points_analyzed": len(temp_max_data),
        "years_analyzed": f"{start_year}-{end_year}"
    }
