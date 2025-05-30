import os
# import sqlite3
from typing import Dict, List, Optional, Tuple, Any
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import AIMessage, HumanMessage, BaseMessage, SystemMessage
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_core.chat_history import BaseChatMessageHistory
from config import settings

# Import functions from other files 
# from auth import perform_face_authentication
# from db_query_handler import handle_db_query
# from service_handler import handle_service_request
# from page_routing_handler import handle_page_routing

from info_retrieval_agent import get_query_from_llm
from service_retrieval_agent import BankingServiceAgent
from service_retrieval_agent import generate_ticket
from routing_agent import PageRoutingAgent

# Chat history management
class InMemoryHistory(BaseChatMessageHistory):
    def __init__(self):
        self.messages: List[BaseMessage] = []
    
    def add_message(self, message: BaseMessage) -> None:
        self.messages.append(message)
    
    def clear(self) -> None:
        self.messages = []

# Message store that returns proper chat history objects
class MessageStore:
    def __init__(self):
        self.store: Dict[str, InMemoryHistory] = {}
    
    def get_session_history(self, session_id: str) -> BaseChatMessageHistory:
        if session_id not in self.store:
            self.store[session_id] = InMemoryHistory()
        return self.store[session_id]

# Authentication state management
class AuthenticationState:
    def __init__(self):
        self.state: Dict[str, Dict] = {}
    
    def get_state(self, session_id: str) -> Dict:
        if session_id not in self.state:
            self.state[session_id] = {
                'authenticated': False,
                'pending_intent': None,
                'pending_query': None,
                'system_response': None  # Store system responses to pass to LLM
            }
        return self.state[session_id]
    
    def reset_state(self, session_id: str) -> None:
        if session_id in self.state:
            self.state[session_id] = {
                'authenticated': False,
                'pending_intent': None,
                'pending_query': None,
                'system_response': None
            }

# Intent recognition using Groq LLM
class IntentRecognizer:
    def __init__(self, model):
        self.model = model
        
        # Improved prompt template for intent detection
        self.intent_prompt = ChatPromptTemplate.from_messages([
            ("system", """
            You are an intent classifier for a banking assistant.
            Analyze the user query and classify it into EXACTLY ONE of these categories:
            
            1. dbquery: Any request for user data or information from the database.
               Examples: account balance, transaction history, account details, credit score,
               personal information, statement requests, interest rates on accounts.
            
            2. service: Requests for banking services or actions to be performed.
               Examples: fund transfers, bill payments, card activation/deactivation, loan requests,
               address changes, mobile number updates, setting up auto-pay, reporting issues.
            
            3. page_routing: Navigation requests to different sections of the banking app.
               Examples: "take me to the transfers page", "show me where I can update my profile",
               "how do I get to the beneficiary management section", "open the investments tab".
            
            4. general: General questions about banking, products, or conversation that doesn't fit
               the above categories. Examples: greetings, general banking information, product inquiries
               not requiring access to user data, thanks, goodbyes.
            
            Respond with ONLY the category name in lowercase, nothing else.
            """),
            ("human", "{question}")
        ])
        
        self.intent_chain = self.intent_prompt | self.model
    
    def detect_intent(self, query: str) -> str:
        """
        Use the Groq LLama model to classify the user query into one of the predefined intents.
        Returns the intent as a string.
        """
        response = self.intent_chain.invoke({"question": query})
        # Extract the intent from the response and normalize
        intent = response.content.strip().lower()
        
        # Validate that the response is one of our expected intents
        valid_intents = ["dbquery", "service", "page_routing", "general"]
        if intent not in valid_intents:
            # Default to general if LLM returns unexpected response
            return "general"
        
        return intent

# Authentication requirement checker
class AuthRequirementChecker:
    def __init__(self):
        # Dictionary defining which intents and specific queries require authentication
        self.auth_requirements = {
            "dbquery": {
                "default": True,  # Most DB queries require auth
                "exceptions": ["bank_info", "branch_locations", "bank_hours"]  # These don't require auth
            },
            "service": {
                "default": True,  # Most services require auth
                "exceptions": ["faq", "contact_info", "new_account_info"]  # These don't require auth
            },
            "page_routing": {
                "default": False,  # Most page routing doesn't require auth
                "requires_auth": ["account_details", "transaction_history", "settings"]  # These require auth
            },
            "general": {
                "default": False  # General queries don't require auth
            }
        }
    
    def requires_authentication(self, intent: str, query_details: Dict[str, Any] = None) -> bool:
        """
        Determine if a given intent and query details require authentication.
        """
        if intent not in self.auth_requirements:
            return False
        
        intent_rules = self.auth_requirements[intent]
        default_requirement = intent_rules.get("default", False)
        
        # If we have query details and a query_type, check for specific rules
        if query_details and "query_type" in query_details:
            query_type = query_details["query_type"]
            
            # Check if it's an exception to the default rule
            if "exceptions" in intent_rules and query_type in intent_rules["exceptions"]:
                return not default_requirement
            
            # Check if it specifically requires auth despite the default
            if "requires_auth" in intent_rules and query_type in intent_rules["requires_auth"]:
                return True
        
        return default_requirement

