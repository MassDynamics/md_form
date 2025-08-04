"""
Shared pytest configuration and fixtures for the test suite.
"""

import pytest
import sys
import os

# Add the project root to the Python path so we can import modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__)))) 