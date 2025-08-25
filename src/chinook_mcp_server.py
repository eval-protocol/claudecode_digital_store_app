#!/usr/bin/env python3
"""
Real MCP server for Chinook database operations.
Provides a proper MCP server that can be connected to by evaluation tools.
"""

import sqlite3
import json
import sys
import os
import argparse
from pathlib import Path
from typing import Dict, List, Any, Optional
from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, Field

# Configure the MCP server
mcp = FastMCP(
    "Chinook Digital Store",
    log_level="INFO"
)

# Get database path from environment or default
DB_PATH = os.getenv("CHINOOK_DB_PATH", str(Path(__file__).parent.parent / "data" / "chinook.db"))

def get_db_connection():
    """Get a database connection."""
    if not os.path.exists(DB_PATH):
        raise FileNotFoundError(f"Database not found at {DB_PATH}")
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # Enable column access by name
    return conn

class SearchTracksInput(BaseModel):
    genre_name: str = Field(description="Genre to search for (partial match)")
    limit: int = Field(default=25, description="Maximum results to return")
    max_price: Optional[float] = Field(default=None, description="Maximum price filter (optional)")

class SearchTracksByDurationInput(BaseModel):
    genre: str = Field(description="Genre to search for")
    min_duration: int = Field(description="Minimum duration in seconds")
    max_duration: int = Field(description="Maximum duration in seconds") 
    max_price: float = Field(description="Maximum price")
    limit: int = Field(default=25, description="Maximum results to return")

class ExecuteQueryInput(BaseModel):
    query: str = Field(description="SQL query to execute")
    params: Optional[List[str]] = Field(default=None, description="Query parameters (optional)")

class AuthenticateCustomerInput(BaseModel):
    email: str = Field(description="Customer email")
    phone: str = Field(description="Customer phone number")
    postal_code: str = Field(description="Customer postal code")

@mcp.tool()
def search_tracks_by_genre(input: SearchTracksInput) -> Dict[str, Any]:
    """Search for tracks by genre with optional price filtering."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
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
        
        params = [f"%{input.genre_name}%"]
        
        if input.max_price is not None:
            query += " AND t.UnitPrice <= ?"
            params.append(input.max_price)
            
        query += " ORDER BY ar.Name, a.Title, t.Name LIMIT ?"
        params.append(input.limit)
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        results = [dict(row) for row in rows]
        
        return {
            "success": True,
            "results": results,
            "row_count": len(results),
            "query_summary": f"Found {len(results)} {input.genre_name} tracks" + (f" under ${input.max_price}" if input.max_price else "")
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

@mcp.tool()
def search_tracks_by_duration_and_price(input: SearchTracksByDurationInput) -> Dict[str, Any]:
    """Search tracks by genre, duration range and price."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
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
        
        params = [f"%{input.genre}%", input.min_duration * 1000, input.max_duration * 1000, input.max_price, input.limit]
        cursor.execute(query, params)
        rows = cursor.fetchall()
        results = [dict(row) for row in rows]
        
        return {
            "success": True,
            "results": results,
            "row_count": len(results),
            "query_summary": f"Found {len(results)} {input.genre} tracks between {input.min_duration}-{input.max_duration}s under ${input.max_price}"
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

@mcp.tool()
def execute_query(input: ExecuteQueryInput) -> Dict[str, Any]:
    """Execute a custom SQL query against the Chinook database."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if input.params:
            cursor.execute(input.query, input.params)
        else:
            cursor.execute(input.query)
            
        if input.query.strip().upper().startswith(('SELECT', 'WITH')):
            rows = cursor.fetchall()
            results = [dict(row) for row in rows]
            return {
                "success": True,
                "results": results,
                "row_count": len(results),
                "query_summary": f"Query returned {len(results)} rows"
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

@mcp.tool()
def authenticate_customer(input: AuthenticateCustomerInput) -> Dict[str, Any]:
    """Authenticate a customer using email, phone, and postal code."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        query = """
        SELECT CustomerId, FirstName, LastName, Email, Phone, PostalCode, SupportRepId
        FROM Customer 
        WHERE Email = ? AND Phone = ? AND PostalCode = ?
        """
        
        cursor.execute(query, [input.email, input.phone, input.postal_code])
        rows = cursor.fetchall()
        
        if len(rows) == 1:
            customer = dict(rows[0])
            return {
                "authenticated": True,
                "customer": customer,
                "message": f"Customer {customer['FirstName']} {customer['LastName']} authenticated successfully"
            }
        elif len(rows) > 1:
            return {
                "authenticated": False,
                "error": "Multiple customers found - escalate to support",
                "message": "Authentication failed: ambiguous customer data"
            }
        else:
            return {
                "authenticated": False,
                "error": "No matching customer found",
                "message": "Authentication failed: invalid credentials"
            }
            
    except Exception as e:
        return {
            "authenticated": False,
            "error": str(e),
            "error_type": type(e).__name__
        }
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Chinook MCP Server")
    parser.add_argument("--port", type=int, default=3001, help="Port to run the server on")
    parser.add_argument("--host", default="localhost", help="Host to run the server on")
    
    args = parser.parse_args()
    
    print(f"Starting Chinook MCP Server on {args.host}:{args.port}")
    print(f"Database path: {DB_PATH}")
    
    # Verify database exists
    if not os.path.exists(DB_PATH):
        print(f"ERROR: Database not found at {DB_PATH}")
        sys.exit(1)
    
    # Run the server
    mcp.run(transport="stdio")
