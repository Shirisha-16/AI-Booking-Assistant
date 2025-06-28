from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

class ChatMessage(BaseModel):
    """Model for incoming chat messages"""
    message: str = Field(..., description="The user's message")
    session_id: Optional[str] = Field(None, description="Session identifier")
    timestamp: Optional[str] = Field(None, description="Message timestamp")
    
    class Config:
        json_schema_extra = {
            "example": {
                "message": "I want to book an appointment for tomorrow at 2 PM",
                "session_id": "12345-67890",
                "timestamp": "2024-01-15T14:30:00Z"
            }
        }

class TimeSlot(BaseModel):
    """Model for available time slots"""
    start: str = Field(..., description="Start time of the slot")
    end: str = Field(..., description="End time of the slot")
    time: Optional[str] = Field(None, description="Formatted time display")
    available: bool = Field(True, description="Whether the slot is available")
    
    class Config:
        json_schema_extra = {
            "example": {
                "start": "2024-01-15T14:00:00Z",
                "end": "2024-01-15T15:00:00Z",
                "time": "2:00 PM - 3:00 PM",
                "available": True
            }
        }

class ChatResponse(BaseModel):
    """Model for chat responses"""
    response: str = Field(..., description="The assistant's response")
    session_id: str = Field(..., description="Session identifier")
    booking_confirmed: bool = Field(False, description="Whether a booking was confirmed")
    suggested_slots: List[Dict[str, Any]] = Field(default_factory=list, description="Suggested time slots")
    booking_status: Optional[str] = Field(None, description="Current booking status")
    
    class Config:
        json_schema_extra = {
            "example": {
                "response": "I found some available slots for tomorrow. Which time works best for you?",
                "session_id": "12345-67890",
                "booking_confirmed": False,
                "suggested_slots": [
                    {
                        "start": "2024-01-15T14:00:00Z",
                        "end": "2024-01-15T15:00:00Z",
                        "time": "2:00 PM - 3:00 PM"
                    }
                ]
            }
        }

class BookingConfirmation(BaseModel):
    """Model for booking confirmation requests"""
    conversation_id: str = Field(..., description="Conversation/session ID")
    selected_slot: Dict[str, Any] = Field(..., description="Selected time slot")
    action: str = Field("confirm_booking", description="Action to perform")
    additional_details: Optional[Dict[str, Any]] = Field(None, description="Additional booking details")
    
    class Config:
        json_schema_extra = {
            "example": {
                "conversation_id": "12345-67890",
                "selected_slot": {
                    "start": "2024-01-15T14:00:00Z",
                    "end": "2024-01-15T15:00:00Z",
                    "time": "2:00 PM - 3:00 PM"
                },
                "action": "confirm_booking"
            }
        }

class BookingResponse(BaseModel):
    """Model for booking confirmation responses"""
    message: str = Field(..., description="Confirmation message")
    booking_confirmed: bool = Field(..., description="Whether booking was successful")
    session_id: str = Field(..., description="Session identifier")
    booking_id: Optional[str] = Field(None, description="Unique booking identifier")
    booking_details: Optional[Dict[str, Any]] = Field(None, description="Booking details")
    
    class Config:
        json_schema_extra = {
            "example": {
                "message": "Your appointment has been confirmed for tomorrow at 2:00 PM",
                "booking_confirmed": True,
                "session_id": "12345-67890",
                "booking_id": "booking_123456",
                "booking_details": {
                    "title": "Meeting",
                    "start_time": "2024-01-15T14:00:00Z",
                    "end_time": "2024-01-15T15:00:00Z"
                }
            }
        }

class SessionData(BaseModel):
    """Model for session data"""
    session_id: str = Field(..., description="Session identifier")
    created_at: Optional[str] = Field(None, description="Session creation timestamp")
    messages: List[Dict[str, Any]] = Field(default_factory=list, description="Message history")
    booking_history: List[Dict[str, Any]] = Field(default_factory=list, description="Booking history")
    
    class Config:
        json_schema_extra = {
            "example": {
                "session_id": "12345-67890",
                "created_at": "2024-01-15T12:00:00Z",
                "messages": [
                    {
                        "role": "user",
                        "content": "I want to book an appointment",
                        "timestamp": "2024-01-15T12:01:00Z"
                    }
                ],
                "booking_history": []
            }
        }

class HealthStatus(BaseModel):
    """Model for health check responses"""
    status: str = Field(..., description="Overall system status")
    agent_status: str = Field(..., description="Booking agent status")
    active_sessions: int = Field(..., description="Number of active sessions")
    timestamp: Optional[str] = Field(None, description="Health check timestamp")
    
    class Config:
        json_schema_extra = {
            "example": {
                "status": "healthy",
                "agent_status": "healthy",
                "active_sessions": 5,
                "timestamp": "2024-01-15T14:30:00Z"
            }
        }