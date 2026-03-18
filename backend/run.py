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
    message = input("Enter your request: ").strip()

    print(f"\n{'='*50}")
    print(f"Request: {message}")
    print(f"{'='*50}\n")

    result = await agent_graph.ainvoke({
        "messages": [HumanMessage(content=message)],
    })

    print("\n" + "="*50)
    print("FINAL RESPONSE:")
    print("="*50)
    print(result["messages"][-1].content)


asyncio.run(test())
# example: do seo analysis for https://www.globalwebproduction.com/about