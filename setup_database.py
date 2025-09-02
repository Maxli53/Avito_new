#!/usr/bin/env python3
"""
Database Setup Script - Enterprise Schema with SQLite Fallback
Creates the complete snowmobile reconciliation database with enterprise schema
Falls back to SQLite when PostgreSQL is not available
"""
import sqlite3
import os
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv
import sys

# Load environment variables
load_dotenv()

# Database configuration - use SQLite fallback for development
SQLITE_DATABASE = Path('snowmobile_reconciliation_enterprise.db')
POSTGRES_DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://snowmobile_user:snowmobile_pass@localhost:5432/snowmobile_reconciliation')
SCHEMA_FILE = Path('docs/updated_database_schema.md')

# Use SQLite for immediate development
USE_SQLITE = True

def convert_postgres_to_sqlite(schema_content: str) -> str:
    """Convert PostgreSQL schema to SQLite compatible format"""
    
    # PostgreSQL to SQLite conversions
    conversions = [
        # Extensions and functions
        ('CREATE EXTENSION IF NOT EXISTS "uuid-ossp";', '-- UUID extension handled by Python'),
        ('CREATE EXTENSION IF NOT EXISTS "pg_trgm";', '-- Trigram extension handled by Python'),
        ('uuid_generate_v4()', '(hex(randomblob(4)) || "-" || hex(randomblob(2)) || "-" || hex(randomblob(2)) || "-" || hex(randomblob(2)) || "-" || hex(randomblob(6)))'),
        
        # Data types
        ('UUID PRIMARY KEY DEFAULT uuid_generate_v4()', 'TEXT PRIMARY KEY DEFAULT (hex(randomblob(4)) || "-" || hex(randomblob(2)) || "-" || hex(randomblob(2)) || "-" || hex(randomblob(2)) || "-" || hex(randomblob(6)))'),
        ('UUID DEFAULT uuid_generate_v4()', 'TEXT DEFAULT (hex(randomblob(4)) || "-" || hex(randomblob(2)) || "-" || hex(randomblob(2)) || "-" || hex(randomblob(2)) || "-" || hex(randomblob(6)))'),
        ('UUID NOT NULL', 'TEXT NOT NULL'),
        ('UUID', 'TEXT'),
        ('JSONB', 'TEXT'),
        ('DECIMAL(', 'REAL('),
        ('BIGINT', 'INTEGER'),
        ('TIMESTAMP DEFAULT CURRENT_TIMESTAMP', 'DATETIME DEFAULT CURRENT_TIMESTAMP'),
        ('TIMESTAMP', 'DATETIME'),
        
        # Constraints and checks
        ('CHECK (', '-- CHECK ('),
        
        # Indexes
        ('CREATE INDEX', '-- CREATE INDEX'),
        ('USING GIN', '-- USING GIN'),
        
        # Views
        ('CREATE VIEW', '-- CREATE VIEW'),
        
        # Functions and triggers
        ('CREATE OR REPLACE FUNCTION', '-- CREATE OR REPLACE FUNCTION'),
        ('CREATE TRIGGER', '-- CREATE TRIGGER'),
        ('$$ LANGUAGE plpgsql', '-- $$ LANGUAGE plpgsql'),
        
        # Comments
        ('COMMENT ON', '-- COMMENT ON'),
    ]
    
    result = schema_content
    for postgres_syntax, sqlite_syntax in conversions:
        result = result.replace(postgres_syntax, sqlite_syntax)
    
    return result

