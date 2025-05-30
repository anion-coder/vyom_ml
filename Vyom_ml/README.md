# Vyom: AI-Powered Voice Banking Assistant

Vyom is an advanced AI-powered voice assistant designed to revolutionize the banking experience through natural language interaction. This intelligent system enables hands-free navigation and banking operations while providing personalized customer support in multiple Indian languages.

## 🌟 Key Features

### 🎯 Voice Navigation
- Seamless page navigation through voice commands
- Intuitive banking operations (e.g., "Transfer money through NEFT")
- Natural language understanding for complex banking queries

### 💰 Banking Operations
- Real-time balance checking with secure authentication
- Transaction history access
- Fund transfer capabilities
- Account management

### 🤖 Intelligent Customer Support
- Instant query resolution through AI
- Smart appointment scheduling with banking officials
- Virtual and in-person meeting coordination
- Priority-based service routing

### 📊 Personalized Banking
- Customized scheme recommendations based on profile
- Transaction tracking and analysis
- Personalized financial insights
- Profile-based service optimization

### 🌐 Multilingual Support
- Support for multiple Indian languages
- Emotion-aware responses
- Cultural context understanding
- Natural conversation flow

## 🛠️ Technical Architecture

The system is built using a modular architecture with the following components:

- **Voice Assistant Module** (`voice_assistant.py`): Core voice interaction system
- **Intent Recognition** (`llm_with_intent.py`): Natural language understanding
- **Service Management** (`service_retrieval_agent.py`): Query resolution and service routing
- **Information Retrieval** (`info_retrieval_agent.py`): Secure data access
- **Priority Prediction** (`priority_prediction.py`): Smart service prioritization
- **Authentication System** (`auth.py`, `authwithwebsocket.py`): Secure user verification
- **Text-to-Speech** (`tts_with_llm.py`): Natural voice responses

## 🚀 Getting Started

### Prerequisites
- Python 3.8+
- PostgreSQL database
- Required system audio libraries

### Installation

1. Clone the repository:
```bash
cd vyom_ml
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your configuration
```

Required environment variables:
```env
# Database Configuration
POSTGRES_USER="Your User_name"
POSTGRES_DB=""
POSTGRES_HOST=""
POSTGRES_PORT=6543
POSTGRES_DB=""

# API Keys
SARVAM_API_KEY="your_sarvam_api_key"
GROQ_API_KEY="your_groq_api_key"
```

4. Initialize the database:
```bash
python init_db.py
```

### Running the Application

```bash
uvicorn main:app --reload
```

## 🔒 Security Features

- Secure authentication system
- Encrypted data transmission
- Privacy-focused information handling
- Role-based access control

## 🤝 Contributing

We welcome contributions! Please read our contributing guidelines before submitting pull requests.


## 🙏 Acknowledgments

- Built as part of the Vyom AI-powered service management initiative
- Special thanks to all contributors and the banking community
