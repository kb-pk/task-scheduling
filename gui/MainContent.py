"""
Backward compatibility wrapper for the refactored MainContent implementation.
This maintains the original API while using the new architecture internally.
"""
import tkinter as tk
from typing import Dict, Any

from .components.MainContentView import MainContent as MainContentImpl


class MainContent(MainContentImpl):
    """Backward compatibility wrapper maintaining the original API."""
    
    def __init__(self, parent: tk.Widget):
        # Initialize the internal MainContent implementation
        super().__init__(parent)