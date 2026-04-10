import os
from dotenv import load_dotenv
import psycopg2

# Load environment variables
load_dotenv()

HOST = os.getenv("SUPABASE_HOST")
DATABASE = os.getenv("SUPABASE_DB", "postgres")
USER = os.getenv("SUPABASE_USER", "postgres")
PASSWORD = os.getenv("SUPABASE_PASSWORD")
PORT = int(os.getenv("SUPABASE_PORT", 5432))

try:
    print("🔄 Connecting to database...")

    conn = psycopg2.connect(
        host=HOST,
        database=DATABASE,
        user=USER,
        password=PASSWORD,
        port=PORT,
        sslmode="require"   # ⚠️ Required for Supabase
    )

    cursor = conn.cursor()
    print("✅ Connection successful!")

    # Test query
    cursor.execute("SELECT version();")
    print("📦 PostgreSQL version:", cursor.fetchone())

    # List tables
    cursor.execute("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public';
    """)

    tables = cursor.fetchall()
    print("\n📋 Tables:")
    for t in tables:
        print("-", t[0])

    cursor.close()
    conn.close()
    print("\n🔒 Connection closed.")

except Exception as e:
    print("❌ Connection failed!")
    print("Error:", e)