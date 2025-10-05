# services/activity_presets.py
"""
Activity-specific weather condition presets for user-friendly planning
"""

ACTIVITY_PRESETS = {
    "beach": {
        "name": "Beach Mode",
        "description": "Sunny, warm, low rainfall",
        "ideal_conditions": {
            "temperature": {"min": 25, "max": 35, "parameter": "T2M"},
            "precipitation": {"max": 5, "parameter": "PRECTOTCORR"},
            "cloud_cover": {"max": 30, "parameter": "CLOUD_AMT"},
            "wind": {"max": 10, "parameter": "WS10M"}
        },
        "avoid_conditions": ["heavy_rain", "storm_wind", "cold_wave"]
    },
    "hiking": {
        "name": "Hiking Mode",
        "description": "Cool, dry, moderate wind",
        "ideal_conditions": {
            "temperature": {"min": 15, "max": 28, "parameter": "T2M"},
            "precipitation": {"max": 2, "parameter": "PRECTOTCORR"},
            "wind": {"max": 15, "parameter": "WS10M"},
            "humidity": {"max": 70, "parameter": "RH2M"}
        },
        "avoid_conditions": ["heavy_rain", "heatwave", "high_wind"]
    },
    "skiing": {
        "name": "Ski Mode",
        "description": "Cold with snow probability",
        "ideal_conditions": {
            "temperature": {"min": -10, "max": 5, "parameter": "T2M"},
            "snow_depth": {"min": 10, "parameter": "SNODP"},
            "wind": {"max": 20, "parameter": "WS10M"}
        },
        "prefer_conditions": ["heavy_snow", "cold_wave"],
        "avoid_conditions": ["heatwave", "heavy_rain"]
    },
    "cycling": {
        "name": "Cycling Mode",
        "description": "Moderate temp, low wind, dry",
        "ideal_conditions": {
            "temperature": {"min": 18, "max": 30, "parameter": "T2M"},
            "precipitation": {"max": 1, "parameter": "PRECTOTCORR"},
            "wind": {"max": 12, "parameter": "WS10M"}
        },
        "avoid_conditions": ["heavy_rain", "high_wind", "heatwave"]
    },
    "camping": {
        "name": "Camping Mode",
        "description": "Mild, dry, low wind",
        "ideal_conditions": {
            "temperature": {"min": 10, "max": 28, "parameter": "T2M"},
            "precipitation": {"max": 5, "parameter": "PRECTOTCORR"},
            "wind": {"max": 15, "parameter": "WS10M"}
        },
        "avoid_conditions": ["heavy_rain", "cold_wave", "high_wind"]
    }
}

def get_activity_suitability(activity: str, weather_data: dict) -> dict:
    """
    Evaluate suitability of weather conditions for a specific activity
    Returns score 0-100 and explanation
    """
    if activity not in ACTIVITY_PRESETS:
        return {"error": "Unknown activity"}
    
    preset = ACTIVITY_PRESETS[activity]
    ideal = preset["ideal_conditions"]
    
    score = 100
    issues = []
    
    # Check each ideal condition
    for condition, rules in ideal.items():
        param = rules.get("parameter")
        if param and param in weather_data:
            value = weather_data[param]
            
            if "min" in rules and value < rules["min"]:
                score -= 20
                issues.append(f"{condition} too low ({value:.1f})")
            
            if "max" in rules and value > rules["max"]:
                score -= 20
                issues.append(f"{condition} too high ({value:.1f})")
    
    score = max(0, score)
    
    if score >= 80:
        rating = "Excellent"
    elif score >= 60:
        rating = "Good"
    elif score >= 40:
        rating = "Fair"
    else:
        rating = "Poor"
    
    return {
        "activity": preset["name"],
        "score": score,
        "rating": rating,
        "issues": issues,
        "description": preset["description"]
    }
