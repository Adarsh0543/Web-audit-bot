"""
agent/llm_agent.py
───────────────────
Two roles:

1. Plan creation — plan is empty
   LLM reads user message → creates plan + sets url

2. Summary — plan = ["summary"]
   LLM reads tool results from STATE → writes final summary
"""

import os
import json
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, AIMessage
from dotenv import load_dotenv
from agent.state import AgentState

load_dotenv()

llm = ChatGroq(
    model=os.getenv("GROQ_MODEL", "llama-3.1-8b-instant"),
    api_key=os.getenv("GROQ_API_KEY"),
    temperature=0
)

# ── Plan creation prompt ──────────────────────────────────────────────
PLAN_PROMPT = """
You are a web analysis agent.
Read the user message and return ONLY a valid JSON object — nothing else.

{
  "url": "full URL if mentioned, else null",
  "plan": ["step1", "step2", ...],
  "db_query": {
    "report_type": "seo", 
    "condition": ""
  }
}

Rules for plan:
- Always end plan with "summary"
- if only database operations are mentioned no need to do other analysis
- Only include steps the user asked for
- Valid steps: "seo", "accessibility", "content", "db_save", "db_fetch", "db_delete", "summary"
- If user says "seo analysis"           → ["seo", "summary"]
- If user says "accessibility"          → ["accessibility", "summary"]
- If user says "seo and accessibility"  → ["seo", "accessibility", "summary"]
- If user says "full analysis" or "all" → ["seo", "accessibility", "content", "summary"]
- If user wants stored reports          → ["db_fetch", "summary"]
- If user wants to delete records       → ["db_delete", "summary"]
- If user says "analyze and save"       → ["seo", "accessibility", "content", "db_save", "summary"]

Rules for db_query (ONLY if user asks to fetch data):
- report_type: Must be one of "seo", "accessibility", "content", or "sites", choose any one of report_type based on users need.`
- condition: A valid SQL WHERE clause based on the user's request (e.g., "url LIKE '%example.com%'"). Leave empty string "" if no specific condition.

Return ONLY valid JSON without markdown code blocks.
"""

# ── Summary prompt ────────────────────────────────────────────────────
SUMMARY_PROMPT = """
You are an expert web analysis assistant.
The analysis tools have already completed. Here are their raw results:

{tool_results_context}

Based on these results, provide a clear structured summary with:
- Score for each analysis performed
- Top issues found in each
- Specific actionable recommendations
- Overall health assessment of the page

Be concise but thorough. Use bullet points for issues.
"""


async def agent_node(state: AgentState) -> dict:
    messages = state.get("messages", [])
    plan     = state.get("plan", [])

    # ── ROLE 1: Plan creation — plan is empty ────────────────────────
    if not plan:
        response = await llm.ainvoke([
            SystemMessage(content=PLAN_PROMPT),
            *messages
        ])

        try:
            # Strip markdown formatting just in case the LLM adds ```json
            clean_text = response.content.strip().strip("`").removeprefix("json")
            parsed = json.loads(clean_text)
        except json.JSONDecodeError:
            parsed = {"url": "", "plan": ["summary"]}

        url  = parsed.get("url") or ""
        plan = parsed.get("plan") or ["summary"]
        db_query = parsed.get("db_query") or {}

        print(f"[agent] Plan created: {plan}")
        print(f"[agent] URL: {url}")

        return {
            "url":  url,
            "plan": plan,
            "db_query": db_query
        }

    # ── ROLE 2: Summary — LLM reads tool results from state ───────
    if plan == ["summary"]:
        # CHANGED: We manually gather the reports from the state here
        context = ""
        if state.get("seo_report"):
            context += f"\n--- SEO REPORT ---\n{json.dumps(state['seo_report'], indent=2)}\n"
        if state.get("accessibility_report"):
            context += f"\n--- ACCESSIBILITY REPORT ---\n{json.dumps(state['accessibility_report'], indent=2)}\n"
        if state.get("content_report"):
            context += f"\n--- CONTENT REPORT ---\n{json.dumps(state['content_report'], indent=2)}\n"
        if state.get("db_result"):
            context += f"\n--- DATABASE RESULT ---\n{json.dumps(state['db_result'], indent=2)}\n"

        # Inject context into the prompt
        formatted_prompt = SUMMARY_PROMPT.format(tool_results_context=context)

        response = await llm.ainvoke([
            SystemMessage(content=formatted_prompt),
            *messages
        ])

        print("[agent] Summary written")
        return {
            "messages": [AIMessage(content=response.content)],
            "plan":     []   # clear plan → graph routes to END
        }

    return {}