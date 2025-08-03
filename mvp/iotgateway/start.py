#!/usr/bin/env python3

import os
import sys
import argparse
from app import app

def setup_sqlite():
    if 'DATABASE_URL' in os.environ:
        del os.environ['DATABASE_URL']
    print("🗃️  Configured to use SQLite database")

def setup_postgres(connection_string=None):
    if connection_string:
        os.environ['DATABASE_URL'] = connection_string
    else:

        default_url = "postgresql://postgres:password@localhost:5432/iot_gateway"
        os.environ['DATABASE_URL'] = default_url
    print(f"🐘 Configured to use PostgreSQL: {os.environ['DATABASE_URL']}")

def check_postgres_connection():
    try:
        import psycopg2
        database_url = os.environ.get('DATABASE_URL')
        if database_url:

            conn = psycopg2.connect(database_url)
            conn.close()
            print("✅ PostgreSQL connection successful")
            return True
    except ImportError:
        print("❌ psycopg2 not installed. Run: pip install psycopg2-binary")
        return False
    except Exception as e:
        print(f"❌ PostgreSQL connection failed: {e}")
        print("💡 Make sure PostgreSQL is running and accessible")
        print("   For Docker: docker-compose up -d postgres")
        return False
    return False

def main():
    parser = argparse.ArgumentParser(description='IoT Gateway API Server')
    parser.add_argument('--db', choices=['sqlite', 'postgres'], 
                       help='Database type to use')
    parser.add_argument('--postgres-url', 
                       help='PostgreSQL connection string')
    parser.add_argument('--check-db', action='store_true',
                       help='Check database connection and exit')
    parser.add_argument('--host', default='0.0.0.0',
                       help='Host to bind to (default: 0.0.0.0)')
    parser.add_argument('--port', type=int, default=8080,
                       help='Port to bind to (default: 8080)')
    parser.add_argument('--debug', action='store_true',
                       help='Run in debug mode')
    
    args = parser.parse_args()
    

    if args.db == 'sqlite':
        setup_sqlite()
    elif args.db == 'postgres':
        setup_postgres(args.postgres_url)
    elif args.postgres_url:
        setup_postgres(args.postgres_url)
    

    if args.check_db:
        database_url = os.environ.get('DATABASE_URL')
        if database_url and database_url.startswith('postgresql'):
            check_postgres_connection()
        else:
            print("🗃️  Using SQLite database")
        return
    

    database_url = os.environ.get('DATABASE_URL')
    if database_url and database_url.startswith('postgresql'):
        if not check_postgres_connection():
            print("\n🔧 To start PostgreSQL with Docker:")
            print("   docker-compose up -d postgres")
            print("\n🔧 Or use SQLite instead:")
            print("   python start.py --db sqlite")
            sys.exit(1)
    
    print(f"\n🚀 Starting IoT Gateway API server...")
    print(f"   Host: {args.host}")
    print(f"   Port: {args.port}")
    print(f"   Debug: {args.debug}")
    

    try:
        print("🔍 Debugging routes:")
        for rule in app.url_map.iter_rules():
            print(f"  {rule} -> {rule.endpoint} ({list(rule.methods)})")
        app.run(debug=args.debug, host=args.host, port=args.port)
    except KeyboardInterrupt:
        print("\n👋 Server stopped")

if __name__ == '__main__':
    main() 