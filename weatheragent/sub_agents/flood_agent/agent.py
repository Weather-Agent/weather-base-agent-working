import datetime
import requests
from zoneinfo import ZoneInfo
from typing import Dict, List, Optional, Union
from google.adk.agents import Agent


def get_city_coordinates(city: str) -> dict:
    """Get latitude and longitude for a city using Open-Meteo Geocoding API.
    
    Args:
        city (str): The name of the city.
        
    Returns:
        dict: status and coordinates or error message.
    """
    try:
        geocoding_url = "https://geocoding-api.open-meteo.com/v1/search"
        geocoding_params = {"name": city, "count": 1}
        response = requests.get(geocoding_url, params=geocoding_params)
        response.raise_for_status()
        data = response.json()
        
        if data.get("results"):
            result = data["results"][0]
            return {
                "status": "success",
                "latitude": result["latitude"],
                "longitude": result["longitude"],
                "name": result["name"],
                "country": result.get("country", ""),
                "timezone": result.get("timezone", "auto")
            }
        else:
            return {
                "status": "error",
                "error_message": f"City '{city}' not found."
            }
    except Exception as e:
        return {
            "status": "error",
            "error_message": f"Error finding coordinates for '{city}': {str(e)}"
        }


def get_flood_forecast(city: str, forecast_days: int = 7, include_ensemble: bool = True) -> dict:
    """Get comprehensive flood forecast for a city or region.
    
    Args:
        city (str): The name of the city or region.
        forecast_days (int): Number of days to forecast (1-35, default: 7).
        include_ensemble (bool): Include ensemble model predictions (default: True).
        
    Returns:
        dict: status and flood forecast data or error message.
    """
    coords = get_city_coordinates(city)
    if coords["status"] == "error":
        return coords
    
    try:
        url = "https://flood-api.open-meteo.com/v1/flood"
        
        # Comprehensive parameters for flood monitoring
        params = {
            "latitude": coords["latitude"],
            "longitude": coords["longitude"],
            "daily": "river_discharge,river_discharge_mean,river_discharge_median,river_discharge_max,"
                     "river_discharge_min,river_discharge_p25,river_discharge_p75",
            "ensemble": str(include_ensemble).lower(),
            "forecast_days": min(forecast_days, 35),  # API limit
            "timezone": "auto"
        }
        
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        
        if "daily" not in data:
            return {
                "status": "error",
                "error_message": f"No flood discharge data available for '{city}'. This location may not be near any monitored water bodies."
            }
        
        # Process daily discharge data
        daily_data = data["daily"]
        forecast_data = []
        
        for i, date in enumerate(daily_data["time"]):
            day_data = {
                "date": date,
                "river_discharge": daily_data.get("river_discharge", [None] * len(daily_data["time"]))[i],
                "discharge_mean": daily_data.get("river_discharge_mean", [None] * len(daily_data["time"]))[i],
                "discharge_median": daily_data.get("river_discharge_median", [None] * len(daily_data["time"]))[i],
                "discharge_max": daily_data.get("river_discharge_max", [None] * len(daily_data["time"]))[i],
                "discharge_min": daily_data.get("river_discharge_min", [None] * len(daily_data["time"]))[i],
                "discharge_p25": daily_data.get("river_discharge_p25", [None] * len(daily_data["time"]))[i],
                "discharge_p75": daily_data.get("river_discharge_p75", [None] * len(daily_data["time"]))[i]
            }
            
            # Add flood risk assessment
            if day_data["discharge_max"] is not None:
                if day_data["discharge_max"] > 1000:
                    day_data["flood_risk"] = "High"
                elif day_data["discharge_max"] > 500:
                    day_data["flood_risk"] = "Moderate"
                else:
                    day_data["flood_risk"] = "Low"
            else:
                day_data["flood_risk"] = "Unknown"
            
            forecast_data.append(day_data)
        
        return {
            "status": "success",
            "city": coords["name"],
            "country": coords["country"],
            "latitude": coords["latitude"],
            "longitude": coords["longitude"],
            "forecast_days": forecast_days,
            "ensemble_enabled": include_ensemble,
            "flood_forecast": forecast_data,
            "units": data.get("daily_units", {}),
            "generated_at": datetime.datetime.now().isoformat()
        }
        
    except Exception as e:
        return {
            "status": "error",
            "error_message": f"Error getting flood forecast for '{city}': {str(e)}"
        }


