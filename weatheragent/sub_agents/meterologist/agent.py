import datetime
import requests
from zoneinfo import ZoneInfo
from google.adk.agents import Agent

def get_city_coordinates(city: str) -> dict:
    """Get latitude and longitude for a city or country using Open-Meteo Geocoding API.
    
    Args:
        city (str): The name of the city or country.
        
    Returns:
        dict: status and coordinates or error message.
    """
    try:
        geocoding_url = "https://geocoding-api.open-meteo.com/v1/search"
        
        # First try: Search for the exact input (city or country)
        geocoding_params = {"name": city, "count": 5}  # Get more results to find best match
        response = requests.get(geocoding_url, params=geocoding_params)
        response.raise_for_status()
        data = response.json()
        
        if data.get("results"):
            # Prioritize exact matches or capital cities for countries
            results = data["results"]
            
            # Look for exact name match first
            for result in results:
                if result["name"].lower() == city.lower():
                    return {
                        "status": "success",
                        "latitude": result["latitude"],
                        "longitude": result["longitude"],
                        "name": result["name"],
                        "country": result.get("country", ""),
                        "timezone": result.get("timezone", "auto"),
                        "type": "exact_match"
                    }
            
            # Look for country match (where the input matches the country name)
            for result in results:
                if result.get("country", "").lower() == city.lower():
                    # This is likely a country search, return the capital or major city
                    return {
                        "status": "success",
                        "latitude": result["latitude"],
                        "longitude": result["longitude"],
                        "name": result["name"],
                        "country": result.get("country", ""),
                        "timezone": result.get("timezone", "auto"),
                        "type": "country_capital"
                    }
            
            # If no exact match, return the first result
            result = results[0]
            return {
                "status": "success",
                "latitude": result["latitude"],
                "longitude": result["longitude"],
                "name": result["name"],
                "country": result.get("country", ""),
                "timezone": result.get("timezone", "auto"),
                "type": "best_match"
            }
        else:
            # Second try: If no results found, try searching with "capital" appended
            capital_search = f"{city} capital"
            geocoding_params = {"name": capital_search, "count": 3}
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
                    "timezone": result.get("timezone", "auto"),
                    "type": "capital_search"
                }
            else:
                return {
                    "status": "error",
                    "error_message": f"Location '{city}' not found. Please try with a specific city name or country."
                }
    except Exception as e:
        return {
            "status": "error",
            "error_message": f"Error finding coordinates for '{city}': {str(e)}"
        }


def get_weather_forecast(city: str, days: int = 3) -> dict:
    """Get detailed weather forecast for a city or country.
    
    Args:
        city (str): The name of the city or country.
        days (int): Number of days to forecast (default: 3) (max 16 days).
        
    Returns:
        dict: status and weather forecast or error message.
    """
    coords = get_city_coordinates(city)
    if coords["status"] == "error":
        return coords
    
    try:
        start_date = datetime.date.today().isoformat()
        end_date = (datetime.date.today() + datetime.timedelta(days=days)).isoformat()
        
        forecast_url = "https://api.open-meteo.com/v1/forecast"
        forecast_params = {
            "latitude": coords["latitude"],
            "longitude": coords["longitude"],
            "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,wind_speed_10m_max,weather_code",
            "hourly": "temperature_2m,precipitation,wind_speed_10m,weather_code",
            "start_date": start_date,
            "end_date": end_date,
            "timezone": "auto"
        }
        
        response = requests.get(forecast_url, params=forecast_params)
        response.raise_for_status()
        data = response.json()
        
        # Format the forecast data
        daily_forecast = []
        if "daily" in data:
            for i, date in enumerate(data["daily"]["time"]):
                daily_forecast.append({
                    "date": date,
                    "max_temp": f"{data['daily']['temperature_2m_max'][i]}°C",
                    "min_temp": f"{data['daily']['temperature_2m_min'][i]}°C",
                    "precipitation": f"{data['daily']['precipitation_sum'][i]}mm",
                    "max_wind_speed": f"{data['daily']['wind_speed_10m_max'][i]}km/h"
                })
        
        # Determine location description based on coordinate type
        location_type = coords.get("type", "unknown")
        location_description = coords["name"]
        if location_type == "country_capital":
            location_description = f"{coords['name']} (capital of {coords['country']})"
        elif location_type == "capital_search":
            location_description = f"{coords['name']} ({coords['country']})"
        
        return {
            "status": "success",
            "location": location_description,
            "city": coords["name"],
            "country": coords["country"],
            "location_type": location_type,
            "coordinates": {"latitude": coords["latitude"], "longitude": coords["longitude"]},
            "forecast": daily_forecast,
            "units": data.get("daily_units", {})
        }
    except Exception as e:
        return {
            "status": "error",
            "error_message": f"Error getting weather forecast for '{city}': {str(e)}"
        }


