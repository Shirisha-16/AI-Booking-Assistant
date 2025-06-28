import streamlit as st
import requests
import json
from datetime import datetime
import uuid
import os

# Page config
st.set_page_config(
    page_title="TailorTalk - AI Booking Assistant",
    page_icon="📅",
    layout="wide"
)

# Custom CSS
st.markdown("""
<style>
    .chat-message {
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
        display: flex;
        flex-direction: column;
    }
    .user-message {
        background-color: #007bff;
        color: white;
        align-self: flex-end;
        max-width: 80%;
        margin-left: auto;
    }
    .assistant-message {
        background-color: #f8f9fa;
        color: #333;
        align-self: flex-start;
        max-width: 80%;
        border: 1px solid #dee2e6;
    }
    .suggested-slots {
        background-color: #e7f3ff;
        border: 1px solid #b3d9ff;
        border-radius: 0.25rem;
        padding: 0.5rem;
        margin: 0.5rem 0;
    }
    .booking-confirmed {
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        color: #155724;
        border-radius: 0.25rem;
        padding: 1rem;
        margin: 1rem 0;
        text-align: center;
    }
</style>
""", unsafe_allow_html=True)

# Configuration
BACKEND_URL = os.getenv('BACKEND_URL', 'http://localhost:8000')

# Initialize session state
if 'conversation_id' not in st.session_state:
    st.session_state.conversation_id = str(uuid.uuid4())
if 'messages' not in st.session_state:
    st.session_state.messages = []
if 'booking_status' not in st.session_state:
    st.session_state.booking_status = None

# Title and header
st.title("TailorTalk - AI Booking Assistant")
st.markdown("---")

# Sidebar with information
with st.sidebar:
    st.header("About TailorTalk")
    st.write("An intelligent booking assistant that helps you schedule appointments through natural conversation.")
    
    st.header("Features")
    st.write("• Natural language booking")
    st.write("• Calendar integration")
    st.write("• Smart scheduling")
    st.write("• Confirmation system")
    
    if st.button("Clear Conversation"):
        st.session_state.messages = []
        st.session_state.conversation_id = str(uuid.uuid4())
        st.session_state.booking_status = None
        st.rerun()

# Main chat interface
st.header("Chat with TailorTalk")

# Display chat messages
for message in st.session_state.messages:
    if message["role"] == "user":
        st.markdown(f"""
        <div class="chat-message user-message">
            <strong>You:</strong> {message["content"]}
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div class="chat-message assistant-message">
            <strong>TailorTalk:</strong> {message["content"]}
        </div>
        """, unsafe_allow_html=True)
        
        # Display suggested slots if available
        if "suggested_slots" in message:
            st.markdown("""
            <div class="suggested-slots">
                <strong>Suggested Time Slots:</strong>
            </div>
            """, unsafe_allow_html=True)
            
            for i, slot in enumerate(message["suggested_slots"]):
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.write(f"• {slot['start']} - {slot['end']}")
                with col2:
                    if st.button(f"Book", key=f"book_{i}_{len(st.session_state.messages)}"):
                        # Send booking confirmation
                        booking_data = {
                            "conversation_id": st.session_state.conversation_id,
                            "selected_slot": slot,
                            "action": "confirm_booking"
                        }
                        
                        try:
                            response = requests.post(f"{BACKEND_URL}/confirm-booking", json=booking_data)
                            if response.status_code == 200:
                                result = response.json()
                                st.session_state.booking_status = "confirmed"
                                st.session_state.messages.append({
                                    "role": "assistant",
                                    "content": result.get("message", "Booking confirmed successfully!")
                                })
                                st.rerun()
                            else:
                                st.error("Failed to confirm booking. Please try again.")
                        except Exception as e:
                            st.error(f"Error: {str(e)}")

# Display booking confirmation
if st.session_state.booking_status == "confirmed":
    st.markdown("""
    <div class="booking-confirmed">
        <h3>🎉 Booking Confirmed!</h3>
        <p>Your appointment has been successfully scheduled.</p>
    </div>
    """, unsafe_allow_html=True)

# Chat input
user_input = st.chat_input("Type your message here...")

if user_input:
    # Add user message to session state
    st.session_state.messages.append({"role": "user", "content": user_input})
    
    # Prepare request data
    request_data = {
        "message": user_input,
        "conversation_id": st.session_state.conversation_id,
        "timestamp": datetime.now().isoformat()
    }
    
    # Send to backend
    try:
        with st.spinner("TailorTalk is thinking..."):
            response = requests.post(f"{BACKEND_URL}/chat", json=request_data)
        
        if response.status_code == 200:
            result = response.json()
            
            # Add assistant response to session state
            assistant_message = {
                "role": "assistant",
                "content": result.get("response", "I'm sorry, I couldn't process that request.")
            }
            
            # Add suggested slots if available
            if "suggested_slots" in result:
                assistant_message["suggested_slots"] = result["suggested_slots"]
            
            st.session_state.messages.append(assistant_message)
            
            # Update booking status if needed
            if result.get("booking_status"):
                st.session_state.booking_status = result["booking_status"]
            
        else:
            st.error(f"Error: {response.status_code} - {response.text}")
            
    except requests.exceptions.ConnectionError:
        st.error("Could not connect to the backend server. Please make sure it's running.")
    except Exception as e:
        st.error(f"An error occurred: {str(e)}")
    
    # Rerun to display new messages
    st.rerun()

# Footer
st.markdown("---")
st.markdown("*Powered by TailorTalk AI Assistant*")