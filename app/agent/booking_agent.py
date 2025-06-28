from groq import Groq
from typing import TypedDict, List, Any, Dict
from datetime import datetime, timedelta
import json
import re
import logging
import os

# Try to import langgraph, fall back to simple state management if not available
try:
    from langgraph.graph import StateGraph, END
    LANGGRAPH_AVAILABLE = True
except ImportError:
    LANGGRAPH_AVAILABLE = False
    logging.warning("LangGraph not available, using simple state management")

from app.agent.tools import check_availability, book_appointment, get_current_time
from app.agent.prompts import BOOKING_AGENT_PROMPT, CONFIRMATION_PROMPT

# Import settings with fallback
try:
    from app.config import settings
except ImportError:
    class Settings:
        GROQ_API_KEY = os.getenv('GROQ_API_KEY')
    settings = Settings()

class BookingState(TypedDict):
    messages: List[Any]
    user_input: str
    intent: str
    booking_details: Dict[str, Any]
    available_slots: List[Dict[str, Any]]
    confirmation_pending: bool
    booking_confirmed: bool
    session_data: Dict[str, Any]

class GroqLLMWrapper:
    """Wrapper to make Groq API compatible with LangChain-style interfaces"""
    
    def __init__(self, api_key: str, model: str = "llama3-70b-8192"):
        self.client = Groq(api_key=api_key)
        self.model = model
    
    def invoke(self, messages):
        """Convert LangChain-style messages to Groq format and get response"""
        # Convert messages to Groq format
        groq_messages = []
        
        for msg in messages:
            if hasattr(msg, 'content'):
                if msg.__class__.__name__ == 'SystemMessage':
                    groq_messages.append({"role": "system", "content": msg.content})
                elif msg.__class__.__name__ == 'HumanMessage':
                    groq_messages.append({"role": "user", "content": msg.content})
                else:
                    groq_messages.append({"role": "assistant", "content": msg.content})
            elif isinstance(msg, dict):
                groq_messages.append(msg)
            else:
                groq_messages.append({"role": "user", "content": str(msg)})
        
        try:
            response = self.client.chat.completions.create(
                messages=groq_messages,
                model=self.model,
                temperature=0.1,
                max_tokens=1000
            )
            
            # Return object with content attribute to match LangChain interface
            class Response:
                def __init__(self, content):
                    self.content = content
            
            return Response(response.choices[0].message.content)
        
        except Exception as e:
            logging.error(f"Groq API call failed: {e}")
            class ErrorResponse:
                def __init__(self, error_msg):
                    self.content = f"I'm having trouble processing that request. Error: {error_msg}"
            return ErrorResponse(str(e))

