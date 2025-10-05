# routers/probability.py
from fastapi import APIRouter, HTTPException, Query, Body
from fastapi.responses import StreamingResponse
from typing import List, Tuple, Optional
import datetime, io, csv, numpy as np

from services.nasa_power import get_nasa_power_data
from services.thresholds import EXTREME_WEATHER_THRESHOLDS
from utils.calculations import (
    filter_data_by_month, calculate_probability, calculate_extreme_statistics,
    filter_by_year_range, filter_by_season, filter_by_doy, summarize_values,
    make_histogram, analyze_trend_yearly_extremes, sample_polygon_to_grid
)
from models import RegionRequest, HistogramRequest

router = APIRouter()
@router.get("/download-report", tags=["Data Export"])
async def download_weather_report(
    lat: float,
    lon: float,
    condition_type: str,
    month: Optional[int] = None,
    format: str = Query("csv", regex="^(csv|json)$")
):
    """
    Download complete weather report as CSV or JSON
    """
    # Get all data
    historical_end = datetime.date.today()
    historical_start = historical_end.replace(year=historical_end.year - 20)
    
    cfg = EXTREME_WEATHER_THRESHOLDS[condition_type]
    parameter = cfg["parameter"]
    
    nasa_data = get_nasa_power_data(lat, lon, historical_start, historical_end, [parameter])
    
    if not nasa_data:
        raise HTTPException(status_code=500, detail="Failed to fetch data")
    
    param_data = nasa_data["properties"]["parameter"][parameter]
    
    if month:
        param_data = filter_data_by_month(param_data, month)
    
    if format == "csv":
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["Date", "Value", "Parameter", "Unit", "Location_Lat", "Location_Lon"])
        
        for date_str, value in param_data.items():
            if value not in (-999, None):
                writer.writerow([date_str, value, parameter, cfg["unit"], lat, lon])
        
        output.seek(0)
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=weather_report_{condition_type}_{lat}_{lon}.csv"}
        )
    else:
        return {
            "metadata": {"lat": lat, "lon": lon, "condition": condition_type, "parameter": parameter},
            "data": param_data
        }

@router.get("/extreme-weather/probability", tags=["Extreme Weather Probability"])
async def get_extreme_weather_probability(
    lat: float = Query(..., ge=-90, le=90, description="Latitude"),
    lon: float = Query(..., ge=-180, le=180, description="Longitude"),
    month: Optional[int] = Query(None, ge=1, le=12, description="Month (1-12)"),
    season: Optional[str] = Query(None, regex="^(djf|mam|jja|son)$", description="Season code"),
    doy: Optional[int] = Query(None, ge=1, le=366, description="Day of year 1-366"),
    start_year: Optional[int] = Query(None, description="Start year inclusive"),
    end_year: Optional[int] = Query(None, description="End year inclusive"),
    condition_type: str = Query(..., description="heatwave, cold_wave, heavy_rain, high_wind, heavy_snow, high_cloud_cover"),
    custom_threshold: Optional[float] = Query(None, description="Override default threshold")
):
    if condition_type not in EXTREME_WEATHER_THRESHOLDS:
        raise HTTPException(status_code=400, detail=f"Invalid condition_type: {condition_type}")

    cfg = EXTREME_WEATHER_THRESHOLDS[condition_type]
    parameter, cond, default_threshold = cfg["parameter"], cfg["condition"], custom_threshold or cfg["default_threshold"]

    end_date = datetime.date.today()
    start_date = end_date.replace(year=end_date.year - 20)

    nasa = get_nasa_power_data(lat, lon, start_date, end_date, [parameter])
    if not nasa:
        raise HTTPException(status_code=500, detail="NASA POWER fetch failed")

    try:
        p = nasa["properties"]["parameter"][parameter]
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Parameter {parameter} not found")

    data = p
    data = filter_by_year_range(data, start_year, end_year)
    if doy:
        data = filter_by_doy(data, doy)
    elif season:
        data = filter_by_season(data, season)
    elif month:
        data = filter_data_by_month(data, month)

    prob = calculate_probability(data, default_threshold, cond)
    stats = calculate_extreme_statistics(data)
    values = [v for v in data.values() if v is not None and v != -999]

    trend = analyze_trend_yearly_extremes(data, default_threshold, cond)
    summary = None
    if prob is not None and stats:
        summary = "High likelihood; plan accordingly" if prob >= 0.6 else ("Moderate likelihood; monitor conditions" if prob >= 0.3 else "Low likelihood")

    return {
        "location": {"latitude": lat, "longitude": lon},
        "time_filter": {"month": month, "season": season, "doy": doy, "start_year": start_year, "end_year": end_year},
        "condition_type": condition_type,
        "parameter": parameter,
        "condition": cond,
        "threshold": default_threshold,
        "probability": prob if prob is not None else 0.0,
        "statistics": stats,
        "distribution": summarize_values(values),
        "trend": trend,
        "summary": summary,
        "metadata": {
            "source": "NASA POWER Daily API",
            "spatial_resolution": "~0.5° grid",
            "temporal_coverage": "1981‑present (varies by var)"
        }
    }
