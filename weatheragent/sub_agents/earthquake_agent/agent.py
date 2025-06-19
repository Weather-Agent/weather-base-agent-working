import datetime
import requests
from zoneinfo import ZoneInfo
from typing import Dict, List, Optional, Union, Any
from google.adk.agents import Agent


def get_city_coordinates(city: str) -> Dict[str, Any]:
    """Get latitude and longitude for a city using Open-Meteo Geocoding API.
    
    Args:
        city (str): The name of the city.
        
    Returns:
        Dict[str, Any]: Status and coordinates or error message.
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


def get_earthquake_data(
    min_magnitude: float = 4.0,
    days_back: int = 30,
    limit: int = 50,
    city: Optional[str] = None,
    radius_km: Optional[int] = None,
    latitude: Optional[float] = None,
    longitude: Optional[float] = None
) -> Dict[str, Any]:
    """Get earthquake data from USGS API.
    
    Args:
        min_magnitude (float): Minimum earthquake magnitude to include (default: 4.0)
        days_back (int): Number of days to look back for earthquakes (default: 30)
        limit (int): Maximum number of results to return (default: 50)
        city (Optional[str]): City name to search around (default: None)
        radius_km (Optional[int]): Radius in kilometers to search around a location (default: None)
        latitude (Optional[float]): Specific latitude to search around (default: None)
        longitude (Optional[float]): Specific longitude to search around (default: None)
        
    Returns:
        Dict[str, Any]: Earthquake data or error message
    """
    try:
        # Set up time parameters
        end_time = datetime.datetime.now()
        start_time = end_time - datetime.timedelta(days=days_back)
        
        # Base parameters for USGS API
        params = {
            "format": "geojson",
            "starttime": start_time.strftime("%Y-%m-%d"),
            "endtime": end_time.strftime("%Y-%m-%d"),
            "minmagnitude": min_magnitude,
            "orderby": "time",
            "limit": limit
        }
        
        # Handle location-based search
        if city:
            coords = get_city_coordinates(city)
            if coords["status"] == "error":
                return coords
            
            if radius_km:
                params.update({
                    "latitude": coords["latitude"],
                    "longitude": coords["longitude"],
                    "maxradiuskm": radius_km
                })
        elif all(x is not None for x in [latitude, longitude, radius_km]):
            params.update({
                "latitude": latitude,
                "longitude": longitude,
                "maxradiuskm": radius_km
            })
        
        # Make API request
        response = requests.get("https://earthquake.usgs.gov/fdsnws/event/1/query", params=params)
        response.raise_for_status()
        data = response.json()
        
        # Format the response
        events = []
        for feature in data.get("features", []):
            props = feature["properties"]
            coords = feature["geometry"]["coordinates"]
            event_time = datetime.datetime.fromtimestamp(props["time"] / 1000)
            
            events.append({
                "time": event_time.isoformat(),
                "date": event_time.strftime("%Y-%m-%d"),
                "time_of_day": event_time.strftime("%H:%M:%S"),
                "magnitude": round(props["mag"], 1),
                "place": props["place"],
                "depth_km": round(coords[2], 1),
                "latitude": round(coords[1], 4),
                "longitude": round(coords[0], 4),
                "significance": props.get("sig", 0),
                "alert_level": props.get("alert", "none"),
                "tsunami_warning": "Yes" if props.get("tsunami", 0) == 1 else "No",
                "felt_reports": props.get("felt", 0),
                "status": props.get("status", "unknown"),
                "details_url": props.get("url", "")
            })
        
        result = {
            "status": "success",
            "total_events": len(events),
            "events": events,
            "query_info": {
                "start_date": start_time.strftime("%Y-%m-%d"),
                "end_date": end_time.strftime("%Y-%m-%d"),
                "min_magnitude": min_magnitude,
                "limit": limit
            },
            "metadata": {
                "generated": datetime.datetime.now().isoformat(),
                "api": "USGS Earthquake API",
                "url": data.get("metadata", {}).get("url", "")
            }
        }
        
        # Add location context if available
        if city and coords["status"] == "success":
            result.update({
                "location": {
                    "city": coords["name"],
                    "country": coords["country"],
                    "latitude": coords["latitude"],
                    "longitude": coords["longitude"],
                    "search_radius_km": radius_km
                }
            })
        
        return result
        
    except Exception as e:
        return {
            "status": "error",
            "error_message": f"Error fetching earthquake data: {str(e)}"
        }


def analyze_earthquake_risk(
    location: str,
    days_back: int = 90,
    radius_km: int = 300
) -> Dict[str, Any]:
    """Analyze earthquake risk for a location based on recent activity.
    
    Args:
        location (str): Name of the city or location
        days_back (int): Number of days of historical data to analyze (default: 90)
        radius_km (int): Radius in kilometers to analyze (default: 300)
        
    Returns:
        Dict[str, Any]: Risk assessment and recommendations
    """
    try:
        # Get earthquake data
        data = get_earthquake_data(
            city=location,
            days_back=days_back,
            radius_km=radius_km,
            min_magnitude=2.0,
            limit=1000
        )
        
        if data["status"] == "error":
            return data
        
        events = data["events"]
        if not events:
            return {
                "status": "success",
                "location": location,
                "risk_level": "Undetermined",
                "message": "No significant seismic activity recorded in this period."
            }
        
        # Analyze the data
        magnitudes = [event["magnitude"] for event in events]
        max_magnitude = max(magnitudes)
        significant_events = len([m for m in magnitudes if m >= 4.0])
        recent_events = len([e for e in events if 
            (datetime.datetime.now() - datetime.datetime.fromisoformat(e["time"])).days <= 30])
        
        # Determine risk level
        risk_level = "Low"
        if max_magnitude >= 6.0 or significant_events >= 5:
            risk_level = "High"
        elif max_magnitude >= 4.5 or significant_events >= 3:
            risk_level = "Moderate"
        
        # Generate recommendations
        recommendations = _generate_safety_recommendations(risk_level, max_magnitude)
        
        return {
            "status": "success",
            "location": location,
            "risk_level": risk_level,
            "analysis": {
                "period_days": days_back,
                "radius_km": radius_km,
                "total_events": len(events),
                "significant_events": significant_events,
                "recent_events_30d": recent_events,
                "max_magnitude": max_magnitude,
                "average_magnitude": round(sum(magnitudes) / len(magnitudes), 1)
            },
            "recommendations": recommendations,
            "generated_at": datetime.datetime.now().isoformat()
        }
        
    except Exception as e:
        return {
            "status": "error",
            "error_message": f"Error analyzing earthquake risk: {str(e)}"
        }


def _generate_safety_recommendations(risk_level: str, max_magnitude: float) -> List[str]:
    """Generate safety recommendations based on risk level.
    
    Args:
        risk_level (str): Assessed risk level
        max_magnitude (float): Maximum recorded magnitude
        
    Returns:
        List[str]: List of safety recommendations
    """
    recommendations = []
    
    if risk_level == "High":
        recommendations.extend([
            "IMMEDIATE ACTION REQUIRED: Review and update earthquake emergency plans",
            "Secure heavy furniture and objects to walls",
            "Prepare emergency supplies including water, food, and first-aid kit",
            "Identify safe spots in each room (under sturdy tables, against interior walls)",
            "Keep important documents in an easily accessible, waterproof container",
            "Learn how to shut off gas, water, and electricity",
            f"Area has experienced magnitude {max_magnitude} earthquake - maintain high preparedness"
        ])
    elif risk_level == "Moderate":
        recommendations.extend([
            "Review earthquake preparedness guidelines",
            "Check and secure potential hazards in your home",
            "Create or update emergency contact list",
            "Stock basic emergency supplies",
            "Practice earthquake safety drills with family",
            f"Be prepared for earthquakes up to magnitude {max_magnitude}"
        ])
    else:
        recommendations.extend([
            "Maintain basic earthquake awareness",
            "Keep emergency contact information updated",
            "Be aware of safe spots in buildings",
            "Consider basic emergency supplies",
            "Stay informed about local seismic activity"
        ])
    
    return recommendations


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


# Create the earthquake agent with tools
earthquake_agent = Agent(
    name="earthquake_agent",
    model="gemini-2.5-flash-lite-preview-06-17",
    description=(
        "Advanced earthquake monitoring and analysis agent that provides comprehensive seismic risk assessment "
        "and real-time earthquake monitoring using the USGS Earthquake API."
    ),
    instruction=(
        "You are a specialized earthquake monitoring agent that helps assess seismic risks and provide "
        "earthquake information and safety recommendations. You use real-time data from the USGS "
        "Earthquake API to deliver accurate and timely earthquake-related information for any location "
        "worldwide. Always prioritize safety and provide actionable recommendations."
        "The user is stiing in kolkata, India. "
    ),
    tools=[
        get_earthquake_data,
        analyze_earthquake_risk,
        get_city_coordinates,
        get_current_time
    ]
)