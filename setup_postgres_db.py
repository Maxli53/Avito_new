"""
Setup PostgreSQL database for real testing.

This script creates the PostgreSQL database and applies the full enterprise schema.
"""
import asyncio
import os
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

# Load environment variables
load_dotenv()

# Import database models
import sys
sys.path.append("snowmobile-reconciliation")
from src.models.database import Base


async def setup_postgres_database():
    """Setup PostgreSQL database with full enterprise schema"""
    
    print("Setting up PostgreSQL database for real testing...")
    
    # Database connection details
    db_host = "localhost"
    db_port = 5432
    db_user = "snowmobile_user"
    db_password = "snowmobile_pass"
    db_name = "snowmobile_reconciliation"
    
    # First connect to default postgres database to create our database
    admin_url = f"postgresql+asyncpg://postgres:password@{db_host}:{db_port}/postgres"
    
    try:
        print(f"Connecting to PostgreSQL at {db_host}:{db_port}...")
        
        admin_engine = create_async_engine(admin_url, isolation_level="AUTOCOMMIT")
        
        async with admin_engine.connect() as conn:
            # Create database user if not exists
            try:
                await conn.execute(text(f"CREATE USER {db_user} WITH PASSWORD '{db_password}';"))
                print(f"Created user: {db_user}")
            except Exception as e:
                if "already exists" in str(e):
                    print(f"User {db_user} already exists")
                else:
                    print(f"Error creating user: {e}")
            
            # Create database if not exists
            try:
                await conn.execute(text(f"CREATE DATABASE {db_name} OWNER {db_user};"))
                print(f"Created database: {db_name}")
            except Exception as e:
                if "already exists" in str(e):
                    print(f"Database {db_name} already exists")
                else:
                    print(f"Error creating database: {e}")
                    
            # Grant permissions
            try:
                await conn.execute(text(f"GRANT ALL PRIVILEGES ON DATABASE {db_name} TO {db_user};"))
                print(f"Granted permissions to {db_user}")
            except Exception as e:
                print(f"Error granting permissions: {e}")
        
        await admin_engine.dispose()
        
        # Now connect to our database and create schema
        app_url = f"postgresql+asyncpg://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
        
        print(f"Connecting to application database: {db_name}")
        app_engine = create_async_engine(app_url, echo=True)
        
        async with app_engine.begin() as conn:
            # Enable required PostgreSQL extensions
            try:
                await conn.execute(text('CREATE EXTENSION IF NOT EXISTS "uuid-ossp";'))
                await conn.execute(text('CREATE EXTENSION IF NOT EXISTS "pg_trgm";'))
                print("Enabled PostgreSQL extensions")
            except Exception as e:
                print(f"Error enabling extensions: {e}")
            
            # Create all tables using the SQLAlchemy models
            await conn.run_sync(Base.metadata.create_all)
            print("Created all database tables")
        
        await app_engine.dispose()
        
        print(f"PostgreSQL database setup complete!")
        print(f"Database URL: {app_url}")
        print(f"You can now run the blind E2E test with real PostgreSQL")
        
        return True
        
    except Exception as e:
        print(f"PostgreSQL setup failed: {e}")
        print("Make sure PostgreSQL is running and accessible")
        return False


async def main():
    """Main setup function"""
    success = await setup_postgres_database()
    if success:
        print("\nSuccess! The blind E2E test can now use real PostgreSQL.")
    else:
        print("\nSetup failed. The test will fall back to SQLite.")


if __name__ == "__main__":
    asyncio.run(main())