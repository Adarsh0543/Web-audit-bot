"""
tools/db/db_delete_tool.py
───────────────────────────
Reads db query parameters from state.
Writes result to state["db_result"].
Always requires a condition — will never delete all records.
"""

from langchain_core.tools import tool
from database.executor import execute_safe
from agent.state import AgentState


@tool
def db_delete_tool(state: AgentState) -> dict:
    """
    Deletes records from MySQL.
    Reads report_type and condition from state["db_query"].
    Writes result to state["db_result"].
    Always requires a WHERE condition — will never delete all records.
    """
    db_query    = state.get("db_query", {})
    report_type = db_query.get("report_type", "sites")
    condition   = db_query.get("condition", "")

    if not condition:
        return {"db_result": {"success": False, "error": "DELETE requires a condition. Aborted for safety."}}

    table_map = {
        "seo":           "seo_reports",
        "accessibility": "accessibility_reports",
        "content":       "content_reports",
        "sites":         "sites"
    }

    table  = table_map.get(report_type, "sites")
    print(f"[db_delete_tool] Deleting from {table}...")
    result = execute_safe(f"DELETE FROM {table} WHERE {condition}")

    return {"db_result": {
        "success":       result["success"],
        "rows_affected": result.get("rows_affected", 0),
        "message":       f"Deleted {result.get('rows_affected', 0)} record(s) from {table}.",
        "error":         result.get("error")
    }}