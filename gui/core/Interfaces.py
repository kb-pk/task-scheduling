"""
Interfaces and protocols for the main application architecture.
"""
from abc import ABC, abstractmethod
from typing import Protocol, Dict, Any, Optional, Callable, List
from scheduler.ProgramState import ProgramState
from scheduler.methods.BaseMethod import BaseMethod


class ApplicationLifecycle(Protocol):
    """Protocol for application lifecycle management."""
    
    def start(self) -> None:
        """Start the application."""
        ...
    
    def shutdown(self) -> None:
        """Shutdown the application gracefully."""
        ...


class MethodRunner(Protocol):
    """Protocol for running optimization methods."""
    
    def run_method(self, method: BaseMethod, callback: Callable[[Dict[str, Any]], None]) -> None:
        """Run a method asynchronously and call callback with results."""
        ...
    
    def is_running(self) -> bool:
        """Check if a method is currently running."""
        ...
    
    def cancel_current_run(self) -> bool:
        """Cancel the currently running method if any."""
        ...


class DataProcessor(Protocol):
    """Protocol for processing method results into UI-ready data."""
    
    def process_method_results(self, method: BaseMethod) -> Dict[str, Any]:
        """Process method results into structured data for UI."""
        ...


class EventDispatcher(Protocol):
    """Protocol for handling application events."""
    
    def dispatch_event(self, event_type: str, data: Optional[Dict[str, Any]] = None) -> None:
        """Dispatch an application event."""
        ...
    
    def subscribe(self, event_type: str, handler: Callable) -> None:
        """Subscribe to an application event."""
        ...


class LoggingService(Protocol):
    """Protocol for application logging."""
    
    def log_info(self, message: str) -> None:
        """Log an info message."""
        ...
    
    def log_warning(self, message: str) -> None:
        """Log a warning message."""
        ...
    
    def log_error(self, message: str, exception: Optional[Exception] = None) -> None:
        """Log an error message."""
        ...


class ApplicationState(ABC):
    """Abstract base for application state management."""
    
    @abstractmethod
    def get_program_state(self) -> ProgramState:
        """Get the program state."""
        pass
    
    @abstractmethod
    def get_methods(self) -> Dict[str, BaseMethod]:
        """Get available optimization methods."""
        pass
    
    @abstractmethod
    def get_selected_method(self) -> Optional[BaseMethod]:
        """Get the currently selected method."""
        pass
    
    @abstractmethod
    def set_selected_method(self, method: Optional[BaseMethod]) -> None:
        """Set the currently selected method."""
        pass


class ApplicationController(ABC):
    """Abstract controller for main application logic."""
    
    @abstractmethod
    def start_method_execution(self, method_name: str, parameters: Dict[str, Any]) -> bool:
        """Start execution of an optimization method."""
        pass
    
    @abstractmethod
    def start_method_execution_direct(self, method: BaseMethod) -> bool:
        """Start execution of an optimization method with direct instance."""
        pass
    
    @abstractmethod
    def change_objective(self, objective: str) -> None:
        """Change the optimization objective."""
        pass
    
    @abstractmethod
    def handle_method_completed(self, results: Dict[str, Any]) -> None:
        """Handle completion of method execution."""
        pass
    
    @abstractmethod
    def handle_method_error(self, error: Exception) -> None:
        """Handle method execution error."""
        pass
