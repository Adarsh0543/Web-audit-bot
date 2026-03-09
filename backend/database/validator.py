"""
database/validator.py
──────────────────────
Safety layer that:
  1. Only allows operations on whitelisted tables
  2. Blocks dangerous SQL patterns (DROP, TRUNCATE, etc.)
  3. Validates query structure before execution
"""

import re

# ── Whitelisted tables — ONLY these can be queried ──────────────────
ALLOWED_TABLES = {
    "sites",
    "seo_reports",
    "accessibility_reports",
    "content_reports",
    "db_operation_logs"
}

# ── Allowed SQL operation types ──────────────────────────────────────
ALLOWED_OPERATIONS = {"SELECT", "INSERT", "UPDATE", "DELETE"}

# ── Dangerous patterns that must NEVER appear in queries ─────────────
DANGEROUS_PATTERNS = [
    r"\bDROP\b",
    r"\bTRUNCATE\b",
    r"\bALTER\b",
    r"\bCREATE\b",
    r"\bEXEC\b",
    r"\bEXECUTE\b",
    r"\bXP_\w+",           # SQL Server extended stored procs
    r"--",                  # SQL comment (injection trick)
    r"/\*.*?\*/",           # Block comments
    r"\bUNION\b",           # UNION-based injection
    r"\bINFORMATION_SCHEMA\b",
    r"\bSYS\.\w+",
    r";\s*\w",              # Multiple statements (stacked queries)
]


def get_operation_type(query: str) -> str | None:
    """
    Extracts the SQL operation type from a query.
    Returns: 'SELECT', 'INSERT', 'UPDATE', 'DELETE', or None
    """
    query_stripped = query.strip().upper()
    for op in ALLOWED_OPERATIONS:
        if query_stripped.startswith(op):
            return op
    return None


def extract_table_names(query: str) -> list[str]:
    """
    Extracts table names referenced in the SQL query.
    Handles FROM, INTO, UPDATE, JOIN clauses.
    """
    # Patterns to find table names after SQL keywords
    patterns = [
        r"\bFROM\s+`?(\w+)`?",
        r"\bINTO\s+`?(\w+)`?",
        r"\bUPDATE\s+`?(\w+)`?",
        r"\bJOIN\s+`?(\w+)`?",
        r"\bDELETE\s+FROM\s+`?(\w+)`?"
    ]
    tables = []
    for pattern in patterns:
        matches = re.findall(pattern, query, re.IGNORECASE)
        tables.extend(matches)
    return [t.lower() for t in tables]


def validate_query(query: str) -> dict:
    """
    Main validation function. Checks query against all safety rules.

    Returns:
        {
            "valid": True/False,
            "operation": "SELECT/INSERT/UPDATE/DELETE",
            "error": "error message if invalid"
        }
    """
    if not query or not query.strip():
        return {"valid": False, "operation": None, "error": "Empty query."}

    # ── Check 1: Dangerous patterns ──────────────────────────────────
    for pattern in DANGEROUS_PATTERNS:
        if re.search(pattern, query, re.IGNORECASE):
            return {
                "valid": False,
                "operation": None,
                "error": f" Dangerous SQL pattern detected: '{pattern}'"
            }

    # ── Check 2: Valid operation type ────────────────────────────────
    operation = get_operation_type(query)
    if not operation:
        return {
            "valid": False,
            "operation": None,
            "error": f" Only SELECT, INSERT, UPDATE, DELETE are allowed."
        }

    # ── Check 3: Only whitelisted tables ─────────────────────────────
    tables_in_query = extract_table_names(query)

    if not tables_in_query:
        return {
            "valid": False,
            "operation": operation,
            "error": " Could not identify table name in query."
        }

    for table in tables_in_query:
        if table not in ALLOWED_TABLES:
            return {
                "valid": False,
                "operation": operation,
                "error": f" Table '{table}' is not allowed. Allowed: {ALLOWED_TABLES}"
            }

    # ── All checks passed ─────────────────────────────────────────────
    return {
        "valid": True,
        "operation": operation,
        "tables": tables_in_query,
        "error": None
    }


# Quick test when run directly
if __name__ == "__main__":
    test_queries = [
        "SELECT * FROM seo_reports WHERE seo_score < 50",
        "INSERT INTO sites (url, domain) VALUES ('https://example.com', 'example.com')",
        "DROP TABLE sites",                          # Should FAIL
        "SELECT * FROM users",                        # Should FAIL (not whitelisted)
        "SELECT * FROM sites; DROP TABLE sites",      # Should FAIL (stacked query)
        "UPDATE seo_reports SET seo_score = 80 WHERE id = 1",
        "DELETE FROM content_reports WHERE analyzed_at < '2024-01-01'",
    ]

    print(" Testing SQL Validator:\n")
    for q in test_queries:
        result = validate_query(q)
        status = " VALID" if result["valid"] else " BLOCKED"
        print(f"{status} — {q[:60]}...")
        if not result["valid"]:
            print(f"   Reason: {result['error']}")
        print()