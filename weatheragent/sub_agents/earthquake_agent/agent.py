import datetime
import requests
from zoneinfo import ZoneInfo
from typing import Dict, List, Optional, Union, Any
import re
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


def smart_earthquake_search(
    query: str,
    location: Optional[str] = None,
    days: Optional[int] = None,
    magnitude_threshold: Optional[float] = None,
    radius_km: Optional[int] = None
) -> Dict[str, Any]:
    """Intelligent earthquake search that parses natural language queries.
    
    This function can handle queries like:
    - "earthquakes in Japan last 14 days"
    - "magnitude 5+ earthquakes near Tokyo in the past week"
    - "recent seismic activity in California"
    - "earthquakes around Mumbai within 200km last month"
    
    Args:
        query (str): Natural language query about earthquakes
        location (Optional[str]): Specific location to search (overrides query parsing)
        days (Optional[int]): Number of days to look back (overrides query parsing)
        magnitude_threshold (Optional[float]): Minimum magnitude (overrides query parsing)
        radius_km (Optional[int]): Search radius in km (overrides query parsing)
        
    Returns:
        Dict[str, Any]: Earthquake data with intelligent parameter extraction
    """
    try:
        # Parse the query for parameters if not provided
        if not location:
            location = _extract_location_from_query(query)
        
        if not days:
            days = _extract_time_period_from_query(query)
        
        if not magnitude_threshold:
            magnitude_threshold = _extract_magnitude_from_query(query)
        
        if not radius_km:
            radius_km = _extract_radius_from_query(query)
        
        # Set defaults
        days = days or 30
        magnitude_threshold = magnitude_threshold or 2.5
        radius_km = radius_km or 500  # Default radius for location searches
        
        # Use existing function with parsed parameters
        if location:
            result = get_earthquake_data(
                city=location,
                days_back=days,
                min_magnitude=magnitude_threshold,
                radius_km=radius_km,
                limit=100
            )
        else:
            # Global search without location
            result = get_earthquake_data(
                days_back=days,
                min_magnitude=magnitude_threshold,
                limit=100
            )
        
        if result["status"] == "success":
            # Add query context to result
            result["query_context"] = {
                "original_query": query,
                "parsed_location": location,
                "parsed_days": days,
                "parsed_magnitude": magnitude_threshold,
                "parsed_radius_km": radius_km
            }
        
        return result
        
    except Exception as e:
        return {
            "status": "error",
            "error_message": f"Error processing earthquake query: {str(e)}"
        }


def get_earthquakes_by_country(
    country: str,
    days_back: int = 30,
    min_magnitude: float = 4.0,
    limit: int = 100
) -> Dict[str, Any]:
    """Get earthquake data for a specific country using approximate boundaries.
    
    Args:
        country (str): Name of the country
        days_back (int): Number of days to look back (default: 30)
        min_magnitude (float): Minimum magnitude (default: 4.0)
        limit (int): Maximum results (default: 100)
        
    Returns:
        Dict[str, Any]: Earthquake data for the country
    """
    try:
        # Get country boundaries (approximate)
        boundaries = _get_country_boundaries(country)
        if not boundaries:
            return {
                "status": "error",
                "error_message": f"Could not determine boundaries for country '{country}'"
            }
        
        # Set up time parameters
        end_time = datetime.datetime.now()
        start_time = end_time - datetime.timedelta(days=days_back)
        
        # Use rectangular search with country boundaries
        params = {
            "format": "geojson",
            "starttime": start_time.strftime("%Y-%m-%d"),
            "endtime": end_time.strftime("%Y-%m-%d"),
            "minmagnitude": min_magnitude,
            "minlatitude": boundaries["min_lat"],
            "maxlatitude": boundaries["max_lat"],
            "minlongitude": boundaries["min_lon"],
            "maxlongitude": boundaries["max_lon"],
            "orderby": "time",
            "limit": limit
        }
        
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
        
        return {
            "status": "success",
            "total_events": len(events),
            "events": events,
            "country": country,
            "query_info": {
                "start_date": start_time.strftime("%Y-%m-%d"),
                "end_date": end_time.strftime("%Y-%m-%d"),
                "min_magnitude": min_magnitude,
                "limit": limit,
                "search_boundaries": boundaries
            },
            "metadata": {
                "generated": datetime.datetime.now().isoformat(),
                "api": "USGS Earthquake API",
                "url": data.get("metadata", {}).get("url", "")
            }
        }
        
    except Exception as e:
        return {
            "status": "error",
            "error_message": f"Error fetching earthquake data for {country}: {str(e)}"
        }


