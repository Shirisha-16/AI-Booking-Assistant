from datetime import datetime, timedelta
from typing import List, Dict, Any
from langchain.tools import tool
from ..calendar_service import GoogleCalendarService
from ..config import settings
import pytz

# Initialize calendar service
calendar_service = GoogleCalendarService(
    credentials_file=settings.GOOGLE_CALENDAR_CREDENTIALS_FILE,
    token_file=settings.GOOGLE_CALENDAR_TOKEN_FILE,
    calendar_id=settings.CALENDAR_ID
)

@tool
def check_availability(start_date: str, end_date: str, duration_minutes: int = 60) -> List[Dict[str, Any]]:
    """
    Check calendar availability for a given date range.
    
    Args:
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format  
        duration_minutes: Duration of the meeting in minutes (default 60)
    
    Returns:
        List of available time slots
    """
    try:
        # Parse dates
        start_dt = datetime.strptime(start_date, '%Y-%m-%d')
        end_dt = datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1)
        
        # Make timezone aware (assuming local timezone)
        local_tz = pytz.timezone('UTC')  # You can change this to user's timezone
        start_dt = local_tz.localize(start_dt)
        end_dt = local_tz.localize(end_dt)
        
        # Get available slots
        slots = calendar_service.find_available_slots(
            start_dt, end_dt, duration_minutes
        )
        
        return [{"time": slot["formatted"], "start": slot["start"].isoformat(), "end": slot["end"].isoformat()} 
                for slot in slots[:10]]  # Limit to 10 slots
    
    except Exception as e:
        return [{"error": f"Error checking availability: {str(e)}"}]

@tool  
def book_appointment(title: str, start_time: str, end_time: str, description: str = "") -> Dict[str, Any]:
    """
    Book an appointment in the calendar.
    
    Args:
        title: Title of the appointment
        start_time: Start time in ISO format
        end_time: End time in ISO format
        description: Optional description
    
    Returns:
        Booking confirmation details
    """
    try:
        # Parse datetime strings
        start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
        end_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
        
        # Create the event
        event_id = calendar_service.create_event(title, start_dt, end_dt, description)
        
        if event_id:
            return {
                "success": True,
                "event_id": event_id,
                "message": f"Successfully booked '{title}' from {start_dt.strftime('%Y-%m-%d %I:%M %p')} to {end_dt.strftime('%I:%M %p')}"
            }
        else:
            return {"success": False, "message": "Failed to create calendar event"}
    
    except Exception as e:
        return {"success": False, "message": f"Error booking appointment: {str(e)}"}

@tool
def get_current_time() -> str:
    """Get the current date and time."""
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S')