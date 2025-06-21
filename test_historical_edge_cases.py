#!/usr/bin/env python3
"""
Test script for various historical weather edge cases
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from weatheragent.sub_agents.meterologist.agent import get_historical_weather, get_weather

def test_edge_cases():
    """Test various edge cases for historical weather"""
    
    print("=== Testing various historical weather edge cases ===\n")
    
    # Test 1: Very long period (should work)
    print("1. Testing 'past 10 years' for India...")
    result = get_historical_weather("India", time_period="past 10 years", variables="basic")
    print(f"Status: {result.get('status')}")
    if result.get('status') == 'success':
        print(f"Period: {result.get('period')}")
        print(f"Total days: {len(result.get('daily_data', []))}")
    else:
        print(f"Error: {result.get('error_message')}")
    
    print("\n" + "-"*50 + "\n")
    
    # Test 2: Recent period (should fail due to 5-day delay)
    print("2. Testing 'past 3 days' for India (should fail due to 5-day delay)...")
    result = get_historical_weather("India", time_period="past 3 days", variables="basic")
    print(f"Status: {result.get('status')}")
    if result.get('status') == 'error':
        print(f"Expected error: {result.get('error_message')}")
    
    print("\n" + "-"*50 + "\n")
    
    # Test 3: Different variable types
    print("3. Testing 'agricultural' variables for India in 2023...")
    result = get_historical_weather("India", time_period="2023", variables="agricultural")
    print(f"Status: {result.get('status')}")
    if result.get('status') == 'success':
        print(f"Variables available: {list(result.get('daily_data', [{}])[0].keys()) if result.get('daily_data') else 'None'}")
    
    print("\n" + "-"*50 + "\n")
    
    # Test 4: City instead of country
    print("4. Testing historical weather for Mumbai (city) - past 2 years...")
    result = get_historical_weather("Mumbai", time_period="past 2 years", variables="detailed")
    print(f"Status: {result.get('status')}")
    if result.get('status') == 'success':
        print(f"Location: {result.get('location')}")
        print(f"Period: {result.get('period')}")
        print(f"Total days: {len(result.get('daily_data', []))}")
    
    print("\n" + "-"*50 + "\n")
    
    # Test 5: Test the unified get_weather function
    print("5. Testing unified get_weather function with historical query...")
    result = get_weather("India", query="past 2 years historical data")
    print(f"Status: {result.get('status')}")
    if result.get('status') == 'success':
        print(f"Location: {result.get('location')}")
        if 'period' in result:  # Historical data
            print(f"Period: {result.get('period')}")
            print(f"Total days: {len(result.get('daily_data', []))}")
        else:  # Current weather
            print("Returned current weather data")
    
    print("\n" + "-"*50 + "\n")
    
    # Test 6: Test winter season
    print("6. Testing winter 2022 for India...")
    result = get_historical_weather("India", time_period="winter 2022", variables="weather_analysis")
    print(f"Status: {result.get('status')}")
    if result.get('status') == 'success':
        print(f"Period: {result.get('period')}")
        print(f"Total days: {len(result.get('daily_data', []))}")
        if result.get('summary_statistics'):
            print("Summary stats available:")
            for key, value in result.get('summary_statistics').items():
                print(f"  {key}: {value}")

def test_data_going_back_to_1940():
    """Test that we can access data back to 1940"""
    print("\n=== Testing data access back to 1940 ===\n")
    
    # Test accessing 1940 data
    print("Testing data from 1940 for India...")
    result = get_historical_weather("India", start_date="1940-01-01", end_date="1940-12-31", variables="basic")
    print(f"Status: {result.get('status')}")
    if result.get('status') == 'success':
        print(f"Successfully retrieved data from 1940!")
        print(f"Period: {result.get('period')}")
        print(f"Total days: {len(result.get('daily_data', []))}")
        if result.get('summary_statistics'):
            print("1940 Summary stats:")
            for key, value in result.get('summary_statistics').items():
                print(f"  {key}: {value}")
    else:
        print(f"Error: {result.get('error_message')}")
    
    print("\n" + "-"*30 + "\n")
    
    # Test accessing data before 1940 (should fail)
    print("Testing data from 1939 (should fail)...")
    result = get_historical_weather("India", start_date="1939-01-01", end_date="1939-12-31", variables="basic")
    print(f"Status: {result.get('status')}")
    if result.get('status') == 'error':
        print(f"Expected error: {result.get('error_message')}")

if __name__ == "__main__":
    test_edge_cases()
    test_data_going_back_to_1940()
