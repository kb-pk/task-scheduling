"""
Application state management and event dispatching.
"""
import logging
from typing import Dict, Any, Optional, Callable, List, DefaultDict
from collections import defaultdict

from scheduler.ProgramState import ProgramState
from scheduler.methods.BaseMethod import BaseMethod
from .Interfaces import ApplicationState, EventDispatcher, LoggingService
from ..config import ApplicationMessages


logger = logging.getLogger(__name__)


class ApplicationStateManager(ApplicationState):
    """Manages application state and selected method."""
    
    def __init__(self, program_state: ProgramState, methods: Dict[str, BaseMethod]):
        self._program_state = program_state
        self._methods = methods
        self._selected_method: Optional[BaseMethod] = None
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Debug logging
        self.logger.debug(f"ApplicationStateManager initialized with methods: {list(methods.keys())}")
        for name, method in methods.items():
            self.logger.debug(f"  {name}: {method.get_name() if hasattr(method, 'get_name') else 'No get_name()'}")
    
    def get_program_state(self) -> ProgramState:
        """Get the program state."""
        return self._program_state
    
    def get_methods(self) -> Dict[str, BaseMethod]:
        """Get available optimization methods."""
        return self._methods.copy()
    
    def get_selected_method(self) -> Optional[BaseMethod]:
        """Get the currently selected method."""
        return self._selected_method
    
    def set_selected_method(self, method: Optional[BaseMethod]) -> None:
        """Set the currently selected method."""
        if method is not None and method not in self._methods.values():
            raise ValueError(f"Method {method.get_name() if hasattr(method, 'get_name') else method} is not in available methods")
        
        self._selected_method = method
        self.logger.info(f"Selected method: {method.get_name() if method else 'None'}")


class SimpleEventDispatcher(EventDispatcher):
    """Simple event dispatcher for application events."""
    
    def __init__(self):
        self._handlers: DefaultDict[str, List[Callable]] = defaultdict(list)
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def dispatch_event(self, event_type: str, data: Optional[Dict[str, Any]] = None) -> None:
        """Dispatch an application event."""
        self.logger.debug(f"Dispatching event: {event_type}")
        
        handlers = self._handlers.get(event_type, [])
        for handler in handlers:
            try:
                if data:
                    handler(data)
                else:
                    handler()
            except Exception as e:
                self.logger.error(f"Error in event handler for {event_type}: {e}")
    
    def subscribe(self, event_type: str, handler: Callable) -> None:
        """Subscribe to an application event."""
        self._handlers[event_type].append(handler)
        self.logger.debug(f"Subscribed to event: {event_type}")


class ApplicationLoggingService(LoggingService):
    """Application logging service with multiple outputs."""
    
    def __init__(self, log_callback: Optional[Callable[[str], None]] = None):
        self.log_callback = log_callback
        self.logger = logging.getLogger("Application")
    
    def log_info(self, message: str) -> None:
        """Log an info message."""
        self.logger.info(message)
        if self.log_callback:
            # Ensure proper line breaks - fix the main logging issue
            formatted_message = message.rstrip('\n') + '\n' if not message.endswith('\n') else message
            self.log_callback(formatted_message)
    
    def log_warning(self, message: str) -> None:
        """Log a warning message."""
        self.logger.warning(message)
        if self.log_callback:
            # Ensure proper line breaks
            formatted_message = f"Warning: {message}"
            if not formatted_message.endswith('\n'):
                formatted_message += '\n'
            self.log_callback(formatted_message)
    
    def log_error(self, message: str, exception: Optional[Exception] = None) -> None:
        """Log an error message."""
        self.logger.error(message, exc_info=exception)
        if self.log_callback:
            # Ensure proper line breaks
            formatted_message = f"Error: {message}"
            if not formatted_message.endswith('\n'):
                formatted_message += '\n'
            self.log_callback(formatted_message)
    
    def set_log_callback(self, callback: Callable[[str], None]) -> None:
        """Set the callback for log messages."""
        self.log_callback = callback
