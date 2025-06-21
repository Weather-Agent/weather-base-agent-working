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
    """Get earthquake data for a specific country using dynamic geocoding.
    
    Args:
        country (str): Name of the country
        days_back (int): Number of days to look back (default: 30)
        min_magnitude (float): Minimum magnitude (default: 4.0)
        limit (int): Maximum results (default: 100)
        
    Returns:
        Dict[str, Any]: Earthquake data for the country
    """
    try:
        # Use the enhanced location-based search instead of hardcoded boundaries
        return get_earthquakes_by_any_location(
            location=country,
            days_back=days_back,
            min_magnitude=min_magnitude,
            limit=limit
        )
        
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
    """Get earthquake data for a specific geographic region using dynamic geocoding.
    
    Args:
        region (str): Name of the region (e.g., "Pacific Ring of Fire", "Mediterranean", "Himalayan region")
        days_back (int): Number of days to look back (default: 30)
        min_magnitude (float): Minimum magnitude (default: 4.0)
        limit (int): Maximum results (default: 100)
        
    Returns:
        Dict[str, Any]: Earthquake data for the region
    """
    try:
        # Try to use dynamic geocoding first
        result = get_earthquakes_by_any_location(
            location=region,
            days_back=days_back,
            min_magnitude=min_magnitude,
            limit=limit
        )
        
        # If dynamic geocoding fails, try hardcoded region boundaries
        if result["status"] == "error":
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
            
            # Format events
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
        
        return result
        
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


def get_enhanced_location_info(location: str, count: int = 5) -> Dict[str, Any]:
    """Get enhanced location information including multiple matches using Open-Meteo Geocoding API.
    
    Args:
        location (str): The name of the location (city, country, region, postal code).
        count (int): Number of results to return (default: 5, max: 100)
        
    Returns:
        Dict[str, Any]: Enhanced location data or error message.
    """
    try:
        geocoding_url = "https://geocoding-api.open-meteo.com/v1/search"
        geocoding_params = {
            "name": location, 
            "count": min(count, 100),  # API limit is 100
            "language": "en"
        }
        response = requests.get(geocoding_url, params=geocoding_params)
        response.raise_for_status()
        data = response.json()
        
        if data.get("results"):
            locations = []
            for result in data["results"]:
                location_info = {
                    "id": result.get("id"),
                    "name": result["name"],
                    "latitude": result["latitude"],
                    "longitude": result["longitude"],
                    "elevation": result.get("elevation", 0),
                    "country": result.get("country", ""),
                    "country_code": result.get("country_code", ""),
                    "timezone": result.get("timezone", "UTC"),
                    "population": result.get("population", 0),
                    "feature_code": result.get("feature_code", ""),
                    "admin1": result.get("admin1", ""),  # State/Province
                    "admin2": result.get("admin2", ""),  # County/District
                    "admin3": result.get("admin3", ""),  # Municipality
                    "admin4": result.get("admin4", ""),  # Neighborhood
                    "postcodes": result.get("postcodes", [])
                }
                locations.append(location_info)
            
            return {
                "status": "success",
                "total_results": len(locations),
                "locations": locations,
                "query": location
            }
        else:
            return {
                "status": "error",
                "error_message": f"Location '{location}' not found."
            }
    except Exception as e:
        return {
            "status": "error",
            "error_message": f"Error finding location info for '{location}': {str(e)}"
        }


