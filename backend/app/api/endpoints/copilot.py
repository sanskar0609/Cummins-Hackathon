from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import Dict
from app.services.agents.copilot import invoke_copilot
from app.core.logging import log

router = APIRouter()

# Simple connection manager for active Copilot sessions
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, session_id: str, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[session_id] = websocket

    def disconnect(self, session_id: str):
        if session_id in self.active_connections:
            del self.active_connections[session_id]

    async def send_personal_message(self, message: str, session_id: str):
        websocket = self.active_connections.get(session_id)
        if websocket:
            await websocket.send_text(message)

manager = ConnectionManager()

@router.websocket("/chat/{session_id}")
async def copilot_websocket_endpoint(websocket: WebSocket, session_id: str):
    """
    Stateful real-time Full-Duplex chat connecting directly into the robust
    LangGraph ReAct AI Copilot Core cleanly.
    """
    await manager.connect(session_id, websocket)
    log.info("copilot_connected", session=session_id)
    
    try:
        # Initial greeting natively rendered to avoid burning a token interaction
        await manager.send_personal_message(
            f"Supply Chain Copilot activated [Session: {session_id}]. How can I optimize your logistics today?", 
            session_id
        )
        
        while True:
            # Block and wait for User interaction
            user_input = await websocket.receive_text()
            log.info("copilot_query_received", session=session_id, input=user_input[:50])
            
            # Execute Long-Running AI generation
            ai_response = invoke_copilot(session_id, user_input)
            
            # Dispatch final stream back natively
            await manager.send_personal_message(ai_response, session_id)
            
    except WebSocketDisconnect:
        manager.disconnect(session_id)
        log.info("copilot_disconnected", session=session_id)
    except Exception as e:
        log.error("websocket_agent_crash", session=session_id, error=str(e))
        manager.disconnect(session_id)
