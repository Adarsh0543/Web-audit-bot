"""
tools/db/db_helper.py
──────────────────────
Shared helper — gets or creates a site record, returns site_id.
Used by db_save_tool only.
"""

from urllib.parse import urlparse
from database.executor import execute_safe


def get_or_create_site(url: str) -> int | None:
    domain = urlparse(url).netloc or url
    execute_safe(
        """
        INSERT INTO sites (url, domain) VALUES (%s, %s)
        ON DUPLICATE KEY UPDATE
            last_analyzed  = CURRENT_TIMESTAMP,
            total_analyses = total_analyses + 1
        """,
        (url, domain)
    )
    result = execute_safe("SELECT id FROM sites WHERE url = %s", (url,))
    print(result)
    rows   = result.get("data", [])
    return rows[0]["id"] if rows else None