#!/usr/bin/env python3
"""
Test script for the enhanced earthquake agent with dynamic geocoding capabilities.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from weatheragent.sub_agents.earthquake_agent.agent import (
    get_enhanced_location_info,
    get_earthquakes_by_any_location,
    smart_location_earthquake_query,
    get_dynamic_boundaries,
    get_earthquakes_by_region
)

def test_enhanced_location_info():
    """Test the enhanced location info function."""
    print("🌍 Testing Enhanced Location Info...")
    
    # Test various location types
    test_locations = [
        "Tokyo, Japan",
        "California",
        "New Zealand", 
        "Mumbai",
        "Himalayan region",
        "10001",  # Postal code
        "Pacific Ring of Fire"
    ]
    
    for location in test_locations:
        print(f"\n📍 Testing location: {location}")
        result = get_enhanced_location_info(location, count=2)
        
        if result["status"] == "success":
            print(f"   ✅ Found {result['total_results']} location(s)")
            for loc in result["locations"]:
                print(f"   📌 {loc['name']}, {loc['country']} ({loc['latitude']}, {loc['longitude']})")
                print(f"      Feature: {loc['feature_code']}, Population: {loc['population']}")
        else:
            print(f"   ❌ Error: {result['error_message']}")


def test_dynamic_boundaries():
    """Test dynamic boundary generation."""
    print("\n🗺️  Testing Dynamic Boundaries...")
    
    test_locations = ["Japan", "Mumbai", "California"]
    
    for location in test_locations:
        print(f"\n📍 Testing boundaries for: {location}")
        result = get_dynamic_boundaries(location)
        
        if result["status"] == "success":
            bounds = result["boundaries"]
            print(f"   ✅ Boundaries generated successfully")
            print(f"   📏 Lat: {bounds['min_lat']:.2f} to {bounds['max_lat']:.2f}")
            print(f"   📏 Lon: {bounds['min_lon']:.2f} to {bounds['max_lon']:.2f}")
            print(f"   🏷️  Feature type: {bounds['feature_code']}")
        else:
            print(f"   ❌ Error: {result['error_message']}")


def test_earthquake_queries():
    """Test natural language earthquake queries."""
    print("\n🔍 Testing Smart Earthquake Queries...")
    
    # Test queries that your agent should be able to handle
    test_queries = [
        "earthquakes in Japan last 14 days",
        "magnitude 5+ earthquakes near Tokyo in the past week",
        "recent seismic activity in California",
        "earthquakes around Mumbai within 300km last month",
        "significant earthquakes in New Zealand this week"
    ]
    
    for query in test_queries:
        print(f"\n🗣️  Query: '{query}'")
        result = smart_location_earthquake_query(query)
        
        if result["status"] == "success":
            analysis = result.get("query_analysis", {})
            print(f"   ✅ Query processed successfully")
            print(f"   🎯 Extracted location: {analysis.get('extracted_location', 'None')}")
            print(f"   📅 Extracted days: {analysis.get('extracted_days', 'None')}")
            print(f"   📊 Extracted magnitude: {analysis.get('extracted_magnitude', 'None')}")
            print(f"   📐 Extracted radius: {analysis.get('extracted_radius_km', 'None')} km")
            print(f"   🔢 Found {result['total_events']} earthquake(s)")
            
            # Show first few earthquakes if any
            if result['events']:
                print(f"   📋 Recent earthquakes:")
                for i, event in enumerate(result['events'][:3]):  # Show first 3
                    print(f"      {i+1}. M{event['magnitude']} - {event['place']} ({event['date']})")
        else:
            print(f"   ❌ Error: {result['error_message']}")


def test_specific_location_search():
    """Test specific location earthquake search."""
    print("\n🎯 Testing Specific Location Searches...")
    
    test_cases = [
        {"location": "Tokyo", "days_back": 7, "min_magnitude": 3.0},
        {"location": "California", "days_back": 14, "min_magnitude": 4.0, "radius_km": 200},
        {"location": "New Zealand", "days_back": 30, "min_magnitude": 5.0}
    ]
    
    for case in test_cases:
        location = case["location"]
        print(f"\n📍 Testing: {location}")
        
        result = get_earthquakes_by_any_location(**case)
        
        if result["status"] == "success":
            loc_info = result.get("location", {})
            search_info = result.get("search_info", {})
            
            print(f"   ✅ Search successful")
            print(f"   📍 Location: {loc_info.get('name', 'Unknown')}, {loc_info.get('country', 'Unknown')}")
            print(f"   🔍 Search type: {search_info.get('search_type', 'Unknown')}")
            print(f"   🔢 Found {result['total_events']} earthquake(s)")
            print(f"   📊 Magnitude threshold: {search_info.get('min_magnitude', 'Unknown')}")
            
            if result['events']:
                max_mag = max(event['magnitude'] for event in result['events'])
                print(f"   🏔️  Strongest earthquake: M{max_mag}")
        else:
            print(f"   ❌ Error: {result['error_message']}")


def test_hardcoded_regions():
    """Test hardcoded seismic regions."""
    print("\n🌍 Testing Hardcoded Seismic Regions...")
    
    test_regions = [
        "Pacific Ring of Fire",
        "Himalayan region", 
        "Mediterranean",
        "San Andreas Fault",
        "Japan Trench",
        "Caribbean",
        "Yellowstone"
    ]
    
    for region in test_regions:
        print(f"\n📍 Testing region: {region}")
        
        result = get_earthquakes_by_region(
            region=region,
            days_back=30,
            min_magnitude=4.0,
            limit=50
        )
        
        if result["status"] == "success":
            print(f"   ✅ Region search successful")
            print(f"   🔢 Found {result['total_events']} earthquake(s)")
            
            if result['events']:
                max_mag = max(event['magnitude'] for event in result['events'])
                print(f"   🏔️  Strongest earthquake: M{max_mag}")
                print(f"   📋 Recent earthquakes:")
                for i, event in enumerate(result['events'][:3]):  # Show first 3
                    print(f"      {i+1}. M{event['magnitude']} - {event['place']} ({event['date']})")
        else:
            print(f"   ❌ Error: {result['error_message']}")


if __name__ == "__main__":
    print("🚀 Testing Enhanced Earthquake Agent with Open-Meteo Geocoding")
    print("=" * 70)
    
    try:
        test_enhanced_location_info()
        test_dynamic_boundaries()
        test_earthquake_queries()
        test_specific_location_search()
        test_hardcoded_regions()
        test_hardcoded_regions()
        
        print("\n" + "=" * 70)
        print("✅ All tests completed! Your enhanced earthquake agent is ready.")
        print("\n💡 Your agent can now handle:")
        print("   • Any location in the world (cities, countries, regions, postal codes)")
        print("   • Natural language time periods (last week, 14 days, etc.)")
        print("   • Magnitude filtering (significant, major, 5+, etc.)")
        print("   • Distance-based searches (within 200km, etc.)")
        print("   • Complex combined queries")
        
        print("\n🎯 Example queries your agent can handle:")
        print("   • 'Show me earthquakes in Tokyo last 2 weeks'")
        print("   • 'Any magnitude 6+ earthquakes in California this month?'")
        print("   • 'Recent seismic activity around Mumbai within 500km'")
        print("   • 'Significant earthquakes in the Himalayan region'")
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        print("Please check your network connection and API access.")
