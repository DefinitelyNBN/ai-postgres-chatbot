from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
import uvicorn
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import logging
import asyncio
from datetime import datetime
import json

from database import DatabaseManager, QueryValidator, SecurityError
from utils import AIQueryGenerator, ChatHistoryManager, ResponseFormatter
from config import get_settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="AI PostgreSQL Chatbot",
    description="An intelligent chatbot for querying PostgreSQL databases using natural language",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global variables
db_manager = None
ai_generator = None
chat_history = None

# Pydantic models
class ChatMessage(BaseModel):
    message: str
    session_id: Optional[str] = "default"

class ChatResponse(BaseModel):
    response: str
    query: Optional[str] = None
    results: Optional[List[Dict]] = None
    error: Optional[str] = None
    timestamp: datetime
    session_id: str

class DatabaseInfo(BaseModel):
    tables: Dict[str, Any]
    relationships: List[Dict]
    connection_status: bool

class QueryRequest(BaseModel):
    query: str
    validate_only: bool = False

class QueryResponse(BaseModel):
    results: Optional[List[Dict]] = None
    error: Optional[str] = None
    is_safe: bool
    execution_time: Optional[float] = None

# Dependency injection
async def get_db_manager():
    global db_manager
    if db_manager is None:
        settings = get_settings()
        db_manager = DatabaseManager(
            host=settings.db_host,
            port=settings.db_port,
            database=settings.db_name,
            username=settings.db_user,
            password=settings.db_password
        )
    return db_manager

async def get_ai_generator():
    global ai_generator
    if ai_generator is None:
        settings = get_settings()
        ai_generator = AIQueryGenerator(
            api_key=settings.openai_api_key,
            model=settings.openai_model
        )
    return ai_generator

async def get_chat_history():
    global chat_history
    if chat_history is None:
        chat_history = ChatHistoryManager()
    return chat_history

# Startup event
@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    try:
        logger.info("Starting AI PostgreSQL Chatbot...")
        
        # Initialize database manager
        db = await get_db_manager()
        if not db.test_connection():
            raise Exception("Failed to connect to database")
        
        # Initialize AI generator
        ai = await get_ai_generator()
        await ai.initialize()
        
        # Initialize chat history
        await get_chat_history()
        
        logger.info("All services initialized successfully")
        
    except Exception as e:
        logger.error(f"Startup failed: {e}")
        raise

# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    if db_manager:
        db_manager.close_all_connections()
    logger.info("AI PostgreSQL Chatbot shutdown complete")

