#!/usr/bin/env python3
"""
Test script for the enhanced historical weather functionality
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from weatheragent.sub_agents.meterologist.agent import get_historical_weather
import json

def test_historical_weather():
    """Test various types of historical weather data retrieval"""
    
    print("🌤️  Testing Enhanced Historical Weather API")
    print("=" * 50)
    
    # Test cases with different variable types
    test_cases = [
        {
            "name": "Basic Historical Data",
            "city": "London",
            "start_date": "2024-01-01",
            "end_date": "2024-01-07",
            "variables": "basic"
        },
        {
            "name": "Detailed Weather Analysis", 
            "city": "New York",
            "start_date": "2024-02-01",
            "end_date": "2024-02-05",
            "variables": "detailed"
        },
        {
            "name": "Solar Radiation Data",
            "city": "Miami",
            "start_date": "2024-03-01",
            "end_date": "2024-03-03",
            "variables": "solar"
        },
        {
            "name": "Agricultural Data",
            "city": "Denver",
            "start_date": "2024-04-01",
            "end_date": "2024-04-03",
            "variables": "agricultural"
        },
        {
            "name": "Weather Analysis",
            "city": "Tokyo",
            "start_date": "2024-05-01",
            "end_date": "2024-05-03",
            "variables": "weather_analysis"
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{i}. {test_case['name']}")
        print(f"   Location: {test_case['city']}")
        print(f"   Period: {test_case['start_date']} to {test_case['end_date']}")
        print(f"   Variables: {test_case['variables']}")
        print("-" * 40)
        
        try:
            result = get_historical_weather(
                city=test_case['city'],
                start_date=test_case['start_date'],
                end_date=test_case['end_date'],
                variables=test_case['variables']
            )
            
            if result['status'] == 'success':
                print(f"   ✅ Success: {result['location']}")
                print(f"   📊 Data points: {len(result.get('daily_data', []))}")
                print(f"   🌡️  Data type: {result.get('data_type', 'N/A')}")
                
                # Show summary statistics if available
                if 'summary_statistics' in result and result['summary_statistics']:
                    print("   📈 Summary Statistics:")
                    for key, value in result['summary_statistics'].items():
                        print(f"      {key}: {value}")
                
                # Show sample daily data
                if result.get('daily_data') and len(result['daily_data']) > 0:
                    print("   📅 Sample Day:")
                    sample_day = result['daily_data'][0]
                    for key, value in sample_day.items():
                        if key != 'date':
                            print(f"      {key}: {value}")
                
                # Show hourly data info if available
                if 'hourly_sample' in result:
                    print(f"   ⏰ Hourly samples: {len(result['hourly_sample'])}")
                
            else:
                print(f"   ❌ Error: {result.get('error_message', 'Unknown error')}")
                
        except Exception as e:
            print(f"   ❌ Exception: {str(e)}")
    
    print("\n" + "=" * 50)
    print("Historical Weather API Test Complete!")

def test_edge_cases():
    """Test edge cases and error handling"""
    
    print("\n🔍 Testing Edge Cases")
    print("=" * 30)
    
    edge_cases = [
        {
            "name": "Invalid City",
            "city": "NonExistentCity12345",
            "start_date": "2024-01-01",
            "end_date": "2024-01-02",
            "variables": "basic"
        },
        {
            "name": "Date Too Recent",
            "city": "Paris",
            "start_date": "2025-06-20",  # Today's date
            "end_date": "2025-06-21",
            "variables": "basic"
        },
        {
            "name": "Date Too Old",
            "city": "Berlin",
            "start_date": "1930-01-01",
            "end_date": "1930-01-02",
            "variables": "basic"
        },
        {
            "name": "Invalid Date Format",
            "city": "Madrid",
            "start_date": "01-01-2024",  # Wrong format
            "end_date": "01-02-2024",
            "variables": "basic"
        }
    ]
    
    for i, test_case in enumerate(edge_cases, 1):
        print(f"\n{i}. {test_case['name']}")
        
        try:
            result = get_historical_weather(
                city=test_case['city'],
                start_date=test_case['start_date'],
                end_date=test_case['end_date'],
                variables=test_case['variables']
            )
            
            if result['status'] == 'error':
                print(f"   ✅ Expected error caught: {result['error_message']}")
            else:
                print(f"   ⚠️  Unexpected success: {result.get('location', 'N/A')}")
                
        except Exception as e:
            print(f"   ❌ Exception: {str(e)}")

if __name__ == "__main__":
    test_historical_weather()
    test_edge_cases()
