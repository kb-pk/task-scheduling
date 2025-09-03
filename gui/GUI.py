"""
Professional GUI application with clean architecture.
"""
import tkinter as tk
from tkinter import ttk, messagebox
import logging
from typing import Dict, Any, Optional

from scheduler.Registry import UIRegistrator
from scheduler.UI import UI
from scheduler.ProgramState import ProgramState
from scheduler.methods.BaseMethod import BaseMethod

from .Sidebar import Sidebar
from .MainContent import MainContent
from .core import ApplicationLifecycle, ApplicationController, EventDispatcher, LoggingService
from .config import ApplicationConfig, ApplicationMessages, WindowConfig
from .core import MainApplicationController
from .core import MethodExecutionService, ResultDataProcessor
from .core import ApplicationStateManager, SimpleEventDispatcher, ApplicationLoggingService


logger = logging.getLogger(__name__)

@UIRegistrator.register_class
class GUI(tk.Tk, UI, ApplicationLifecycle):
    """Professional Task Scheduling GUI application with clean separation of concerns."""
    
    def __init__(
        self, 
        state: ProgramState, 
        t, 
        method_instances: Dict[str, BaseMethod],
        config: Optional[ApplicationConfig] = None
    ) -> None:
        super().__init__()
        
        # Configuration
        self.config = config or ApplicationConfig()
        
        # Core dependencies
        self.T = t
        
        # Initialize logging
        self.logging_service = ApplicationLoggingService()
        
        # Initialize state management
        self.state_manager = ApplicationStateManager(state, method_instances)
        
        # Initialize event system
        self.event_dispatcher = SimpleEventDispatcher()
        
        # Initialize services
        self.data_processor = ResultDataProcessor()
        self.method_runner = MethodExecutionService(self.config.threading, self.data_processor)
        
        # Initialize controller
        self.controller = MainApplicationController(
            self.state_manager,
            self.method_runner,
            self.event_dispatcher,
            self.logging_service
        )
        
        # UI components (will be initialized in _setup_ui)
        self.sidebar: Optional[Sidebar] = None
        self.main_content: Optional[MainContent] = None
        
        # Setup
        self._setup_window()
        self._setup_ui()
        self._setup_event_handlers()
        self._setup_layout()
        
        # Connect logging
        self._connect_logging()
        
        logger.info("Task Scheduling GUI application initialized successfully")
    
    def start(self) -> None:
        """Start the application."""
        logger.info(ApplicationMessages.STARTING_APPLICATION)
        
        try:
            self.logging_service.log_info(ApplicationMessages.APPLICATION_READY)
            self.mainloop()
        except Exception as e:
            logger.error(f"Error starting application: {e}")
            self.logging_service.log_error(ApplicationMessages.UNEXPECTED_ERROR.format(error=str(e)), e)
            raise
    
    def shutdown(self) -> None:
        """Shutdown the application gracefully."""
        logger.info(ApplicationMessages.SHUTTING_DOWN)
        
        try:
            # Check if method is running and warn user
            if self.controller.is_method_running():
                if self.config.ui.confirm_exit_when_running:
                    if not messagebox.askyesno("Confirm Exit", ApplicationMessages.UNSAVED_WORK_WARNING):
                        return
                
                # Cancel running method
                self.controller.cancel_current_execution()
            
            # Shutdown services
            self.method_runner.shutdown()
            
            # Destroy window
            self.destroy()
            
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")
    
    def log(self, message: str) -> None:
        """Log a message (UI interface compliance)."""
        # Fix the main logging issue - ensure proper line breaks
        clean_message = message.rstrip('\n')
        if clean_message:  # Don't log empty messages
            formatted_message = clean_message + '\n'
            self.logging_service.log_info(formatted_message.strip())
    
    def _setup_window(self) -> None:
        """Setup main window properties."""
        window_config = self.config.window
        
        try:
            self.title(window_config.title)
            self.protocol("WM_DELETE_WINDOW", self._on_closing)
            
            if window_config.center_on_startup:
                self.after(0, self._center_window)
            
            # Set minimum size
            self.minsize(window_config.min_width, window_config.min_height)
            
        except Exception as e:
            logger.warning(f"{ApplicationMessages.WINDOW_SETUP_ERROR}: {e}")
    
    def _setup_ui(self) -> None:
        """Setup UI components."""
        # Configure grid
        self.columnconfigure(0, weight=0, minsize=self.config.window.sidebar_width)
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)
        
        # Create sidebar
        self.sidebar = Sidebar(
            self,
            state=self.state_manager.get_program_state(),
            method_instances=self.state_manager.get_methods(),
            on_start_clicked=self._on_start_clicked,
            on_objective_changed=self._on_objective_changed,
            width=self.config.window.sidebar_width
        )
        
        # Create main content
        self.main_content = MainContent(self)
    
    def _setup_event_handlers(self) -> None:
        """Setup event handlers."""
        # Subscribe to application events
        self.event_dispatcher.subscribe("method_execution_starting", self._on_method_starting)
        self.event_dispatcher.subscribe("method_execution_completed", self._on_method_completed)
        self.event_dispatcher.subscribe("method_execution_failed", self._on_method_failed)
        self.event_dispatcher.subscribe("objective_changed", self._on_objective_changed_event)
    
    def _setup_layout(self) -> None:
        """Setup component layout."""
        # Layout is handled by individual components
        pass
    
    def _connect_logging(self) -> None:
        """Connect logging service to UI."""
        if self.main_content:
            self.logging_service.set_log_callback(self.main_content.log)
    
    def _center_window(self) -> None:
        """Center the window on screen."""
        try:
            window_config = self.config.window
            
            sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
            w = max(window_config.min_width, int(sw * window_config.default_width_ratio))
            h = max(window_config.min_height, int(sh * window_config.default_height_ratio))
            x = max(0, (sw - w) // 2)
            y = max(0, (sh - h) // 2)
            
            self.geometry(f"{w}x{h}+{x}+{y}")
            
        except Exception as e:
            logger.warning(f"Failed to center window: {e}")
    
    def _on_closing(self) -> None:
        """Handle window closing event."""
        self.shutdown()
    
    def _on_start_clicked(self) -> None:
        """Handle start button click."""
        if not self.sidebar:
            logger.debug("No sidebar available")
            return
        
        method = self.sidebar.get_selected_method()
        logger.debug(f"Selected method: {method}")
        if not method:
            logger.warning("No method selected from sidebar")
            self.logging_service.log_warning("Please select a method first")
            return
        
        # Apply parameters from sidebar and get warnings
        warnings = self.sidebar.apply_parameters_to_method(method)
        
        # Log warnings
        for warning in warnings:
            self.logging_service.log_warning(warning)
        
        # Start execution through controller - pass method instance directly
        logger.debug(f"Starting method execution: {method.get_name()}")
        self.controller.start_method_execution_direct(method)
    
    def _on_objective_changed(self, new_objective: str) -> None:
        """Handle objective change from sidebar."""
        self.controller.change_objective(new_objective)
    
    def _on_method_starting(self, data: Dict[str, Any]) -> None:
        """Handle method execution starting."""
        if self.config.ui.auto_clear_plots_on_start and self.main_content:
            self.main_content.clear_plots()
        
        if self.sidebar:
            self.sidebar.disable_start_button()
    
    def _on_method_completed(self, data: Dict[str, Any]) -> None:
        """Handle method execution completion."""
        if self.sidebar:
            self.sidebar.enable_start_button()
        
        if self.main_content and "results" in data:
            try:
                self.main_content.render_plots(data["results"])
            except Exception as e:
                logger.error(f"Error rendering plots: {e}")
                self.logging_service.log_error(f"Error rendering plots: {e}")
    
    def _on_method_failed(self, data: Dict[str, Any]) -> None:
        """Handle method execution failure."""
        if self.sidebar:
            self.sidebar.enable_start_button()
    
    def _on_objective_changed_event(self, data: Dict[str, Any]) -> None:
        """Handle objective changed event."""
        # Could update UI to reflect objective change
        pass