@router.get("/activity-forecast", tags=["Activity Planning"])
async def get_activity_forecast(
    lat: float = Query(..., description="Latitude"),
    lon: float = Query(..., description="Longitude"),
    activity: str = Query(..., regex="^(beach|hiking|skiing|cycling|camping)$"),
    month: Optional[int] = Query(None, ge=1, le=12),
    date: Optional[str] = Query(None, description="Specific date YYYY-MM-DD")
):
    """
    Get weather suitability score for specific activity
    """
    from services.activity_presets import get_activity_suitability, ACTIVITY_PRESETS
    from datetime import date as dt, timedelta
    
    # Get weather data for the period
    end_date = dt.today()
    start_date = end_date.replace(year=end_date.year - 10)
    
    params = ["T2M", "PRECTOTCORR", "WS10M", "RH2M", "CLOUD_AMT", "SNODP"]
    nasa_data = get_nasa_power_data(lat, lon, start_date, end_date, params)
    
    if not nasa_data:
        raise HTTPException(status_code=500, detail="Failed to fetch weather data")
    
    # Calculate average conditions for the month/date
    averages = {}
    for param in params:
        if param in nasa_data["properties"]["parameter"]:
            data = nasa_data["properties"]["parameter"][param]
            if month:
                data = filter_data_by_month(data, month)
            values = [v for v in data.values() if v not in (-999, None)]
            averages[param] = sum(values) / len(values) if values else 0
    
    suitability = get_activity_suitability(activity, averages)
    
    return {
        "location": {"latitude": lat, "longitude": lon},
        "month": month,
        "activity": activity,
        "suitability": suitability,
        "average_conditions": averages,
        "data_source": "NASA POWER (10-year historical average)"
    }
