"""
agent/state.py
───────────────
AgentState — single shared data structure for the entire workflow.

Flow:
  agent_node     → sets url, plan
  executor_node  → reads plan[0], executes it, removes it from plan
  scrape_node    → reads url, writes scraped_data
  tools          → read scraped_data, write reports
"""

from typing import Annotated, List,Optional
from typing_extensions import TypedDict
from langgraph.graph.message import add_messages


class AgentState(TypedDict,total=False):
    # ── Conversation history ─────────────────────────────────────────
    messages: Annotated[list, add_messages]

    # ── Set by agent_node ────────────────────────────────────────────
    url:  str
    plan: List[str]
    # e.g. ["seo", "accessibility", "summary"]
    # e.g. ["seo", "content", "summary"]
    # e.g. ["seo", "accessibility", "content", "summary"]
    # items are removed one by one as they complete

    # ── Set by scrape_node ───────────────────────────────────────────
    scraped_data: dict

    # ── Set by each tool ─────────────────────────────────────────────
    seo_report:           Optional[dict]   
    accessibility_report: Optional[dict]
    content_report:       Optional[dict]   

    # ── Set by db tools ──────────────────────────────────────────────
    db_query: dict
    db_result:            Optional[dict]