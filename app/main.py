from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from contextlib import asynccontextmanager
import uuid
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import with error handling - using absolute imports
try:
    from app.models import ChatMessage, ChatResponse
except ImportError:
    # Define models inline if import fails
    class ChatMessage(BaseModel):
        message: str
        session_id: Optional[str] = None
        timestamp: Optional[str] = None
    
    class ChatResponse(BaseModel):
        response: str
        session_id: str
        booking_confirmed: bool = False
        suggested_slots: List[Dict[str, Any]] = []

try:
    from app.agent.booking_agent import BookingAgent
except ImportError:
    logger.error("Could not import BookingAgent. Make sure all dependencies are installed.")
    # Create a dummy agent for testing
    class BookingAgent:
        def process_message(self, message: str, session_id: str = None):
            return {
                "response": "I'm sorry, the booking agent is not available right now. Please try again later.",
                "session_id": session_id or str(uuid.uuid4()),
                "booking_confirmed": False,
                "suggested_slots": []
            }
        
        def confirm_booking(self, slot_data: dict, session_id: str = None):
            return {
                "response": "Booking service is currently unavailable.",
                "session_id": session_id or str(uuid.uuid4()),
                "booking_confirmed": False
            }

# Import settings with fallback
try:
    from app.config import settings
except ImportError:
    import os
    class Settings:
        API_HOST = os.getenv('API_HOST', '0.0.0.0')
        API_PORT = int(os.getenv('API_PORT', 8000))
        GROQ_API_KEY = os.getenv('GROQ_API_KEY')
        FRONTEND_URL = os.getenv('FRONTEND_URL', 'http://localhost:8501')
    
    settings = Settings()

# Global variables for the app
booking_agent = None
sessions = {}

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    global booking_agent
    logger.info("TailorTalk Booking API starting up...")
    logger.info(f"API will be available at http://{settings.API_HOST}:{settings.API_PORT}")
    
    # Initialize the booking agent
    try:
        booking_agent = BookingAgent()
        logger.info("BookingAgent initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize BookingAgent: {e}")
        booking_agent = BookingAgent()  # Will use dummy agent
    
    yield
    
    # Shutdown
    logger.info("TailorTalk Booking API shutting down...")

app = FastAPI(
    title="TailorTalk Booking API", 
    version="1.0.0",
    description="AI-powered booking assistant API",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        settings.FRONTEND_URL,
        "http://localhost:8501",
        "http://127.0.0.1:8501"
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    """Root endpoint to check API status"""
    return {
        "message": "TailorTalk Booking API is running!",
        "version": "1.0.0",
        "endpoints": {
            "chat": "/chat",
            "confirm_booking": "/confirm-booking",
            "health": "/health"
        }
    }

@app.post("/chat", response_model=ChatResponse)
async def chat(message: ChatMessage):
    """Handle chat messages from the frontend"""
    global booking_agent, sessions
    
    try:
        # Validate input
        if not message.message or not message.message.strip():
            raise HTTPException(status_code=400, detail="Message cannot be empty")
        
        # Generate session ID if not provided
        session_id = message.session_id or str(uuid.uuid4())
        
        # Store session data
        if session_id not in sessions:
            sessions[session_id] = {
                "created_at": message.timestamp,
                "messages": []
            }
        
        # Add user message to session
        sessions[session_id]["messages"].append({
            "role": "user",
            "content": message.message,
            "timestamp": message.timestamp
        })
        
        logger.info(f"Processing message for session {session_id}: {message.message[:50]}...")
        
        # Process message with the agent
        result = booking_agent.process_message(message.message, session_id)
        
        # Add assistant response to session
        sessions[session_id]["messages"].append({
            "role": "assistant",
            "content": result["response"],
            "timestamp": message.timestamp
        })
        
        return ChatResponse(
            response=result["response"],
            session_id=result["session_id"],
            booking_confirmed=result.get("booking_confirmed", False),
            suggested_slots=result.get("suggested_slots", [])
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing chat message: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.post("/confirm-booking")
async def confirm_booking(booking_data: dict):
    """Confirm a booking slot"""
    global booking_agent, sessions
    
    try:
        session_id = booking_data.get("conversation_id")
        selected_slot = booking_data.get("selected_slot")
        
        if not selected_slot:
            raise HTTPException(status_code=400, detail="No slot selected")
        
        logger.info(f"Confirming booking for session {session_id}")
        
        # Process booking confirmation
        result = booking_agent.confirm_booking(selected_slot, session_id)
        
        # Update session if exists
        if session_id and session_id in sessions:
            sessions[session_id]["messages"].append({
                "role": "assistant",
                "content": result["response"],
                "booking_confirmed": True
            })
        
        return {
            "message": result["response"],
            "booking_confirmed": result.get("booking_confirmed", False),
            "session_id": session_id
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error confirming booking: {e}")
        raise HTTPException(status_code=500, detail="Failed to confirm booking")

@app.get("/sessions/{session_id}")
async def get_session(session_id: str):
    """Get session history"""
    global sessions
    
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return sessions[session_id]

@app.delete("/sessions/{session_id}")
async def clear_session(session_id: str):
    """Clear session history"""
    global sessions
    
    if session_id in sessions:
        del sessions[session_id]
        return {"message": "Session cleared"}
    else:
        raise HTTPException(status_code=404, detail="Session not found")

@app.get("/health")
async def health():
    """Health check endpoint"""
    global booking_agent, sessions
    
    try:
        # Test if agent is working
        test_result = booking_agent.process_message("test", "health_check")
        agent_status = "healthy" if test_result else "unhealthy"
    except:
        agent_status = "unhealthy"
    
    return {
        "status": "healthy",
        "agent_status": agent_status,
        "active_sessions": len(sessions)
    }

# Exception handlers
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.error(f"Global exception handler caught: {exc}")
    return HTTPException(status_code=500, detail="Internal server error")

if __name__ == "__main__":
    import uvicorn
    
    logger.info(f"Starting server on {settings.API_HOST}:{settings.API_PORT}")
    
    uvicorn.run(
        "main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=True,
        log_level="info"
    )