@router.get("/multi-day-forecast", tags=["Extended Planning"])
async def get_multi_day_probability(
    lat: float = Query(..., description="Latitude"),
    lon: float = Query(..., description="Longitude"),
    start_date: str = Query(..., description="Start date YYYY-MM-DD"),
    end_date: str = Query(..., description="End date YYYY-MM-DD"),
    condition_type: str = Query(..., description="Weather condition to check")
):
    """
    Get probability for multi-day event (e.g., 3-day festival, week-long trek)
    """
    from datetime import datetime
    
    try:
        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        end_dt = datetime.strptime(end_date, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
    
    if (end_dt - start_dt).days > 30:
        raise HTTPException(status_code=400, detail="Maximum 30-day range allowed")
    
    # Get historical data for same calendar period across multiple years
    historical_end = datetime.date.today()
    historical_start = historical_end.replace(year=historical_end.year - 20)
    
    cfg = EXTREME_WEATHER_THRESHOLDS[condition_type]
    parameter = cfg["parameter"]
    threshold = cfg["default_threshold"]
    condition = cfg["condition"]
    
    nasa_data = get_nasa_power_data(lat, lon, historical_start, historical_end, [parameter])
    
    if not nasa_data:
        raise HTTPException(status_code=500, detail="Failed to fetch NASA data")
    
    param_data = nasa_data["properties"]["parameter"][parameter]
    
    # Filter to same day-of-year range across all years
    start_doy = start_dt.timetuple().tm_yday
    end_doy = end_dt.timetuple().tm_yday
    
    multi_day_events = []
    years_analyzed = set()
    
    for date_str, value in param_data.items():
        try:
            dt_obj = datetime.strptime(date_str, "%Y%m%d")
            doy = dt_obj.timetuple().tm_yday
            
            if start_doy <= doy <= end_doy:
                years_analyzed.add(dt_obj.year)
                if value not in (-999, None):
                    meets_condition = (value > threshold) if condition == "above" else (value < threshold)
                    multi_day_events.append({
                        "year": dt_obj.year,
                        "date": date_str,
                        "value": value,
                        "exceeds_threshold": meets_condition
                    })
        except:
            continue
    
    # Calculate probability of at least one day meeting condition during the period
    years_with_event = len(set(e["year"] for e in multi_day_events if e["exceeds_threshold"]))
    total_years = len(years_analyzed)
    probability = years_with_event / total_years if total_years > 0 else 0
    
    return {
        "location": {"latitude": lat, "longitude": lon},
        "date_range": {"start": start_date, "end": end_date, "days": (end_dt - start_dt).days + 1},
        "condition_type": condition_type,
        "probability": round(probability, 3),
        "years_analyzed": total_years,
        "years_with_event": years_with_event,
        "summary": f"{'High' if probability > 0.5 else 'Moderate' if probability > 0.3 else 'Low'} risk",
        "events": multi_day_events[:50],  # Limit response size
        "data_source": "NASA POWER Daily API"
    }
@router.get("/seasonal-heatmap", tags=["Visualization Data"])
async def get_seasonal_heatmap(
    lat: float = Query(..., description="Latitude"),
    lon: float = Query(..., description="Longitude"),
    condition_type: str = Query(..., description="Weather condition")
):
    """
    Get probability matrix for all 12 months to create heatmap visualization
    Shows best/worst months for planning
    """
    historical_end = datetime.date.today()
    historical_start = historical_end.replace(year=historical_end.year - 20)
    
    cfg = EXTREME_WEATHER_THRESHOLDS[condition_type]
    parameter = cfg["parameter"]
    threshold = cfg["default_threshold"]
    condition = cfg["condition"]
    
    nasa_data = get_nasa_power_data(lat, lon, historical_start, historical_end, [parameter])
    
    if not nasa_data:
        raise HTTPException(status_code=500, detail="Failed to fetch NASA data")
    
    param_data = nasa_data["properties"]["parameter"][parameter]
    
    # Calculate probability for each month
    monthly_probabilities = {}
    for month in range(1, 13):
        filtered = filter_data_by_month(param_data, month)
        prob = calculate_probability(filtered, threshold, condition)
        monthly_probabilities[month] = round(prob, 3) if prob is not None else 0
    
    # Find best and worst months
    sorted_months = sorted(monthly_probabilities.items(), key=lambda x: x[1])
    best_months = sorted_months[:3]  # Lowest probability
    worst_months = sorted_months[-3:]  # Highest probability
    
    month_names = ["", "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    
    return {
        "location": {"latitude": lat, "longitude": lon},
        "condition_type": condition_type,
        "heatmap_data": monthly_probabilities,
        "best_months": [{"month": m, "name": month_names[m], "probability": p} for m, p in best_months],
        "worst_months": [{"month": m, "name": month_names[m], "probability": p} for m, p in worst_months],
        "recommendation": f"Best time to avoid {condition_type}: {', '.join([month_names[m] for m, _ in best_months])}",
        "data_source": "NASA POWER (20-year analysis)"
    }




@router.post("/extreme-weather/region-probability", tags=["Extreme Weather Probability"])
async def region_probability(req: RegionRequest = Body(...)):
    cfg = EXTREME_WEATHER_THRESHOLDS[req.condition_type]
    parameter, cond, threshold = cfg["parameter"], cfg["condition"], req.custom_threshold or cfg["default_threshold"]

    # Build sampling list
    points: List[Tuple[float, float]] = []
    if req.points:
        points.extend([(p.lat, p.lon) for p in req.points])
    if req.polygon:
        poly = [(c.lat, c.lon) for c in req.polygon]
        sampled = sample_polygon_to_grid(poly, step=0.5)
        if not sampled:  # fallback to polygon centroid
            centroid = tuple(np.mean(np.array(poly), axis=0).tolist())
            sampled = [centroid]
        points.extend(sampled)
    if not points:
        raise HTTPException(status_code=400, detail="Provide points or polygon")

    end_date = datetime.date.today()
    start_date = end_date.replace(year=end_date.year - 20)

    probs, counts, agg_vals = [], [], []
    for lat, lon in points:
        nasa = get_nasa_power_data(lat, lon, start_date, end_date, [parameter])
        if not nasa:
            continue
        try:
            p = nasa["properties"]["parameter"][parameter]
        except KeyError:
            continue
        data = p
        data = filter_by_year_range(data, req.start_year, req.end_year)
        if req.doy:
            data = filter_by_doy(data, req.doy)
        elif req.season:
            data = filter_by_season(data, req.season)
        elif req.month:
            data = filter_data_by_month(data, req.month)
        pr = calculate_probability(data, threshold, cond)
        if pr is not None:
            probs.append(pr)
        vs = [v for v in data.values() if v is not None and v != -999]
        agg_vals.extend(vs)
        counts.append(len(vs))

    if not probs:
        raise HTTPException(status_code=404, detail="No valid samples inside region")

    region_prob = round(float(np.mean(probs)), 3)
    return {
        "region": {"points_used": len(probs), "total_samples": len(points)},
        "condition_type": req.condition_type,
        "parameter": parameter,
        "condition": cond,
        "threshold": threshold,
        "probability": region_prob,
        "region_stats": {
            "mean_point_days": int(np.mean(counts)) if counts else 0,
            "value_summary": summarize_values(agg_vals)
        }
    }

@router.post("/extreme-weather/histogram", tags=["Charts & Distributions"])
async def histogram(req: HistogramRequest):
    end_date = datetime.date.today()
    start_date = end_date.replace(year=end_date.year - 20)

    nasa = get_nasa_power_data(req.lat, req.lon, start_date, end_date, [req.parameter])
    if not nasa:
        raise HTTPException(status_code=500, detail="NASA POWER fetch failed")

    try:
        p = nasa["properties"]["parameter"][req.parameter]
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Parameter {req.parameter} not found")

    data = p
    data = filter_by_year_range(data, req.start_year, req.end_year)
    if req.doy:
        data = filter_by_doy(data, req.doy)
    elif req.season:
        data = filter_by_season(data, req.season)
    elif req.month:
        data = filter_data_by_month(data, req.month)

    values = [v for v in data.values() if v is not None and v != -999]
    hist = make_histogram(values, bins=req.bins)
    return {
        "histogram": hist,
        "summary": summarize_values(values),
        "metadata": {"parameter": req.parameter, "bins": req.bins}
    }

# Optional: keep your existing CSV download endpoint unchanged
