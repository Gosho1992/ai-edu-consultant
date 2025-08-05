# main.py
from fastapi import FastAPI, Security
from fastapi.middleware.cors import CORSMiddleware
from backend import EduBot, api_key_header  # assumes your EduBot is in backend.py

app = FastAPI()
edubot = EduBot()

# Optional: Allow access from frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # You can restrict this later
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/chat")
async def chat_endpoint(message: str, api_key: str = Security(api_key_header)):
    edubot.security.validate_api_key(api_key)
    return {"response": edubot.generate_response(message)}
