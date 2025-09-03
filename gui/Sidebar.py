"""
Backward compatibility wrapper for the refactored sidebar implementation.
This maintains the original API while using the new architecture internally.
"""
import tkinter as tk
from tkinter import ttk
from typing import Dict, Callable, Any, List

from scheduler.ProgramState import ProgramState
from scheduler.methods.BaseMethod import BaseMethod

from .components.SidebarController import create_sidebar, SidebarControllerImpl
from .config import SidebarConfig


class Sidebar(ttk.Frame):
    """
    Backward compatibility wrapper for the new sidebar implementation.
    Maintains the original API while delegating to the new architecture.
    """
    
    def __init__(
        self, 
        parent, 
        state: ProgramState, 
        method_instances: Dict[str, BaseMethod], 
        on_start_clicked: Callable, 
        on_objective_changed: Callable, 
        **kwargs
    ):
        # Extract width if provided
        width = kwargs.pop('width', 360)
        config = SidebarConfig(width=width)
        
        # Create the new implementation
        self._controller = create_sidebar(
            parent, state, method_instances,
            on_start_clicked, on_objective_changed, config
        )
        
        # Get the view frame - this is what we'll present as "self"
        self._view = self._controller.view
        
        # Copy the frame's interface
        super().__init__(parent, **kwargs)
        
        # Hide this frame and show the actual view
        self.grid_remove()
        
        # Forward the grid configuration to the actual view
        self._view.grid(row=0, column=0, sticky="nsw")
    
    def get_selected_method(self) -> BaseMethod | None:
        """Get currently selected method."""
        return self._controller.get_selected_method()
    
    def get_objective(self) -> str:
        """Get selected optimization objective."""
        return self._controller.get_objective()
    
    def apply_parameters_to_method(self, method: BaseMethod) -> List[str]:
        """Apply UI parameters to method instance. Returns warnings."""
        return self._controller.apply_parameters(method)
    
    def enable_start_button(self):
        """Enable the start button."""
        self._controller.set_start_button_enabled(True)
    
    def disable_start_button(self):
        """Disable the start button."""
        self._controller.set_start_button_enabled(False)
    
    def cleanup(self):
        """Cleanup resources."""
        if hasattr(self._controller, 'cleanup'):
            self._controller.cleanup()