def get_flood_risk_assessment(city: str, threshold_discharge: float = 500.0) -> dict:
    """Get flood risk assessment based on river discharge thresholds.
    
    Args:
        city (str): The name of the city or region.
        threshold_discharge (float): Critical discharge threshold in m³/s (default: 500.0).
        
    Returns:
        dict: status and flood risk assessment or error message.
    """
    flood_data = get_flood_forecast(city, forecast_days=7, include_ensemble=True)
    
    if flood_data["status"] == "error":
        return flood_data
    
    try:
        forecast = flood_data["flood_forecast"]
        risk_assessment = {
            "critical_days": [],
            "high_risk_days": [],
            "moderate_risk_days": [],
            "max_discharge_expected": 0,
            "days_above_threshold": 0,
            "overall_risk_level": "Low"
        }
        
        for day in forecast:
            if day["discharge_max"] is not None:
                discharge = day["discharge_max"]
                risk_assessment["max_discharge_expected"] = max(
                    risk_assessment["max_discharge_expected"], discharge
                )
                
                if discharge > threshold_discharge * 2:  # Critical level
                    risk_assessment["critical_days"].append(day["date"])
                elif discharge > threshold_discharge * 1.5:  # High risk
                    risk_assessment["high_risk_days"].append(day["date"])
                elif discharge > threshold_discharge:  # Moderate risk
                    risk_assessment["moderate_risk_days"].append(day["date"])
                
                if discharge > threshold_discharge:
                    risk_assessment["days_above_threshold"] += 1
        
        # Determine overall risk level
        if risk_assessment["critical_days"]:
            risk_assessment["overall_risk_level"] = "Critical"
        elif risk_assessment["high_risk_days"]:
            risk_assessment["overall_risk_level"] = "High"
        elif risk_assessment["moderate_risk_days"]:
            risk_assessment["overall_risk_level"] = "Moderate"
        
        return {
            "status": "success",
            "city": flood_data["city"],
            "country": flood_data["country"],
            "threshold_discharge": threshold_discharge,
            "assessment_period": f"{forecast[0]['date']} to {forecast[-1]['date']}",
            "risk_assessment": risk_assessment,
            "recommendations": _generate_flood_recommendations(risk_assessment),
            "generated_at": datetime.datetime.now().isoformat()
        }
        
    except Exception as e:
        return {
            "status": "error",
            "error_message": f"Error assessing flood risk for '{city}': {str(e)}"
        }


def get_historical_flood_data(city: str, start_date: str, end_date: str) -> dict:
    """Get historical flood and river discharge data.
    
    Args:
        city (str): The name of the city or region.
        start_date (str): Start date in YYYY-MM-DD format.
        end_date (str): End date in YYYY-MM-DD format.
        
    Returns:
        dict: status and historical flood data or error message.
    """
    coords = get_city_coordinates(city)
    if coords["status"] == "error":
        return coords
    
    try:
        # Note: Historical flood data might use archive API
        url = "https://archive-api.open-meteo.com/v1/archive"
        
        params = {
            "latitude": coords["latitude"],
            "longitude": coords["longitude"],
            "start_date": start_date,
            "end_date": end_date,
            "daily": "precipitation_sum,temperature_2m_max,temperature_2m_min",
            "timezone": "auto"
        }
        
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        
        if "daily" not in data:
            return {
                "status": "error",
                "error_message": f"No historical data available for '{city}' in the specified period."
            }
        
        # Process historical data
        daily_data = data["daily"]
        historical_records = []
        
        for i, date in enumerate(daily_data["time"]):
            day_data = {
                "date": date,
                "precipitation": daily_data.get("precipitation_sum", [None] * len(daily_data["time"]))[i],
                "max_temperature": daily_data.get("temperature_2m_max", [None] * len(daily_data["time"]))[i],
                "min_temperature": daily_data.get("temperature_2m_min", [None] * len(daily_data["time"]))[i]
            }
            
            # Add flood risk indicators based on precipitation
            if day_data["precipitation"] is not None:
                if day_data["precipitation"] > 100:
                    day_data["flood_risk_indicator"] = "Very High"
                elif day_data["precipitation"] > 50:
                    day_data["flood_risk_indicator"] = "High"
                elif day_data["precipitation"] > 25:
                    day_data["flood_risk_indicator"] = "Moderate"
                else:
                    day_data["flood_risk_indicator"] = "Low"
            else:
                day_data["flood_risk_indicator"] = "Unknown"
            
            historical_records.append(day_data)
        
        return {
            "status": "success",
            "city": coords["name"],
            "country": coords["country"],
            "period": f"{start_date} to {end_date}",
            "historical_data": historical_records,
            "units": data.get("daily_units", {}),
            "data_source": "Open-Meteo Archive API",
            "generated_at": datetime.datetime.now().isoformat()
        }
        
    except Exception as e:
        return {
            "status": "error",
            "error_message": f"Error getting historical flood data for '{city}': {str(e)}"
        }


