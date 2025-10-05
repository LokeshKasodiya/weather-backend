# models.py
from typing import List, Optional, Literal, Annotated
from pydantic import BaseModel, Field

class Coordinate(BaseModel):
    lat: float = Field(..., ge=-90, le=90, description="Latitude")
    lon: float = Field(..., ge=-180, le=180, description="Longitude")

class RegionRequest(BaseModel):
    # Either points or polygon; polygon must have >= 3 coordinates
    points: Optional[List[Coordinate]] = Field(
        default=None, description="Optional array of points (lat/lon)"
    )
    polygon: Optional[Annotated[List[Coordinate], Field(min_length=3)]] = Field(
        default=None, description="Optional polygon (>=3 coordinates)"
    )

    # Time selectors (choose one of month/season/doy)
    month: Optional[int] = Field(None, ge=1, le=12, description="Month filter 1-12")
    season: Optional[Literal["djf","mam","jja","son"]] = Field(
        None, description="Season code: djf/mam/jja/son"
    )
    doy: Optional[int] = Field(None, ge=1, le=366, description="Day of year 1-366")

    # Multi-year window (optional)
    start_year: Optional[int] = Field(None, description="Earliest year to include")
    end_year: Optional[int] = Field(None, description="Latest year to include")

    # Extreme condition selection and optional threshold override
    condition_type: Literal[
        "heatwave","cold_wave","heavy_rain","high_wind","heavy_snow","high_cloud_cover"
    ]
    custom_threshold: Optional[float] = Field(None, description="Override threshold")

class HistogramRequest(BaseModel):
    lat: float = Field(..., ge=-90, le=90)
    lon: float = Field(..., ge=-180, le=180)
    parameter: str = Field(..., description="NASA POWER parameter, e.g., T2M_MAX")
    month: Optional[int] = Field(None, ge=1, le=12)
    season: Optional[Literal["djf","mam","jja","son"]] = None
    doy: Optional[int] = Field(None, ge=1, le=366)
    start_year: Optional[int] = None
    end_year: Optional[int] = None
    bins: int = Field(24, ge=4, le=200, description="Histogram bin count")