def get_dynamic_boundaries(location: str, padding_degrees: float = 1.0) -> Dict[str, Any]:
    """Get dynamic boundaries for any location using geocoding API.
    
    Args:
        location (str): Location name (city, country, region, etc.)
        padding_degrees (float): Degrees to add around the location for search area (default: 1.0)
        
    Returns:
        Dict[str, Any]: Boundary coordinates or error message
    """
    try:
        location_info = get_enhanced_location_info(location, count=1)
        if location_info["status"] == "error":
            return location_info
        
        if not location_info["locations"]:
            return {
                "status": "error",
                "error_message": f"No location data found for '{location}'"
            }
        
        loc = location_info["locations"][0]
        lat = loc["latitude"]
        lon = loc["longitude"]
        
        # Create boundaries with padding
        boundaries = {
            "min_lat": lat - padding_degrees,
            "max_lat": lat + padding_degrees,
            "min_lon": lon - padding_degrees,
            "max_lon": lon + padding_degrees,
            "center_lat": lat,
            "center_lon": lon,
            "location_name": loc["name"],
            "country": loc["country"],
            "feature_code": loc["feature_code"]
        }
        
        # Adjust padding based on feature type
        if loc["feature_code"] in ["PCLI", "PCL"]:  # Country
            boundaries.update({
                "min_lat": lat - 5.0,
                "max_lat": lat + 5.0,
                "min_lon": lon - 5.0,
                "max_lon": lon + 5.0
            })
        elif loc["feature_code"] in ["ADM1"]:  # State/Province
            boundaries.update({
                "min_lat": lat - 2.0,
                "max_lat": lat + 2.0,
                "min_lon": lon - 2.0,
                "max_lon": lon + 2.0
            })
        elif loc["feature_code"] in ["PPL", "PPLA", "PPLC"]:  # Cities
            boundaries.update({
                "min_lat": lat - 0.5,
                "max_lat": lat + 0.5,
                "min_lon": lon - 0.5,
                "max_lon": lon + 0.5
            })
        
        return {
            "status": "success",
            "boundaries": boundaries,
            "location_info": loc
        }
        
    except Exception as e:
        return {
            "status": "error",
            "error_message": f"Error getting boundaries for '{location}': {str(e)}"
        }


def get_earthquakes_by_any_location(
    location: str,
    days_back: int = 30,
    min_magnitude: float = 4.0,
    radius_km: Optional[int] = None,
    limit: int = 100
) -> Dict[str, Any]:
    """Get earthquake data for any location (city, country, region) using dynamic geocoding.
    
    Args:
        location (str): Name of any location (city, country, region, postal code)
        days_back (int): Number of days to look back (default: 30)
        min_magnitude (float): Minimum magnitude (default: 4.0)
        radius_km (Optional[int]): Search radius in km. If None, uses rectangular boundaries
        limit (int): Maximum results (default: 100)
        
    Returns:
        Dict[str, Any]: Earthquake data for the location
    """
    try:
        # Get location information
        location_info = get_enhanced_location_info(location, count=1)
        if location_info["status"] == "error":
            return location_info
        
        if not location_info["locations"]:
            return {
                "status": "error",
                "error_message": f"No location data found for '{location}'"
            }
        
        loc = location_info["locations"][0]
        
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
        
        # Use either radius or rectangular search
        if radius_km:
            # Circular search around the location
            params.update({
                "latitude": loc["latitude"],
                "longitude": loc["longitude"],
                "maxradiuskm": radius_km
            })
            search_type = "circular"
        else:
            # Get dynamic boundaries for rectangular search
            boundary_info = get_dynamic_boundaries(location)
            if boundary_info["status"] == "error":
                return boundary_info
            
            boundaries = boundary_info["boundaries"]
            params.update({
                "minlatitude": boundaries["min_lat"],
                "maxlatitude": boundaries["max_lat"],
                "minlongitude": boundaries["min_lon"],
                "maxlongitude": boundaries["max_lon"]
            })
            search_type = "rectangular"
        
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
            "location": {
                "name": loc["name"],
                "country": loc["country"],
                "latitude": loc["latitude"],
                "longitude": loc["longitude"],
                "elevation": loc["elevation"],
                "timezone": loc["timezone"],
                "population": loc["population"],
                "feature_type": loc["feature_code"]
            },
            "search_info": {
                "search_type": search_type,
                "radius_km": radius_km,
                "start_date": start_time.strftime("%Y-%m-%d"),
                "end_date": end_time.strftime("%Y-%m-%d"),
                "min_magnitude": min_magnitude,
                "limit": limit
            },
            "metadata": {
                "generated": datetime.datetime.now().isoformat(),
                "api": "USGS Earthquake API",
                "geocoding_api": "Open-Meteo Geocoding API",
                "url": data.get("metadata", {}).get("url", "")
            }
        }
        
    except Exception as e:
        return {
            "status": "error",
            "error_message": f"Error fetching earthquake data for '{location}': {str(e)}"
        }


