# services/nasa_air_quality.py
import requests
from datetime import datetime, timedelta

def get_modis_aod_data(lat: float, lon: float, start_date, end_date):
    """
    Get NASA MODIS Aerosol Optical Depth data
    AOD is a proxy for air quality - higher values = worse air quality
    """
    # NASA POWER doesn't have direct air quality, but has AOD proxy
    # For hackathon, we can use atmospheric parameters as air quality indicators
    
    base_url = "https://power.larc.nasa.gov/api/temporal/daily/point"
    
    # These parameters relate to air quality
    params = {
        "parameters": "T2M,RH2M,WS10M,PRECTOTCORR",  # Temperature, humidity, wind, precip affect air quality
        "community": "AG",
        "longitude": lon,
        "latitude": lat,
        "start": start_date.strftime("%Y%m%d"),
        "end": end_date.strftime("%Y%m%d"),
        "format": "JSON"
    }
    
    try:
        response = requests.get(base_url, params=params, timeout=60)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"NASA API Error: {e}")
        return None


def calculate_air_quality_proxy(temp, humidity, wind_speed, precip):
    """
    Calculate air quality proxy based on meteorological conditions
    High temp + low wind + low precip + high humidity = worse air quality
    """
    # Simple scoring algorithm (0-5 scale, lower is better)
    score = 0
    
    # High temperature increases pollution concentration
    if temp > 35:
        score += 2
    elif temp > 30:
        score += 1
    
    # Low wind speed reduces dispersion
    if wind_speed < 2:
        score += 2
    elif wind_speed < 5:
        score += 1
    
    # Rain cleans air
    if precip < 1:
        score += 1
    
    # High humidity can trap pollutants
    if humidity > 70:
        score += 1
    
    # Convert to AQI-like scale
    if score <= 1:
        return {"aqi_proxy": 1, "quality": "Good"}
    elif score <= 2:
        return {"aqi_proxy": 2, "quality": "Moderate"}
    elif score <= 3:
        return {"aqi_proxy": 3, "quality": "Unhealthy for Sensitive Groups"}
    elif score <= 5:
        return {"aqi_proxy": 4, "quality": "Unhealthy"}
    else:
        return {"aqi_proxy": 5, "quality": "Very Unhealthy"}


def get_air_quality_probability(lat: float, lon: float, month: int):
    """
    Calculate probability of poor air quality based on historical meteorological conditions
    """
    from datetime import date
    end_date = date.today()
    start_date = end_date.replace(year=end_date.year - 20)
    
    # Get meteorological data from NASA POWER
    data = get_modis_aod_data(lat, lon, start_date, end_date)
    
    if not data:
        return None
    
    # Extract parameters
    temps = data["properties"]["parameter"]["T2M"]
    humidity = data["properties"]["parameter"]["RH2M"]
    wind = data["properties"]["parameter"]["WS10M"]
    precip = data["properties"]["parameter"]["PRECTOTCORR"]
    
    # Filter by month
    from utils.calculations import filter_data_by_month
    temps_filtered = filter_data_by_month(temps, month)
    humidity_filtered = filter_data_by_month(humidity, month)
    wind_filtered = filter_data_by_month(wind, month)
    precip_filtered = filter_data_by_month(precip, month)
    
    # Calculate daily air quality proxy
    poor_air_days = 0
    total_days = 0
    
    for date_key in temps_filtered.keys():
        if date_key in humidity_filtered and date_key in wind_filtered and date_key in precip_filtered:
            t = temps_filtered[date_key]
            h = humidity_filtered[date_key]
            w = wind_filtered[date_key]
            p = precip_filtered[date_key]
            
            if t != -999 and h != -999 and w != -999 and p != -999:
                total_days += 1
                proxy = calculate_air_quality_proxy(t, h, w, p)
                if proxy["aqi_proxy"] >= 3:  # Unhealthy or worse
                    poor_air_days += 1
    
    if total_days == 0:
        return None
    
    probability = poor_air_days / total_days
    
    return {
        "poor_air_quality_probability": round(probability, 3),
        "days_analyzed": total_days,
        "method": "Meteorological proxy based on NASA POWER data",
        "note": "Based on temperature, humidity, wind, and precipitation patterns that affect air quality"
    }
