TailorTalk Booking Agent
An AI-powered booking assistant that integrates with Google Calendar to help manage appointments and bookings through a conversational interface.
Features

🤖 AI-Powered Chat Interface - Natural language booking conversations using Groq API
📅 Google Calendar Integration - Seamless appointment scheduling and management
🎯 Smart Agent System - LangGraph-powered agent for intelligent booking workflows
⚡ FastAPI Backend - High-performance REST API for booking operations
🎨 Streamlit Frontend - User-friendly chat interface for customers
🔄 Real-time Availability - Live calendar availability checking
📱 Session Management - Persistent conversation tracking

Technology Stack

Backend: FastAPI, Python 3.8+
AI/ML: Groq API, LangGraph
Calendar: Google Calendar API
Frontend: Streamlit
Authentication: Google OAuth 2.0

Project Structure
tailortalk-booking-agent/
├── app/
│   ├── main.py                 # FastAPI main application
│   ├── models.py              # Pydantic models
│   ├── calendar_service.py    # Google Calendar integration
│   ├── config.py              # Configuration settings
│   └── agent/
│       ├── booking_agent.py   # LangGraph agent implementation
│       ├── tools.py           # Calendar tools for agent
│       └── prompts.py         # Agent prompts and templates
├── frontend/
│   └── streamlit_app.py       # Streamlit chat interface
├── .env.example               # Environment variables template
├── credentials.json.example   # Google API credentials template
├── requirements.txt           # Python dependencies
└── README.md                  # This file
Prerequisites

Python 3.8 or higher
Google Cloud Project with Calendar API enabled
Groq API account
Git

Installation
1. Clone the Repository
   https://github.com/Shirisha-16/AI-Booking-Assistant.git
   cd AI-Booking-Assistant
   2. Create Virtual Environment
bashpython -m venv venv

# On Windows
venv\Scripts\activate

# On macOS/Linux
source venv/bin/activate
3. Install Dependencies
bashpip install -r requirements.txt
4. Set Up Environment Variables
bash# Copy the example file
cp .env.example .env

# Edit .env with your actual values
Required environment variables:

GROQ_API_KEY: Your Groq API key
GOOGLE_CLIENT_ID: Google OAuth client ID
GOOGLE_CLIENT_SECRET: Google OAuth client secret
API_HOST: API host (default: 0.0.0.0)
API_PORT: API port (default: 8000)
FRONTEND_URL: Frontend URL (default: http://localhost:8501)

5. Set Up Google Calendar API

Go to Google Cloud Console
Create a new project or select existing one
Enable Google Calendar API
Create OAuth 2.0 credentials
Download the credentials JSON file
Copy credentials.json.example to credentials.json
Replace with your actual Google credentials

6. Configure Google OAuth
Add these redirect URIs in your Google Cloud Console:

http://localhost:8000/auth/callback
http://localhost:8501 (for Streamlit)

Usage
Start the Backend API
bash# From project root directory
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
The API will be available at: http://localhost:8000
API Documentation: http://localhost:8000/docs
Start the Frontend (Optional)
bash# In a new terminal
streamlit run frontend/streamlit_app.py
The frontend will be available at: http://localhost:8501
API Endpoints
Main Endpoints

GET / - API status and information
POST /chat - Send chat messages to the booking agent
POST /confirm-booking - Confirm a booking slot
GET /health - Health check endpoint

Session Management

GET /sessions/{session_id} - Get session history
DELETE /sessions/{session_id} - Clear session history

Example API Usage
Send a Chat Message
bashcurl -X POST "http://localhost:8000/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "I want to book an appointment for tomorrow at 2 PM",
    "session_id": "optional-session-id"
  }'
Confirm a Booking
bashcurl -X POST "http://localhost:8000/confirm-booking" \
  -H "Content-Type: application/json" \
  -d '{
    "conversation_id": "session-id",
    "selected_slot": {
      "start": "2024-01-15T14:00:00",
      "end": "2024-01-15T15:00:00",
      "title": "Appointment"
    }
  }'
Configuration
Business Settings
Update app/config.py or environment variables:
pythonBUSINESS_NAME = "TailorTalk"
BUSINESS_EMAIL = "your-email@example.com"
BUSINESS_TIMEZONE = "Asia/Kolkata"
DEFAULT_APPOINTMENT_DURATION = 60  # minutes
Agent Prompts
Customize the AI agent behavior in app/agent/prompts.py:

BOOKING_AGENT_PROMPT: Main agent instructions
CONFIRMATION_PROMPT: Booking confirmation messages

Development
Running Tests
bash# Install test dependencies
pip install pytest pytest-asyncio

# Run tests
pytest
Code Style
bash# Install formatting tools
pip install black flake8

# Format code
black .

# Check code style
flake8 .
Adding New Features

Create a new branch: git checkout -b feature/new-feature
Make your changes
Test thoroughly
Commit: git commit -m "Add new feature"
Push: git push origin feature/new-feature
Create a Pull Request

Deployment
Using Docker (Coming Soon)
bash# Build image
docker build -t tailortalk-booking .

# Run container
docker run -p 8000:8000 tailortalk-booking
Cloud Deployment
The application can be deployed to:

Heroku: Use the included Procfile
Railway: Connect your GitHub repository
Google Cloud Run: Deploy containerized version
AWS: Use ECS or Lambda

Troubleshooting
Common Issues

Import Error: Make sure you're running from the project root directory
bashpython -m uvicorn app.main:app --reload

Google Calendar API Error: Verify your credentials.json file and OAuth setup
Groq API Error: Check your API key in the .env file
Port Already in Use: Change the port in .env or kill existing processes
bash# Find process using port 8000
lsof -i :8000  # macOS/Linux
netstat -ano | findstr :8000  # Windows


Logs
Check application logs for debugging:

API logs: Console output when running uvicorn
Streamlit logs: Browser console and terminal output

Contributing

Fork the repository
Create your feature branch (git checkout -b feature/AmazingFeature)
Commit your changes (git commit -m 'Add some AmazingFeature')
Push to the branch (git push origin feature/AmazingFeature)
Open a Pull Request
