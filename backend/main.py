"""
main.py
────────
FastAPI backend with continuous chat endpoint.
Run with: python3 main.py
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from agent.graph import agent_graph
from langchain_core.messages import HumanMessage
import uvicorn

app = FastAPI(title="WebAudit AI Agent API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    message: str   # single message e.g. "do seo analysis for https://example.com"


@app.post("/chat")
async def chat(request: ChatRequest):
    try:
        result = await agent_graph.ainvoke({
            "messages": [HumanMessage(content=request.message)],
        })
        return {
            "reply":               result["messages"][-1].content,
            "seo_report":          result.get("seo_report"),
            "accessibility_report": result.get("accessibility_report"),
            "content_report":      result.get("content_report"),
            "db_result":           result.get("db_result")
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health():
    return {"status": "ok"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)