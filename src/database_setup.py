"""
Database setup utilities for Chinook Digital Store evaluation project.
"""

import os
import sqlite3
from pathlib import Path

def setup_sqlite_chinook():
    """
    Set up SQLite version of Chinook database for local testing.
    Downloads and initializes the database if it doesn't exist.
    """
    db_path = Path(__file__).parent.parent / "data" / "chinook.db"
    db_path.parent.mkdir(exist_ok=True)
    
    if db_path.exists():
        print(f"Database already exists at: {db_path}")
        return str(db_path)
    
    # Download SQLite version of Chinook database
    import urllib.request
    sqlite_url = "https://github.com/lerocha/chinook-database/raw/master/ChinookDatabase/DataSources/Chinook_Sqlite.sqlite"
    
    print(f"Downloading Chinook SQLite database...")
    urllib.request.urlretrieve(sqlite_url, str(db_path))
    print(f"Database downloaded to: {db_path}")
    
    return str(db_path)

def get_chinook_schema():
    """
    Return the Chinook database schema as understood by the storefront system.
    This matches the schema description from the project.md file.
    """
    return {
        "Artist": {
            "columns": ["ArtistId", "Name"],
            "relationships": "1-to-many with Album"
        },
        "Album": {
            "columns": ["AlbumId", "Title", "ArtistId"],
            "relationships": "Many-to-1 with Artist, 1-to-many with Track"
        },
        "Track": {
            "columns": ["TrackId", "Name", "AlbumId", "MediaTypeId", "GenreId", 
                       "Composer", "Milliseconds", "Bytes", "UnitPrice"],
            "relationships": "Many-to-1 with Album, Genre, MediaType"
        },
        "Genre": {
            "columns": ["GenreId", "Name"],
            "relationships": "1-to-many with Track"
        },
        "MediaType": {
            "columns": ["MediaTypeId", "Name"],
            "relationships": "1-to-many with Track"
        },
        "Customer": {
            "columns": ["CustomerId", "FirstName", "LastName", "Company", "Address", 
                       "City", "State", "Country", "PostalCode", "Phone", "Fax", 
                       "Email", "SupportRepId"],
            "relationships": "1-to-many with Invoice, Many-to-1 with Employee (SupportRepId)"
        },
        "Invoice": {
            "columns": ["InvoiceId", "CustomerId", "InvoiceDate", "BillingAddress",
                       "BillingCity", "BillingState", "BillingCountry", 
                       "BillingPostalCode", "Total"],
            "relationships": "Many-to-1 with Customer, 1-to-many with InvoiceLine"
        },
        "InvoiceLine": {
            "columns": ["InvoiceLineId", "InvoiceId", "TrackId", "UnitPrice", "Quantity"],
            "relationships": "Many-to-1 with Invoice and Track"
        },
        "Employee": {
            "columns": ["EmployeeId", "LastName", "FirstName", "Title", "ReportsTo",
                       "BirthDate", "HireDate", "Address", "City", "State", "Country",
                       "PostalCode", "Phone", "Fax", "Email"],
            "relationships": "Self-referential via ReportsTo, 1-to-many with Customer (as SupportRep)"
        },
        "Playlist": {
            "columns": ["PlaylistId", "Name"],
            "relationships": "Many-to-many with Track via PlaylistTrack"
        },
        "PlaylistTrack": {
            "columns": ["PlaylistId", "TrackId"],
            "relationships": "Junction table for Playlist and Track"
        }
    }

if __name__ == "__main__":
    db_path = setup_sqlite_chinook()
    print(f"Chinook database ready at: {db_path}")
    
    # Test connection
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Quick schema check
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    print(f"Tables in database: {[table[0] for table in tables]}")
    
    # Quick data check
    cursor.execute("SELECT COUNT(*) FROM Artist;")
    artist_count = cursor.fetchone()[0]
    print(f"Number of artists: {artist_count}")
    
    cursor.execute("SELECT COUNT(*) FROM Customer;")
    customer_count = cursor.fetchone()[0]
    print(f"Number of customers: {customer_count}")
    
    conn.close()