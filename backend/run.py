"""
run.py
───────
Continuous chat entry point.
Run with: python3 run.py
Type 'bye' to exit.
"""
import asyncio
from agent.graph import agent_graph
from langchain_core.messages import HumanMessage


async def chat():
    print("\n" + "="*50)
    print("  SEO Agent — Continuous Chat")
    print("  Type 'bye' to exit")
    print("="*50 + "\n")

    while True:
        # ── Get user input ────────────────────────────────────────────
        try:
            message = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n[Agent] Goodbye!")
            break

        # ── Exit condition ────────────────────────────────────────────
        if message.lower() in {"bye", "exit", "quit", "goodbye"}:
            print("[Agent] Goodbye!")
            break

        if not message:
            continue

        # ── Run agent — fresh state each turn ────────────────────────
        # Each request is independent — no history sent to LLM
        # This keeps token usage flat and avoids rate limits
        try:
            result = await agent_graph.ainvoke({
                "messages": [HumanMessage(content=message)],
            })

            print("\n[Agent]")
            print("-" * 50)
            print(result["messages"][-1].content)
            print("-" * 50 + "\n")

        except Exception as e:
            print(f"\n[Agent] Error: {e}\n")


asyncio.run(chat())