def get_flood_alert_system(city: str, alert_threshold: float = 750.0) -> dict:
    """Get flood alert system with early warning capabilities.
    
    Args:
        city (str): The name of the city or region.
        alert_threshold (float): Discharge threshold for alerts in m³/s (default: 750.0).
        
    Returns:
        dict: status and flood alert information or error message.
    """
    flood_data = get_flood_forecast(city, forecast_days=5, include_ensemble=True)
    
    if flood_data["status"] == "error":
        return flood_data
    
    try:
        forecast = flood_data["flood_forecast"]
        alerts = []
        
        for day in forecast:
            if day["discharge_max"] is not None and day["discharge_max"] > alert_threshold:
                alert_level = "WARNING"
                if day["discharge_max"] > alert_threshold * 1.5:
                    alert_level = "CRITICAL"
                
                alerts.append({
                    "date": day["date"],
                    "alert_level": alert_level,
                    "expected_discharge": day["discharge_max"],
                    "threshold_exceeded_by": day["discharge_max"] - alert_threshold,
                    "confidence": "High" if day["discharge_p75"] > alert_threshold else "Moderate"
                })
        
        return {
            "status": "success",
            "city": flood_data["city"],
            "country": flood_data["country"],
            "alert_threshold": alert_threshold,
            "active_alerts": len(alerts),
            "alerts": alerts,
            "next_update": (datetime.datetime.now() + datetime.timedelta(hours=6)).isoformat(),
            "emergency_contacts": _get_emergency_contacts(),
            "generated_at": datetime.datetime.now().isoformat()
        }
        
    except Exception as e:
        return {
            "status": "error",
            "error_message": f"Error generating flood alerts for '{city}': {str(e)}"
        }


