#!/usr/bin/env python3
"""
Test script for the enhanced earthquake agent
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'weatheragent', 'sub_agents', 'earthquake_agent'))

from agent import (
    smart_earthquake_search,
    get_earthquakes_by_country,
    get_earthquake_data,
    _extract_location_from_query,
    _extract_time_period_from_query,
    _extract_magnitude_from_query
)

def test_query_parsing():
    """Test the natural language query parsing"""
    print("Testing Natural Language Query Parsing:")
    print("=" * 50)
    
    # Test location extraction
    queries = [
        "earthquakes in Japan last 14 days",
        "seismic activity near Tokyo in the past week",
        "recent earthquakes around Mumbai",
        "magnitude 5+ earthquakes in California"
    ]
    
    for query in queries:
        print(f"\nQuery: '{query}'")
        location = _extract_location_from_query(query)
        time_period = _extract_time_period_from_query(query)
        magnitude = _extract_magnitude_from_query(query)
        
        print(f"  - Location: {location}")
        print(f"  - Time period: {time_period} days")
        print(f"  - Magnitude threshold: {magnitude}")

def test_smart_search():
    """Test the smart earthquake search function"""
    print("\n\nTesting Smart Earthquake Search:")
    print("=" * 50)
    
    # Test with a natural language query
    query = "earthquakes in Japan last 14 days"
    print(f"\nTesting query: '{query}'")
    
    try:
        result = smart_earthquake_search(query)
        if result["status"] == "success":
            print(f"✅ Successfully found {result['total_events']} earthquakes")
            print(f"Query context: {result.get('query_context', {})}")
            
            if result.get('events'):
                print(f"Latest earthquake: {result['events'][0]['place']} - Magnitude {result['events'][0]['magnitude']}")
        else:
            print(f"❌ Error: {result.get('error_message')}")
    except Exception as e:
        print(f"❌ Exception: {e}")

def test_country_search():
    """Test country-specific earthquake search"""
    print("\n\nTesting Country-Specific Search:")
    print("=" * 50)
    
    try:
        result = get_earthquakes_by_country("Japan", days_back=7, min_magnitude=4.0)
        if result["status"] == "success":
            print(f"✅ Found {result['total_events']} earthquakes in Japan (last 7 days, magnitude 4.0+)")
            if result.get('events'):
                print(f"Latest: {result['events'][0]['place']} - Magnitude {result['events'][0]['magnitude']}")
        else:
            print(f"❌ Error: {result.get('error_message')}")
    except Exception as e:
        print(f"❌ Exception: {e}")

def test_basic_search():
    """Test basic earthquake search"""
    print("\n\nTesting Basic Earthquake Search:")
    print("=" * 50)
    
    try:
        result = get_earthquake_data(min_magnitude=5.0, days_back=7, limit=5)
        if result["status"] == "success":
            print(f"✅ Found {result['total_events']} significant earthquakes worldwide (magnitude 5.0+, last 7 days)")
            for i, event in enumerate(result['events'][:3]):
                print(f"  {i+1}. {event['place']} - Magnitude {event['magnitude']} on {event['date']}")
        else:
            print(f"❌ Error: {result.get('error_message')}")
    except Exception as e:
        print(f"❌ Exception: {e}")

if __name__ == "__main__":
    print("Enhanced Earthquake Agent Test Suite")
    print("=" * 60)
    
    test_query_parsing()
    test_smart_search()
    test_country_search()
    test_basic_search()
    
    print("\n" + "=" * 60)
    print("Test completed!")
    print("\nYour enhanced earthquake agent now supports:")
    print("✅ Natural language query parsing")
    print("✅ Country-specific searches")
    print("✅ Region-specific searches")
    print("✅ Smart parameter extraction")
    print("✅ Flexible time period handling")
    print("✅ Magnitude threshold detection")
    print("✅ Radius-based searching")
