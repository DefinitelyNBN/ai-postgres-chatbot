import openai
import asyncio
import json
import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
import re
from dataclasses import dataclass, asdict
import hashlib
import time

# Configure logging
logger = logging.getLogger(__name__)

@dataclass
class ChatMessage:
    """Represents a single chat message"""
