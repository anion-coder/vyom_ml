from fastapi import FastAPI, APIRouter, HTTPException, Depends, BackgroundTasks, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Dict, Any, Optional, List, Union
import time
import uuid
import asyncio
from contextlib import asynccontextmanager
import json
import uvicorn


# ----- Models for request/response data -----

class AuthChallengeRequest(BaseModel):
    session_id: str
    intent_type: str
    voice_transcript: Optional[str] = None


class AuthResult(BaseModel):
    success: bool
    confidence: Optional[float] = None
    method: str = "face"
    error: Optional[str] = None


class AuthVerifyRequest(BaseModel):
    session_id: str
    auth_result: AuthResult
    challenge_id: Optional[str] = None


class PendingAuthRequest(BaseModel):
    challenge_id: str
    session_id: str
    auth_methods: List[str]
    intent_type: str
    timestamp: float
    expires_at: float


# ----- WebSocket connection manager -----

class ConnectionManager:
    """Manages WebSocket connections for real-time auth requests"""
    
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}
    
    async def connect(self, websocket: WebSocket, session_id: str):
        """Register a new WebSocket connection for a session"""
        await websocket.accept()
        if session_id not in self.active_connections:
            self.active_connections[session_id] = []
        self.active_connections[session_id].append(websocket)
        
    def disconnect(self, websocket: WebSocket, session_id: str):
        """Remove a WebSocket connection"""
        if session_id in self.active_connections:
            if websocket in self.active_connections[session_id]:
                self.active_connections[session_id].remove(websocket)
            if not self.active_connections[session_id]:
                del self.active_connections[session_id]
    
    async def send_auth_request(self, session_id: str, challenge: PendingAuthRequest):
        """Send authentication request to a connected client"""
        if session_id in self.active_connections:
            # Convert to dict for serialization
            challenge_dict = challenge.dict()
            
            message = {
                "type": "auth_required",
                "challenge": challenge_dict,
                "message": "Please complete face authentication to continue"
            }
            
            # Send to all connections for this session (might be multiple devices)
            for connection in self.active_connections[session_id]:
                try:
                    await connection.send_text(json.dumps(message))
                except Exception as e:
                    print(f"Failed to send auth request: {str(e)}")
                    
    async def send_auth_result(self, session_id: str, result: Dict[str, Any]):
        """Send authentication result to connected clients"""
        if session_id in self.active_connections:
            message = {
                "type": "auth_result",
                **result
            }
            
            for connection in self.active_connections[session_id]:
                try:
                    await connection.send_text(json.dumps(message))
                except Exception:
                    pass


# ----- Authentication state management -----

