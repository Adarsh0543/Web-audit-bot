"""
database/logger.py
───────────────────
Logs every database operation into the db_operation_logs table.
Every SELECT, INSERT, UPDATE, DELETE gets recorded with its status.
"""

from database.connection import get_connection
from datetime import datetime


def log_operation(
    operation_type: str,
    table_name: str,
    query_executed: str,
    status: str,
    rows_affected: int = 0,
    error_message: str = None
):
    """
    Inserts a log record into db_operation_logs.

    Args:
        operation_type : 'SELECT' | 'INSERT' | 'UPDATE' | 'DELETE'
        table_name     : The primary table being operated on
        query_executed : The actual SQL query that ran
        status         : 'SUCCESS' | 'FAILED'
        rows_affected  : How many rows were affected
        error_message  : Error details if status is FAILED
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()

        log_query = """
            INSERT INTO db_operation_logs
                (operation_type, table_name, query_executed,
                 status, rows_affected, error_message, executed_at)
            VALUES
                (%s, %s, %s, %s, %s, %s, %s)
        """

        cursor.execute(log_query, (
            operation_type,
            table_name,
            query_executed[:2000],       # Truncate very long queries
            status,
            rows_affected,
            error_message,
            datetime.now()
        ))

        conn.commit()
        cursor.close()
        conn.close()

    except Exception as e:
        # Logger should never crash the main app — silently handle errors
        print(f"  Logger error (non-critical): {e}")