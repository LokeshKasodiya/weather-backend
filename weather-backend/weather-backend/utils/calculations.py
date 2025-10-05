# utils/calculations.py - COMPLETE FILE

from datetime import datetime
import numpy as np
from typing import Dict, List, Tuple, Optional

# ========== EXISTING FUNCTIONS (keep these) ==========

def filter_data_by_month(param_data, month):
    """
    Filter historical data for a specific month
    
    Args:
        param_data: Dictionary with date strings as keys
        month: Month number (1-12)
    
    Returns:
        Filtered dictionary
    """
    filtered = {}
    for date_str, value in param_data.items():
        try:
            date_obj = datetime.strptime(date_str, "%Y%m%d")
            if date_obj.month == month:
                filtered[date_str] = value
        except:
            continue
    return filtered

def calculate_probability(filtered_data, threshold, condition_type):
    """
    Calculate probability of weather condition occurring
    
    Args:
        filtered_data: Dictionary of date:value pairs
        threshold: Threshold value
        condition_type: "above" or "below"
    
    Returns:
        Probability (0.0 to 1.0) or None if insufficient data
    """
    if not filtered_data:
        return None
    
    # Filter out invalid values (NASA uses -999 for missing data)
    values = [v for v in filtered_data.values() if v is not None and v != -999]
    
    if not values:
        return None
    
    if condition_type == "above":
        exceeding_count = sum(1 for v in values if v > threshold)
    else:
        exceeding_count = sum(1 for v in values if v < threshold)
    
    probability = exceeding_count / len(values)
    return round(probability, 3)

def calculate_extreme_statistics(filtered_data):
    """
    Calculate additional statistics for extreme events
    
    Args:
        filtered_data: Dictionary of date:value pairs
    
    Returns:
        Dictionary with max, min, average, and data_points
    """
    values = [v for v in filtered_data.values() if v is not None and v != -999]
    
    if not values:
        return None
    
    return {
        "max": round(max(values), 2),
        "min": round(min(values), 2),
        "average": round(sum(values) / len(values), 2),
        "data_points": len(values)
    }

# ========== NEW FUNCTIONS (add these) ==========

SEASON_MONTHS = {
    "djf": {12, 1, 2},
    "mam": {3, 4, 5},
    "jja": {6, 7, 8},
    "son": {9, 10, 11},
}

def filter_by_year_range(param_data: Dict[str, float], start_year: Optional[int], end_year: Optional[int]) -> Dict[str, float]:
    if not start_year and not end_year:
        return param_data
    out = {}
    for d, v in param_data.items():
        try:
            y = int(d[:4])
            if (start_year is None or y >= start_year) and (end_year is None or y <= end_year):
                out[d] = v
        except:
            continue
    return out

def filter_by_season(param_data: Dict[str, float], season: Optional[str]) -> Dict[str, float]:
    if not season:
        return param_data
    months = SEASON_MONTHS[season]
    out = {}
    for d, v in param_data.items():
        try:
            m = int(d[4:6])
            if m in months:
                out[d] = v
        except:
            continue
    return out

def filter_by_doy(param_data: Dict[str, float], doy: Optional[int]) -> Dict[str, float]:
    if not doy:
        return param_data
    out = {}
    for d, v in param_data.items():
        try:
            dt = datetime.strptime(d, "%Y%m%d")
            if dt.timetuple().tm_yday == doy:
                out[d] = v
        except:
            continue
    return out

def summarize_values(values: List[float]):
    if not values:
        return None
    arr = np.array(values, dtype=float)
    return {
        "mean": round(float(np.nanmean(arr)), 2),
        "median": round(float(np.nanmedian(arr)), 2),
        "p75": round(float(np.nanpercentile(arr, 75)), 2),
        "p95": round(float(np.nanpercentile(arr, 95)), 2),
        "count": int(arr.size),
    }

def make_histogram(values: List[float], bins:int=24):
    if not values:
        return {"bins": [], "counts": []}
    counts, bin_edges = np.histogram(values, bins=bins)
    return {
        "bins": [round(float(b), 3) for b in bin_edges.tolist()],
        "counts": counts.tolist()
    }

def analyze_trend_yearly_extremes(param_data: Dict[str, float], threshold: float, condition_type: str):
    # Count extreme-event days per year, then fit trend line
    yearly = {}
    for d, v in param_data.items():
        try:
            if v is None or v == -999:
                continue
            y = int(d[:4])
            ok = v > threshold if condition_type == "above" else v < threshold
            if ok:
                yearly[y] = yearly.get(y, 0) + 1
        except:
            continue
    if not yearly:
        return {"yearly_counts": {}, "slope": 0.0, "trend": "flat"}
    years = np.array(sorted(yearly.keys()))
    counts = np.array([yearly[y] for y in years], dtype=float)
    slope, intercept = np.polyfit(years, counts, 1)
    trend = "increasing" if slope > 0 else ("decreasing" if slope < 0 else "flat")
    return {"yearly_counts": {int(y): int(c) for y, c in zip(years, counts)}, "slope": round(float(slope), 4), "trend": trend}

# ----- Polygon sampling aligned to ~0.5° POWER daily grid -----

def _point_in_polygon(lat: float, lon: float, polygon: List[Tuple[float, float]]) -> bool:
    # Ray casting algorithm
    x, y = lon, lat
    inside = False
    n = len(polygon)
    for i in range(n):
        x1, y1 = polygon[i][1], polygon[i][0]
        x2, y2 = polygon[(i+1) % n][1], polygon[(i+1) % n][0]
        if ((y1 > y) != (y2 > y)) and (x < (x2 - x1) * (y - y1) / (y2 - y1 + 1e-12) + x1):
            inside = not inside
    return inside

def sample_polygon_to_grid(polygon: List[Tuple[float, float]], step: float = 0.5) -> List[Tuple[float, float]]:
    lats = [p[0] for p in polygon]
    lons = [p[1] for p in polygon]
    min_lat, max_lat = min(lats), max(lats)
    min_lon, max_lon = min(lons), max(lons)
    points = []
    lat = round(min_lat / step) * step
    while lat <= max_lat + 1e-9:
        lon = round(min_lon / step) * step
        while lon <= max_lon + 1e-9:
            if _point_in_polygon(lat, lon, polygon):
                points.append((lat, lon))
            lon = round(lon + step, 6)
        lat = round(lat + step, 6)
    return points