def smart_location_earthquake_query(
    query: str,
    auto_detect_params: bool = True
) -> Dict[str, Any]:
    """Ultra-intelligent earthquake search that can handle any natural language query about any location.
    
    This function can handle complex queries like:
    - "earthquakes in Tokyo last 2 weeks"
    - "magnitude 6+ earthquakes in California last month"
    - "seismic activity around Mumbai within 300km"
    - "recent earthquakes in New Zealand"
    - "earthquakes near postal code 10001"
    - "earthquake activity in Himalayan region"
    
    Args:
        query (str): Natural language query about earthquakes
        auto_detect_params (bool): Whether to auto-detect parameters from query (default: True)
        
    Returns:
        Dict[str, Any]: Earthquake data with comprehensive location and parameter extraction
    """
    try:
        parsed_params = {
            "location": None,
            "days": None,
            "magnitude": None,
            "radius_km": None
        }
        
        if auto_detect_params:
            # Extract all parameters from the query
            parsed_params["location"] = _extract_location_from_query(query)
            parsed_params["days"] = _extract_time_period_from_query(query)
            parsed_params["magnitude"] = _extract_magnitude_from_query(query)
            parsed_params["radius_km"] = _extract_radius_from_query(query)
        
        # Set intelligent defaults
        location = parsed_params["location"]
        days = parsed_params["days"] or 30
        magnitude = parsed_params["magnitude"] or 2.5
        radius_km = parsed_params["radius_km"]
        
        if not location:
            # If no location detected, return global search
            result = get_earthquake_data(
                days_back=days,
                min_magnitude=magnitude,
                limit=100
            )
        else:
            # Use the enhanced location-based search
            result = get_earthquakes_by_any_location(
                location=location,
                days_back=days,
                min_magnitude=magnitude,
                radius_km=radius_km,
                limit=100
            )
        
        if result["status"] == "success":
            # Add query analysis to result
            result["query_analysis"] = {
                "original_query": query,
                "extracted_location": location,
                "extracted_days": days,
                "extracted_magnitude": magnitude,
                "extracted_radius_km": radius_km,
                "search_strategy": "location-based" if location else "global"
            }
        
        return result
        
    except Exception as e:
        return {
            "status": "error",
            "error_message": f"Error processing smart location query: {str(e)}"
        }


# Helper functions for query parsing and boundaries

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


