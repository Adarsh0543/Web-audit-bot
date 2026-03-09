"""
database/connection.py
─────────────────────
Handles MySQL connection using environment variables.
Provides a reusable get_connection() function used across the app.
"""

import mysql.connector
from mysql.connector import Error
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


def get_connection():
    """
    Creates and returns a MySQL database connection.
    Reads credentials from environment variables.
    Raises an exception if connection fails.
    """
    try:
        connection = mysql.connector.connect(
            host=os.getenv("DB_HOST", "localhost"),
            port=int(os.getenv("DB_PORT", 3306)),
            user=os.getenv("DB_USER", "root"),
            password=os.getenv("DB_PASSWORD", ""),
            database=os.getenv("DB_NAME", "seo_agent_db"),
            autocommit=False           # We handle commits manually for safety
        )

        if connection.is_connected():
            return connection

    except Error as e:
        raise ConnectionError(f"❌ Failed to connect to MySQL: {str(e)}")


def test_connection():
    """
    Quick test to verify DB connection is working.
    Prints success or failure message.
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT VERSION()")
        version = cursor.fetchone()
        print(f"✅ Connected to MySQL — Version: {version[0]}")
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return False


# Run this file directly to test connection
if __name__ == "__main__":
    test_connection()