def get_current_weather(city: str) -> dict:
    """Get current weather conditions for a city or country.
    
    Args:
        city (str): The name of the city or country.
        
    Returns:
        dict: status and current weather or error message.
    """
    coords = get_city_coordinates(city)
    if coords["status"] == "error":
        return coords
    
    try:
        forecast_url = "https://api.open-meteo.com/v1/forecast"
        forecast_params = {
            "latitude": coords["latitude"],
            "longitude": coords["longitude"],
            "current": "temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m,wind_direction_10m",
            "timezone": "auto"
        }
        
        response = requests.get(forecast_url, params=forecast_params)
        response.raise_for_status()
        data = response.json()
        
        current = data.get("current", {})
        
        # Determine location description based on coordinate type
        location_type = coords.get("type", "unknown")
        location_description = coords["name"]
        if location_type == "country_capital":
            location_description = f"{coords['name']} (capital of {coords['country']})"
        elif location_type == "capital_search":
            location_description = f"{coords['name']} ({coords['country']})"
        
        return {
            "status": "success",
            "location": location_description,
            "city": coords["name"],
            "country": coords["country"],
            "location_type": location_type,
            "coordinates": {"latitude": coords["latitude"], "longitude": coords["longitude"]},
            "current_weather": {
                "temperature": f"{current.get('temperature_2m', 'N/A')}°C",
                "humidity": f"{current.get('relative_humidity_2m', 'N/A')}%",
                "wind_speed": f"{current.get('wind_speed_10m', 'N/A')}km/h",
                "wind_direction": f"{current.get('wind_direction_10m', 'N/A')}°"
            },
            "time": current.get("time", ""),
            "units": data.get("current_units", {})
        }
    except Exception as e:
        return {
            "status": "error",
            "error_message": f"Error getting current weather for '{city}': {str(e)}"
        }


def get_air_quality(city: str) -> dict:
    """Get air quality information for a city or country.
    
    Args:
        city (str): The name of the city or country.
        
    Returns:
        dict: status and air quality data or error message.
    """
    coords = get_city_coordinates(city)
    if coords["status"] == "error":
        return coords
    
    try:
        start_date = datetime.date.today().isoformat()
        end_date = (datetime.date.today() + datetime.timedelta(days=1)).isoformat()
        
        air_url = "https://air-quality-api.open-meteo.com/v1/air-quality"
        air_params = {
            "latitude": coords["latitude"],
            "longitude": coords["longitude"],
            "current": "pm10,pm2_5,carbon_monoxide,nitrogen_dioxide,ozone",
            "start_date": start_date,
            "end_date": end_date,
            "timezone": "auto"
        }
        
        response = requests.get(air_url, params=air_params)
        response.raise_for_status()
        data = response.json()
        
        current = data.get("current", {})
        
        # Determine location description based on coordinate type
        location_type = coords.get("type", "unknown")
        location_description = coords["name"]
        if location_type == "country_capital":
            location_description = f"{coords['name']} (capital of {coords['country']})"
        elif location_type == "capital_search":
            location_description = f"{coords['name']} ({coords['country']})"
        
        return {
            "status": "success",
            "location": location_description,
            "city": coords["name"],
            "country": coords["country"],
            "location_type": location_type,
            "coordinates": {"latitude": coords["latitude"], "longitude": coords["longitude"]},
            "air_quality": {
                "pm10": f"{current.get('pm10', 'N/A')} µg/m³",
                "pm2_5": f"{current.get('pm2_5', 'N/A')} µg/m³",
                "carbon_monoxide": f"{current.get('carbon_monoxide', 'N/A')} µg/m³",
                "nitrogen_dioxide": f"{current.get('nitrogen_dioxide', 'N/A')} µg/m³",
                "ozone": f"{current.get('ozone', 'N/A')} µg/m³"
            },
            "time": current.get("time", ""),
            "units": data.get("current_units", {})
        }
    except Exception as e:
        return {
            "status": "error",
            "error_message": f"Error getting air quality for '{city}': {str(e)}"
        }


