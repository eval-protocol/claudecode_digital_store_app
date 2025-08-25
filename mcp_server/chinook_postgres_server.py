#!/usr/bin/env python3
"""
MCP Postgres Server for Chinook Database
Adapted from: https://github.com/gldc/mcp-postgres
"""

import asyncio
import json
import logging
import os
import sys
from typing import Any, Dict, List, Optional, Sequence
from urllib.parse import quote

import asyncpg
from fastmcp import FastMCP
from pydantic import BaseModel, Field

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("chinook-postgres-server")


class QueryInput(BaseModel):
    """Input for SQL query execution."""
    sql: str = Field(description="SQL query to execute")
    row_limit: Optional[int] = Field(default=100, description="Maximum number of rows to return")


class QueryResult(BaseModel):
    """Result of SQL query execution."""
    columns: List[str] = Field(description="Column names")
    rows: List[List[Any]] = Field(description="Query result rows")
    row_count: int = Field(description="Number of rows returned")
    truncated: bool = Field(description="Whether results were truncated due to row limit")


class ChinookPostgresServer:
    """MCP server for Chinook PostgreSQL database."""
    
    def __init__(self):
        self.connection_string = self._build_connection_string()
        self.pool: Optional[asyncpg.Pool] = None
        self.readonly = os.getenv("POSTGRES_READONLY", "false").lower() == "true"
        self.statement_timeout_ms = int(os.getenv("POSTGRES_STATEMENT_TIMEOUT_MS", "15000"))
        
        # Create FastMCP instance
        self.mcp = FastMCP("Chinook Postgres Server")
        self._register_tools()
    
    def _build_connection_string(self) -> str:
        """Build PostgreSQL connection string from environment variables."""
        host = os.getenv("POSTGRES_HOST", "localhost")
        port = os.getenv("POSTGRES_PORT", "5432")
        database = os.getenv("POSTGRES_DB", "chinook")
        user = os.getenv("POSTGRES_USER", "chinook_user")
        password = os.getenv("POSTGRES_PASSWORD", "chinook_password")
        
        # URL encode the password in case it contains special characters
        password_encoded = quote(password)
        
        return f"postgresql://{user}:{password_encoded}@{host}:{port}/{database}"
    
    async def initialize(self):
        """Initialize the database connection pool."""
        try:
            self.pool = await asyncpg.create_pool(
                self.connection_string,
                min_size=1,
                max_size=10,
                command_timeout=self.statement_timeout_ms / 1000,
                server_settings={
                    'application_name': 'chinook_mcp_server',
                    'statement_timeout': f'{self.statement_timeout_ms}ms'
                }
            )
            logger.info("Database pool initialized successfully")
            
            # Test connection
            async with self.pool.acquire() as conn:
                result = await conn.fetchval("SELECT version();")
                logger.info(f"Connected to: {result}")
                
        except Exception as e:
            logger.error(f"Failed to initialize database pool: {e}")
            raise
    
    async def close(self):
        """Close the database connection pool."""
        if self.pool:
            await self.pool.close()
            logger.info("Database pool closed")
    
    def _register_tools(self):
        """Register MCP tools."""
        
        @self.mcp.tool()
        async def run_query_json(input: QueryInput) -> Dict[str, Any]:
            """
            Execute a SQL query and return results as structured JSON.
            
            This tool allows executing SQL queries against the Chinook database.
            Results are returned in a structured format with columns and rows.
            """
            return await self._execute_query(input.sql, input.row_limit)
        
        @self.mcp.tool()
        async def list_tables() -> Dict[str, Any]:
            """
            List all tables in the Chinook database with their descriptions.
            
            Returns table names, row counts, and basic schema information
            to help understand the database structure.
            """
            query = """
            SELECT 
                schemaname,
                tablename,
                tableowner
            FROM pg_tables 
            WHERE schemaname = 'public'
            ORDER BY tablename;
            """
            
            result = await self._execute_query(query, 1000)
            
            # Get row counts for each table
            tables_info = []
            if self.pool:
                async with self.pool.acquire() as conn:
                    for row in result["rows"]:
                        schema, table, owner = row
                        try:
                            count_result = await conn.fetchval(f'SELECT COUNT(*) FROM "{table}";')
                            tables_info.append({
                                "schema": schema,
                                "table": table,
                                "owner": owner,
                                "row_count": count_result
                            })
                        except Exception as e:
                            logger.warning(f"Failed to count rows in {table}: {e}")
                            tables_info.append({
                                "schema": schema,
                                "table": table,
                                "owner": owner,
                                "row_count": "unknown"
                            })
            
            return {
                "tables": tables_info,
                "total_tables": len(tables_info)
            }
        
        @self.mcp.tool()
        async def describe_table(table_name: str) -> Dict[str, Any]:
            """
            Get detailed schema information for a specific table.
            
            Args:
                table_name: Name of the table to describe
            
            Returns detailed column information including data types,
            constraints, and relationships.
            """
            # Get column information
            query = """
            SELECT 
                column_name,
                data_type,
                is_nullable,
                column_default,
                character_maximum_length,
                numeric_precision,
                numeric_scale
            FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = $1
            ORDER BY ordinal_position;
            """
            
            if not self.pool:
                raise RuntimeError("Database pool not initialized")
            
            async with self.pool.acquire() as conn:
                columns = await conn.fetch(query, table_name)
                
                # Get primary key information
                pk_query = """
                SELECT a.attname
                FROM pg_index i
                JOIN pg_attribute a ON a.attrelid = i.indrelid AND a.attnum = ANY(i.indkey)
                WHERE i.indrelid = $1::regclass AND i.indisprimary;
                """
                
                try:
                    primary_keys = await conn.fetch(pk_query, table_name)
                    pk_columns = [row['attname'] for row in primary_keys]
                except Exception:
                    pk_columns = []
                
                # Get foreign key information
                fk_query = """
                SELECT
                    kcu.column_name,
                    ccu.table_name AS foreign_table_name,
                    ccu.column_name AS foreign_column_name
                FROM information_schema.table_constraints AS tc
                JOIN information_schema.key_column_usage AS kcu
                    ON tc.constraint_name = kcu.constraint_name
                    AND tc.table_schema = kcu.table_schema
                JOIN information_schema.constraint_column_usage AS ccu
                    ON ccu.constraint_name = tc.constraint_name
                    AND ccu.table_schema = tc.table_schema
                WHERE tc.constraint_type = 'FOREIGN KEY'
                    AND tc.table_schema = 'public'
                    AND tc.table_name = $1;
                """
                
                try:
                    foreign_keys = await conn.fetch(fk_query, table_name)
                    fk_info = [dict(row) for row in foreign_keys]
                except Exception:
                    fk_info = []
                
                # Get row count
                try:
                    row_count = await conn.fetchval(f'SELECT COUNT(*) FROM "{table_name}";')
                except Exception:
                    row_count = "unknown"
            
            return {
                "table_name": table_name,
                "columns": [dict(row) for row in columns],
                "primary_keys": pk_columns,
                "foreign_keys": fk_info,
                "row_count": row_count
            }
    
    async def _execute_query(self, sql: str, row_limit: Optional[int] = None) -> Dict[str, Any]:
        """Execute a SQL query and return structured results."""
        if not self.pool:
            raise RuntimeError("Database pool not initialized")
        
        # Security check: if readonly mode, only allow certain query types
        if self.readonly:
            sql_upper = sql.strip().upper()
            allowed_prefixes = ('SELECT', 'WITH', 'EXPLAIN', 'SHOW', 'VALUES')
            if not any(sql_upper.startswith(prefix) for prefix in allowed_prefixes):
                raise ValueError("Only SELECT, CTE, EXPLAIN, SHOW, and VALUES statements are allowed in readonly mode")
        
        # Apply row limit
        if row_limit and row_limit > 0:
            # Simple LIMIT injection (be careful with this in production)
            if not sql.strip().upper().endswith(';'):
                sql = sql.strip() + f" LIMIT {row_limit};"
            else:
                sql = sql.strip()[:-1] + f" LIMIT {row_limit};"
        
        try:
            async with self.pool.acquire() as conn:
                # Execute query
                if sql.strip().upper().startswith(('INSERT', 'UPDATE', 'DELETE')):
                    # For modification queries, use execute and return affected rows
                    result = await conn.execute(sql)
                    return {
                        "columns": ["affected_rows"],
                        "rows": [[result.split()[-1]]],  # Extract number from "UPDATE 5" etc.
                        "row_count": 1,
                        "truncated": False
                    }
                else:
                    # For select queries, use fetch
                    rows = await conn.fetch(sql)
                    
                    if not rows:
                        return {
                            "columns": [],
                            "rows": [],
                            "row_count": 0,
                            "truncated": False
                        }
                    
                    # Extract column names
                    columns = list(rows[0].keys())
                    
                    # Convert rows to list of lists
                    row_data = []
                    for row in rows:
                        row_values = []
                        for value in row.values():
                            # Convert non-serializable types to strings
                            if hasattr(value, 'isoformat'):  # datetime objects
                                row_values.append(value.isoformat())
                            elif isinstance(value, (bytes, bytearray)):
                                row_values.append(value.hex())
                            else:
                                row_values.append(value)
                        row_data.append(row_values)
                    
                    # Check if results were truncated
                    truncated = row_limit and len(row_data) == row_limit
                    
                    return {
                        "columns": columns,
                        "rows": row_data,
                        "row_count": len(row_data),
                        "truncated": truncated
                    }
                    
        except Exception as e:
            logger.error(f"Query execution failed: {e}")
            raise RuntimeError(f"Query execution failed: {str(e)}")


async def main():
    """Main server function."""
    server = ChinookPostgresServer()
    
    try:
        # Initialize database connection
        await server.initialize()
        
        # Start the server
        logger.info("Starting Chinook Postgres MCP server...")
        await server.mcp.run(
            transport="streamable-http",
            host="0.0.0.0",
            port=8000
        )
        
    except KeyboardInterrupt:
        logger.info("Server shutting down...")
    except Exception as e:
        logger.error(f"Server error: {e}")
        sys.exit(1)
    finally:
        await server.close()


if __name__ == "__main__":
    asyncio.run(main())
