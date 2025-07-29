#!/usr/bin/env python3
"""
AI PostgreSQL Chatbot - Main Application Entry Point

This is the main entry point for the AI PostgreSQL chatbot application.
It provides multiple interfaces: CLI, Web UI, and Python API.

Usage:
    python main.py                    # Start interactive CLI
    python main.py --web             # Start web interface
    python main.py --query "..."     # Run single query
    python main.py --help            # Show help
"""

import argparse
import sys
import os
from pathlib import Path

# Add project root to Python path
