#!/usr/bin/env python3
"""
Local API Server for Weather Agent
Run this script to start a local server that provides REST API endpoints
for testing with Postman.
"""

import asyncio
import json
import uuid
from datetime import datetime
from typing import Dict, Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

# Import your weather agent
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'weatheragent'))

from weatheragent.agent import root_agent
from google.adk.runners import InMemoryRunner

# Initialize FastAPI app
app = FastAPI(title="Weather Agent API", version="1.0.0")

# Add CORS middleware for web testing
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global storage for sessions (in production, use a database)
sessions: Dict[str, Any] = {}
runners: Dict[str, InMemoryRunner] = {}

# Request/Response models
class CreateSessionRequest(BaseModel):
    user_id: str
    app_name: str = "weatheragent"

class SessionResponse(BaseModel):
    id: str
    user_id: str
    app_name: str
    state: Dict[str, Any]
    last_update_time: float

class QueryRequest(BaseModel):
    message: str
    user_id: str

class QueryResponse(BaseModel):
    response: str
    session_id: str
    events: list

# API Endpoints

@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "message": "Weather Agent API is running!",
        "agent": root_agent.name,
        "endpoints": {
            "create_session": "POST /v1/sessions",
            "query_agent": "POST /v1/sessions/{session_id}/query",
            "get_session": "GET /v1/sessions/{session_id}",
            "list_sessions": "GET /v1/sessions"
        }
    }

@app.post("/v1/sessions", response_model=SessionResponse)
async def create_session(request: CreateSessionRequest):
    """Create a new session for the weather agent"""
    try:
        session_id = str(uuid.uuid4())
        
        # Create a new runner for this session
        runner = InMemoryRunner(
            agent=root_agent,
            app_name=request.app_name
        )
        
        # Create session
        session = runner.create_session(user_id=request.user_id)
        
        # Store session and runner
        sessions[session_id] = {
            "id": session_id,
            "user_id": request.user_id,
            "app_name": request.app_name,
            "state": session.state.to_dict(),
            "last_update_time": datetime.now().timestamp(),
            "adk_session": session
        }
        runners[session_id] = runner
        
        return SessionResponse(
            id=session_id,
            user_id=request.user_id,
            app_name=request.app_name,
            state=session.state.to_dict(),
            last_update_time=sessions[session_id]["last_update_time"]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create session: {str(e)}")

@app.get("/v1/sessions/{session_id}", response_model=SessionResponse)
async def get_session(session_id: str):
    """Get session details"""
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = sessions[session_id]
    return SessionResponse(
        id=session["id"],
        user_id=session["user_id"],
        app_name=session["app_name"],
        state=session["state"],
        last_update_time=session["last_update_time"]
    )

@app.get("/v1/sessions")
async def list_sessions(user_id: str = None):
    """List all sessions, optionally filtered by user_id"""
    if user_id:
        user_sessions = [s for s in sessions.values() if s["user_id"] == user_id]
        return {"sessions": [s["id"] for s in user_sessions]}
    else:
        return {"sessions": list(sessions.keys())}

@app.post("/v1/sessions/{session_id}/query", response_model=QueryResponse)
async def query_agent(session_id: str, request: QueryRequest):
    """Send a query to the weather agent and get response"""
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    if session_id not in runners:
        raise HTTPException(status_code=500, detail="Runner not found for session")
    
    try:
        runner = runners[session_id]
        session_data = sessions[session_id]
        adk_session = session_data["adk_session"]
        
        # Run the agent with the user's message
        events = []
        response_text = ""
        
        async for event in runner.run_async(
            session=adk_session,
            new_message=request.message
        ):
            events.append({
                "author": event.author,
                "content": str(event.content) if event.content else "",
                "timestamp": event.timestamp,
                "is_final_response": event.is_final_response()
            })
            
            # Extract text response
            if event.content and hasattr(event.content, 'parts'):
                for part in event.content.parts:
                    if hasattr(part, 'text') and part.text:
                        response_text += part.text
        
        # Update session timestamp
        sessions[session_id]["last_update_time"] = datetime.now().timestamp()
        sessions[session_id]["state"] = adk_session.state.to_dict()
        
        return QueryResponse(
            response=response_text or "No response generated",
            session_id=session_id,
            events=events
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process query: {str(e)}")

@app.delete("/v1/sessions/{session_id}")
async def delete_session(session_id: str):
    """Delete a session"""
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    del sessions[session_id]
    if session_id in runners:
        del runners[session_id]
    
    return {"message": f"Session {session_id} deleted successfully"}

if __name__ == "__main__":
    print("🚀 Starting Weather Agent API Server...")
    print("📖 API Documentation: http://localhost:8080/docs")
    print("🔍 Health Check: http://localhost:8080/")
    print("💡 Use Postman to test the endpoints!")
    
    uvicorn.run(
        "local_api_server:app",
        host="127.0.0.1",
        port=8080,
        reload=True,
        log_level="info"
    )
