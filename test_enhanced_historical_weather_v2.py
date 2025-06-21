#!/usr/bin/env python3
"""
Test script for enhanced historical weather functionality with natural language date parsing.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '.'))

from weatheragent.sub_agents.meterologist.agent import (
    get_historical_weather,
    get_weather,
    get_city_coordinates
)

def test_natural_language_queries():
    """Test historical weather queries with natural language date ranges."""
    
    print("=== Testing Enhanced Historical Weather with Natural Language Queries ===\n")
    
    # Test cases with different natural language time periods
    test_cases = [
        {
            "city": "India", 
            "time_period": "past 5 years",
            "description": "India - Past 5 Years"
        },
        {
            "city": "London", 
            "time_period": "last 2 years",
            "description": "London - Last 2 Years"
        },
        {
            "city": "New York", 
            "time_period": "past 12 months",
            "description": "New York - Past 12 Months"
        },
        {
            "city": "Tokyo", 
            "time_period": "2023",
            "description": "Tokyo - Year 2023"
        },
        {
            "city": "Berlin", 
            "time_period": "winter 2023",
            "description": "Berlin - Winter 2023"
        },
        {
            "city": "Sydney", 
            "time_period": "summer 2023",
            "description": "Sydney - Summer 2023"
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n--- Test {i}: {test_case['description']} ---")
        
        try:
            # Test using get_historical_weather directly
            result = get_historical_weather(
                city=test_case["city"],
                time_period=test_case["time_period"],
                variables="detailed"
            )
            
            if result["status"] == "success":
                print(f"✓ SUCCESS: {test_case['description']}")
                print(f"  Location: {result['location']}")
                print(f"  Period: {result['period']}")
                print(f"  Data Type: {result['data_type']}")
                print(f"  Coordinates: {result['coordinates']}")
                
                # Print summary statistics if available
                if result.get("summary_statistics"):
                    stats = result["summary_statistics"]
                    print(f"  Summary Stats:")
                    for key, value in stats.items():
                        print(f"    {key.replace('_', ' ').title()}: {value}")
                
                # Print sample daily data (first 3 days)
                if result.get("daily_data"):
                    print(f"  Sample Daily Data (first 3 days):")
                    for j, day in enumerate(result["daily_data"][:3]):
                        print(f"    {day['date']}: {day}")
                        
                print(f"  Total daily records: {len(result.get('daily_data', []))}")
                
                if result.get("hourly_sample"):
                    print(f"  Hourly sample records: {len(result['hourly_sample'])}")
                    
            else:
                print(f"✗ ERROR: {test_case['description']}")
                print(f"  Error: {result.get('error_message', 'Unknown error')}")
                
        except Exception as e:
            print(f"✗ EXCEPTION: {test_case['description']}")
            print(f"  Exception: {str(e)}")
        
        print("-" * 60)

def test_intelligent_get_weather():
    """Test the enhanced get_weather function that can handle both current and historical queries."""
    
    print("\n\n=== Testing Intelligent get_weather Function ===\n")
    
    test_queries = [
        {
            "city": "India",
            "query": "past 5 years",
            "description": "India historical weather past 5 years"
        },
        {
            "city": "India",
            "query": None,
            "description": "India current weather (no query)"
        },
        {
            "city": "Paris",
            "query": "winter 2023",
            "description": "Paris winter 2023 historical weather"
        },
        {
            "city": "Tokyo",
            "query": "last 6 months", 
            "description": "Tokyo last 6 months historical weather"
        }
    ]
    
    for i, test in enumerate(test_queries, 1):
        print(f"\n--- Test {i}: {test['description']} ---")
        
        try:
            if test["query"]:
                result = get_weather(test["city"], test["query"])
            else:
                result = get_weather(test["city"])
            
            if result["status"] == "success":
                print(f"✓ SUCCESS: {test['description']}")
                print(f"  Location: {result['location']}")
                
                # Check if it's historical or current weather
                if "period" in result:
                    print(f"  Type: Historical Weather")
                    print(f"  Period: {result['period']}")
                    print(f"  Data records: {len(result.get('daily_data', []))}")
                elif "current_weather" in result:
                    print(f"  Type: Current Weather")
                    print(f"  Temperature: {result['current_weather'].get('temperature', 'N/A')}")
                    print(f"  Humidity: {result['current_weather'].get('humidity', 'N/A')}")
                elif "forecast" in result:
                    print(f"  Type: Weather Forecast")
                    print(f"  Forecast days: {len(result.get('forecast', []))}")
                    
            else:
                print(f"✗ ERROR: {test['description']}")
                print(f"  Error: {result.get('error_message', 'Unknown error')}")
                
        except Exception as e:
            print(f"✗ EXCEPTION: {test['description']}")
            print(f"  Exception: {str(e)}")
        
        print("-" * 60)

def test_coordinates_api():
    """Test the coordinates API with various locations."""
    
    print("\n\n=== Testing Coordinates API ===\n")
    
    locations = ["India", "London", "New York", "Tokyo", "Paris", "Berlin", "Sydney"]
    
    for location in locations:
        print(f"Testing coordinates for: {location}")
        result = get_city_coordinates(location)
        
        if result["status"] == "success":
            print(f"  ✓ {location}: {result['name']}, {result['country']}")
            print(f"    Coordinates: ({result['latitude']}, {result['longitude']})")
            print(f"    Type: {result.get('type', 'unknown')}")
        else:
            print(f"  ✗ {location}: {result.get('error_message', 'Unknown error')}")
        print()

if __name__ == "__main__":
    print("Enhanced Historical Weather Test Suite")
    print("=" * 60)
    
    # Test coordinates API first
    test_coordinates_api()
    
    # Test natural language historical weather queries
    test_natural_language_queries()
    
    # Test intelligent get_weather function
    test_intelligent_get_weather()
    
    print("\n" + "=" * 60)
    print("Test suite completed!")