class BookingAgent:
    def __init__(self):
        # Initialize Groq LLM instead of OpenAI
        self.llm = GroqLLMWrapper(
            api_key=settings.GROQ_API_KEY,
            model="llama3-70b-8192"  # You can change this to other models
        )
        self.tools = [check_availability, book_appointment, get_current_time]
        
        if LANGGRAPH_AVAILABLE:
            self.graph = self._build_graph()
        else:
            self.graph = None
    
    def _build_graph(self):
        """Build the LangGraph workflow"""
        if not LANGGRAPH_AVAILABLE:
            return None
            
        workflow = StateGraph(BookingState)
        
        # Add nodes
        workflow.add_node("understand_intent", self._understand_intent)
        workflow.add_node("check_calendar", self._check_calendar)
        workflow.add_node("confirm_booking", self._confirm_booking)
        workflow.add_node("complete_booking", self._complete_booking)
        workflow.add_node("respond", self._respond)
        
        # Add edges
        workflow.set_entry_point("understand_intent")
        workflow.add_edge("understand_intent", "check_calendar")
        workflow.add_edge("check_calendar", "confirm_booking")
        workflow.add_edge("confirm_booking", "complete_booking")
        workflow.add_edge("complete_booking", "respond")
        workflow.add_edge("respond", END)
        
        return workflow.compile()
    
    def _understand_intent(self, state: BookingState) -> BookingState:
        """Understand user intent and extract booking details"""
        user_message = state["user_input"]
        
        # Enhanced prompt for better Groq performance
        prompt = f"""
        You are a professional appointment booking assistant. Analyze the user's message and extract booking information.
        
        User message: "{user_message}"
        
        Extract the following information and respond ONLY with a valid JSON object:
        - intent: one of [book_appointment, check_availability, confirm_booking, general_inquiry]
        - details: object containing:
          - date: date in YYYY-MM-DD format if mentioned (null if not specified)
          - time: time in HH:MM format if mentioned (null if not specified)
          - duration: duration in minutes (default 60 if not specified)
          - title: purpose/title of meeting (default "Meeting" if not specified)
          - needs_clarification: array of missing information needed

        Examples:
        - "Book a meeting tomorrow at 2 PM" → {{"intent": "book_appointment", "details": {{"date": "2024-XX-XX", "time": "14:00", "duration": 60, "title": "Meeting", "needs_clarification": []}}}}
        - "Do you have time Friday?" → {{"intent": "check_availability", "details": {{"date": null, "time": null, "duration": 60, "title": "Meeting", "needs_clarification": ["specific_date", "preferred_time"]}}}}

        JSON Response:
        """
        
        try:
            # Create message in the format expected by the wrapper
            class SystemMessage:
                def __init__(self, content):
                    self.content = content
            
            response = self.llm.invoke([SystemMessage(content=prompt)])
            
            # Clean the response to extract JSON
            content = response.content.strip()
            
            # Try to find JSON in the response
            json_start = content.find('{')
            json_end = content.rfind('}') + 1
            
            if json_start != -1 and json_end > json_start:
                json_str = content[json_start:json_end]
                result = json.loads(json_str)
            else:
                # Fallback if no proper JSON found
                result = json.loads(content)
            
            state["intent"] = result.get("intent", "general_inquiry")
            state["booking_details"] = result.get("details", {})
            
        except Exception as e:
            # Enhanced fallback parsing
            logging.warning(f"Intent extraction failed: {e}")
            state["intent"] = "general_inquiry"
            state["booking_details"] = self._parse_basic_intent(user_message)
        
        return state
    
    def _parse_basic_intent(self, message: str) -> Dict[str, Any]:
        """Enhanced fallback parsing for booking details"""
        details = {
            "duration": 60,
            "title": "Meeting",
            "needs_clarification": []
        }
        
        message_lower = message.lower()
        
        # Detect intent
        if any(word in message_lower for word in ['book', 'schedule', 'appointment', 'meeting', 'call']):
            # Date parsing
            if 'tomorrow' in message_lower:
                tomorrow = datetime.now() + timedelta(days=1)
                details["date"] = tomorrow.strftime('%Y-%m-%d')
            elif 'today' in message_lower:
                details["date"] = datetime.now().strftime('%Y-%m-%d')
            elif 'next week' in message_lower:
                next_week = datetime.now() + timedelta(days=7)
                details["date"] = next_week.strftime('%Y-%m-%d')
            elif any(day in message_lower for day in ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']):
                # Basic day detection - you could enhance this
                details["needs_clarification"].append("specific_date")
            
            # Time parsing - enhanced patterns
            time_patterns = [
                r'\b(\d{1,2}):(\d{2})\s*(am|pm|AM|PM)\b',  # 2:30 PM
                r'\b(\d{1,2})\s*(am|pm|AM|PM)\b',          # 2 PM
                r'\b(\d{1,2}):(\d{2})\b',                  # 14:30
            ]
            
            for pattern in time_patterns:
                time_match = re.search(pattern, message)
                if time_match:
                    details["time"] = time_match.group(0)
                    break
            
            # Duration parsing
            duration_match = re.search(r'(\d+)\s*(hour|hr|minute|min)', message_lower)
            if duration_match:
                num = int(duration_match.group(1))
                unit = duration_match.group(2)
                if 'hour' in unit or 'hr' in unit:
                    details["duration"] = num * 60
                else:
                    details["duration"] = num
            
            # Title extraction
            meeting_types = ['call', 'meeting', 'appointment', 'interview', 'consultation', 'session']
            for meeting_type in meeting_types:
                if meeting_type in message_lower:
                    details["title"] = meeting_type.capitalize()
                    break
        
        return details
    
    def _check_calendar(self, state: BookingState) -> BookingState:
        """Check calendar availability with better error handling"""
        details = state["booking_details"]
        
        if state["intent"] in ["book_appointment", "check_availability"]:
            try:
                if details.get("date"):
                    # Check availability for the specified date
                    start_date = details["date"]
                    end_date = details["date"]
                    duration = details.get("duration", 60)
                    
                    result = check_availability.invoke({
                        "start_date": start_date,
                        "end_date": end_date,
                        "duration_minutes": duration
                    })
                    
                    state["available_slots"] = result if isinstance(result, list) else []
                else:
                    # Check next few days if no specific date
                    today = datetime.now()
                    end_date = today + timedelta(days=7)
                    
                    result = check_availability.invoke({
                        "start_date": today.strftime('%Y-%m-%d'),
                        "end_date": end_date.strftime('%Y-%m-%d'),
                        "duration_minutes": details.get("duration", 60)
                    })
                    
                    # Limit to top 5 slots for better UX
                    state["available_slots"] = (result[:5] if isinstance(result, list) else [])
                    
            except Exception as e:
                logging.error(f"Calendar check failed: {e}")
                state["available_slots"] = []
                state["booking_details"]["error"] = "Could not check calendar availability"
        
        return state
    
    def _confirm_booking(self, state: BookingState) -> BookingState:
        """Handle booking confirmation with better intent detection"""
        user_input_lower = state["user_input"].lower()
        
        # Enhanced confirmation detection
        confirmation_phrases = ['yes', 'confirm', 'book it', 'schedule it', 'that works', 'perfect', 'sounds good']
        rejection_phrases = ['no', 'cancel', 'not now', 'different time']
        
        if (state["intent"] == "confirm_booking" or 
            any(phrase in user_input_lower for phrase in confirmation_phrases)):
            state["confirmation_pending"] = False
            state["booking_confirmed"] = True
        elif any(phrase in user_input_lower for phrase in rejection_phrases):
            state["confirmation_pending"] = False
            state["booking_confirmed"] = False
        else:
            state["confirmation_pending"] = True
        
        return state
    
    def _complete_booking(self, state: BookingState) -> BookingState:
        """Complete the booking if confirmed"""
        if state.get("booking_confirmed") and state["booking_details"].get("confirmed_slot"):
            try:
                slot = state["booking_details"]["confirmed_slot"]
                title = state["booking_details"].get("title", "Meeting")
                
                result = book_appointment.invoke({
                    "title": title,
                    "start_time": slot["start"],
                    "end_time": slot["end"],
                    "description": f"Booked via TailorTalk assistant"
                })
                
                state["booking_details"]["booking_result"] = result
                
            except Exception as e:
                logging.error(f"Booking completion failed: {e}")
                state["booking_details"]["booking_result"] = {"error": str(e)}
        
        return state
    
    def _respond(self, state: BookingState) -> BookingState:
        """Generate appropriate response using Groq"""
        intent = state["intent"]
        details = state["booking_details"]
        slots = state.get("available_slots", [])
        
        # Build context for response generation
        context = {
            "intent": intent,
            "details": details,
            "available_slots": slots[:3],  # Limit for better response
            "confirmation_pending": state.get("confirmation_pending", False),
            "booking_confirmed": state.get("booking_confirmed", False)
        }
        
        try:
            response_prompt = f"""
            You are a friendly, professional appointment booking assistant. Generate a natural response based on this context.

            Context: {json.dumps(context, default=str, indent=2)}
            User input: "{state['user_input']}"

            Guidelines:
            - Be conversational and helpful
            - If showing available slots, present them clearly with times
            - If booking is confirmed, be enthusiastic and provide details
            - If information is missing, ask specific questions
            - Keep responses concise but complete
            - Use a friendly, professional tone

            Response:
            """
            
            class SystemMessage:
                def __init__(self, content):
                    self.content = content
            
            response = self.llm.invoke([SystemMessage(content=response_prompt)])
            state["messages"] = [{"role": "assistant", "content": response.content}]
            
        except Exception as e:
            logging.error(f"Response generation failed: {e}")
            # Fallback response based on context
            if slots:
                slot_text = "\n".join([f"• {slot.get('formatted', slot.get('time', 'Available slot'))}" for slot in slots[:3]])
                fallback_response = f"I found these available times:\n{slot_text}\n\nWhich one works best for you?"
            else:
                fallback_response = "I'm here to help you book appointments. What would you like to schedule?"
            
            state["messages"] = [{"role": "assistant", "content": fallback_response}]
        
        return state
    
    def _process_without_langgraph(self, message: str, session_id: str = None) -> dict:
        """Process message without LangGraph (fallback method)"""
        state = BookingState(
            messages=[],
            user_input=message,
            intent="",
            booking_details={},
            available_slots=[],
            confirmation_pending=False,
            booking_confirmed=False,
            session_data={}
        )
        
        # Process through each step manually
        state = self._understand_intent(state)
        state = self._check_calendar(state)
        state = self._confirm_booking(state)
        state = self._complete_booking(state)
        state = self._respond(state)
        
        return {
            "response": state["messages"][-1]["content"] if state["messages"] else "I'm here to help you book appointments. What would you like to schedule?",
            "session_id": session_id or "default",
            "booking_confirmed": state.get("booking_confirmed", False),
            "suggested_slots": [
                {
                    "start": slot.get("start", ""),
                    "end": slot.get("end", ""),
                    "time": slot.get("formatted", slot.get("time", ""))
                } 
                for slot in state.get("available_slots", [])[:3]
            ]
        }
    
    def process_message(self, message: str, session_id: str = None) -> dict:
        """Process a user message and return response"""
        if not message or not message.strip():
            return {
                "response": "Hi! I'm your appointment booking assistant. I can help you schedule meetings, check availability, and manage your calendar. What would you like to schedule?",
                "session_id": session_id or "default",
                "booking_confirmed": False,
                "suggested_slots": []
            }
        
        try:
            if LANGGRAPH_AVAILABLE and self.graph:
                initial_state = BookingState(
                    messages=[],
                    user_input=message,
                    intent="",
                    booking_details={},
                    available_slots=[],
                    confirmation_pending=False,
                    booking_confirmed=False,
                    session_data={}
                )
                
                final_state = self.graph.invoke(initial_state)
                
                return {
                    "response": final_state["messages"][-1]["content"] if final_state["messages"] else "I'm here to help you book appointments. What would you like to schedule?",
                    "session_id": session_id or "default",
                    "booking_confirmed": final_state.get("booking_confirmed", False),
                    "suggested_slots": [
                        {
                            "start": slot.get("start", ""),
                            "end": slot.get("end", ""),
                            "time": slot.get("formatted", slot.get("time", ""))
                        } 
                        for slot in final_state.get("available_slots", [])[:3]
                    ]
                }
            else:
                return self._process_without_langgraph(message, session_id)
                
        except Exception as e:
            logging.error(f"Message processing failed: {e}")
            return {
                "response": f"I apologize, but I encountered an issue processing your request. Could you please try rephrasing that?",
                "session_id": session_id or "default",
                "booking_confirmed": False,
                "suggested_slots": []
            }
    
    def confirm_booking(self, slot_data: dict, session_id: str = None) -> dict:
        """Confirm a specific booking slot"""
        try:
            title = slot_data.get("title", "Meeting")
            
            result = book_appointment.invoke({
                "title": title,
                "start_time": slot_data["start"],
                "end_time": slot_data["end"],
                "description": f"Booked via TailorTalk assistant"
            })
            
            if result.get("success", False):
                return {
                    "response": f"Perfect! Your {title} has been confirmed for {slot_data.get('time', slot_data['start'])}. I've added it to your calendar and you should receive a confirmation shortly.",
                    "session_id": session_id or "default",
                    "booking_confirmed": True,
                    "booking_result": result
                }
            else:
                return {
                    "response": "I'm sorry, there was an issue confirming your booking. The time slot might no longer be available. Please try selecting a different time.",
                    "session_id": session_id or "default",
                    "booking_confirmed": False,
                    "booking_result": result
                }
                
        except Exception as e:
            logging.error(f"Booking confirmation failed: {e}")
            return {
                "response": "I apologize, but I couldn't confirm your booking at this time. Please try again later or contact support if the issue persists.",
                "session_id": session_id or "default",
                "booking_confirmed": False,
                "error": str(e)
            }