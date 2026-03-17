"""
run.py
───────
Entry point for testing the agent from backend/ folder.
Run with: python3 run.py
"""

import asyncio
from agent.graph import agent_graph
from langchain_core.messages import HumanMessage


async def test():
    url     = input("Enter URL to analyze: ").strip()
    message = input("What would you like to do?: ").strip()

    print(f"\n{'='*50}")
    print(f"Running agent for: {url}")
    print(f"{'='*50}\n")

    result = await agent_graph.ainvoke({
        "messages": [HumanMessage(content=f"{message} for {url}")],
        "url":      url
    })

    print("\n" + "="*50)
    print("FINAL RESPONSE:")
    print("="*50)
    print(result["messages"][-1].content)


asyncio.run(test())

#  https://www.globalwebproduction.com/about