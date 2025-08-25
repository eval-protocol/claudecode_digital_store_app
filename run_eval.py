#!/usr/bin/env python3
"""
Simple runner script to demonstrate the Chinook Digital Store evaluation.

This script runs a single evaluation test to demonstrate the system working end-to-end.
"""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "src"))

from mcp_chinook_server import ChinookMCPServer
from tests.test_chinook_storefront import storefront_dataset_to_evaluation_row, load_system_prompt

def run_simple_test():
    """Run a simple test to demonstrate the evaluation system."""
    print("🎵 Chinook Digital Store Evaluation Demo")
    print("=" * 50)
    
    # Initialize database
    db_path = project_root / "data" / "chinook.db"
    if not db_path.exists():
        print("❌ Database not found. Please run 'python src/database_setup.py' first.")
        return False
        
    mcp_server = ChinookMCPServer(str(db_path))
    
    # Test database connectivity
    print("\n🗄️  Testing database connectivity...")
    result = mcp_server.search_tracks_by_genre("Bossa Nova", limit=3, max_price=0.99)
    if result["success"]:
        print(f"✅ Database connected! Found {result['row_count']} Bossa Nova tracks under $0.99")
        for track in result["results"][:2]:  # Show first 2
            print(f"   • {track['TrackName']} by {track['ArtistName']} - ${track['FormattedPrice']}")
    else:
        print(f"❌ Database error: {result.get('error', 'Unknown error')}")
        return False
    
    # Test system prompt loading
    print("\n📋 Testing system prompt...")
    system_prompt = load_system_prompt()
    print(f"✅ System prompt loaded ({len(system_prompt)} characters)")
    
    # Test dataset processing
    print("\n📊 Testing dataset processing...")
    test_data = [
        {
            "id": "demo_browse_search",
            "prompt": "Find bossa nova songs under $0.99.",
            "expected_behaviors": ["browse_only_mode", "applies_limit", "price_filter", "genre_search"],
            "test_type": "browse_search"
        }
    ]
    
    evaluation_rows = storefront_dataset_to_evaluation_row(test_data)
    print(f"✅ Created {len(evaluation_rows)} evaluation rows")
    
    # Display the conversation that would be sent to LLM
    print("\n💬 Sample conversation for LLM evaluation:")
    print("-" * 50)
    row = evaluation_rows[0]
    print(f"System: {row.messages[0].content[:200]}...")
    print(f"User: {row.messages[1].content}")
    print(f"Expected behaviors: {row.input_metadata.dataset_info['expected_behaviors']}")
    
    # Display available MCP tools
    print(f"\n🔧 Available MCP tools: {len(row.tools)}")
    for tool in row.tools:
        print(f"   • {tool['name']}: {tool['description']}")
    
    print("\n✅ End-to-end system test completed successfully!")
    print("\n🚀 To run full evaluation with LLM:")
    print("   1. Set up API keys in .env file (OPENAI_API_KEY or FIREWORKS_API_KEY)")
    print("   2. Run: source venv/bin/activate && pytest tests/test_chinook_storefront.py -v")
    print("\n📊 To view results in Eval Protocol UI:")
    print("   source venv/bin/activate && ep logs")
    
    return True

if __name__ == "__main__":
    success = run_simple_test()
    sys.exit(0 if success else 1)