def _get_region_boundaries(region: str) -> Optional[Dict[str, float]]:
    """Get approximate boundaries for major seismic regions and important geological areas."""
    region_boundaries = {
        # Major Seismic Regions
        "pacific ring of fire": {"min_lat": -60.0, "max_lat": 70.0, "min_lon": -180.0, "max_lon": 180.0},
        "ring of fire": {"min_lat": -60.0, "max_lat": 70.0, "min_lon": -180.0, "max_lon": 180.0},
        "mediterranean": {"min_lat": 30.0, "max_lat": 48.0, "min_lon": -10.0, "max_lon": 42.0},
        "himalayan region": {"min_lat": 25.0, "max_lat": 40.0, "min_lon": 70.0, "max_lon": 105.0},
        "himalaya": {"min_lat": 25.0, "max_lat": 40.0, "min_lon": 70.0, "max_lon": 105.0},
        "middle east": {"min_lat": 12.0, "max_lat": 42.0, "min_lon": 25.0, "max_lon": 65.0},
        "caribbean": {"min_lat": 10.0, "max_lat": 28.0, "min_lon": -90.0, "max_lon": -58.0},
        "pacific": {"min_lat": -60.0, "max_lat": 70.0, "min_lon": 120.0, "max_lon": -70.0},
        "atlantic": {"min_lat": -60.0, "max_lat": 70.0, "min_lon": -80.0, "max_lon": 20.0},
        
        # Major Fault Lines and Seismic Zones
        "san andreas fault": {"min_lat": 32.0, "max_lat": 40.0, "min_lon": -125.0, "max_lon": -115.0},
        "anatolian fault": {"min_lat": 38.0, "max_lat": 42.0, "min_lon": 26.0, "max_lon": 42.0},
        "north anatolian fault": {"min_lat": 39.0, "max_lat": 42.0, "min_lon": 26.0, "max_lon": 42.0},
        "alpine fault": {"min_lat": -47.0, "max_lat": -40.0, "min_lon": 166.0, "max_lon": 172.0},
        "dead sea fault": {"min_lat": 29.0, "max_lat": 37.0, "min_lon": 34.0, "max_lon": 37.0},
        
        # Mid-Ocean Ridges
        "mid-atlantic ridge": {"min_lat": -60.0, "max_lat": 70.0, "min_lon": -45.0, "max_lon": -5.0},
        "east pacific rise": {"min_lat": -55.0, "max_lat": 60.0, "min_lon": -130.0, "max_lon": -100.0},
        "indian ocean ridge": {"min_lat": -55.0, "max_lat": 25.0, "min_lon": 20.0, "max_lon": 90.0},
        
        # Subduction Zones
        "cascadia subduction zone": {"min_lat": 40.0, "max_lat": 50.0, "min_lon": -130.0, "max_lon": -120.0},
        "japan trench": {"min_lat": 30.0, "max_lat": 45.0, "min_lon": 140.0, "max_lon": 148.0},
        "peru-chile trench": {"min_lat": -45.0, "max_lat": -5.0, "min_lon": -85.0, "max_lon": -65.0},
        "mariana trench": {"min_lat": 10.0, "max_lat": 25.0, "min_lon": 140.0, "max_lon": 148.0},
        "aleutian trench": {"min_lat": 50.0, "max_lat": 60.0, "min_lon": -180.0, "max_lon": -140.0},
        
        # Volcanic Regions
        "yellowstone": {"min_lat": 44.0, "max_lat": 45.5, "min_lon": -111.5, "max_lon": -110.0},
        "kamchatka": {"min_lat": 50.0, "max_lat": 62.0, "min_lon": 155.0, "max_lon": 166.0},
        "iceland": {"min_lat": 63.0, "max_lat": 67.0, "min_lon": -25.0, "max_lon": -13.0},
        "andes": {"min_lat": -55.0, "max_lat": 12.0, "min_lon": -82.0, "max_lon": -65.0},
        
        # Regional Earthquake Zones
        "california": {"min_lat": 32.0, "max_lat": 42.0, "min_lon": -125.0, "max_lon": -114.0},
        "alaska": {"min_lat": 55.0, "max_lat": 72.0, "min_lon": -180.0, "max_lon": -130.0},
        "indonesia": {"min_lat": -11.0, "max_lat": 6.0, "min_lon": 95.0, "max_lon": 141.0},
        "philippines": {"min_lat": 4.0, "max_lat": 21.0, "min_lon": 116.0, "max_lon": 127.0},
        "new zealand": {"min_lat": -47.0, "max_lat": -34.0, "min_lon": 166.0, "max_lon": 179.0},
        "chile": {"min_lat": -56.0, "max_lat": -17.0, "min_lon": -76.0, "max_lon": -66.0},
        "mexico": {"min_lat": 14.0, "max_lat": 33.0, "min_lon": -118.0, "max_lon": -86.0},
        "turkey": {"min_lat": 35.0, "max_lat": 43.0, "min_lon": 25.0, "max_lon": 45.0},
        "iran": {"min_lat": 25.0, "max_lat": 40.0, "min_lon": 44.0, "max_lon": 64.0},
        "italy": {"min_lat": 35.0, "max_lat": 47.0, "min_lon": 6.0, "max_lon": 19.0},
        "greece": {"min_lat": 34.0, "max_lat": 42.0, "min_lon": 19.0, "max_lon": 30.0},
        "japan": {"min_lat": 24.0, "max_lat": 46.0, "min_lon": 129.0, "max_lon": 146.0},
        "taiwan": {"min_lat": 21.0, "max_lat": 26.0, "min_lon": 119.0, "max_lon": 122.0},
        "papua new guinea": {"min_lat": -12.0, "max_lat": -1.0, "min_lon": 140.0, "max_lon": 156.0},
        "vanuatu": {"min_lat": -21.0, "max_lat": -13.0, "min_lon": 166.0, "max_lon": 171.0},
        "solomon islands": {"min_lat": -12.0, "max_lat": -5.0, "min_lon": 155.0, "max_lon": 163.0},
        "fiji": {"min_lat": -22.0, "max_lat": -12.0, "min_lon": 177.0, "max_lon": -177.0},
        "tonga": {"min_lat": -25.0, "max_lat": -15.0, "min_lon": -177.0, "max_lon": -173.0},
        "peru": {"min_lat": -18.5, "max_lat": -0.5, "min_lon": -82.0, "max_lon": -68.0},
        "ecuador": {"min_lat": -5.0, "max_lat": 2.0, "min_lon": -82.0, "max_lon": -75.0},
        "colombia": {"min_lat": -5.0, "max_lat": 13.0, "min_lon": -82.0, "max_lon": -66.0},
        "afghanistan": {"min_lat": 29.0, "max_lat": 39.0, "min_lon": 60.0, "max_lon": 75.0},
        "pakistan": {"min_lat": 23.0, "max_lat": 37.0, "min_lon": 60.0, "max_lon": 78.0},
        "india": {"min_lat": 6.0, "max_lat": 37.0, "min_lon": 68.0, "max_lon": 97.0},
        "nepal": {"min_lat": 26.0, "max_lat": 31.0, "min_lon": 80.0, "max_lon": 89.0},
        "bhutan": {"min_lat": 26.5, "max_lat": 28.5, "min_lon": 88.5, "max_lon": 92.5},
        "myanmar": {"min_lat": 9.0, "max_lat": 29.0, "min_lon": 92.0, "max_lon": 102.0},
        "china": {"min_lat": 18.0, "max_lat": 54.0, "min_lon": 73.0, "max_lon": 135.0},
        "mongolia": {"min_lat": 41.0, "max_lat": 52.0, "min_lon": 87.0, "max_lon": 120.0},
        "kyrgyzstan": {"min_lat": 39.0, "max_lat": 44.0, "min_lon": 69.0, "max_lon": 81.0},
        "tajikistan": {"min_lat": 36.0, "max_lat": 41.0, "min_lon": 67.0, "max_lon": 75.0},
        "uzbekistan": {"min_lat": 37.0, "max_lat": 46.0, "min_lon": 55.0, "max_lon": 74.0},
        "kazakhstan": {"min_lat": 40.0, "max_lat": 56.0, "min_lon": 46.0, "max_lon": 88.0},
        "russia": {"min_lat": 41.0, "max_lat": 82.0, "min_lon": 19.0, "max_lon": -169.0},
        "haiti": {"min_lat": 17.5, "max_lat": 20.5, "min_lon": -75.0, "max_lon": -71.0},
        "guatemala": {"min_lat": 13.0, "max_lat": 18.0, "min_lon": -93.0, "max_lon": -88.0},
        "costa rica": {"min_lat": 8.0, "max_lat": 11.5, "min_lon": -86.0, "max_lon": -82.5},
        "el salvador": {"min_lat": 12.5, "max_lat": 14.5, "min_lon": -90.5, "max_lon": -87.5},
        "nicaragua": {"min_lat": 10.5, "max_lat": 15.5, "min_lon": -88.0, "max_lon": -83.0},
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
        smart_location_earthquake_query,
        get_earthquakes_by_any_location,
        get_enhanced_location_info,
        get_earthquake_data,
        get_earthquakes_by_country,
        get_earthquakes_by_region,
        get_recent_significant_earthquakes,
        analyze_earthquake_risk,
        get_city_coordinates,
        get_current_time
    ]
)