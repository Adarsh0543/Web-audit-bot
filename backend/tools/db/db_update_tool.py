"""
tools/db/db_update_tool.py
───────────────────────────
Reads db query parameters from state.
Writes result to state["db_result"].
Requires both set_clause and condition for safety.
"""

from langchain_core.tools import tool
from database.executor import execute_safe
from agent.state import AgentState


# @tool
def db_update_tool(state: AgentState) -> dict:
    """
    Updates existing records in MySQL.
    Reads report_type, set_clause and condition from state["db_query"].
    Writes result to state["db_result"].
    """
    db_query    = state.get("db_query", {})
    report_type = db_query.get("report_type", "sites")
    condition   = db_query.get("condition", "")
    set_clause  = db_query.get("set_clause", "")

    if not condition:
        return {"db_result": {"success": False, "error": "UPDATE requires a condition. Aborted for safety."}}
    if not set_clause:
        return {"db_result": {"success": False, "error": "UPDATE requires a set_clause. Aborted."}}

    table_map = {
        "seo":           "seo_reports",
        "accessibility": "accessibility_reports",
        "content":       "content_reports",
        "sites":         "sites"
    }

    table  = table_map.get(report_type, "sites")
    print(f"[db_update_tool] Updating {table}...")
    result = execute_safe(f"UPDATE {table} SET {set_clause} WHERE {condition}")

    return {"db_result": {
        "success":       result["success"],
        "rows_affected": result.get("rows_affected", 0),
        "message":       f"Updated {result.get('rows_affected', 0)} record(s) in {table}.",
        "error":         result.get("error")
    }}