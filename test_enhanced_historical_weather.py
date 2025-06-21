#!/usr/bin/env python3
"""
Enhanced test script for the historical weather API with comprehensive error handling
and various data retrieval types.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from weatheragent.sub_agents.meterologist.agent import get_historical_weather, get_city_coordinates
import json

def test_coordinates_api():
    """Test the coordinates API first"""
    print("=== Testing Coordinates API ===")
    
    test_cities = ["London", "New York", "India", "Germany", "Tokyo"]
    
    for city in test_cities:
        print(f"\nTesting coordinates for: {city}")
        result = get_city_coordinates(city)
        if result["status"] == "success":
            print(f"✅ Success: {result['name']}, {result['country']} ({result['latitude']}, {result['longitude']})")
        else:
            print(f"❌ Error: {result['error_message']}")

def test_historical_weather_basic():
    """Test basic historical weather retrieval"""
    print("\n=== Testing Basic Historical Weather ===")
    
    # Test with London for a short period
    result = get_historical_weather("London", "2024-01-01", "2024-01-07", "basic")
    
    if result["status"] == "success":
        print(f"✅ Success for London!")
        print(f"Location: {result['location']}")
        print(f"Period: {result['period']}")
        print(f"Data type: {result['data_type']}")
        print(f"Number of daily records: {len(result['daily_data'])}")
        
        if result['daily_data']:
            print("Sample daily data:")
            for i, day in enumerate(result['daily_data'][:3]):  # Show first 3 days
                print(f"  Day {i+1}: {day}")
        
        if 'summary_statistics' in result:
            print("Summary Statistics:")
            for key, value in result['summary_statistics'].items():
                print(f"  {key}: {value}")
    else:
        print(f"❌ Error: {result['error_message']}")

def test_historical_weather_comprehensive():
    """Test comprehensive historical weather data"""
    print("\n=== Testing Comprehensive Historical Weather ===")
    
    # Test different variable types
    test_types = ["basic", "detailed", "solar", "agricultural", "pressure_analysis"]
    
    for var_type in test_types:
        print(f"\nTesting {var_type} variables:")
        result = get_historical_weather("New York", "2024-01-01", "2024-01-03", var_type)
        
        if result["status"] == "success":
            print(f"✅ Success for {var_type}")
            print(f"  Daily records: {len(result['daily_data'])}")
            if 'hourly_sample' in result:
                print(f"  Hourly samples: {len(result['hourly_sample'])}")
        else:
            print(f"❌ Error for {var_type}: {result['error_message']}")

def test_historical_weather_countries():
    """Test historical weather for countries"""
    print("\n=== Testing Historical Weather for Countries ===")
    
    countries = ["Germany", "India", "Japan"]
    
    for country in countries:
        print(f"\nTesting {country}:")
        result = get_historical_weather(country, "2024-01-01", "2024-01-05", "basic")
        
        if result["status"] == "success":
            print(f"✅ Success for {country}")
            print(f"  Representative location: {result['location']}")
            print(f"  Location type: {result['location_type']}")
            print(f"  Daily records: {len(result['daily_data'])}")
        else:
            print(f"❌ Error for {country}: {result['error_message']}")

def test_error_handling():
    """Test error handling scenarios"""
    print("\n=== Testing Error Handling ===")
    
    # Test invalid date format
    print("Testing invalid date format:")
    result = get_historical_weather("London", "2024/01/01", "2024-01-07", "basic")
    if result["status"] == "error":
        print(f"✅ Correctly caught invalid date format: {result['error_message']}")
    else:
        print("❌ Should have caught invalid date format")
    
    # Test too recent date
    print("\nTesting too recent date:")
    result = get_historical_weather("London", "2025-06-19", "2025-06-21", "basic")
    if result["status"] == "error":
        print(f"✅ Correctly caught too recent date: {result['error_message']}")
    else:
        print("❌ Should have caught too recent date")
    
    # Test too old date
    print("\nTesting too old date:")
    result = get_historical_weather("London", "1930-01-01", "1930-01-07", "basic")
    if result["status"] == "error":
        print(f"✅ Correctly caught too old date: {result['error_message']}")
    else:
        print("❌ Should have caught too old date")
    
    # Test invalid city
    print("\nTesting invalid city:")
    result = get_historical_weather("NonExistentCity12345", "2024-01-01", "2024-01-07", "basic")
    if result["status"] == "error":
        print(f"✅ Correctly caught invalid city: {result['error_message']}")
    else:
        print("❌ Should have caught invalid city")

def main():
    """Run all tests"""
    print("Starting Enhanced Historical Weather API Tests")
    print("=" * 50)
    
    try:
        test_coordinates_api()
        test_historical_weather_basic()
        test_historical_weather_comprehensive()
        test_historical_weather_countries()
        test_error_handling()
        
        print("\n" + "=" * 50)
        print("✅ All tests completed!")
        
    except Exception as e:
        print(f"\n❌ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
