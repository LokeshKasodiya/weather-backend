# services/thresholds.py

EXTREME_WEATHER_THRESHOLDS = {
    "heatwave": {
        "parameter": "T2M_MAX",
        "default_threshold": 40.0,
        "condition": "above",
        "unit": "°C",
        "description": "Extreme heat conditions"
    },
    "hot_day": {
        "parameter": "T2M_MAX",
        "default_threshold": 35.0,
        "condition": "above",
        "unit": "°C",
        "description": "Very hot day"
    },
    "warm_day": {
        "parameter": "T2M_MAX",
        "default_threshold": 30.0,
        "condition": "above",
        "unit": "°C",
        "description": "Warm weather"
    },
    "cold_wave": {
        "parameter": "T2M_MIN",
        "default_threshold": 5.0,
        "condition": "below",
        "unit": "°C",
        "description": "Extreme cold conditions"
    },
    "cold_day": {
        "parameter": "T2M_MIN",
        "default_threshold": 10.0,
        "condition": "below",
        "unit": "°C",
        "description": "Cold day"
    },
    "heavy_rain": {
        "parameter": "PRECTOTCORR",
        "default_threshold": 50.0,
        "condition": "above",
        "unit": "mm/day",
        "description": "Heavy rainfall"
    },
    "high_wind": {
        "parameter": "WS10M",
        "default_threshold": 15.0,
        "condition": "above",
        "unit": "m/s",
        "description": "Strong winds"
    },
    "overcast": {
        "parameter": "CLOUD_AMT",
        "default_threshold": 80.0,
        "condition": "above",
        "unit": "%",
        "description": "Heavily overcast sky"
    },
    "high_humidity": {
        "parameter": "RH2M",
        "default_threshold": 80.0,
        "condition": "above",
        "unit": "%",
        "description": "Very humid conditions"
    },
}
