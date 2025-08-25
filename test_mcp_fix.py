#!/usr/bin/env python3
"""
Test script to verify MCP tools integration is working correctly.
"""

import sys
import os
from pathlib import Path

# Add src to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "src"))

from mcp_chinook_server import get_mcp_tools, call_mcp_tool

def test_mcp_tools():
    """Test that MCP tools are working correctly."""
    
    print("🧪 Testing MCP Tools Integration")
    print("=" * 50)
    
    # Test 1: Check tools are defined
    print("\n1. Checking MCP tool definitions...")
    tools = get_mcp_tools()
    print(f"✓ Found {len(tools)} MCP tools:")
    for tool in tools:
        print(f"  - {tool['function']['name']}: {tool['function']['description']}")
    
    # Test 2: Test simple genre search
    print("\n2. Testing genre search...")
    result = call_mcp_tool("search_tracks_by_genre", {
        "genre_name": "Bossa Nova",
        "limit": 5,
        "max_price": 0.99
    })
    
    if result["success"]:
        print(f"✓ Found {result['row_count']} Bossa Nova tracks under $0.99")
        if result["results"]:
            first_track = result["results"][0]
            print(f"  Example: {first_track['TrackName']} by {first_track['ArtistName']} - ${first_track['UnitPrice']}")
    else:
        print(f"✗ Error: {result['error']}")
    
    # Test 3: Test duration + price search
    print("\n3. Testing duration and price search...")
    result = call_mcp_tool("search_tracks_by_duration_and_price", {
        "genre": "Jazz",
        "min_duration": 180,
        "max_duration": 240, 
        "max_price": 1.0,
        "limit": 5
    })
    
    if result["success"]:
        print(f"✓ Found {result['row_count']} Jazz tracks (3-4 minutes, under $1.00)")
        if result["results"]:
            first_track = result["results"][0]
            print(f"  Example: {first_track['TrackName']} - {first_track['Duration']} - ${first_track['UnitPrice']}")
    else:
        print(f"✗ Error: {result['error']}")
    
    # Test 4: Test custom query
    print("\n4. Testing custom SQL query...")
    result = call_mcp_tool("execute_query", {
        "query": "SELECT COUNT(*) as total_tracks FROM Track"
    })
    
    if result["success"]:
        total_tracks = result["results"][0]["total_tracks"]
        print(f"✓ Database contains {total_tracks} total tracks")
    else:
        print(f"✗ Error: {result['error']}")
    
    # Test 5: Test authentication (with fake data)
    print("\n5. Testing customer authentication...")
    result = call_mcp_tool("authenticate_customer", {
        "email": "fake@example.com",
        "phone": "555-1234",
        "postal_code": "12345"
    })
    
    if not result["authenticated"]:
        print("✓ Authentication correctly rejected fake credentials")
    else:
        print("✗ Authentication should have rejected fake credentials")
    
    print("\n" + "=" * 50)
    print("🎉 MCP Tools Integration Test Complete!")

if __name__ == "__main__":
    test_mcp_tools()