# this will make a service request to the banking backend API.

import asyncio
import json
import requests  # For making HTTP requests to the ticket generation system
from fastapi import FastAPI
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from config import settings

app = FastAPI()

# External API for ticket generation (Replace with actual URL)
TICKET_API_URL = "https://1998-42-106-207-28.ngrok-free.app/query/process"

# Initialize LLM Model
# GROQ_API_KEY = "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"  # Replace with actual API Key
LLM_MODEL = ChatGroq(api_key=settings.GROQ_API_KEY, model="llama-3.1-8b-instant")

# Define banking-related services
BANKING_SERVICES = {
    "new_credit_card": ["apply for credit card", "request a new credit card"],
    "email_update": ["change email", "update email id", "modify email address"],
    "phone_update": ["change phone number", "update mobile", "modify contact number"],
    "address_update": ["change address", "update address", "modify residence details"],
    "account_closure": ["close my account", "shut down my bank account"],
    "debit_card_replacement": ["lost debit card", "replace my ATM card"],
    "loan_application": ["apply for loan", "new loan request", "home loan inquiry"],
    "transaction_dispute": ["report unauthorized transaction", "dispute a charge", "refund request"],
    "balance_inquiry": ["check balance", "account balance", "available funds"],
    "statement_request": ["get account statement", "download bank statement"],
    "general_banking_support": ["customer service", "help with banking app", "banking support"]
}

# Service Identification Agent
class BankingServiceAgent:
    def __init__(self, model):
        self.model = model
        self.service_prompt = ChatPromptTemplate.from_messages([
            ("system", """
            You are an AI assistant specializing in banking service requests. 
            Your task is to classify user queries into predefined banking service categories.
            Based on the user's request, identify the most relevant service.

            Available Banking Services:
            - New Credit Card: Apply for a new credit card.
            - Email Update: Change or update email address linked to bank account.
            - Phone Update: Modify or change registered phone number.
            - Address Update: Update residential or mailing address.
            - Account Closure: Request to close a bank account.
            - Debit Card Replacement: Request a new debit/ATM card.
            - Loan Application: Apply for personal, home, or car loans.
            - Transaction Dispute: Report unauthorized transactions or request refunds.
            - Balance Inquiry: Ask about available funds or account balance.
            - Statement Request: Request bank statements.
            - General Banking Support: Any other banking-related inquiries.

            Examples:
            - "I want to apply for a credit card." → new_credit_card
            - "I lost my debit card, need a replacement." → debit_card_replacement
            - "How do I change my registered mobile number?" → phone_update
            - "Please help me close my bank account." → account_closure
            - "There is an unauthorized charge on my account!" → transaction_dispute

            Respond with ONLY the service name in lowercase (e.g., 'new_credit_card', 'email_update'). 
            If unclear, return 'general_banking_support'.
            """),
            ("human", "{query}")
        ])
        self.service_chain = self.service_prompt | self.model

    def get_service(self, query: str) -> str:
        response = self.service_chain.invoke({"query": query})
        service = response.content.strip().lower()
        return service if service in BANKING_SERVICES else "general_banking_support"


# Function to send request to ticket system
def generate_ticket(username: str, query: str, service: str):
    """
    Sends user request details to an external ticketing system and retrieves the ticket number.
    """
    
    TICKET_API_URL = "https://1998-42-106-207-28.ngrok-free.app/query/process"
    payload = {
        "user_id": username,
        "query": query
    }
    try:
        response = requests.post(TICKET_API_URL, json=payload)
        response_data = response.json()
        print(f"Ticket System Response: {response_data}")
        return [response_data.get("query_id", "N/A") , service]
    except Exception as e:
        print(f"Error contacting ticket system: {e}")
        return "N/A"


# # API Route to Identify Service and Generate Ticket
# @app.post("/process-banking-request")
# async def process_banking_request(request: dict):
#     username = request.get("username", "unknown_user")
#     user_query = request.get("query", "")

#     # Identify the service request type
#     service_agent = BankingServiceAgent(LLM_MODEL)
#     identified_service = service_agent.get_service(user_query)

#     # Generate a ticket for the request
#     ticket_number = generate_ticket(username,identified_service)

#     return {
#         "ticket_number": ticket_number,
#         "service": identified_service
#     }



user_query = "I want to apply for a credit card"  # Example user query
username = "3e0c98bf-c9b9-4d9b-b244-5d3e4906a386" # Example username

    # Identify the service request type
service_agent = BankingServiceAgent(LLM_MODEL)
identified_service = service_agent.get_service(user_query)

    # Generate a ticket for the request
ticket_number = generate_ticket(username,user_query,identified_service)
print(f"Ticket Number: {ticket_number} | Service: {identified_service}")
