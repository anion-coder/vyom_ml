import asyncio
import json
from fastapi import FastAPI, WebSocket
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
import websockets  # For connecting to Flutter's WebSocket server
from config import settings

app = FastAPI()

# Flutter WebSocket URL (Replace with actual Flutter WebSocket IP/Port)
FLUTTER_WS_URL = "ws://your-flutter-app-ip:5000/ws/user123"

SCREENS = {
    "home": ["home", "main menu", "dashboard"],
    "profile": ["profile", "my account", "user details"],
    "settings": ["settings", "preferences", "account settings"],
    "financial_aid": ["financial aid", "scholarship", "student loans"],
    "transactions": ["transactions", "banking", "payment history"],
    "help": ["help", "customer support", "faq"]
}

# WebSocket connection handler
@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """Handles incoming WebSocket connections from Flutter."""
    await websocket.accept()
    print(f"Connected to Flutter WebSocket for session: {session_id}")

    try:
        while True:
            await websocket.receive_text()  # Keep connection alive
    except:
        print(f"Flutter WebSocket disconnected for session: {session_id}")

# Routing Agent using LLM
class PageRoutingAgent:
    def __init__(self, model):
        self.model = model
        self.routing_prompt = ChatPromptTemplate.from_messages([
            ("system", """
            You are an AI assistant that helps users navigate an app by understanding their requests.
            Given a user query, identify the screen they wish to go to. 
            
            Available Screens:
            - Home
            - Profile
            - Settings
            - Financial Aid
            - Transactions
            - Help

            Respond with ONLY the screen name in lowercase (e.g., 'home', 'profile', 'settings'). 
            If unclear, return 'home' as the default screen.
            """),
            ("human", "{query}")
        ])
        self.routing_chain = self.routing_prompt | self.model

    def get_screen(self, query: str) -> str:
        response = self.routing_chain.invoke({"query": query})
        screen = response.content.strip().lower()
        return screen if screen in SCREENS else "home"

# Function to manually trigger routing and send WebSocket message to Flutter
async def process_manual_query(user_query: str):
    """
    Manually input a query, determine the target screen, and send a WebSocket message to Flutter.
    """
    # Remove hardcoded API key
    # groq_api_key = "your_groq_api_key_here"  # Replace with your API Key
    model = ChatGroq(api_key=settings.GROQ_API_KEY, model="llama-3.1-8b-instant")
    routing_agent = PageRoutingAgent(model)

    # Determine screen
    target_screen = routing_agent.get_screen(user_query)

    # Create WebSocket message
    message = json.dumps({
        "action": "navigate",
        "screen": target_screen,
        "message": f"Navigate to {target_screen} screen."
    })

    # Connect to Flutter WebSocket and send message
    try:
        async with websockets.connect(FLUTTER_WS_URL) as ws:
            await ws.send(message)
            print(f"Sent navigation command: {message}")
    except Exception as e:
        print(f"Failed to send message to Flutter WebSocket: {e}")

# Example route to trigger routing manually
@app.post("/test-route")
async def test_routing():
    user_query = "I want to check my past transactions"  # Manually change this query
    await process_manual_query(user_query)
    return {"status": "Query sent to Flutter"}