def get_earthquakes_by_region(
    region: str,
    days_back: int = 30,
    min_magnitude: float = 4.0,
    limit: int = 100
) -> Dict[str, Any]:
    """Get earthquake data for a specific geographic region.
    
    Args:
        region (str): Name of the region (e.g., "Pacific Ring of Fire", "Mediterranean", "Himalayan region")
        days_back (int): Number of days to look back (default: 30)
        min_magnitude (float): Minimum magnitude (default: 4.0)
        limit (int): Maximum results (default: 100)
        
    Returns:
        Dict[str, Any]: Earthquake data for the region
    """
    try:
        # Get region boundaries
        boundaries = _get_region_boundaries(region)
        if not boundaries:
            return {
                "status": "error",
                "error_message": f"Unknown region '{region}'. Try specific countries or cities instead."
            }
        
        # Set up time parameters
        end_time = datetime.datetime.now()
        start_time = end_time - datetime.timedelta(days=days_back)
        
        # Use rectangular search with region boundaries
        params = {
            "format": "geojson",
            "starttime": start_time.strftime("%Y-%m-%d"),
            "endtime": end_time.strftime("%Y-%m-%d"),
            "minmagnitude": min_magnitude,
            "minlatitude": boundaries["min_lat"],
            "maxlatitude": boundaries["max_lat"],
            "minlongitude": boundaries["min_lon"],
            "maxlongitude": boundaries["max_lon"],
            "orderby": "time",
            "limit": limit
        }
        
        # Make API request
        response = requests.get("https://earthquake.usgs.gov/fdsnws/event/1/query", params=params)
        response.raise_for_status()
        data = response.json()
        
        # Format events (same as country function)
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
        
        return {
            "status": "success",
            "total_events": len(events),
            "events": events,
            "region": region,
            "query_info": {
                "start_date": start_time.strftime("%Y-%m-%d"),
                "end_date": end_time.strftime("%Y-%m-%d"),
                "min_magnitude": min_magnitude,
                "limit": limit,
                "search_boundaries": boundaries
            },
            "metadata": {
                "generated": datetime.datetime.now().isoformat(),
                "api": "USGS Earthquake API"
            }
        }
        
    except Exception as e:
        return {
            "status": "error",
            "error_message": f"Error fetching earthquake data for {region}: {str(e)}"
        }


def get_recent_significant_earthquakes(
    magnitude_threshold: float = 5.0,
    days_back: int = 7,
    limit: int = 20
) -> Dict[str, Any]:
    """Get recent significant earthquakes worldwide.
    
    Args:
        magnitude_threshold (float): Minimum magnitude (default: 5.0)
        days_back (int): Days to look back (default: 7)
        limit (int): Maximum results (default: 20)
        
    Returns:
        Dict[str, Any]: Recent significant earthquake data
    """
    try:
        return get_earthquake_data(
            min_magnitude=magnitude_threshold,
            days_back=days_back,
            limit=limit
        )
    except Exception as e:
        return {
            "status": "error",
            "error_message": f"Error fetching recent significant earthquakes: {str(e)}"
        }


# Helper functions for query parsing

def _extract_location_from_query(query: str) -> Optional[str]:
    """Extract location from natural language query."""
    query_lower = query.lower()
    
    # Common location patterns
    location_patterns = [
        r'in\s+([a-zA-Z\s]+?)(?:\s+(?:last|past|during|within|over))',
        r'near\s+([a-zA-Z\s]+?)(?:\s+(?:last|past|during|within|over))',
        r'around\s+([a-zA-Z\s]+?)(?:\s+(?:last|past|during|within|over))',
        r'(?:earthquakes?|seismic|activity)\s+(?:in|near|around)\s+([a-zA-Z\s]+?)(?:\s|$)',
    ]
    
    for pattern in location_patterns:
        match = re.search(pattern, query_lower)
        if match:
            location = match.group(1).strip()
            # Clean up common words
            location = re.sub(r'\b(the|area|region)\b', '', location).strip()
            return location if location else None
    
    return None


