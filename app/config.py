import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    GROQ_API_KEY = os.getenv("GROQ_API_KEY")
    GOOGLE_CALENDAR_CREDENTIALS_FILE = os.getenv("GOOGLE_CALENDAR_CREDENTIALS_FILE", "credentials.json")
    GOOGLE_CALENDAR_TOKEN_FILE = os.getenv("GOOGLE_CALENDAR_TOKEN_FILE", "token.json")
    CALENDAR_ID = os.getenv("CALENDAR_ID", "primary")
    
    # FastAPI settings
    API_HOST = os.getenv("API_HOST", "0.0.0.0")
    API_PORT = int(os.getenv("API_PORT", 8000))
    
    # Streamlit settings
    FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:8501")
    BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

settings = Settings()