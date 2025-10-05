# services/giovanni_data.py
"""
Optional: Giovanni web service integration for advanced visualizations
Giovanni provides pre-rendered time-series and maps
"""

def get_giovanni_visualization_url(lat, lon, parameter, start_date, end_date):
    """
    Generate Giovanni URL for interactive time-series plot
    """
    base_url = "https://giovanni.gsfc.nasa.gov/giovanni/"
    
    # Giovanni parameter mappings
    giovanni_params = {
        "T2M": "MAT1NXSLV_5_2_0_T2M",
        "PRECTOTCORR": "GPM_3IMERGM_06_precipitation"
    }
    
    giovanni_param = giovanni_params.get(parameter, parameter)
    
    # Construct Giovanni session URL (users can click to explore)
    return {
        "giovanni_url": f"{base_url}#service=TmAvMp&starttime={start_date}&endtime={end_date}&data={giovanni_param}&bbox={lon},{lat},{lon+1},{lat+1}",
        "description": "Click to open interactive NASA Giovanni visualization"
    }
