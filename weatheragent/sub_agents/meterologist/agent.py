import datetime
import requests
import re
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
        response = requests.get(geocoding_url, params=geocoding_params, timeout=10)
        response.raise_for_status()
        
        # Check if response is actually JSON
        content_type = response.headers.get('content-type', '')
        if 'application/json' not in content_type:
            return {
                "status": "error",
                "error_message": f"API returned non-JSON response for '{city}'. Content-Type: {content_type}"
            }
        
        try:
            data = response.json()
        except requests.exceptions.JSONDecodeError as json_err:
            return {
                "status": "error",
                "error_message": f"Invalid JSON response for '{city}': {str(json_err)}. Response: {response.text[:200]}"
            }
        
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
            response = requests.get(geocoding_url, params=geocoding_params, timeout=10)
            response.raise_for_status()
            
            # Check content type for second request
            content_type = response.headers.get('content-type', '')
            if 'application/json' not in content_type:
                return {
                    "status": "error",
                    "error_message": f"API returned non-JSON response for capital search '{capital_search}'. Content-Type: {content_type}"
                }
            
            try:
                data = response.json()
            except requests.exceptions.JSONDecodeError as json_err:
                return {
                    "status": "error",
                    "error_message": f"Invalid JSON response for capital search '{capital_search}': {str(json_err)}. Response: {response.text[:200]}"
                }
            
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
        
        response = requests.get(forecast_url, params=forecast_params, timeout=10)
        response.raise_for_status()
        
        # Check if response is actually JSON
        content_type = response.headers.get('content-type', '')
        if 'application/json' not in content_type:
            return {
                "status": "error",
                "error_message": f"API returned non-JSON response for '{city}'. Content-Type: {content_type}"
            }
        
        try:
            data = response.json()
        except requests.exceptions.JSONDecodeError as json_err:
            return {
                "status": "error",
                "error_message": f"Invalid JSON response for '{city}': {str(json_err)}. Response: {response.text[:200]}"
            }
        
        # Check for API errors
        if data.get("error"):
            return {
                "status": "error",
                "error_message": f"API Error: {data.get('reason', 'Unknown error')}"
            }
        
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
        
        response = requests.get(forecast_url, params=forecast_params, timeout=10)
        response.raise_for_status()
        
        # Check if response is actually JSON
        content_type = response.headers.get('content-type', '')
        if 'application/json' not in content_type:
            return {
                "status": "error",
                "error_message": f"API returned non-JSON response for '{city}'. Content-Type: {content_type}"
            }
        
        try:
            data = response.json()
        except requests.exceptions.JSONDecodeError as json_err:
            return {
                "status": "error",
                "error_message": f"Invalid JSON response for '{city}': {str(json_err)}. Response: {response.text[:200]}"
            }
        
        # Check for API errors
        if data.get("error"):
            return {
                "status": "error",
                "error_message": f"API Error: {data.get('reason', 'Unknown error')}"
            }
        
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
        
        response = requests.get(air_url, params=air_params, timeout=10)
        response.raise_for_status()
        
        # Check if response is actually JSON
        content_type = response.headers.get('content-type', '')
        if 'application/json' not in content_type:
            return {
                "status": "error",
                "error_message": f"API returned non-JSON response for '{city}'. Content-Type: {content_type}"
            }
        
        try:
            data = response.json()
        except requests.exceptions.JSONDecodeError as json_err:
            return {
                "status": "error",
                "error_message": f"Invalid JSON response for '{city}': {str(json_err)}. Response: {response.text[:200]}"
            }
        
        # Check for API errors
        if data.get("error"):
            return {
                "status": "error",
                "error_message": f"API Error: {data.get('reason', 'Unknown error')}"
            }
        
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
        
        response = requests.get(marine_url, params=marine_params, timeout=10)
        response.raise_for_status()
        
        # Check if response is actually JSON
        content_type = response.headers.get('content-type', '')
        if 'application/json' not in content_type:
            return {
                "status": "error",
                "error_message": f"API returned non-JSON response for '{city}'. Content-Type: {content_type}"
            }
        
        try:
            data = response.json()
        except requests.exceptions.JSONDecodeError as json_err:
            return {
                "status": "error",
                "error_message": f"Invalid JSON response for '{city}': {str(json_err)}. Response: {response.text[:200]}"
            }
        
        # Check for API errors
        if data.get("error"):
            return {
                "status": "error",
                "error_message": f"API Error: {data.get('reason', 'Unknown error')}"
            }
        
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


