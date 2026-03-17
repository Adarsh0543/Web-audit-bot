from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from agent.graph import agent_graph
from langchain_core.messages import HumanMessage
import uvicorn

from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="WebAudit AI Agent API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, replace with your actual domain
    allow_methods=["*"],
    allow_headers=["*"],
)

# Define the request structure
class AuditRequest(BaseModel):
    url: str
    task: str = "analyze"

@app.post("/audit")
async def run_audit(request: AuditRequest):
    try:
        # 1. Prepare the initial state
        # We format the prompt just like your test() script did
        input_state = {
            "messages": [HumanMessage(content=f"{request.task} for {request.url}")],
            "url": request.url
        }

        # 2. Invoke the graph
        result = await agent_graph.ainvoke(input_state)

        # 3. Return the final summary and any data stored in state
        return {
            "summary": result["messages"][-1].content,
            "seo_report": result.get("seo_report"),
            "accessibility_report": result.get("accessibility_report"),
            "content_report": result.get("content_report"),
            "db_result": result.get("db_result")
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)