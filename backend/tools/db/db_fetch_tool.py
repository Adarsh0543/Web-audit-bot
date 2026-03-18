"""
tools/db/db_fetch_tool.py
──────────────────────────
Reads db query parameters from state.
Writes fetched records to state["db_result"].

report_type options:
  "all"           → LEFT JOIN all 3 reports per site (default)
  "seo"           → seo_reports table only
  "accessibility" → accessibility_reports table only
  "content"       → content_reports table only
  "sites"         → sites table only
"""

from database.executor import execute_safe
from agent.state import AgentState


async def db_fetch_tool(state: AgentState) -> dict:
    """
    Fetches analysis reports from MySQL.
    Reads report_type and condition from state["db_query"].
    Writes results to state["db_result"].
    """
    db_query    = state.get("db_query", {})
    report_type = db_query.get("report_type", "all")
    condition   = db_query.get("condition", "")

    where = f"WHERE {condition}" if condition else ""

    # ── All reports — LEFT JOIN across all 3 tables ───────────────────
    if report_type == "all":
        query = f"""
            SELECT
                s.id          AS site_id,
                s.url,
                s.domain,
                s.last_analyzed,
                sr.seo_score,
                sr.issues     AS seo_issues,
                ar.accessibility_score,
                ar.issues     AS accessibility_issues,
                cr.content_score,
                cr.issues     AS content_issues
            FROM sites s
            LEFT JOIN seo_reports sr
                ON s.id = sr.site_id
            LEFT JOIN accessibility_reports ar
                ON s.id = ar.site_id
            LEFT JOIN content_reports cr
                ON s.id = cr.site_id
            {where}
            ORDER BY s.last_analyzed DESC
            LIMIT 10
        """
        print(f"[db_fetch_tool] Fetching all reports (LEFT JOIN)...")

    # ── Single table fetches ──────────────────────────────────────────
    else:
        table_map = {
            "seo":           "seo_reports",
            "accessibility": "accessibility_reports",
            "content":       "content_reports",
            "sites":         "sites"
        }
        table = table_map.get(report_type, "sites")
        order = (
            "ORDER BY last_analyzed DESC LIMIT 10"
            if table == "sites"
            else "ORDER BY analyzed_at DESC LIMIT 10"
        )
        query = f"SELECT * FROM {table} {where} {order}"
        print(f"[db_fetch_tool] Fetching from {table}...")

    result = execute_safe(query)

    return {
        "db_result": {
            "success":     result["success"],
            "report_type": report_type,
            "data":        result.get("data", []),
            "count":       len(result.get("data", [])),
            "error":       result.get("error")
        }
    }