class AuthenticationState:
    """Manages authentication state for voice assistant sessions"""
    
    def __init__(self):
        self.state: Dict[str, Dict] = {}
        self.pending_challenges: Dict[str, PendingAuthRequest] = {}
        
        # For event callbacks
        self.auth_success_callbacks: Dict[str, List[Any]] = {}
        self.auth_failure_callbacks: Dict[str, List[Any]] = {}
    
    def get_state(self, session_id: str) -> Dict:
        """Get or initialize authentication state for a session"""
        if session_id not in self.state:
            self.state[session_id] = {
                'authenticated': False,
                'auth_timestamp': None,
                'auth_method': None,
                'auth_expiry': None,
                'pending_intent': None,
                'failed_attempts': 0,
                'voice_chat_paused_at': None
            }
        return self.state[session_id]
    
    def reset_state(self, session_id: str) -> None:
        """Reset authentication state"""
        if session_id in self.state:
            self.state[session_id] = {
                'authenticated': False,
                'auth_timestamp': None,
                'auth_method': None,
                'auth_expiry': None,
                'pending_intent': None,
                'failed_attempts': 0,
                'voice_chat_paused_at': None
            }
    
    def mark_authenticated(self, session_id: str, auth_method: str, 
                          expiry_seconds: int = 300) -> None:
        """Mark a session as authenticated"""
        state = self.get_state(session_id)
        state['authenticated'] = True
        state['auth_timestamp'] = time.time()
        state['auth_method'] = auth_method
        state['auth_expiry'] = time.time() + expiry_seconds
        state['failed_attempts'] = 0
        state['voice_chat_paused_at'] = None
        
        # Trigger success callbacks
        self._trigger_auth_success_callbacks(session_id)
    
    def is_authenticated(self, session_id: str) -> bool:
        """Check if a session is authenticated and not expired"""
        state = self.get_state(session_id)
        
        if not state['authenticated']:
            return False
        
        # Check for expiry
        if state['auth_expiry'] and time.time() > state['auth_expiry']:
            state['authenticated'] = False
            state['auth_timestamp'] = None
            state['auth_method'] = None
            state['auth_expiry'] = None
            return False
            
        return True
    
    def set_pending_intent(self, session_id: str, intent_type: str) -> None:
        """Store a pending intent to be processed after successful auth"""
        state = self.get_state(session_id)
        state['pending_intent'] = intent_type
    
    def get_pending_intent(self, session_id: str) -> Optional[str]:
        """Get and clear any pending intent"""
        state = self.get_state(session_id)
        pending = state.get('pending_intent')
        state['pending_intent'] = None
        return pending
    
    def record_failed_attempt(self, session_id: str) -> int:
        """Record a failed authentication attempt and return total count"""
        state = self.get_state(session_id)
        state['failed_attempts'] += 1
        
        # Trigger failure callbacks if too many attempts
        if state['failed_attempts'] >= 3:
            self._trigger_auth_failure_callbacks(session_id)
            
        return state['failed_attempts']
    
    def pause_voice_chat(self, session_id: str) -> None:
        """Mark voice chat as paused for authentication"""
        state = self.get_state(session_id)
        state['voice_chat_paused_at'] = time.time()
    
    def get_voice_chat_pause_time(self, session_id: str) -> Optional[float]:
        """Get the timestamp when voice chat was paused for this session"""
        state = self.get_state(session_id)
        return state.get('voice_chat_paused_at')
    
    def store_challenge(self, challenge: PendingAuthRequest) -> None:
        """Store a pending auth challenge"""
        self.pending_challenges[challenge.challenge_id] = challenge
    
    def get_challenge(self, challenge_id: str) -> Optional[PendingAuthRequest]:
        """Get a pending auth challenge"""
        return self.pending_challenges.get(challenge_id)
    
    def register_auth_success_callback(self, session_id: str, callback) -> None:
        """Register a callback for successful authentication"""
        if session_id not in self.auth_success_callbacks:
            self.auth_success_callbacks[session_id] = []
        self.auth_success_callbacks[session_id].append(callback)
    
    def register_auth_failure_callback(self, session_id: str, callback) -> None:
        """Register a callback for failed authentication"""
        if session_id not in self.auth_failure_callbacks:
            self.auth_failure_callbacks[session_id] = []
        self.auth_failure_callbacks[session_id].append(callback)
    
    def _trigger_auth_success_callbacks(self, session_id: str) -> None:
        """Trigger all registered success callbacks for a session"""
        if session_id in self.auth_success_callbacks:
            for callback in self.auth_success_callbacks[session_id]:
                asyncio.create_task(callback(session_id))
    
    def _trigger_auth_failure_callbacks(self, session_id: str) -> None:
        """Trigger all registered failure callbacks for a session"""
        if session_id in self.auth_failure_callbacks:
            for callback in self.auth_failure_callbacks[session_id]:
                asyncio.create_task(callback(session_id))


