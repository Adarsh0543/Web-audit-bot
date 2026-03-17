"""
tools/__init__.py
──────────────────
All tools available to the LLM agent.
scraper_tool is removed — scraping is now handled by
scrape_node in graph.py directly, never by the LLM.
"""

from tools.seo_tool           import seo_tool
from tools.accessibility_tool import accessibility_tool
from tools.content_tool       import content_tool
from tools.db                 import db_save_tool, db_fetch_tool, db_update_tool, db_delete_tool

all_tools = [
    seo_tool,            # reads scraped_data from state, writes seo_report
    accessibility_tool,  # reads scraped_data from state, writes accessibility_report
    content_tool,        # reads scraped_data from state, writes content_report
    db_save_tool,        # reads all reports from state, saves to MySQL
    db_fetch_tool,       # reads db_query from state, fetches records
    db_update_tool,      # reads db_query from state, updates records
    db_delete_tool,      # reads db_query from state, deletes records
]

__all__ = ["all_tools"]