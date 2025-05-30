from dotenv import load_dotenv
import os
import psycopg2 
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from config import settings

load_dotenv()  # Load environment variables



def get_query_from_llm(question, schema_description , username):
    """
    Use LLM to convert natural language to PostgreSQL query
    """
    
    
    prompt = ChatPromptTemplate.from_messages([("system",
    """                                           
    You are an expert in converting English questions to PostgreSQL queries.
    
    {schema_description}
    
    username: {username}
    
    
    Given the user question, generate ONLY a valid PostgreSQL query.
    Do not include any explanations, markdown formatting, or backticks.
    Return just the raw query that can be executed directly.
    """
    ),
    ("user","{question}")
    ]
    )
    
    llm = ChatGroq(
    api_key=settings.GROQ_API_KEY,
    model="llama-3.1-8b-instant"
)
    chain = prompt | llm
    
    result = chain.invoke({
    "question": question,
    "schema_description": schema_description,
    "username": username
})
    print(result.content.strip())
    return result.content.strip()

# def query_postgresql(user_question, db_params, schema_description):

def query_postgresql(user_question,db_params,schema_description):
    """
    Main function to retrieve information from PostgreSQL based on natural language questions
    
    Parameters:
    - user_question: Natural language question about the data
    - db_params: Dictionary containing database connection parameters
                 (dbname, user, password, host, port)
    - schema_description: String describing your database schema
    
    Returns:
    - Dictionary with the query, results, and status information
    """
    try:
        # Get PostgreSQL query from LLM
        query = get_query_from_llm(user_question, schema_description,"user121")
        
        db_name = os.getenv("POSTGRES_DB")
        user = os.getenv("POSTGRES_USER")
        password = os.getenv("POSTGRES_PASSWORD")
        host = os.getenv("POSTGRES_HOST")
        port = os.getenv("POSTGRES_PORT")
        
        
        
        # Connect to PostgreSQL
        conn = psycopg2.connect("postgresql://postgres:Idea%402k25@db.elmmlkdcziylxwjxjkma.supabase.co:5432/postgres")
        if conn is None:
            return {
                "query": query,
                "column_names": [],
                "results": [],
                "success": False,
                "error": "Could not connect to the database"
            }
        
        # Create a cursor
        cursor = conn.cursor()
        
        # Execute the query
        cursor.execute(query)
        
        # Get column names
        column_names = [desc[0] for desc in cursor.description] if cursor.description else []
        
        # Fetch results
        results = cursor.fetchall()
        
        # Close cursor and connection
        cursor.close()
        conn.close()
        
        # column_names = ["user_id", "username", "email", "phone_no", "device_id", "push_enabled", "bank_balance", "cred_score", "dob", "branch_id", "join_date", "additional_info"]
        # results = [
        #     (1, "john_doe")
        # ]  # Sample results  
        
        return {
            "query": query,
            "column_names": column_names,
            "results": results,
            "success": True,
            "error": None
        }
    
    except Exception as e:
        return {
            "query": query if 'query' in locals() else None,
            "column_names": [],
            "results": [],
            "success": False,
            "error": str(e)
        }

# Example usage
if __name__ == "__main__":
    # Database connection parameters
    db_params = {
        "dbname": os.getenv("DB_NAME"),
        "user": os.getenv("DB_USER"),
        "password": os.getenv("DB_PASSWORD"),
        "host": os.getenv("DB_HOST"),
        "port": os.getenv("DB_PORT")
    }
    
    # Your schema description - you can replace this with your actual schema
    schema_description = """
The database has a table named 'customer' with the following columns:
	•	cust_id (UUID, primary key): Unique identifier for each customer
	•	custname (text): The customer's name
	•	email (text): The customer's email address
	•	phone_no (text): The customer's phone number
	•	device_id (text): Identifier for the customer's device
	•	push_enabled (boolean): Whether push notifications are enabled for the customer
	•	bank_balance (numeric): The customer's bank balance
	•	cred_score (integer): The customer's credit score
	•	dob (date): The customer's date of birth
	•	branch_id (integer): The branch ID the customer is associated with
	•	join_date (timestamptz): The date and time when the customer joined
	•	verified_docs (jsonb): Verified documents of the customer stored as JSON
	•	addition_info (jsonb): Additional information about the customer stored as JSON
	•	locations (jsonb): Location details of the customer stored as JSON
	•	profile_pic (jsonb): Profile picture data stored as JSON
"""
    
    # Test with a sample question
    question = input("Enter a natural language question: ")
    result = query_postgresql(question, db_params, schema_description)
    # result = query_postgresql(question,schema_description)
    
    if result["success"]:
        print("Query:", result["query"])
        print("Columns:", result["column_names"])
        print("Results:")
        for row in result["results"]:
            print(row)
    else:
        print("Error:", result["error"])