class EdgeAuthenticator:
    """
    Handles authentication via Flutter app's on-device face recognition
    """
    
    def __init__(self, auth_state: AuthenticationState, connection_manager: ConnectionManager):
        self.auth_state = auth_state
        self.connection_manager = connection_manager
    
    async def process_auth_result(self, session_id: str, auth_result: AuthResult) -> Dict[str, Any]:
        """
        Process authentication result received from Flutter app's edge processing
        
        Args:
            session_id: The user session ID
            auth_result: Authentication result from edge processing
                
        Returns:
            Response dictionary
        """
        if auth_result.success:
            # Authentication succeeded
            self.auth_state.mark_authenticated(
                session_id, 
                auth_result.method,
                300  # 5 minute expiry
            )
            
            # Get pending intent if any
            pending_intent = self.auth_state.get_pending_intent(session_id)
            
            result = {
                "success": True,
                "message": "Authentication successful",
                "pending_intent": pending_intent,
                "continue_voice_chat": True
            }
            
            # Notify all connected WebSockets for this session
            await self.connection_manager.send_auth_result(session_id, result)
            
            return result
        else:
            # Authentication failed
            failed_attempts = self.auth_state.record_failed_attempt(session_id)
            error_msg = auth_result.error or "Authentication failed"
            
            if failed_attempts >= 3:
                result = {
                    "success": False,
                    "message": f"{error_msg}. Too many failed attempts.",
                    "continue_voice_chat": False
                }
            else:
                result = {
                    "success": False,
                    "message": error_msg,
                    "continue_voice_chat": True,
                    "retry": True
                }
            
            # Notify all connected WebSockets for this session
            await self.connection_manager.send_auth_result(session_id, result)
            
            return result
    
    def create_auth_challenge(self, session_id: str, intent_type: str) -> PendingAuthRequest:
        """
        Creates an authentication challenge to be sent to the Flutter app
        
        Args:
            session_id: The user session ID
            intent_type: The type of intent requiring authentication
            
        Returns:
            Challenge data to be sent to the Flutter app
        """
        # Store the pending intent
        self.auth_state.set_pending_intent(session_id, intent_type)
        
        # Pause voice chat session
        self.auth_state.pause_voice_chat(session_id)
        
        # Create a challenge
        challenge_id = f"ch_{uuid.uuid4().hex}"
        challenge = PendingAuthRequest(
            challenge_id=challenge_id,
            session_id=session_id,
            auth_methods=["face"],
            intent_type=intent_type,
            timestamp=time.time(),
            expires_at=time.time() + 120  # 2 minute expiry for challenge
        )
        
        # Store the challenge
        self.auth_state.store_challenge(challenge)
        
        return challenge
    
    async def request_authentication(self, session_id: str, intent_type: str) -> Dict[str, Any]:
        """
        Request authentication from Flutter app via WebSocket
        
        Args:
            session_id: The user session ID
            intent_type: The type of intent requiring authentication
            
        Returns:
            Response dictionary
        """
        # Check if already authenticated
        if self.auth_state.is_authenticated(session_id):
            return {
                "already_authenticated": True,
                "message": "Already authenticated",
                "continue_voice_chat": True
            }
        
        # Create the challenge
        challenge = self.create_auth_challenge(session_id, intent_type)
        
        # Send authentication request via WebSocket
        await self.connection_manager.send_auth_request(session_id, challenge)
        
        # Return challenge that the Flutter app will use for face auth
        return {
            "challenge": challenge.dict(),
            "message": "Please complete face authentication to continue",
            "pause_voice_chat": True
        }


# ----- FastAPI Application Setup -----

# Create application
app = FastAPI(title="banking_auth")

# Initialize state and managers
connection_manager = ConnectionManager()
auth_state = AuthenticationState()
edge_authenticator = EdgeAuthenticator(auth_state, connection_manager)

# Create router
auth_router = APIRouter(prefix="/api/auth", tags=["authentication"])


# ----- WebSocket Endpoints -----

