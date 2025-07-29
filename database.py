import psycopg2
import psycopg2.extras
from psycopg2 import pool
import logging
from typing import List, Dict, Any, Optional, Tuple
import os
from contextlib import contextmanager
import json

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DatabaseManager:
    """
    PostgreSQL database manager with connection pooling and error handling
    """
    
    def __init__(self, 