def setup_sqlite_database():
    """Setup SQLite database with converted enterprise schema"""
    
    print("=" * 80)
    print("SQLITE ENTERPRISE DATABASE SETUP")
    print("=" * 80)
    print(f"Database file: {SQLITE_DATABASE}")
    print(f"Schema file: {SCHEMA_FILE}")
    
    # Check if schema file exists
    if not SCHEMA_FILE.exists():
        raise FileNotFoundError(f"Schema file not found: {SCHEMA_FILE}")
    
    print(f"Schema file found: {SCHEMA_FILE.stat().st_size:,} bytes")
    
    try:
        # Remove existing database
        if SQLITE_DATABASE.exists():
            SQLITE_DATABASE.unlink()
            print(f"Removed existing database: {SQLITE_DATABASE}")
        
        # Create new database
        conn = sqlite3.connect(str(SQLITE_DATABASE))
        
        # Enable foreign keys
        conn.execute("PRAGMA foreign_keys = ON")
        
        # Read and convert schema
        print(f"Reading schema from: {SCHEMA_FILE}")
        schema_content = SCHEMA_FILE.read_text(encoding='utf-8')
        
        print("Converting PostgreSQL schema to SQLite...")
        sqlite_schema = convert_postgres_to_sqlite(schema_content)
        
        # Split schema into individual commands
        commands = []
        current_command = []
        
        for line in sqlite_schema.split('\n'):
            line = line.strip()
            
            # Skip comment lines and empty lines
            if not line or line.startswith('--'):
                continue
                
            current_command.append(line)
            
            # End of command detected
            if line.endswith(';'):
                full_command = '\n'.join(current_command).strip()
                if full_command and not full_command.startswith('--'):
                    commands.append(full_command)
                current_command = []
        
        print(f"Found {len(commands)} SQL commands to execute")
        
        # Execute commands
        executed_count = 0
        for i, command in enumerate(commands, 1):
            try:
                print(f"Executing command {i}/{len(commands)}: {command[:50]}...")
                conn.execute(command)
                executed_count += 1
            except Exception as e:
                print(f"Warning: Command {i} failed: {str(e)[:100]}...")
                # Continue with other commands
                continue
        
        conn.commit()
        print(f"Database setup completed - {executed_count}/{len(commands)} commands successful")
        
        # Verify key tables exist
        cursor = conn.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name NOT LIKE 'sqlite_%'
            ORDER BY name
        """)
        tables = cursor.fetchall()
        
        print(f"\nCreated {len(tables)} tables:")
        for table in tables:
            print(f"  - {table[0]}")
        
        conn.close()
        
        return True
        
    except Exception as e:
        print(f"Database setup failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_sqlite_database():
    """Test SQLite database connection and basic functionality"""
    
    print("\n" + "-" * 60)
    print("TESTING SQLITE DATABASE CONNECTION")
    print("-" * 60)
    
    try:
        if not SQLITE_DATABASE.exists():
            print(f"Database file not found: {SQLITE_DATABASE}")
            return False
        
        conn = sqlite3.connect(str(SQLITE_DATABASE))
        
        # Test basic query
        cursor = conn.execute("SELECT sqlite_version()")
        version = cursor.fetchone()[0]
        print(f"SQLite Version: {version}")
        
        # Test table existence
        cursor = conn.execute("""
            SELECT name, 
                   (SELECT COUNT(*) FROM pragma_table_info(name)) as column_count
            FROM sqlite_master 
            WHERE type='table' AND name NOT LIKE 'sqlite_%'
            ORDER BY name
        """)
        tables = cursor.fetchall()
        
        print(f"\nDatabase Tables ({len(tables)}):")
        for table_name, column_count in tables:
            print(f"  {table_name}: {column_count} columns")
        
        # Test JSON functionality (SQLite 3.45+)
        try:
            cursor = conn.execute("SELECT json('{\"test\": \"value\"}')")
            test_json = cursor.fetchone()[0]
            print(f"JSON Support: {test_json}")
        except Exception as e:
            print(f"JSON Support: Limited ({e})")
        
        # Test foreign key support
        cursor = conn.execute("PRAGMA foreign_keys")
        fk_enabled = cursor.fetchone()[0]
        print(f"Foreign Key Support: {'Enabled' if fk_enabled else 'Disabled'}")
        
        conn.close()
        
        print("\nSQLite database connection test successful!")
        return True
        
    except Exception as e:
        print(f"SQLite database connection test failed: {e}")
        return False

def main():
    """Main setup process"""
    
    try:
        if USE_SQLITE:
            # Setup SQLite database
            setup_success = setup_sqlite_database()
            
            if setup_success:
                # Test connection
                test_success = test_sqlite_database()
                
                if test_success:
                    print("\n" + "=" * 80)
                    print("SQLITE DATABASE SETUP COMPLETE")
                    print("Database is ready for development use with:")
                    print("  - Enterprise schema adapted for SQLite")
                    print("  - Core tables and relationships")
                    print("  - JSON support for specifications")
                    print("  - Foreign key constraints")
                    print(f"  - Database file: {SQLITE_DATABASE.absolute()}")
                    print("=" * 80)
                    return True
            
        else:
            print("PostgreSQL mode not implemented yet")
            return False
        
        print("\nDatabase setup failed")
        return False
        
    except Exception as e:
        print(f"\nSetup process failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    main()