@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """WebSocket endpoint for real-time communication with Flutter app"""
    await connection_manager.connect(websocket, session_id)
    try:
        # Send initial connection confirmation
        await websocket.send_text(json.dumps({
            "type": "connection_established",
            "session_id": session_id,
            "message": "WebSocket connection established"
        }))
        
        # Process incoming messages (like auth results)
        while True:
            data = await websocket.receive_text()
            try:
                message = json.loads(data)
                message_type = message.get("type")
                
                if message_type == "auth_result":
                    # Process authentication result
                    auth_result = AuthResult(**message.get("auth_result", {}))
                    challenge_id = message.get("challenge_id")
                    await edge_authenticator.process_auth_result(session_id, auth_result)
                    
                elif message_type == "heartbeat":
                    # Respond to keep-alive messages
                    await websocket.send_text(json.dumps({
                        "type": "heartbeat_ack",
                        "timestamp": time.time()
                    }))
            except Exception as e:
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "message": f"Error processing message: {str(e)}"
                }))
                
    except WebSocketDisconnect:
        connection_manager.disconnect(websocket, session_id)
        print(f"WebSocket client disconnected: {session_id}")
    except Exception as e:
        print(f"WebSocket error: {str(e)}")
        connection_manager.disconnect(websocket, session_id)


# ----- API Endpoints -----

@auth_router.post("/challenge")
async def create_challenge(request: AuthChallengeRequest):
    """Create authentication challenge for voice assistant"""
    session_id = request.session_id
    intent_type = request.intent_type
    
    # Use the edge authenticator to create and send challenge via WebSocket
    response = await edge_authenticator.request_authentication(
        session_id=session_id, 
        intent_type=intent_type
    )
    
    return response


@auth_router.post("/verify")
async def verify_authentication(request: AuthVerifyRequest):
    """Process authentication result from Flutter app via REST API"""
    session_id = request.session_id
    auth_result = request.auth_result
    
    # Process the auth result
    response = await edge_authenticator.process_auth_result(session_id, auth_result)
    
    return response


@auth_router.get("/status/{session_id}")
async def check_auth_status(session_id: str):
    """Check authentication status for a voice assistant session"""
    is_authenticated = auth_state.is_authenticated(session_id)
    state = auth_state.get_state(session_id)
    
    return {
        "authenticated": is_authenticated,
        "auth_method": state.get("auth_method"),
        "auth_expiry": state.get("auth_expiry"),
        "voice_chat_active": is_authenticated  # Only keep voice chat active if authenticated
    }


# ----- Intent Authentication Helper -----

# async def check_intent_auth(session_id: str, intent_type: str) -> Dict[str, Any]:
#     """
#     Check if an intent requires authentication and request it if needed
    
#     This function should be called from your voice assistant backend
#     when processing intents that might require authentication.
    
#     Args:
#         session_id: The user session ID
#         intent_type: The type of intent (e.g., "transfer_funds", "account_details")
        
#     Returns:
#         Dict with authentication status and next steps
#     """
#     # Define intents that require authentication
#     secure_intents = [
#         "transfer_funds", 
#         "account_details", 
#         "update_profile",
#         "payment_setup",
#         "view_statements",
#         "change_pin"
#     ]
    
#     # Check if this intent requires authentication
#     requires_auth = intent_type in secure_intents
    
#     if not requires_auth:
#         # No authentication needed
#         return {
#             "requires_auth": False,
#             "authenticated": True,
#             "continue_voice_chat": True
#         }
    
#     # Check if already authenticated
#     if auth_state.is_authenticated(session_id):
#         return {
#             "requires_auth": True,
#             "authenticated": True,
#             "continue_voice_chat": True
#         }
    
#     # Request authentication via WebSocket
#     auth_response = await edge_authenticator.request_authentication(
#         session_id=session_id,
#         intent_type=intent_type
#     )
    
#     return {
#         "requires_auth": True,
#         "authenticated": False,
#         "auth_requested": True,
#         "challenge": auth_response.get("challenge"),
#         "continue_voice_chat": False
#     }


# ----- Mount router and start the application -----

app.include_router(auth_router)

# # Example middleware for request logging (optional)
# @app.middleware("http")
# async def log_requests(request: Request, call_next):
#     start_time = time.time()
#     response = await call_next(request)
#     process_time = time.time() - start_time
#     print(f"Request {request.url.path} processed in {process_time:.4f} seconds")
#     return response


if __name__ == "__main__":
    uvicorn.run("authwithwebsocket:app", host="0.0.0.0", port=8000, reload=True)