# Routes
@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve the main chat interface"""
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>AI PostgreSQL Chatbot</title>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body { font-family: Arial, sans-serif; margin: 0; padding: 20px; background-color: #f5f5f5; }
            .container { max-width: 800px; margin: 0 auto; background: white; border-radius: 10px; padding: 20px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
            .header { text-align: center; color: #2c3e50; margin-bottom: 30px; }
            .chat-container { height: 400px; border: 1px solid #ddd; border-radius: 5px; padding: 20px; overflow-y: auto; background: #f9f9f9; margin-bottom: 20px; }
            .message { margin-bottom: 15px; padding: 10px; border-radius: 5px; }
            .user-message { background: #3498db; color: white; text-align: right; }
            .bot-message { background: #ecf0f1; color: #2c3e50; }
            .input-container { display: flex; gap: 10px; }
            .input-field { flex: 1; padding: 10px; border: 1px solid #ddd; border-radius: 5px; }
            .send-button { padding: 10px 20px; background: #3498db; color: white; border: none; border-radius: 5px; cursor: pointer; }
            .send-button:hover { background: #2980b9; }
            .query-display { background: #f8f9fa; border: 1px solid #e9ecef; border-radius: 3px; padding: 10px; margin: 5px 0; font-family: monospace; font-size: 12px; }
            .results-table { width: 100%; border-collapse: collapse; margin: 10px 0; }
            .results-table th, .results-table td { border: 1px solid #ddd; padding: 8px; text-align: left; }
            .results-table th { background-color: #f2f2f2; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🤖 AI PostgreSQL Chatbot</h1>
                <p>Ask questions about your database in natural language!</p>
            </div>
            
            <div class="chat-container" id="chatContainer">
                <div class="message bot-message">
                    Hello! I'm your AI database assistant. You can ask me questions about your PostgreSQL database in natural language, and I'll help you find the information you need.
                </div>
            </div>
            
            <div class="input-container">
                <input type="text" id="messageInput" class="input-field" placeholder="Ask me about your database..." onkeypress="handleKeyPress(event)">
                <button onclick="sendMessage()" class="send-button">Send</button>
            </div>
        </div>

        <script>
            async function sendMessage() {
                const input = document.getElementById('messageInput');
                const message = input.value.trim();
                if (!message) return;

                const chatContainer = document.getElementById('chatContainer');
                
                // Add user message
                addMessage(message, 'user-message');
                input.value = '';

                try {
                    const response = await fetch('/chat', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify({
                            message: message,
                            session_id: 'web-session'
                        })
                    });

                    const data = await response.json();
                    
                    let botResponse = data.response;
                    
                    if (data.query) {
                        botResponse += '<div class="query-display"><strong>Generated Query:</strong><br>' + data.query + '</div>';
                    }
                    
                    if (data.results && data.results.length > 0) {
                        botResponse += formatResults(data.results);
                    }
                    
                    addMessage(botResponse, 'bot-message');
                    
                } catch (error) {
                    addMessage('Sorry, I encountered an error: ' + error.message, 'bot-message');
                }
            }

            function addMessage(message, className) {
                const chatContainer = document.getElementById('chatContainer');
                const messageDiv = document.createElement('div');
                messageDiv.className = 'message ' + className;
                messageDiv.innerHTML = message;
                chatContainer.appendChild(messageDiv);
                chatContainer.scrollTop = chatContainer.scrollHeight;
            }

            function formatResults(results) {
                if (!results || results.length === 0) return '';
                
                const keys = Object.keys(results[0]);
                let table = '<table class="results-table"><thead><tr>';
                
                keys.forEach(key => {
                    table += '<th>' + key + '</th>';
                });
                table += '</tr></thead><tbody>';
                
                results.slice(0, 10).forEach(row => {
                    table += '<tr>';
                    keys.forEach(key => {
                        table += '<td>' + (row[key] || '') + '</td>';
                    });
                    table += '</tr>';
                });
                
                table += '</tbody></table>';
                
                if (results.length > 10) {
                    table += '<p><em>Showing first 10 results out of ' + results.length + ' total results.</em></p>';
                }
                
                return table;
            }

            function handleKeyPress(event) {
                if (event.key === 'Enter') {
                    sendMessage();
                }
            }

            // Auto-focus on input
            document.getElementById('messageInput').focus();
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

@app.post("/chat", response_model=ChatResponse)
async def chat(
    message: ChatMessage,
    db: DatabaseManager = Depends(get_db_manager),
    ai: AIQueryGenerator = Depends(get_ai_generator),
    history: ChatHistoryManager = Depends(get_chat_history)
):
    """Main chat endpoint for natural language queries"""
    try:
        # Get database metadata for context
        metadata = db.get_database_metadata()
        
        # Generate SQL query from natural language
        query_result = await ai.generate_query(
            user_message=message.message,
            database_metadata=metadata,
            chat_history=history.get_history(message.session_id)
        )
        
        response_data = {
            "response": query_result["explanation"],
            "query": query_result.get("query"),
            "results": None,
            "error": None,
            "timestamp": datetime.now(),
            "session_id": message.session_id
        }
        
        # Execute query if one was generated
        if query_result.get("query"):
            # Validate query for security
            is_safe, reason = QueryValidator.is_safe_query(query_result["query"])
            
            if not is_safe:
                response_data["error"] = f"Query validation failed: {reason}"
            else:
                try:
                    results = db.execute_select(query_result["query"])
                    response_data["results"] = results
                    
                    # Format results for better presentation
                    if results:
                        formatter = ResponseFormatter()
                        response_data["response"] = formatter.format_query_response(
                            query_result["explanation"], 
                            results
                        )
else:
                        response_data["response"] += "\n\nNo results found."
                        
except Exception as e:
                    response_data["error"] = f"Query execution failed: {str(e)}"
        
        # Add to chat history
        history.add_message(
            session_id=message.session_id,
            user_message=message.message,
            bot_response=response_data["response"],
            query=response_data.get("query"),
            results=response_data.get("results")
        )
        
        return ChatResponse(**response_data)
        
except Exception as e:
        logger.error(f"Chat error: {e}")
        return ChatResponse(
            response=f"I encountered an error while processing your request: {str(e)}",
            error=str(e),
            timestamp=datetime.now(),
            session_id=message.session_id
        )

@app.get("/database/info", response_model=DatabaseInfo)
async def get_database_info(db: DatabaseManager = Depends(get_db_manager)):
    """Get database schema information"""
    try:
        metadata = db.get_database_metadata()
        connection_status = db.test_connection()
        
        return DatabaseInfo(
            tables=metadata["tables"],
            relationships=metadata["relationships"],
            connection_status=connection_status
        )
    except Exception as e:
        logger.error(f"Database info error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/query/execute", response_model=QueryResponse)
async def execute_direct_query(
    request: QueryRequest,
    db: DatabaseManager = Depends(get_db_manager)
):
    """Execute a direct SQL query with validation"""
    try:
        # Validate query
        is_safe, reason = QueryValidator.is_safe_query(request.query)
        
        if not is_safe:
            return QueryResponse(
                error=f"Query validation failed: {reason}",
                is_safe=False
            )
        
        if request.validate_only:
            return QueryResponse(is_safe=True)
        
        # Execute query
        import time
        start_time = time.time()
        
        results = db.execute_select(request.query)
        execution_time = time.time() - start_time
        
        return QueryResponse(
            results=results,
            is_safe=True,
            execution_time=execution_time
        )
        
except Exception as e:
        logger.error(f"Query execution error: {e}")
        return QueryResponse(
            error=str(e),
            is_safe=True
        )

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        db = await get_db_manager()
        db_status = db.test_connection()
        
        return {
            "status": "healthy" if db_status else "unhealthy",
            "database_connected": db_status,
            "timestamp": datetime.now()
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now()
        }

@app.get("/chat/history/{session_id}")
async def get_chat_history_endpoint(
    session_id: str,
    history: ChatHistoryManager = Depends(get_chat_history)
):
    """Get chat history for a session"""
    return {"history": history.get_history(session_id)}

@app.delete("/chat/history/{session_id}")
async def clear_chat_history(
    session_id: str,
    history: ChatHistoryManager = Depends(get_chat_history)
):
    """Clear chat history for a session"""
    history.clear_history(session_id)
    return {"message": "Chat history cleared"}

if __name__ == "__main__":
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