def get_marine_weather(city: str) -> dict:
    """Get marine weather conditions for coastal cities or countries.
    
    Args:
        city (str): The name of the coastal city or country.
        
    Returns:
        dict: status and marine weather data or error message.
    """
    coords = get_city_coordinates(city)
    if coords["status"] == "error":
        return coords
    
    try:
        start_date = datetime.date.today().isoformat()
        end_date = (datetime.date.today() + datetime.timedelta(days=3)).isoformat()
        
        marine_url = "https://marine-api.open-meteo.com/v1/marine"
        marine_params = {
            "latitude": coords["latitude"],
            "longitude": coords["longitude"],
            "current": "wave_height,wave_direction,wave_period",
            "daily": "wave_height_max,wave_direction_dominant,wave_period_max",
            "start_date": start_date,
            "end_date": end_date,
            "timezone": "auto"
        }
        
        response = requests.get(marine_url, params=marine_params)
        response.raise_for_status()
        data = response.json()
        
        current = data.get("current", {})
        daily_forecast = []
        
        if "daily" in data:
            for i, date in enumerate(data["daily"]["time"]):
                daily_forecast.append({
                    "date": date,
                    "max_wave_height": f"{data['daily']['wave_height_max'][i]}m",
                    "dominant_wave_direction": f"{data['daily']['wave_direction_dominant'][i]}°",
                    "max_wave_period": f"{data['daily']['wave_period_max'][i]}s"
                })
        
        # Determine location description based on coordinate type
        location_type = coords.get("type", "unknown")
        location_description = coords["name"]
        if location_type == "country_capital":
            location_description = f"{coords['name']} (capital of {coords['country']})"
        elif location_type == "capital_search":
            location_description = f"{coords['name']} ({coords['country']})"
        
        return {
            "status": "success",
            "location": location_description,
            "city": coords["name"],
            "country": coords["country"],
            "location_type": location_type,
            "coordinates": {"latitude": coords["latitude"], "longitude": coords["longitude"]},
            "current_marine": {
                "wave_height": f"{current.get('wave_height', 'N/A')}m",
                "wave_direction": f"{current.get('wave_direction', 'N/A')}°",
                "wave_period": f"{current.get('wave_period', 'N/A')}s"
            },
            "marine_forecast": daily_forecast,
            "time": current.get("time", "")
        }
    except Exception as e:
        return {
            "status": "error",
            "error_message": f"Error getting marine weather for '{city}': {str(e)}"
        }


def get_historical_weather(city: str, start_date: str, end_date: str) -> dict:
    """Get historical weather data for a city or country.
    
    Args:
        city (str): The name of the city or country.
        start_date (str): Start date in YYYY-MM-DD format.
        end_date (str): End date in YYYY-MM-DD format.
        
    Returns:
        dict: status and historical weather data or error message.
    """
    coords = get_city_coordinates(city)
    if coords["status"] == "error":
        return coords
    
    try:
        historical_url = "https://archive-api.open-meteo.com/v1/archive"
        historical_params = {
            "latitude": coords["latitude"],
            "longitude": coords["longitude"],
            "start_date": start_date,
            "end_date": end_date,
            "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum",
            "timezone": "auto"
        }
        
        response = requests.get(historical_url, params=historical_params)
        response.raise_for_status()
        data = response.json()
        
        daily_data = []
        if "daily" in data:
            for i, date in enumerate(data["daily"]["time"]):
                daily_data.append({
                    "date": date,
                    "max_temp": f"{data['daily']['temperature_2m_max'][i]}°C",
                    "min_temp": f"{data['daily']['temperature_2m_min'][i]}°C",
                    "precipitation": f"{data['daily']['precipitation_sum'][i]}mm"
                })
        
        # Determine location description based on coordinate type
        location_type = coords.get("type", "unknown")
        location_description = coords["name"]
        if location_type == "country_capital":
            location_description = f"{coords['name']} (capital of {coords['country']})"
        elif location_type == "capital_search":
            location_description = f"{coords['name']} ({coords['country']})"
        
        return {
            "status": "success",
            "location": location_description,
            "city": coords["name"],
            "country": coords["country"],
            "location_type": location_type,
            "coordinates": {"latitude": coords["latitude"], "longitude": coords["longitude"]},
            "period": f"{start_date} to {end_date}",
            "historical_data": daily_data,
            "units": data.get("daily_units", {})
        }
    except Exception as e:
        return {
            "status": "error",
            "error_message": f"Error getting historical weather for '{city}': {str(e)}"
        }


