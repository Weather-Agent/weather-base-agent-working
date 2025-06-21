#!/usr/bin/env python3
"""
Test script to verify date calculations for natural language queries
"""
import sys
import os
from datetime import datetime, timedelta
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from weatheragent.sub_agents.meterologist.agent import get_historical_weather

def verify_date_calculations():
    """Verify that date calculations are correct"""
    
    print("=== Verifying Date Calculations ===\n")
    
    # Current date
    today = datetime.now()
    print(f"Today's date: {today.strftime('%Y-%m-%d')}")
    print(f"5 days ago (API delay): {(today - timedelta(days=5)).strftime('%Y-%m-%d')}")
    
    # Expected dates for "past 5 years"
    expected_start = today.replace(year=today.year - 5, month=1, day=1)
    expected_end = today - timedelta(days=5)
    
    print(f"\nExpected for 'past 5 years':")
    print(f"Start: {expected_start.strftime('%Y-%m-%d')}")
    print(f"End: {expected_end.strftime('%Y-%m-%d')}")
    
    # Test the actual function
    result = get_historical_weather("India", time_period="past 5 years", variables="basic")
    
    if result.get('status') == 'success':
        actual_period = result.get('period')
        print(f"\nActual period returned: {actual_period}")
        
        start_str, end_str = actual_period.split(' to ')
        print(f"Start: {start_str}")
        print(f"End: {end_str}")
        
        # Verify dates match
        if start_str == expected_start.strftime('%Y-%m-%d') and end_str == expected_end.strftime('%Y-%m-%d'):
            print("\n✅ Date calculations are CORRECT!")
        else:
            print("\n❌ Date calculations don't match expectations")
    else:
        print(f"Error: {result.get('error_message')}")

def test_various_time_periods():
    """Test various time period calculations"""
    
    print("\n=== Testing Various Time Period Calculations ===\n")
    
    test_periods = [
        "past 1 year",
        "last 6 months", 
        "past 30 days",
        "2024",
        "2022-2024",
        "summer 2023",
        "winter 2022"
    ]
    
    for period in test_periods:
        print(f"Testing '{period}'...")
        result = get_historical_weather("India", time_period=period, variables="basic")
        
        if result.get('status') == 'success':
            print(f"  ✅ Period: {result.get('period')}")
            print(f"     Days: {len(result.get('daily_data', []))}")
        else:
            print(f"  ❌ Error: {result.get('error_message')}")
        print()

if __name__ == "__main__":
    verify_date_calculations()
    test_various_time_periods()
