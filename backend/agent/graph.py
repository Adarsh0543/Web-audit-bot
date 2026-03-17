"""
agent/graph.py
───────────────
Plan and Execute pattern with single executor_node.

Flow:
  START
    ↓
  agent_node       ← creates plan e.g. ["seo", "accessibility", "summary"]
    ↓
  router
    ├── analysis step + no scraped_data → scrape_node → executor_node
    ├── analysis step + scraped_data    → executor_node
    ├── db step                         → executor_node
    ├── "summary"                       → agent_node (writes final response)
    └── plan empty                      → END

  executor_node    ← reads plan[0], runs correct tool, removes step from plan
    ↓
  router           ← reads next plan[0], routes again
    ↓
  ... loop until plan = [] → END
"""

from typing import Annotated
from langgraph.graph import StateGraph, END
from agent.state import AgentState
from agent.llm_agent import agent_node
from scraper.scraper import scrape_page
from tools.seo_tool            import seo_tool
from tools.accessibility_tool  import accessibility_tool
from tools.content_tool        import content_tool
from tools.db.db_save_tool     import db_save_tool
from tools.db.db_fetch_tool    import db_fetch_tool
from tools.db.db_delete_tool   import db_delete_tool


# ── Scrape node ───────────────────────────────────────────────────────
async def scrape_node(state: AgentState) -> dict:
    """Scrapes URL, writes scraped_data to state. HTML never touches LLM."""
    url    = state.get("url", "")
    result = await scrape_page(url)
    print(f"[scrape_node] Scraped {url} — {result.get('page_size_kb', 0)} KB")
    return {"scraped_data": result}


# ── Executor node — single node that runs any tool ────────────────────
async def executor_node(state: AgentState) -> dict:
    """
    Reads plan[0], runs the correct tool, removes the step from plan.
    Returns tool result + updated plan to state.
    """
    plan      = state.get("plan", [])
    next_step = plan[0]

    print(f"[executor] Running: {next_step} | Remaining after: {plan[1:]}")

    # ── Analysis tools ────────────────────────────────────────────────
    if next_step == "seo":
        result = await seo_tool.ainvoke({"state": state})

    elif next_step == "accessibility":
        result = await accessibility_tool.ainvoke({"state": state})

    elif next_step == "content":
        result = await content_tool.ainvoke({"state": state})

    # ── DB tools ──────────────────────────────────────────────────────
    elif next_step == "db_save":
        result = await db_save_tool(state)
        # result = await db_save_tool.ainvoke({"state": state})

    elif next_step == "db_fetch":
        result = await db_fetch_tool(state)
        # result = await db_fetch_tool.ainvoke({"state": state})

    elif next_step == "db_delete":
        result = await db_delete_tool.ainvoke({"state": state})

    else:
        result = {}

    # Remove completed step from plan and return everything to state
    return {**result, "plan": plan[1:]}


# ── Router — single router for the entire graph ───────────────────────
def router(state: AgentState) -> str:
    """
    Called after agent_node and executor_node.
    Reads plan[0] and routes to the correct next node.
    """
    plan         = state.get("plan", [])
    scraped_data = state.get("scraped_data", {})

    # Plan empty → done
    if not plan:
        return END

    next_step = plan[0]

    # Analysis steps — check if scraping is needed first
    if next_step in {"seo", "accessibility", "content"}:
        if not scraped_data:
            return "scrape_node"    # scrape first, then executor
        return "executor_node"      # already scraped, run tool directly

    # Summary → agent_node writes final response
    if next_step == "summary":
        return "agent_node"

    # DB steps — no scraping needed
    return "executor_node"


# ── Build the graph ───────────────────────────────────────────────────
def build_graph():
    graph = StateGraph(AgentState)

    # ── Register nodes ───────────────────────────────────────────────
    graph.add_node("agent_node",    agent_node)
    graph.add_node("scrape_node",   scrape_node)
    graph.add_node("executor_node", executor_node)

    # ── Entry point ──────────────────────────────────────────────────
    graph.set_entry_point("agent_node")

    # ── agent_node → router ──────────────────────────────────────────
    graph.add_conditional_edges(
        "agent_node",
        router,
        {
            "scrape_node":   "scrape_node",
            "executor_node": "executor_node",
            "agent_node":    "agent_node",
            END:             END
        }
    )

    # ── scrape_node → executor_node (always) ─────────────────────────
    graph.add_edge("scrape_node", "executor_node")

    # ── executor_node → router ───────────────────────────────────────
    graph.add_conditional_edges(
        "executor_node",
        router,
        {
            "scrape_node":   "scrape_node",
            "executor_node": "executor_node",
            "agent_node":    "agent_node",
            END:             END
        }
    )

    return graph.compile()


agent_graph = build_graph()


if __name__ == "__main__":
    import asyncio
    from langchain_core.messages import HumanMessage

    async def test():
        url     = input("Enter URL to analyze: ").strip()
        message = input("What would you like to do?: ").strip()

        print(f"\n{'='*50}")
        print(f"Running agent for: {url}")
        print(f"{'='*50}\n")

        result = await agent_graph.ainvoke({
            "messages": [HumanMessage(content=f"{message} for {url}")],
        })

        print("\n" + "="*50)
        print("FINAL RESPONSE:")
        print("="*50)
        print(result["messages"][-1].content)

    asyncio.run(test())