def get_climate_forecast(city: str, year: int = 2040) -> dict:
    """Get long-term climate forecast for a city or country.
    
    Args:
        city (str): The name of the city or country.
        year (int): Target year for climate forecast (default: 2040).
        
    Returns:
        dict: status and climate forecast or error message.
    """
    coords = get_city_coordinates(city)
    if coords["status"] == "error":
        return coords
    
    try:
        climate_url = "https://climate-api.open-meteo.com/v1/climate"
        climate_params = {
            "latitude": coords["latitude"],
            "longitude": coords["longitude"],
            "daily": "temperature_2m_min,temperature_2m_max,precipitation_sum",
            "start_date": f"{year}-01-01",
            "end_date": f"{year}-12-31",
            "model": "EC-Earth3",
            "timezone": "auto"
        }
        
        response = requests.get(climate_url, params=climate_params)
        response.raise_for_status()
        data = response.json()
        
        # Calculate monthly averages
        monthly_avg = {}
        if "daily" in data:
            for i, date in enumerate(data["daily"]["time"]):
                month = date[:7]  # YYYY-MM
                if month not in monthly_avg:
                    monthly_avg[month] = {"temps_max": [], "temps_min": [], "precip": []}
                
                monthly_avg[month]["temps_max"].append(data["daily"]["temperature_2m_max"][i])
                monthly_avg[month]["temps_min"].append(data["daily"]["temperature_2m_min"][i])
                monthly_avg[month]["precip"].append(data["daily"]["precipitation_sum"][i])
        
        # Format monthly summaries
        monthly_summary = []
        for month, values in monthly_avg.items():
            monthly_summary.append({
                "month": month,
                "avg_max_temp": f"{sum(values['temps_max'])/len(values['temps_max']):.1f}°C",
                "avg_min_temp": f"{sum(values['temps_min'])/len(values['temps_min']):.1f}°C",
                "total_precipitation": f"{sum(values['precip']):.1f}mm"
            })
        
        # Determine location description based on coordinate type
        location_type = coords.get("type", "unknown")
        location_description = coords["name"]
        if location_type == "country_capital":
            location_description = f"{coords['name']} (capital of {coords['country']})"
        elif location_type == "capital_search":
            location_description = f"{coords['name']} ({coords['country']})"
        
        return {
            "status": "success",
            "location": location_description,
            "city": coords["name"],
            "country": coords["country"],
            "location_type": location_type,
            "coordinates": {"latitude": coords["latitude"], "longitude": coords["longitude"]},
            "forecast_year": year,
            "monthly_climate": monthly_summary,
            "model": "EC-Earth3"
        }
    except Exception as e:
        return {
            "status": "error",
            "error_message": f"Error getting climate forecast for '{city}': {str(e)}"
        }


def get_weather(city: str) -> dict:
    """Retrieves the current weather report for a specified city or country.

    Args:
        city (str): The name of the city or country for which to retrieve the weather report.

    Returns:
        dict: status and result or error msg.
    """
    return get_current_weather(city)


def get_current_time(city: str) -> dict:
    """Returns the current time in a specified city or country.

    Args:
        city (str): The name of the city or country for which to retrieve the current time.

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
        
        # Determine location description based on coordinate type
        location_type = coords.get("type", "unknown")
        location_description = coords["name"]
        if location_type == "country_capital":
            location_description = f"{coords['name']} (capital of {coords['country']})"
        elif location_type == "capital_search":
            location_description = f"{coords['name']} ({coords['country']})"
        
        report = (
            f'The current time in {location_description} is {now.strftime("%Y-%m-%d %H:%M:%S %Z%z")}'
        )
        
        return {
            "status": "success", 
            "report": report,
            "location": location_description,
            "city": coords["name"],
            "country": coords["country"],
            "location_type": location_type,
            "coordinates": {"latitude": coords["latitude"], "longitude": coords["longitude"]},
            "timezone": tz_identifier,
            "current_time": now.strftime("%Y-%m-%d %H:%M:%S %Z%z")
        }
    except Exception as e:
        return {
            "status": "error",
            "error_message": f"Error getting time for '{city}': {str(e)}"
        }


meterologist = Agent(
    name="meterologist",
    model="gemini-2.5-flash-lite-preview-06-17",
    description=(
        "Advanced weather agent that provides comprehensive meteorological information including "
        "current weather, forecasts, historical data, air quality, marine conditions, and climate projections "
        "for both cities and countries worldwide. Intelligently handles country queries by using capital cities "
        "or major population centers as reference points."
    ),
    instruction=(
        "You are a comprehensive meteorologist agent that can provide detailed weather information for any city or country worldwide. "
        "When a user asks for weather information about a country, you will automatically find the most appropriate location "
        "(usually the capital city) to provide representative data for that country. You can get current weather conditions, "
        "multi-day forecasts, historical weather data, air quality information, marine weather for coastal areas, and "
        "long-term climate forecasts. Always provide accurate, detailed, and helpful weather information based on real-time "
        "data from Open-Meteo APIs. Clearly indicate whether you're providing data for a specific city or a representative "
        "location within a country. You should calculate and analyze the data whenever it is needed to provide meaningful insights."
    ),
    tools=[
        get_weather,
        get_current_weather,
        get_weather_forecast,
        get_air_quality,
        get_marine_weather,
        get_historical_weather,
        get_climate_forecast,
        get_current_time,
        get_city_coordinates
    ],
)