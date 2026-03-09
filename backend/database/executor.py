"""
database/executor.py
─────────────────────
The ONLY place where SQL queries are actually executed.
Every query passes through the validator before running.
Every operation is logged regardless of success or failure.
"""

from database.connection import get_connection
from database.validator import validate_query, extract_table_names
from database.logger import log_operation


def execute_query(query: str, params: tuple = None) -> dict:
    """
    Safely executes a SQL query after validation.

    Args:
        query  : The SQL query string
        params : Optional tuple of parameterized values (prevents injection)

    Returns:
        {
            "success"      : True/False,
            "operation"    : "SELECT/INSERT/UPDATE/DELETE",
            "data"         : list of rows (for SELECT),
            "rows_affected": int (for INSERT/UPDATE/DELETE),
            "last_insert_id": int (for INSERT),
            "error"        : error message if failed
        }
    """

    # ── Step 1: Validate the query ───────────────────────────────────
    validation = validate_query(query)

    if not validation["valid"]:
        # Log the blocked attempt
        log_operation(
            operation_type="SELECT",          # Unknown type, default to SELECT
            table_name="unknown",
            query_executed=query,
            status="FAILED",
            error_message=validation["error"]
        )
        return {
            "success": False,
            "operation": None,
            "data": None,
            "rows_affected": 0,
            "error": validation["error"]
        }

    operation = validation["operation"]
    tables = validation.get("tables", ["unknown"])
    primary_table = tables[0] if tables else "unknown"

    # ── Step 2: Execute the query ────────────────────────────────────
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)    # Returns rows as dicts

        cursor.execute(query, params or ())

        result = {
            "success": True,
            "operation": operation,
            "data": None,
            "rows_affected": 0,
            "last_insert_id": None,
            "error": None
        }

        if operation == "SELECT":
            rows = cursor.fetchall()
            result["data"] = rows
            result["rows_affected"] = len(rows)

        else:
            conn.commit()                        # Commit INSERT/UPDATE/DELETE
            result["rows_affected"] = cursor.rowcount
            result["last_insert_id"] = cursor.lastrowid

        # ── Step 3: Log success ──────────────────────────────────────
        log_operation(
            operation_type=operation,
            table_name=primary_table,
            query_executed=query,
            status="SUCCESS",
            rows_affected=result["rows_affected"]
        )

        cursor.close()
        conn.close()
        return result

    except Exception as e:
        # ── Step 4: Rollback & log failure ───────────────────────────
        if conn:
            try:
                conn.rollback()
            except Exception:
                pass
            conn.close()

        error_msg = str(e)

        log_operation(
            operation_type=operation,
            table_name=primary_table,
            query_executed=query,
            status="FAILED",
            error_message=error_msg
        )

        return {
            "success": False,
            "operation": operation,
            "data": None,
            "rows_affected": 0,
            "error": f" Query execution failed: {error_msg}"
        }


def execute_safe(query: str, params: tuple = None) -> dict:
    """
    Alias for execute_query — use this everywhere in the app.
    Preferred entry point for all DB operations.
    """
    return execute_query(query, params)