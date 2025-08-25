"""
Simple MCP server for Chinook database operations.
Provides database query tools for the storefront evaluation.
"""

import sqlite3
import json
import sys
import os
from pathlib import Path
from typing import Dict, List, Any, Optional

# Add the mcp server to Python path
mcp_server_path = Path(__file__).parent.parent / "mcp_server" / "src"
if mcp_server_path.exists():
    sys.path.insert(0, str(mcp_server_path))

class ChinookMCPServer:
    """Simple MCP server for Chinook database operations."""
    
    def __init__(self, db_path: str = None):
        # Support both direct path and environment variable
        if db_path:
            self.db_path = db_path
        else:
            # Get connection string from environment
            conn_string = os.getenv("POSTGRES_CONNECTION_STRING")
            if conn_string and conn_string.startswith("sqlite:///"):
                self.db_path = conn_string.replace("sqlite:///", "")
                # Make path absolute if it's relative
                if not os.path.isabs(self.db_path):
                    self.db_path = os.path.join(os.path.dirname(__file__), "..", self.db_path)
            else:
                # Default fallback
                self.db_path = str(Path(__file__).parent.parent / "data" / "chinook.db")
        
    def execute_query(self, query: str, params: Optional[List] = None) -> Dict[str, Any]:
        """
        Execute a SQL query against the Chinook database.
        Returns results in a structured format.
        """
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row  # Enable column access by name
            cursor = conn.cursor()
            
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
                
            if query.strip().upper().startswith(('SELECT', 'WITH')):
                rows = cursor.fetchall()
                results = [dict(row) for row in rows]
                return {
                    "success": True,
                    "results": results,
                    "row_count": len(results)
                }
            else:
                # For INSERT, UPDATE, DELETE
                affected_rows = cursor.rowcount
                conn.commit()
                return {
                    "success": True,
                    "affected_rows": affected_rows,
                    "message": f"Query executed successfully, {affected_rows} rows affected"
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__
            }
        finally:
            if 'conn' in locals():
                conn.close()
    
    def search_tracks_by_genre(self, genre_name: str, limit: int = 25, max_price: Optional[float] = None) -> Dict[str, Any]:
        """Search for tracks by genre with optional price filtering."""
        query = """
        SELECT 
            t.TrackId,
            t.Name as TrackName,
            a.Title as AlbumTitle,
            ar.Name as ArtistName,
            g.Name as GenreName,
            t.UnitPrice,
            t.Milliseconds,
            PRINTF('%.2f', t.UnitPrice) as FormattedPrice,
            PRINTF('%d:%02d', t.Milliseconds / 60000, (t.Milliseconds % 60000) / 1000) as Duration
        FROM Track t
        JOIN Album a ON t.AlbumId = a.AlbumId
        JOIN Artist ar ON a.ArtistId = ar.ArtistId  
        JOIN Genre g ON t.GenreId = g.GenreId
        WHERE g.Name LIKE ? COLLATE NOCASE
        """
        
        params = [f"%{genre_name}%"]
        
        if max_price is not None:
            query += " AND t.UnitPrice <= ?"
            params.append(max_price)
            
        query += " ORDER BY ar.Name, a.Title, t.Name LIMIT ?"
        params.append(limit)
        
        return self.execute_query(query, params)
    
    def search_tracks_by_duration_and_price(self, genre: str, min_duration: int, max_duration: int, max_price: float, limit: int = 25) -> Dict[str, Any]:
        """Search tracks by genre, duration range, and price."""
        query = """
        SELECT 
            t.TrackId,
            t.Name as TrackName,
            a.Title as AlbumTitle,
            ar.Name as ArtistName,
            g.Name as GenreName,
            t.UnitPrice,
            t.Milliseconds,
            PRINTF('%.2f', t.UnitPrice) as FormattedPrice,
            PRINTF('%d:%02d', t.Milliseconds / 60000, (t.Milliseconds % 60000) / 1000) as Duration
        FROM Track t
        JOIN Album a ON t.AlbumId = a.AlbumId
        JOIN Artist ar ON a.ArtistId = ar.ArtistId  
        JOIN Genre g ON t.GenreId = g.GenreId
        WHERE g.Name LIKE ? COLLATE NOCASE
        AND t.Milliseconds >= ?
        AND t.Milliseconds <= ?
        AND t.UnitPrice <= ?
        ORDER BY ar.Name, a.Title, t.Name 
        LIMIT ?
        """
        
        params = [f"%{genre}%", min_duration * 1000, max_duration * 1000, max_price, limit]
        return self.execute_query(query, params)
    
    def get_customer_by_triple_match(self, email: str, phone: str, postal_code: str) -> Dict[str, Any]:
        """Authenticate customer using triple-match (email, phone, postal_code)."""
        query = """
        SELECT CustomerId, FirstName, LastName, Email, Phone, PostalCode, SupportRepId
        FROM Customer 
        WHERE Email = ? AND Phone = ? AND PostalCode = ?
        """
        
        result = self.execute_query(query, [email, phone, postal_code])
        
        if result["success"] and result["results"]:
            if len(result["results"]) == 1:
                return {
                    "authenticated": True,
                    "customer": result["results"][0]
                }
            else:
                return {
                    "authenticated": False,
                    "error": "Multiple customers found - escalate to support"
                }
        else:
            return {
                "authenticated": False,
                "error": "No matching customer found"
            }