def get_historical_weather(city: str, start_date: str = None, end_date: str = None, variables: str = "basic", time_period: str = None) -> dict:
    """Get historical weather data for a city or country with comprehensive variable options.
    
    Args:
        city (str): The name of the city or country.
        start_date (str, optional): Start date in YYYY-MM-DD format (available from 1940).
        end_date (str, optional): End date in YYYY-MM-DD format.
        variables (str): Type of data to retrieve:
            - "basic": temperature, precipitation, humidity, wind
            - "detailed": basic + pressure, cloud cover, solar radiation
            - "comprehensive": detailed + soil data, evapotranspiration
            - "weather_analysis": focus on weather codes and conditions
            - "solar": solar radiation and sunshine duration data
            - "agricultural": soil temperature, moisture, evapotranspiration
            - "pressure_analysis": atmospheric pressure variables
            - "wind_analysis": comprehensive wind data
            - "cloud_analysis": detailed cloud cover data
        time_period (str, optional): Natural language time period like:
            - "past 5 years", "last 3 years", "previous 2 years"
            - "past 12 months", "last 6 months"
            - "past 30 days", "last week"
            - "2023", "2022-2023", "winter 2023", "summer 2022"
        
    Returns:
        dict: status and historical weather data or error message.
    """
    coords = get_city_coordinates(city)
    if coords["status"] == "error":
        return coords
    
    try:
        # Parse natural language time periods or use provided dates
        from datetime import datetime, timedelta
        import re
        
        # If time_period is provided, parse it to get start_date and end_date
        if time_period and not start_date and not end_date:
            today = datetime.now()
            
            # Parse natural language time periods
            time_period_lower = time_period.lower().strip()
            
            if "past" in time_period_lower or "last" in time_period_lower or "previous" in time_period_lower:
                # Extract number and unit
                numbers = re.findall(r'\d+', time_period_lower)
                if numbers:
                    num = int(numbers[0])
                    
                    if "year" in time_period_lower:
                        start_dt = today.replace(year=today.year - num, month=1, day=1)
                        end_dt = today - timedelta(days=5)  # 5-day delay for historical data
                    elif "month" in time_period_lower:
                        months_ago = today.month - num
                        year_offset = 0
                        while months_ago <= 0:
                            months_ago += 12
                            year_offset -= 1
                        start_dt = today.replace(year=today.year + year_offset, month=months_ago, day=1)
                        end_dt = today - timedelta(days=5)
                    elif "day" in time_period_lower:
                        start_dt = today - timedelta(days=num + 5)  # Add 5-day delay
                        end_dt = today - timedelta(days=5)
                    elif "week" in time_period_lower:
                        start_dt = today - timedelta(weeks=num, days=5)
                        end_dt = today - timedelta(days=5)
                    else:
                        return {
                            "status": "error",
                            "error_message": f"Unable to parse time period: '{time_period}'. Use formats like 'past 5 years', 'last 3 months', etc."
                        }
                else:
                    return {
                        "status": "error",
                        "error_message": f"Unable to extract number from time period: '{time_period}'"
                    }
                    
            elif re.match(r'^\d{4}$', time_period_lower):  # Single year like "2023"
                year = int(time_period_lower)
                start_dt = datetime(year, 1, 1)
                end_dt = datetime(year, 12, 31)
                
            elif re.match(r'^\d{4}-\d{4}$', time_period_lower):  # Year range like "2022-2023"
                start_year, end_year = map(int, time_period_lower.split('-'))
                start_dt = datetime(start_year, 1, 1)
                end_dt = datetime(end_year, 12, 31)
                
            elif "winter" in time_period_lower:
                year_match = re.findall(r'\d{4}', time_period_lower)
                if year_match:
                    year = int(year_match[0])
                    start_dt = datetime(year, 12, 1)
                    end_dt = datetime(year + 1, 2, 28)
                else:
                    return {"status": "error", "error_message": "Please specify year for winter, e.g., 'winter 2023'"}
                    
            elif "summer" in time_period_lower:
                year_match = re.findall(r'\d{4}', time_period_lower)
                if year_match:
                    year = int(year_match[0])
                    start_dt = datetime(year, 6, 1)
                    end_dt = datetime(year, 8, 31)
                else:
                    return {"status": "error", "error_message": "Please specify year for summer, e.g., 'summer 2023'"}
                    
            elif "spring" in time_period_lower:
                year_match = re.findall(r'\d{4}', time_period_lower)
                if year_match:
                    year = int(year_match[0])
                    start_dt = datetime(year, 3, 1)
                    end_dt = datetime(year, 5, 31)
                else:
                    return {"status": "error", "error_message": "Please specify year for spring, e.g., 'spring 2023'"}
                    
            elif "autumn" in time_period_lower or "fall" in time_period_lower:
                year_match = re.findall(r'\d{4}', time_period_lower)
                if year_match:
                    year = int(year_match[0])
                    start_dt = datetime(year, 9, 1)
                    end_dt = datetime(year, 11, 30)
                else:
                    return {"status": "error", "error_message": "Please specify year for autumn/fall, e.g., 'autumn 2023'"}
            else:
                return {
                    "status": "error",
                    "error_message": f"Unable to parse time period: '{time_period}'. Use formats like 'past 5 years', 'last 3 months', '2023', 'winter 2023', etc."
                }
            
            start_date = start_dt.strftime("%Y-%m-%d")
            end_date = end_dt.strftime("%Y-%m-%d")
            
        elif not start_date or not end_date:
            return {
                "status": "error",
                "error_message": "Either provide both start_date and end_date, or use time_period parameter for natural language queries."
            }
        
        # Validate date range (API supports from 1940 with 5-day delay)
        
        try:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
            end_dt = datetime.strptime(end_date, "%Y-%m-%d")
            today = datetime.now()
            
            # Check if dates are too recent (5-day delay for historical data)
            if end_dt > today - timedelta(days=5):
                return {
                    "status": "error",
                    "error_message": "Historical weather data has a 5-day delay. For recent data, use the forecast API with past_days parameter."
                }
                
            # Check if start date is too old
            if start_dt.year < 1940:
                return {
                    "status": "error",
                    "error_message": "Historical weather data is only available from 1940 onwards."
                }
                
        except ValueError:
            return {
                "status": "error",
                "error_message": "Invalid date format. Please use YYYY-MM-DD format."
            }
        
        historical_url = "https://archive-api.open-meteo.com/v1/archive"
        
        # Define variable sets based on requested type according to API documentation
        daily_variables = []
        hourly_variables = []
        
        if variables == "basic":
            daily_variables = [
                "temperature_2m_max", "temperature_2m_min", "precipitation_sum",
                "wind_speed_10m_max", "weather_code"
            ]
            hourly_variables = [
                "temperature_2m", "relative_humidity_2m", "precipitation",
                "wind_speed_10m", "wind_direction_10m"
            ]
            
        elif variables == "detailed":
            daily_variables = [
                "temperature_2m_max", "temperature_2m_min", "precipitation_sum",
                "wind_speed_10m_max", "wind_gusts_10m_max", "weather_code",
                "shortwave_radiation_sum", "sunshine_duration"
            ]
            hourly_variables = [
                "temperature_2m", "relative_humidity_2m", "precipitation",
                "wind_speed_10m", "wind_direction_10m", "pressure_msl",
                "cloudcover", "shortwave_radiation"
            ]
            
        elif variables == "comprehensive":
            daily_variables = [
                "temperature_2m_max", "temperature_2m_min", "precipitation_sum",
                "wind_speed_10m_max", "wind_gusts_10m_max", "weather_code",
                "shortwave_radiation_sum", "sunshine_duration", "et0_fao_evapotranspiration"
            ]
            hourly_variables = [
                "temperature_2m", "relative_humidity_2m", "precipitation",
                "wind_speed_10m", "wind_direction_10m", "pressure_msl",
                "cloudcover", "shortwave_radiation", "soil_temperature_0_7cm",
                "soil_moisture_0_7cm", "vapour_pressure_deficit"
            ]
            
        elif variables == "weather_analysis":
            daily_variables = [
                "weather_code", "temperature_2m_max", "temperature_2m_min",
                "precipitation_sum", "precipitation_hours", "wind_speed_10m_max",
                "wind_direction_10m_dominant"
            ]
            hourly_variables = [
                "weather_code", "temperature_2m", "precipitation",
                "cloudcover", "cloudcover_low", "cloudcover_mid", "cloudcover_high"
            ]
            
        elif variables == "solar":
            daily_variables = [
                "shortwave_radiation_sum", "sunshine_duration",
                "temperature_2m_max", "temperature_2m_min"
            ]
            hourly_variables = [
                "shortwave_radiation", "direct_radiation", "diffuse_radiation",
                "sunshine_duration", "cloudcover"
            ]
            
        elif variables == "agricultural":
            daily_variables = [
                "temperature_2m_max", "temperature_2m_min", "precipitation_sum",
                "et0_fao_evapotranspiration"
            ]
            hourly_variables = [
                "temperature_2m", "relative_humidity_2m", "precipitation",
                "soil_temperature_0_7cm", "soil_temperature_7_28cm", "soil_temperature_28_100cm",
                "soil_moisture_0_7cm", "soil_moisture_7_28cm", "et0_fao_evapotranspiration"
            ]
            
        elif variables == "pressure_analysis":
            daily_variables = [
                "temperature_2m_max", "temperature_2m_min", "precipitation_sum"
            ]
            hourly_variables = [
                "pressure_msl", "surface_pressure", "temperature_2m", "relative_humidity_2m"
            ]
            
        elif variables == "wind_analysis":
            daily_variables = [
                "wind_speed_10m_max", "wind_gusts_10m_max", "wind_direction_10m_dominant"
            ]
            hourly_variables = [
                "wind_speed_10m", "wind_speed_100m", "wind_direction_10m", 
                "wind_direction_100m", "wind_gusts_10m"
            ]
            
        elif variables == "cloud_analysis":
            daily_variables = [
                "temperature_2m_max", "temperature_2m_min", "sunshine_duration"
            ]
            hourly_variables = [
                "cloudcover", "cloudcover_low", "cloudcover_mid", "cloudcover_high",
                "shortwave_radiation"
            ]
        else:
            # Default to basic if unknown type
            daily_variables = [
                "temperature_2m_max", "temperature_2m_min", "precipitation_sum",
                "wind_speed_10m_max", "weather_code"
            ]
            hourly_variables = [
                "temperature_2m", "relative_humidity_2m", "precipitation"
            ]
        
        # Build API parameters - using coordinates from get_city_coordinates
        historical_params = {
            "latitude": coords["latitude"],
            "longitude": coords["longitude"],
            "start_date": start_date,
            "end_date": end_date,
            "timezone": "auto",
            "daily": ",".join(daily_variables)
        }
        
        # Add hourly data for detailed analysis (limit to shorter periods to avoid large responses)
        date_diff = (end_dt - start_dt).days
        if date_diff <= 31 and hourly_variables:  # Only include hourly for periods <= 31 days
            historical_params["hourly"] = ",".join(hourly_variables[:5])  # Limit to 5 variables
        
        # Make API request with enhanced error handling
        response = requests.get(historical_url, params=historical_params, timeout=30)
        response.raise_for_status()
        
        # Enhanced error handling for API responses
        content_type = response.headers.get('content-type', '')
        if 'application/json' not in content_type:
            return {
                "status": "error",
                "error_message": f"API returned non-JSON response. Content-Type: {content_type}. Response: {response.text[:200]}"
            }
        
        try:
            data = response.json()
        except requests.exceptions.JSONDecodeError as json_err:
            return {
                "status": "error",
                "error_message": f"Invalid JSON response: {str(json_err)}. Response: {response.text[:200]}"
            }
        
        # Check for API errors
        if data.get("error"):
            return {
                "status": "error",
                "error_message": f"API Error: {data.get('reason', 'Unknown error')}"
            }
        
        # Process daily data
        daily_data = []
        if "daily" in data and data["daily"].get("time"):
            times = data["daily"]["time"]
            for i, date in enumerate(times):
                day_data = {"date": date}
                
                # Add available daily variables
                for var in daily_variables:
                    if var in data["daily"] and i < len(data["daily"][var]):
                        value = data["daily"][var][i]
                        if value is not None:
                            if "temperature" in var:
                                day_data[var] = f"{value}°C"
                            elif "precipitation" in var or "rain" in var or "snow" in var:
                                day_data[var] = f"{value}mm"
                            elif "wind" in var:
                                day_data[var] = f"{value}km/h"
                            elif "radiation" in var:
                                day_data[var] = f"{value}MJ/m²"
                            elif "sunshine" in var:
                                day_data[var] = f"{value}s"
                            elif "evapotranspiration" in var:
                                day_data[var] = f"{value}mm"
                            else:
                                day_data[var] = value
                
                daily_data.append(day_data)
        
        # Process hourly data (if available and requested)
        hourly_data = []
        if "hourly" in data and data["hourly"].get("time") and len(data["hourly"]["time"]) <= 744:  # Max 31 days * 24 hours
            times = data["hourly"]["time"]
            # Sample hourly data (every 6 hours to reduce response size)
            for i in range(0, len(times), 6):
                if i < len(times):
                    hour_data = {"time": times[i]}
                    
                    for var in hourly_variables[:5]:  # Limit variables
                        if var in data["hourly"] and i < len(data["hourly"][var]):
                            value = data["hourly"][var][i]
                            if value is not None:
                                if "temperature" in var:
                                    hour_data[var] = f"{value}°C"
                                elif "precipitation" in var:
                                    hour_data[var] = f"{value}mm"
                                elif "wind_speed" in var:
                                    hour_data[var] = f"{value}km/h"
                                elif "pressure" in var:
                                    hour_data[var] = f"{value}hPa"
                                elif "humidity" in var:
                                    hour_data[var] = f"{value}%"
                                else:
                                    hour_data[var] = value
                    
                    hourly_data.append(hour_data)
        
        # Calculate summary statistics
        summary_stats = {}
        if daily_data:
            # Calculate averages for temperature
            temps_max = [float(d.get("temperature_2m_max", "0").replace("°C", "")) for d in daily_data if d.get("temperature_2m_max")]
            temps_min = [float(d.get("temperature_2m_min", "0").replace("°C", "")) for d in daily_data if d.get("temperature_2m_min")]
            precip = [float(d.get("precipitation_sum", "0").replace("mm", "")) for d in daily_data if d.get("precipitation_sum")]
            
            if temps_max:
                summary_stats["avg_max_temp"] = f"{sum(temps_max)/len(temps_max):.1f}°C"
                summary_stats["highest_temp"] = f"{max(temps_max):.1f}°C"
            if temps_min:
                summary_stats["avg_min_temp"] = f"{sum(temps_min)/len(temps_min):.1f}°C"
                summary_stats["lowest_temp"] = f"{min(temps_min):.1f}°C"
            if precip:
                summary_stats["total_precipitation"] = f"{sum(precip):.1f}mm"
                summary_stats["avg_daily_precipitation"] = f"{sum(precip)/len(precip):.1f}mm"
                summary_stats["max_daily_precipitation"] = f"{max(precip):.1f}mm"
        
        # Determine location description based on coordinate type
        location_type = coords.get("type", "unknown")
        location_description = coords["name"]
        if location_type == "country_capital":
            location_description = f"{coords['name']} (capital of {coords['country']})"
        elif location_type == "capital_search":
            location_description = f"{coords['name']} ({coords['country']})"
        
        result = {
            "status": "success",
            "location": location_description,
            "city": coords["name"],
            "country": coords["country"],
            "location_type": location_type,
            "coordinates": {"latitude": coords["latitude"], "longitude": coords["longitude"]},
            "period": f"{start_date} to {end_date}",
            "data_type": variables,
            "summary_statistics": summary_stats,
            "daily_data": daily_data,
            "daily_units": data.get("daily_units", {}),
            "data_source": "Historical Weather API (Open-Meteo)",
            "model_info": "ERA5 reanalysis model with 0.25° resolution"
        }
        
        # Add hourly data if available
        if hourly_data:
            result["hourly_sample"] = hourly_data
            result["hourly_units"] = data.get("hourly_units", {})
            result["hourly_note"] = "Sampled every 6 hours to limit response size"
        
        return result
        
    except requests.exceptions.Timeout:
        return {
            "status": "error",
            "error_message": f"Request timeout while getting historical weather for '{city}'. Try reducing the date range."
        }
    except requests.exceptions.RequestException as e:
        return {
            "status": "error",
            "error_message": f"Network error getting historical weather for '{city}': {str(e)}"
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
        
        response = requests.get(climate_url, params=climate_params, timeout=10)
        response.raise_for_status()
        
        # Check if response is actually JSON
        content_type = response.headers.get('content-type', '')
        if 'application/json' not in content_type:
            return {
                "status": "error",
                "error_message": f"API returned non-JSON response for '{city}'. Content-Type: {content_type}"
            }
        
        try:
            data = response.json()
        except requests.exceptions.JSONDecodeError as json_err:
            return {
                "status": "error",
                "error_message": f"Invalid JSON response for '{city}': {str(json_err)}. Response: {response.text[:200]}"
            }
        
        # Check for API errors
        if data.get("error"):
            return {
                "status": "error",
                "error_message": f"API Error: {data.get('reason', 'Unknown error')}"
            }
        
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


def get_weather(city: str, query: str = None) -> dict:
    """Retrieves weather information for a specified city or country.
    
    This function intelligently determines whether to get current weather or historical weather
    based on the query parameters. It can handle natural language time periods.
    
    Args:
        city (str): The name of the city or country for which to retrieve the weather report.
        query (str, optional): Natural language query that may contain time periods like:
            - "past 5 years", "last 3 months", "winter 2023"
            - If not provided, returns current weather
        
    Returns:
        dict: status and result or error msg.
    """
    # If no query provided, return current weather
    if not query:
        return get_current_weather(city)
    
    # Check if query contains historical time indicators
    query_lower = query.lower()
    historical_indicators = [
        'past', 'last', 'previous', 'ago', 'history', 'historical',
        'winter', 'summer', 'spring', 'autumn', 'fall',
        'january', 'february', 'march', 'april', 'may', 'june',
        'july', 'august', 'september', 'october', 'november', 'december'
    ]
    
    # Check for year patterns (2020, 2021-2023, etc.)
    import re
    year_patterns = re.findall(r'\b(19[4-9]\d|20[0-4]\d)\b', query_lower)
    
    # If historical indicators found or year patterns, use historical weather
    if any(indicator in query_lower for indicator in historical_indicators) or year_patterns:
        return get_historical_weather(city, time_period=query, variables="detailed")
    else:
        # Default to current weather
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