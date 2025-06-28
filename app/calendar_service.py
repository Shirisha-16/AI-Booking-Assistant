import pickle
import os
from datetime import datetime, timedelta
from typing import List, Optional
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import pytz

SCOPES = ['https://www.googleapis.com/auth/calendar']

class GoogleCalendarService:
    def __init__(self, credentials_file: str, token_file: str, calendar_id: str = 'primary'):
        self.credentials_file = credentials_file
        self.token_file = token_file
        self.calendar_id = calendar_id
        self.service = None
        self._authenticate()
    
    def _authenticate(self):
        """Authenticate with Google Calendar API"""
        creds = None
        
        # Load existing token
        if os.path.exists(self.token_file):
            with open(self.token_file, 'rb') as token:
                creds = pickle.load(token)
        
        # If no valid credentials, get new ones
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_file, SCOPES)
                # Changed: Use run_local_server() without specifying port for desktop apps
                # This will automatically find an available port
                creds = flow.run_local_server(port=0)
            
            # Save credentials for next run
            with open(self.token_file, 'wb') as token:
                pickle.dump(creds, token)
        
        self.service = build('calendar', 'v3', credentials=creds)
    
    def get_free_busy(self, start_time: datetime, end_time: datetime) -> List[dict]:
        """Get free/busy information for the specified time range"""
        try:
            freebusy_request = {
                'timeMin': start_time.isoformat(),
                'timeMax': end_time.isoformat(),
                'items': [{'id': self.calendar_id}]
            }
            
            response = self.service.freebusy().query(body=freebusy_request).execute()
            return response.get('calendars', {}).get(self.calendar_id, {}).get('busy', [])
        
        except HttpError as error:
            print(f"Error getting free/busy info: {error}")
            return []
    
    def find_available_slots(self, start_date: datetime, end_date: datetime, 
                           duration_minutes: int = 60, 
                           working_hours: tuple = (9, 17)) -> List[dict]:
        """Find available time slots within the given date range"""
        available_slots = []
        busy_times = self.get_free_busy(start_date, end_date)
        
        # Convert busy times to datetime objects
        busy_periods = []
        for busy in busy_times:
            busy_start = datetime.fromisoformat(busy['start'].replace('Z', '+00:00'))
            busy_end = datetime.fromisoformat(busy['end'].replace('Z', '+00:00'))
            busy_periods.append((busy_start, busy_end))
        
        # Check each day in the range
        current_date = start_date.date()
        end_date_only = end_date.date()
        
        while current_date <= end_date_only:
            # Create working hours for this day
            work_start = datetime.combine(current_date, datetime.min.time().replace(hour=working_hours[0]))
            work_end = datetime.combine(current_date, datetime.min.time().replace(hour=working_hours[1]))
            
            # Make timezone aware
            if start_date.tzinfo:
                work_start = work_start.replace(tzinfo=start_date.tzinfo)
                work_end = work_end.replace(tzinfo=start_date.tzinfo)
            
            # Find free slots in this day
            current_time = work_start
            while current_time + timedelta(minutes=duration_minutes) <= work_end:
                slot_end = current_time + timedelta(minutes=duration_minutes)
                
                # Check if this slot conflicts with any busy period
                is_free = True
                for busy_start, busy_end in busy_periods:
                    if (current_time < busy_end and slot_end > busy_start):
                        is_free = False
                        break
                
                if is_free:
                    available_slots.append({
                        'start': current_time,
                        'end': slot_end,
                        'formatted': f"{current_time.strftime('%Y-%m-%d %I:%M %p')} - {slot_end.strftime('%I:%M %p')}"
                    })
                
                current_time += timedelta(minutes=30)  # 30-minute intervals
            
            current_date += timedelta(days=1)
        
        return available_slots
    
    def create_event(self, title: str, start_time: datetime, end_time: datetime, 
                    description: str = None) -> Optional[str]:
        """Create a new calendar event"""
        try:
            event = {
                'summary': title,
                'start': {
                    'dateTime': start_time.isoformat(),
                    'timeZone': str(start_time.tzinfo) if start_time.tzinfo else 'UTC',
                },
                'end': {
                    'dateTime': end_time.isoformat(),
                    'timeZone': str(end_time.tzinfo) if end_time.tzinfo else 'UTC',
                },
            }
            
            if description:
                event['description'] = description
            
            result = self.service.events().insert(calendarId=self.calendar_id, body=event).execute()
            return result.get('id')
        
        except HttpError as error:
            print(f"Error creating event: {error}")
            return None