def get_mcp_tools():
    """Return the MCP tool definitions for the Chinook server in OpenAI function calling format."""
    return [
        {
            "type": "function",
            "function": {
                "name": "search_tracks_by_genre",
                "description": "Search for music tracks by genre with optional price filtering",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "genre_name": {"type": "string", "description": "Genre to search for (partial match)"},
                        "limit": {"type": "integer", "default": 25, "description": "Maximum results to return"},
                        "max_price": {"type": "number", "description": "Maximum price filter (optional)"}
                    },
                    "required": ["genre_name"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "search_tracks_by_duration_and_price",
                "description": "Search tracks by genre, duration range and price",
                "parameters": {
                    "type": "object", 
                    "properties": {
                        "genre": {"type": "string"},
                        "min_duration": {"type": "integer", "description": "Minimum duration in seconds"},
                        "max_duration": {"type": "integer", "description": "Maximum duration in seconds"}, 
                        "max_price": {"type": "number", "description": "Maximum price"},
                        "limit": {"type": "integer", "default": 25}
                    },
                    "required": ["genre", "min_duration", "max_duration", "max_price"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "execute_query",
                "description": "Execute a custom SQL query against the Chinook database",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "SQL query to execute"},
                        "params": {
                            "type": "array",
                            "description": "Query parameters (optional)",
                            "items": {"type": "string"}
                        }
                    },
                    "required": ["query"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "authenticate_customer", 
                "description": "Authenticate a customer using email, phone, and postal code",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "email": {"type": "string"},
                        "phone": {"type": "string"},
                        "postal_code": {"type": "string"}
                    },
                    "required": ["email", "phone", "postal_code"]
                }
            }
        }
    ]

def call_mcp_tool(tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """
    Call an MCP tool with proper error handling and response formatting.
    This simulates how the MCP tools would be called in a real MCP environment.
    """
    try:
        # Get default database path from environment
        server = ChinookMCPServer()
        
        if tool_name == "search_tracks_by_genre":
            return server.search_tracks_by_genre(
                genre_name=arguments["genre_name"],
                limit=arguments.get("limit", 25),
                max_price=arguments.get("max_price")
            )
        elif tool_name == "search_tracks_by_duration_and_price":
            return server.search_tracks_by_duration_and_price(
                genre=arguments["genre"],
                min_duration=arguments["min_duration"], 
                max_duration=arguments["max_duration"],
                max_price=arguments["max_price"],
                limit=arguments.get("limit", 25)
            )
        elif tool_name == "execute_query":
            return server.execute_query(
                query=arguments["query"],
                params=arguments.get("params")
            )
        elif tool_name == "authenticate_customer":
            return server.get_customer_by_triple_match(
                email=arguments["email"],
                phone=arguments["phone"],
                postal_code=arguments["postal_code"]
            )
        else:
            return {
                "success": False,
                "error": f"Unknown tool: {tool_name}",
                "error_type": "UnknownToolError"
            }
            
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__
        }

if __name__ == "__main__":
    # Test the server
    db_path = Path(__file__).parent.parent / "data" / "chinook.db"
    server = ChinookMCPServer(str(db_path))
    
    # Test genre search
    result = server.search_tracks_by_genre("Bossa Nova", limit=5, max_price=0.99)
    print("Bossa Nova search results:")
    print(json.dumps(result, indent=2))
    
    # Test duration + price search  
    result2 = server.search_tracks_by_duration_and_price("Jazz", 180, 240, 1.0, limit=5)
    print("\nJazz duration/price search results:")
    print(json.dumps(result2, indent=2))