def _extract_time_period_from_query(query: str) -> Optional[int]:
    """Extract time period from natural language query."""
    query_lower = query.lower()
    
    # Time period patterns
    time_patterns = [
        (r'last\s+(\d+)\s+days?', 1),
        (r'past\s+(\d+)\s+days?', 1),
        (r'(\d+)\s+days?', 1),
        (r'last\s+week', 7),
        (r'past\s+week', 7),
        (r'this\s+week', 7),
        (r'last\s+month', 30),
        (r'past\s+month', 30),
        (r'this\s+month', 30),
        (r'last\s+(\d+)\s+weeks?', 7),
        (r'past\s+(\d+)\s+weeks?', 7),
        (r'(\d+)\s+weeks?', 7),
        (r'today', 1),
        (r'yesterday', 2),
        (r'recent', 14)
    ]
    
    for pattern, multiplier in time_patterns:
        match = re.search(pattern, query_lower)
        if match:
            if multiplier == 1:  # Days
                return int(match.group(1))
            elif multiplier == 7:  # Weeks
                if match.groups():
                    return int(match.group(1)) * 7
                else:
                    return 7
            else:  # Fixed values
                return multiplier
    
    return None


def _extract_magnitude_from_query(query: str) -> Optional[float]:
    """Extract magnitude threshold from natural language query."""
    query_lower = query.lower()
    
    magnitude_patterns = [
        r'magnitude\s+(\d+(?:\.\d+)?)\+',
        r'magnitude\s+(\d+(?:\.\d+)?)\s+(?:or\s+)?(?:above|higher)',
        r'mag\s+(\d+(?:\.\d+)?)\+',
        r'(\d+(?:\.\d+)?)\+\s+magnitude',
        r'above\s+magnitude\s+(\d+(?:\.\d+)?)',
        r'stronger\s+than\s+(\d+(?:\.\d+)?)',
        r'significant', # Default to 4.5 for "significant"
        r'major', # Default to 6.0 for "major"
        r'minor', # Default to 2.0 for "minor"
    ]
    
    for pattern in magnitude_patterns:
        match = re.search(pattern, query_lower)
        if match:
            if pattern in [r'significant']:
                return 4.5
            elif pattern in [r'major']:
                return 6.0
            elif pattern in [r'minor']:
                return 2.0
            else:
                return float(match.group(1))
    
    return None


def _extract_radius_from_query(query: str) -> Optional[int]:
    """Extract search radius from natural language query."""
    query_lower = query.lower()
    
    radius_patterns = [
        r'within\s+(\d+)\s*km',
        r'(\d+)\s*km\s+radius',
        r'(\d+)\s+kilometers?',
        r'within\s+(\d+)\s+miles?',
    ]
    
    for pattern in radius_patterns:
        match = re.search(pattern, query_lower)
        if match:
            value = int(match.group(1))
            # Convert miles to km if needed
            if 'mile' in pattern:
                value = int(value * 1.60934)
            return value
    
    return None


