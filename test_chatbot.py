import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from fastapi.testclient import TestClient
import json

from app import app
from database import DatabaseManager, QueryValidator
from utils import AIQueryGenerator, ChatHistoryManager, ResponseFormatter
from config import TestingSettings

# Test client
client = TestClient(app)

class TestDatabaseManager:
    """Test database manager functionality"""
    
    @pytest.fixture
    def db_manager(self):
        """Create a test database manager"""
        return DatabaseManager(
            host="localhost",
            port=5432,
            database="test_db",
            username="test_user",
            password="test_pass"
        )
    
    def test_connection_initialization(self, db_manager):
        """Test database connection initialization"""
        assert db_manager.host == "localhost"
        assert db_manager.port == 5432
        assert db_manager.database == "test_db"
        assert db_manager.username == "test_user"
    
    @patch('database.psycopg2.pool.ThreadedConnectionPool')
    def test_connection_pool_creation(self, mock_pool, db_manager):
        """Test connection pool creation"""
        mock_pool.return_value = Mock()
        db_manager._initialize_connection_pool()
        mock_pool.assert_called_once()
    
    def test_query_validator_safe_query(self):
        """Test query validator with safe queries"""
        safe_query = "SELECT * FROM users WHERE id = 1"
        is_safe, reason = QueryValidator.is_safe_query(safe_query)
        assert is_safe
        assert reason == "Query is safe"
    
    def test_query_validator_dangerous_query(self):
        """Test query validator with dangerous queries"""
        dangerous_query = "DROP TABLE users"
        is_safe, reason = QueryValidator.is_safe_query(dangerous_query)
        assert not is_safe
        assert "Dangerous keyword 'DROP' found" in reason
    
    def test_query_validator_non_select(self):
        """Test query validator with non-SELECT queries"""
        update_query = "UPDATE users SET name = 'test'"
        is_safe, reason = QueryValidator.is_safe_query(update_query)
        assert not is_safe
        assert "Only SELECT queries are allowed" in reason
    
    def test_query_sanitization(self):
        """Test query sanitization"""
        query = "  SELECT   *   FROM   users  "
        sanitized = QueryValidator.sanitize_query(query)
        assert sanitized == "SELECT * FROM users;"

class TestAIQueryGenerator:
    """Test AI query generator functionality"""
    
    @pytest.fixture
    def ai_generator(self):
        """Create a test AI query generator"""
        return AIQueryGenerator(api_key="test_key", model="gpt-3.5-turbo")
    
    def test_initialization(self, ai_generator):
        """Test AI generator initialization"""
        assert ai_generator.api_key == "test_key"
        assert ai_generator.model == "gpt-3.5-turbo"
    
    def test_system_prompt_creation(self, ai_generator):
        """Test system prompt creation with database metadata"""
        metadata = {
            "tables": {
                "users": {
                    "columns": [
                        {"column_name": "id", "data_type": "integer", "is_nullable": "NO", "column_default": None},
                        {"column_name": "name", "data_type": "varchar", "is_nullable": "YES", "column_default": None}
                    ]
                }
            },
            "relationships": []
        }
        
        prompt = ai_generator._create_system_prompt(metadata)
        assert "Table: users" in prompt
        assert "id (integer, NOT NULL)" in prompt
        assert "name (varchar)" in prompt
    
    def test_user_prompt_creation(self, ai_generator):
        """Test user prompt creation with chat history"""
        user_message = "Show me all users"
        chat_history = [
            {
                "user_message": "What tables do we have?",
                "bot_response": "We have users, orders, and products tables."
            }
        ]
        
        prompt = ai_generator._create_user_prompt(user_message, chat_history)
        assert "Show me all users" in prompt
        assert "What tables do we have?" in prompt
    
    @patch('utils.openai.ChatCompletion.acreate')
    @pytest.mark.asyncio
    async def test_query_generation_success(self, mock_openai, ai_generator):
        """Test successful query generation"""
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = json.dumps({
            "query": "SELECT * FROM users LIMIT 10;",
            "explanation": "This query retrieves all users from the database.",
            "confidence": "high"
        })
        mock_openai.return_value = mock_response
        
        metadata = {"tables": {}, "relationships": []}
        result = await ai_generator.generate_query("Show me all users", metadata)
        
        assert result["query"] == "SELECT * FROM users LIMIT 10;"
        assert result["explanation"] == "This query retrieves all users from the database."
        assert result["confidence"] == "high"
    
    @patch('utils.openai.ChatCompletion.acreate')
    @pytest.mark.asyncio
    async def test_query_generation_invalid_json(self, mock_openai, ai_generator):
        """Test query generation with invalid JSON response"""
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "This is not valid JSON"
        mock_openai.return_value = mock_response
        
        metadata = {"tables": {}, "relationships": []}
        result = await ai_generator.generate_query("Show me all users", metadata)
        
        assert result["query"] is None
        assert "This is not valid JSON" in result["explanation"]
        assert result["confidence"] == "low"

class TestChatHistoryManager:
    """Test chat history manager functionality"""
    
    @pytest.fixture
    def chat_manager(self):
        """Create a test chat history manager"""
        return ChatHistoryManager(max_history_per_session=5)
    
    def test_add_message(self, chat_manager):
        """Test adding messages to chat history"""
        chat_manager.add_message(
            session_id="test_session",
            user_message="Hello",
            bot_response="Hi there!",
            query="SELECT 1",
            results=[{"test": "data"}]
        )
        
        history = chat_manager.get_history("test_session")
        assert len(history) == 1
        assert history[0]["user_message"] == "Hello"
        assert history[0]["bot_response"] == "Hi there!"
        assert history[0]["query"] == "SELECT 1"
        assert history[0]["results_count"] == 1
    
    def test_history_limit(self, chat_manager):
        """Test chat history size limit"""
        for i in range(10):
            chat_manager.add_message(
                session_id="test_session",
                user_message=f"Message {i}",
                bot_response=f"Response {i}"
            )
        
        history = chat_manager.get_history("test_session")
        assert len(history) == 5  # max_history_per_session
        assert history[0]["user_message"] == "Message 5"  # Oldest kept message
    
    def test_clear_history(self, chat_manager):
        """Test clearing chat history"""
        chat_manager.add_message("test_session", "Hello", "Hi")
        chat_manager.clear_history("test_session")
        
        history = chat_manager.get_history("test_session")
        assert len(history) == 0