# db query integrate karunga 
def handle_db_query(session_id: str, user_input: str, query_details: Dict = None) -> str:
    """
    Simulate database query handler that returns mock data.
    In a real implementation, this function would be imported from db_query_handler.py
    """
    result = get_query_from_llm(user_input, "user121")
    return result
                                                           
            

def handle_service_request(session_id: str, user_input: str) -> str:
    """
    Simulate service request handler.
    In a real implementation, this function would be imported from service_handler.py
    """
    # Initialize LLM Model
    LLM_MODEL = ChatGroq(api_key=settings.GROQ_API_KEY, model="llama-3.1-8b-instant")
    service_agent = BankingServiceAgent(LLM_MODEL)
    identified_service = service_agent.get_service(user_input)
    ticket_number = generate_ticket("user123",user_input,identified_service)
    
    return [identified_service,ticket_number]
    
    

def handle_page_routing(session_id: str, user_input: str) -> str:
    """
    Simulate page routing handler.
    In a real implementation, this function would be imported from page_routing_handler.py
    """
    target_page = ""
    if "transfer" in user_input.lower():
        target_page = "funds transfer"
    elif "settings" in user_input.lower():
        target_page = "account settings"
    elif "profile" in user_input.lower():
        target_page = "profile management"
    else:
        target_page = "home"
    
    return {
        "status": "success",
        "target_page": target_page,
        "message": f"Navigating to the {target_page} page."
    }

def perform_face_authentication(session_id: str) -> bool:
    """
    Simulate face authentication.
    In a real implementation, this function would be imported from auth_module.py
    """
    # taran model se face auth karunga
    return False

# Main application class
class BankingAssistant:
    def __init__(self, groq_api_key):
        # Create the LLM model using Groq
        self.model = ChatGroq(
            api_key=groq_api_key,
            model="llama-3.1-8b-instant"
        )
        
        # Initialize components
        self.message_store = MessageStore()
        self.auth_state = AuthenticationState()
        self.intent_recognizer = IntentRecognizer(self.model)
        self.auth_checker = AuthRequirementChecker()
        
        # Create an improved prompt template for general conversations
        system_message = """
        You are a friendly and professional banking assistant named BankBuddy. Your job is to help customers with their banking needs.
        **Keep your reply short and consise and always maintain a friendly tone.**
        When responding to customers:
        1. Be warm, professional, and conversational - imagine you're a helpful bank teller
        2. Address the customer's specific question directly and concisely
        3. Use the information provided by the system - never invent account details or transaction information
        4. Provide clear next steps when appropriate
        5. Maintain appropriate privacy and security practices - never ask for full account numbers, passwords, or PINs
        
        Important: When system provides data like transaction details or account information, present it in a natural, 
        conversational way. Incorporate the data seamlessly into your response.
        
        Remember: You're the friendly face of the bank! Make the customer feel valued while providing accurate information.
        """
        
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", system_message),
            MessagesPlaceholder(variable_name="history"),
            ("system", "{system_info}"),
            ("human", "{question}")
        ])
        
        # Create the chain with history for general conversations
        self.chain_with_history = RunnableWithMessageHistory(
            self.prompt | self.model,
            self.message_store.get_session_history,
            input_messages_key="question",
            history_messages_key="history"
        )
    
    def handle_general_query(self, session_id: str, user_input: str, system_info: str = "") -> str:
        """
        Use the Groq LLama model to handle general banking queries.
        """
        response = self.chain_with_history.invoke(
            {"question": user_input, "system_info": system_info},
            config={"configurable": {"session_id": session_id}}
        )
        return response.content
    
    def process_message(self, session_id: str, user_input: str) -> str:
        """
        Main function to process user messages and route them to appropriate handlers.
        """
        # Get authentication state
        state = self.auth_state.get_state(session_id)
        
        # Add user message to history
        self.message_store.get_session_history(session_id).add_message(HumanMessage(content=user_input))
        
        # If we have a pending intent and are now returning from authentication
        if state.get('pending_intent') and state.get('authenticated'):
            intent = state['pending_intent']
            query_details = state.get('pending_query')
            
            # Clear pending state
            state['pending_intent'] = None
            state['pending_query'] = None
            
            # Process the original request now that authentication is complete
            system_response = self.process_intent(session_id, intent, user_input, query_details)
            
            # Store system response data for LLM to use
            state['system_response'] = system_response
            
            # Use LLM to generate natural response using the system data
            return self.handle_general_query(
                session_id, 
                user_input, 
                f"System response: {system_response}"
            )
        
        # Step 1: Use LLM to recognize intent
        intent = self.intent_recognizer.detect_intent(user_input)
        
        # Step 2: Get additional query details if needed
        query_details = {"query": user_input}  # Simplified; your actual implementation may vary
        
        # Step 3: Check if this intent/query requires authentication
        requires_auth = self.auth_checker.requires_authentication(intent, query_details)
        
        # Step 4: Handle authentication if needed
        if requires_auth and not state['authenticated']:
            # Store the intent and query for after authentication
            state['pending_intent'] = intent
            state['pending_query'] = query_details
            
            # Call the face authentication function
            auth_successful = perform_face_authentication(session_id)
            
            if auth_successful:
                state['authenticated'] = True
                
                # Process the original intent now that authentication is successful
                system_response = self.process_intent(session_id, intent, user_input, query_details)
                
                # Store system response data for LLM to use
                state['system_response'] = system_response
                
                # Use LLM to generate natural response that includes authentication success
                llm_prompt = f"The user has been successfully authenticated. System response: {system_response}"
                response = self.handle_general_query(session_id, user_input, llm_prompt)
                
                # Add response to history
                self.message_store.get_session_history(session_id).add_message(AIMessage(content=response))
                
                return response
            else:
                # Authentication failed
                state['pending_intent'] = None
                state['pending_query'] = None
                
                # Use LLM to generate a natural response for auth failure
                response = self.handle_general_query(
                    session_id, 
                    user_input, 
                    "Authentication has failed. Please advise the user to try again or contact customer support."
                )
                
                # Add response to history
                self.message_store.get_session_history(session_id).add_message(AIMessage(content=response))
                
                return response
        
        # Step 5: Process the intent if no authentication needed or already authenticated
        system_response = self.process_intent(session_id, intent, user_input, query_details)
        
        # Store system response data for LLM to use
        state['system_response'] = system_response
        
        # Use LLM to generate natural response using the system data
        response = self.handle_general_query(
            session_id, 
            user_input, 
            f"System response: {system_response}"
        )
        
        # Add response to history
        self.message_store.get_session_history(session_id).add_message(AIMessage(content=response))
        
        return response
    
    def process_intent(self, session_id: str, intent: str, user_input: str, query_details: Dict[str, Any] = None) -> Dict:
        """
        Process the recognized intent and route to the appropriate handler.
        Returns structured data that the LLM can use to generate a natural response.
        """
        if intent == "dbquery":
           
            return handle_db_query(session_id, user_input, query_details)
        
        elif intent == "service":
           
            return handle_service_request(session_id, user_input)
        
        elif intent == "page_routing":
            
            return handle_page_routing(session_id, user_input)
        
        else:  
            # For general queries, just pass basic info for the LLM to use
            return {
                "status": "general_query",
                "message": "This is a general banking query that doesn't require system data."
            }