def _get_country_boundaries(country: str) -> Optional[Dict[str, float]]:
    """Get approximate boundaries for common countries."""
    country_boundaries = {
        "japan": {"min_lat": 24.0, "max_lat": 46.0, "min_lon": 129.0, "max_lon": 146.0},
        "india": {"min_lat": 6.0, "max_lat": 37.0, "min_lon": 68.0, "max_lon": 98.0},
        "china": {"min_lat": 18.0, "max_lat": 54.0, "min_lon": 73.0, "max_lon": 135.0},
        "indonesia": {"min_lat": -11.0, "max_lat": 6.0, "min_lon": 95.0, "max_lon": 141.0},
        "usa": {"min_lat": 24.0, "max_lat": 72.0, "min_lon": -180.0, "max_lon": -66.0},
        "united states": {"min_lat": 24.0, "max_lat": 72.0, "min_lon": -180.0, "max_lon": -66.0},
        "california": {"min_lat": 32.5, "max_lat": 42.0, "min_lon": -124.5, "max_lon": -114.0},
        "turkey": {"min_lat": 35.8, "max_lat": 42.1, "min_lon": 25.7, "max_lon": 44.8},
        "chile": {"min_lat": -56.0, "max_lat": -17.5, "min_lon": -75.6, "max_lon": -66.4},
        "mexico": {"min_lat": 14.5, "max_lat": 32.7, "min_lon": -118.4, "max_lon": -86.7},
        "italy": {"min_lat": 36.6, "max_lat": 47.1, "min_lon": 6.6, "max_lon": 18.5},
        "greece": {"min_lat": 34.8, "max_lat": 41.7, "min_lon": 19.4, "max_lon": 29.6},
        "iran": {"min_lat": 25.1, "max_lat": 39.8, "min_lon": 44.0, "max_lon": 63.3},
        "philippines": {"min_lat": 4.6, "max_lat": 21.1, "min_lon": 116.9, "max_lon": 126.6},
        "new zealand": {"min_lat": -47.3, "max_lat": -34.4, "min_lon": 166.4, "max_lon": 178.6},
        "alaska": {"min_lat": 54.0, "max_lat": 72.0, "min_lon": -180.0, "max_lon": -129.0},
    }
    
    return country_boundaries.get(country.lower())


def _get_region_boundaries(region: str) -> Optional[Dict[str, float]]:
    """Get approximate boundaries for major seismic regions."""
    region_boundaries = {
        "pacific ring of fire": {"min_lat": -60.0, "max_lat": 70.0, "min_lon": -180.0, "max_lon": 180.0},
        "ring of fire": {"min_lat": -60.0, "max_lat": 70.0, "min_lon": -180.0, "max_lon": 180.0},
        "mediterranean": {"min_lat": 30.0, "max_lat": 48.0, "min_lon": -10.0, "max_lon": 42.0},
        "himalayan region": {"min_lat": 25.0, "max_lat": 40.0, "min_lon": 70.0, "max_lon": 105.0},
        "himalaya": {"min_lat": 25.0, "max_lat": 40.0, "min_lon": 70.0, "max_lon": 105.0},
        "middle east": {"min_lat": 12.0, "max_lat": 42.0, "min_lon": 25.0, "max_lon": 65.0},
        "caribbean": {"min_lat": 10.0, "max_lat": 28.0, "min_lon": -90.0, "max_lon": -58.0},
        "pacific": {"min_lat": -60.0, "max_lat": 70.0, "min_lon": 120.0, "max_lon": -70.0},
        "atlantic": {"min_lat": -60.0, "max_lat": 70.0, "min_lon": -80.0, "max_lon": 20.0},
    }
    
    return region_boundaries.get(region.lower())


# Create the earthquake agent with tools
earthquake_agent = Agent(
    name="earthquake_agent",
    model="gemini-2.5-flash-lite-preview-06-17",
    description=(
        "Advanced earthquake monitoring and analysis agent that provides comprehensive seismic risk assessment "
        "and real-time earthquake monitoring using the USGS Earthquake API with intelligent natural language processing."
    ),
    instruction=(
        "You are a specialized earthquake monitoring agent that helps assess seismic risks and provide "
        "earthquake information and safety recommendations. You use real-time data from the USGS "
        "Earthquake API to deliver accurate and timely earthquake-related information for any location "
        "worldwide. Always prioritize safety and provide actionable recommendations. "
        "You can understand natural language queries and automatically extract location, time periods, "
        "magnitude thresholds, and search radii from user requests. The user is sitting in Kolkata, India. "
        "Use smart_earthquake_search for complex natural language queries that need parameter extraction."
    ),
    tools=[
        smart_earthquake_search,
        get_earthquake_data,
        get_earthquakes_by_country,
        get_earthquakes_by_region,
        get_recent_significant_earthquakes,
        analyze_earthquake_risk,
        get_city_coordinates,
        get_current_time
    ]
)