def analyze_flood_patterns(city: str, analysis_days: int = 14) -> dict:
    """Analyze flood patterns and trends for better preparedness.
    
    Args:
        city (str): The name of the city or region.
        analysis_days (int): Number of days to analyze (default: 14).
        
    Returns:
        dict: status and flood pattern analysis or error message.
    """
    flood_data = get_flood_forecast(city, forecast_days=analysis_days, include_ensemble=True)
    
    if flood_data["status"] == "error":
        return flood_data
    
    try:
        forecast = flood_data["flood_forecast"]
        
        # Extract discharge values for analysis
        discharge_values = [day["discharge_max"] for day in forecast if day["discharge_max"] is not None]
        
        if not discharge_values:
            return {
                "status": "error",
                "error_message": f"Insufficient discharge data for pattern analysis in '{city}'."
            }
        
        # Calculate statistics
        avg_discharge = sum(discharge_values) / len(discharge_values)
        max_discharge = max(discharge_values)
        min_discharge = min(discharge_values)
        
        # Trend analysis (simple linear trend)
        trend = "stable"
        if len(discharge_values) >= 7:
            first_half = sum(discharge_values[:len(discharge_values)//2]) / (len(discharge_values)//2)
            second_half = sum(discharge_values[len(discharge_values)//2:]) / (len(discharge_values) - len(discharge_values)//2)
            
            if second_half > first_half * 1.1:
                trend = "increasing"
            elif second_half < first_half * 0.9:
                trend = "decreasing"
        
        return {
            "status": "success",
            "city": flood_data["city"],
            "country": flood_data["country"],
            "analysis_period": f"{forecast[0]['date']} to {forecast[-1]['date']}",
            "pattern_analysis": {
                "average_discharge": round(avg_discharge, 2),
                "maximum_discharge": max_discharge,
                "minimum_discharge": min_discharge,
                "discharge_range": round(max_discharge - min_discharge, 2),
                "trend": trend,
                "variability": "high" if (max_discharge - min_discharge) > avg_discharge else "moderate",
                "risk_days": len([d for d in discharge_values if d > 500]),
                "critical_days": len([d for d in discharge_values if d > 1000])
            },
            "recommendations": _generate_pattern_recommendations(trend, avg_discharge, max_discharge),
            "generated_at": datetime.datetime.now().isoformat()
        }
        
    except Exception as e:
        return {
            "status": "error",
            "error_message": f"Error analyzing flood patterns for '{city}': {str(e)}"
        }


def get_current_time(city: str) -> dict:
    """Returns the current time in a specified city.

    Args:
        city (str): The name of the city for which to retrieve the current time.

    Returns:
        dict: status and result or error msg.
    """
    coords = get_city_coordinates(city)
    if coords["status"] == "error":
        return coords
    
    try:
        # Use the timezone from geocoding result or fallback to auto
        tz_identifier = coords.get("timezone", "auto")
        
        if tz_identifier == "auto":
            # Fallback for common cities
            city_lower = city.lower()
            timezone_map = {
                "new york": "America/New_York",
                "london": "Europe/London",
                "paris": "Europe/Paris",
                "tokyo": "Asia/Tokyo",
                "sydney": "Australia/Sydney",
                "los angeles": "America/Los_Angeles",
                "chicago": "America/Chicago",
                "berlin": "Europe/Berlin",
                "mumbai": "Asia/Kolkata",
                "beijing": "Asia/Shanghai"
            }
            tz_identifier = timezone_map.get(city_lower, "UTC")
        
        tz = ZoneInfo(tz_identifier)
        now = datetime.datetime.now(tz)
        report = (
            f'The current time in {coords["name"]} is {now.strftime("%Y-%m-%d %H:%M:%S %Z%z")}'
        )
        return {"status": "success", "report": report}
    except Exception as e:
        return {
            "status": "error",
            "error_message": f"Error getting time for '{city}': {str(e)}"
        }


def _generate_flood_recommendations(risk_assessment: dict) -> List[str]:
    """Generate flood preparedness recommendations based on risk assessment."""
    recommendations = []
    
    if risk_assessment["overall_risk_level"] == "Critical":
        recommendations.extend([
            "IMMEDIATE ACTION REQUIRED: Evacuate low-lying areas immediately",
            "Contact local emergency services and follow evacuation procedures",
            "Avoid travel near water bodies and flood-prone areas",
            "Monitor emergency broadcasts and official communications continuously"
        ])
    elif risk_assessment["overall_risk_level"] == "High":
        recommendations.extend([
            "Prepare evacuation plan and emergency supplies",
            "Move valuable items to higher ground",
            "Avoid unnecessary travel in flood-prone areas",
            "Stay updated with local weather and flood warnings"
        ])
    elif risk_assessment["overall_risk_level"] == "Moderate":
        recommendations.extend([
            "Review flood preparedness plan",
            "Check drainage systems around property",
            "Keep emergency supplies ready",
            "Monitor weather forecasts regularly"
        ])
    else:
        recommendations.extend([
            "Maintain general flood preparedness awareness",
            "Ensure emergency contact information is updated",
            "Review flood insurance coverage"
        ])
    
    return recommendations


def _generate_pattern_recommendations(trend: str, avg_discharge: float, max_discharge: float) -> List[str]:
    """Generate recommendations based on flood pattern analysis."""
    recommendations = []
    
    if trend == "increasing":
        recommendations.append("Warning: Discharge levels are trending upward - increase monitoring")
    elif trend == "decreasing":
        recommendations.append("Good news: Discharge levels are trending downward")
    
    if max_discharge > 1000:
        recommendations.append("Critical discharge levels expected - prepare for potential flooding")
    elif max_discharge > 500:
        recommendations.append("Elevated discharge levels - monitor flood warnings closely")
    
    if avg_discharge > 300:
        recommendations.append("Above-average discharge levels - maintain flood preparedness")
    
    return recommendations


def _get_emergency_contacts() -> dict:
    """Get standard emergency contact information."""
    return {
        "emergency_services": "Emergency services number for your region",
        "flood_hotline": "Local flood information hotline",
        "evacuation_centers": "Contact local authorities for evacuation center information",
        "weather_service": "National weather service flood warnings"
    }


# Create the flood agent with all tools
flood_agent = Agent(
    name="flood_agent",
    model="gemini-2.5-flash-lite-preview-06-17",
    description=(
        "Advanced flood monitoring and forecasting agent that provides comprehensive flood risk assessment, "
        "river discharge monitoring, early warning systems, and flood pattern analysis using Open-Meteo flood APIs."
    ),
    instruction=(
        "You are a specialized flood monitoring agent that helps assess flood risks, analyze river discharge patterns, "
        "provide early warning alerts, and offer flood preparedness recommendations. You use real-time data from "
        "Open-Meteo flood APIs to deliver accurate and timely flood-related information for any location worldwide. "
        "Always prioritize safety and provide actionable recommendations based on current flood risks."
    ),
    tools=[
        get_flood_forecast,
        get_flood_risk_assessment,
        get_historical_flood_data,
        get_flood_alert_system,
        analyze_flood_patterns,
        get_city_coordinates,
        get_current_time
    ],
)