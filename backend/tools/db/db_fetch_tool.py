"""
tools/db/db_fetch_tool.py
──────────────────────────
Reads db query parameters from state.
Writes fetched records to state["db_result"].
"""

# from langchain_core.tools import tool
from database.executor import execute_safe
from agent.state import AgentState


# @tool
async def db_fetch_tool(state: AgentState) -> dict:
    """
    Fetches analysis reports from MySQL.
    Reads report_type and condition from state["db_query"].
    Writes results to state["db_result"].
    """
    db_query    = state.get("db_query", {})
    report_type = db_query.get("report_type", "sites")
    condition   = db_query.get("condition", "")

    table_map = {
        "seo":           "seo_reports",
        "accessibility": "accessibility_reports",
        "content":       "content_reports",
        "sites":         "sites"
    }

    table = table_map.get(report_type, "sites")
    where = f"WHERE {condition}" if condition else ""
    order = (
        "ORDER BY last_analyzed DESC LIMIT 10"
        if table == "sites"
        else "ORDER BY analyzed_at DESC LIMIT 10"
    )

    print(f"[db_fetch_tool] Fetching from {table}...")
    result = execute_safe(f"SELECT * FROM {table} {where} {order}")
    # print('recived results from executor',result)
    return {"db_result": {
        "success": result["success"],
        "data":    result.get("data", []),
        "table":   table,
        "error":   result.get("error")
    }}