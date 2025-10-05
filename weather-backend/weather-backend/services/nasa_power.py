import requests
import datetime

def get_nasa_power_data(lat, lon, start_date, end_date, parameters):
    """
    Fetch historical weather data from NASA POWER API
    
    Args:
        lat: Latitude (-90 to 90)
        lon: Longitude (-180 to 180)
        start_date: Start date (datetime.date object)
        end_date: End date (datetime.date object)
        parameters: List of NASA POWER parameter codes
    
    Returns:
        Dictionary with weather data or None if error
    """
    base_url = "https://power.larc.nasa.gov/api/temporal/daily/point"
    
    params = {
        "parameters": ",".join(parameters),
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