# chat func which can be imported 
def create_chat_session(groq_api_key=None, session_id=None):
    """
    Factory function to create a chat session that can be used by other modules.
    Returns a function that accepts user input and returns assistant responses.
    
    Args:
        groq_api_key (str, optional): Your Groq API key. If None, it will use the API key from config.
        session_id (str, optional): A unique identifier for this session. 
                                    If None, a random ID will be generated.
    
    Returns:
        tuple: (chat_function, session_id) where chat_function is a callable 
               that processes user messages and returns assistant responses
    """
    if groq_api_key is None:
        groq_api_key = settings.GROQ_API_KEY
    
    # Create a unique session ID if none provided
    if session_id is None:
        import uuid
        session_id = str(uuid.uuid4())
    
    # Initialize the banking assistant
    assistant = BankingAssistant(groq_api_key)
    
  
    def chat(user_input):
        return assistant.process_message(session_id, user_input)
    
    return chat, session_id

# This function runs a command-line chat session if this file is run directly
def run_cli_chat():
    print("Starting Banking Assistant CLI Chat...")
    
    # Ask for API key if not set in environment
    groq_api_key = os.environ.get("GROQ_API_KEY")
    if not groq_api_key:
        groq_api_key = input("Please enter your Groq API key: ")
        if not groq_api_key:
            print("Error: Groq API key is required.")
            return
    
    # Create a session ID
    session_id = "user123" 
    # username will be given by the flutter app / backend
    
    # Create the chat function
    chat_func, _ = create_chat_session(groq_api_key, session_id)
    
    print("\nBanking Assistant: Hello! I'm your banking assistant. How can I help you today?")
    
    try:
        while True:
            user_input = input("You: ")
            if user_input.lower() in ["exit", "quit", "bye"]:
                print("Banking Assistant: Thank you for using our banking services. Have a great day!")
                break
                
            response = chat_func(user_input)
            print(f"Banking Assistant: {response}")
    
    except KeyboardInterrupt:
        print("\nBanking Assistant: Session ended. Thank you for using our banking services.")
    except Exception as e:
        print(f"\nError: {e}")

# to check and chat command prompt (because tts costs money😭)
if __name__ == "__main__":
    run_cli_chat()