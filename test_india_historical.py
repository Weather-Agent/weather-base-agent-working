#!/usr/bin/env python3
"""
Test script for historical weather functionality with India example
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from weatheragent.sub_agents.meterologist.agent import get_historical_weather

def test_india_historical_weather():
    """Test historical weather for India with natural language query"""
    print("Testing historical weather for India - past 5 years...")
    
    # Test the query that was mentioned
    result = get_historical_weather("India", time_period="past 5 years", variables="detailed")
    
    print("\n=== RESULT ===")
    print(f"Status: {result.get('status')}")
    
    if result.get('status') == 'success':
        print(f"Location: {result.get('location')}")
        print(f"Period: {result.get('period')}")
        print(f"Data Type: {result.get('data_type')}")
        print(f"Coordinates: {result.get('coordinates')}")
        
        # Print summary statistics
        if result.get('summary_statistics'):
            print("\n=== SUMMARY STATISTICS ===")
            for key, value in result.get('summary_statistics').items():
                print(f"{key}: {value}")
        
        # Print first few days of data
        if result.get('daily_data'):
            print(f"\n=== SAMPLE DATA (first 5 days) ===")
            for i, day in enumerate(result.get('daily_data')[:5]):
                print(f"Date: {day.get('date')}")
                for key, value in day.items():
                    if key != 'date':
                        print(f"  {key}: {value}")
                print()
        
        print(f"Total days of data: {len(result.get('daily_data', []))}")
        
    else:
        print(f"Error: {result.get('error_message')}")

def test_specific_year():
    """Test historical weather for a specific year"""
    print("\n" + "="*50)
    print("Testing historical weather for India - year 2023...")
    
    result = get_historical_weather("India", time_period="2023", variables="basic")
    
    print(f"Status: {result.get('status')}")
    
    if result.get('status') == 'success':
        print(f"Location: {result.get('location')}")
        print(f"Period: {result.get('period')}")
        
        # Print summary statistics
        if result.get('summary_statistics'):
            print("\n=== 2023 SUMMARY STATISTICS ===")
            for key, value in result.get('summary_statistics').items():
                print(f"{key}: {value}")
        
        print(f"Total days of data: {len(result.get('daily_data', []))}")
        
    else:
        print(f"Error: {result.get('error_message')}")

def test_seasonal_query():
    """Test historical weather for a specific season"""
    print("\n" + "="*50)
    print("Testing historical weather for India - summer 2023...")
    
    result = get_historical_weather("India", time_period="summer 2023", variables="weather_analysis")
    
    print(f"Status: {result.get('status')}")
    
    if result.get('status') == 'success':
        print(f"Location: {result.get('location')}")
        print(f"Period: {result.get('period')}")
        
        # Print summary statistics
        if result.get('summary_statistics'):
            print("\n=== SUMMER 2023 STATISTICS ===")
            for key, value in result.get('summary_statistics').items():
                print(f"{key}: {value}")
        
        print(f"Total days of data: {len(result.get('daily_data', []))}")
        
    else:
        print(f"Error: {result.get('error_message')}")

if __name__ == "__main__":
    test_india_historical_weather()
    test_specific_year()
    test_seasonal_query()
