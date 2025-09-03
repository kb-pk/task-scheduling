"""
Main application controller implementing business logic.
"""
import logging
from typing import Dict, Any, Optional

from scheduler.methods.BaseMethod import BaseMethod
from .Interfaces import ApplicationController, MethodRunner, EventDispatcher, LoggingService, ApplicationState
from ..config import ApplicationMessages


logger = logging.getLogger(__name__)


class MainApplicationController(ApplicationController):
    """Main controller coordinating application business logic."""
    
    def __init__(
        self,
        state_manager: ApplicationState,
        method_runner: MethodRunner,
        event_dispatcher: EventDispatcher,
        logging_service: LoggingService
    ):
        self.state_manager = state_manager
        self.method_runner = method_runner
        self.event_dispatcher = event_dispatcher
        self.logging_service = logging_service
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Subscribe to events
        self._setup_event_handlers()
    
    def start_method_execution(self, method_name: str, parameters: Dict[str, Any]) -> bool:
        """Start execution of an optimization method."""
        self.logger.debug(f"Attempting to start method: {method_name}")
        
        if self.method_runner.is_running():
            self.logging_service.log_warning(ApplicationMessages.METHOD_ALREADY_RUNNING)
            return False
        
        # Get method
        methods = self.state_manager.get_methods()
        self.logger.debug(f"Available methods: {list(methods.keys())}")
        method = methods.get(method_name)
        if not method:
            self.logger.error(f"Method {method_name} not found in available methods")
            self.logging_service.log_error(ApplicationMessages.NO_METHOD_SELECTED)
            return False
        
        # Note: Parameters are already applied by the sidebar before this call
        
        # Log start
        self.logging_service.log_info(ApplicationMessages.METHOD_STARTING.format(method_name=method.get_name()))
        
        # Dispatch pre-execution events
        self.event_dispatcher.dispatch_event("method_execution_starting", {
            "method": method,
            "parameters": parameters
        })
        
        # Start execution
        self.method_runner.run_method(method, self._on_method_completed)
        return True
    
    def start_method_execution_direct(self, method: BaseMethod) -> bool:
        """Start execution of an optimization method with direct method instance."""
        self.logger.debug(f"Attempting to start method directly: {method.get_name()}")
        
        if self.method_runner.is_running():
            self.logging_service.log_warning(ApplicationMessages.METHOD_ALREADY_RUNNING)
            return False
        
        # Note: Parameters are already applied by the sidebar before this call
        
        # Log start
        self.logging_service.log_info(ApplicationMessages.METHOD_STARTING.format(method_name=method.get_name()))
        
        # Dispatch pre-execution events
        self.event_dispatcher.dispatch_event("method_execution_starting", {
            "method": method,
            "parameters": {}
        })
        
        # Start execution
        self.method_runner.run_method(method, self._on_method_completed)
        return True
    
    def change_objective(self, objective: str) -> None:
        """Change the optimization objective."""
        try:
            program_state = self.state_manager.get_program_state()
            state_enum = program_state.scheduling.State

            
            if objective.upper() == "MAKESPAN":
                program_state.scheduling.set(state_enum.makespan)
            elif objective.upper() == "ENERGY":
                program_state.scheduling.set(state_enum.energy)
            else:
                raise ValueError(f"Unknown objective: {objective}")
            
            self.logging_service.log_info(ApplicationMessages.OBJECTIVE_CHANGED.format(objective=objective))
            
            # Dispatch event
            self.event_dispatcher.dispatch_event("objective_changed", {
                "objective": objective
            })
            
        except Exception as e:
            self.logging_service.log_error(f"Failed to change objective: {e}", e)
    
    def handle_method_completed(self, results: Dict[str, Any]) -> None:
        """Handle completion of method execution."""
        if results.get("success"):
            self.logging_service.log_info(ApplicationMessages.METHOD_COMPLETED)
            
            # Dispatch success event
            self.event_dispatcher.dispatch_event("method_execution_completed", {
                "results": results
            })
        else:
            error = results.get("error", "Unknown error")
            self.handle_method_error(Exception(error))
    
    def handle_method_error(self, error: Exception) -> None:
        """Handle method execution error."""
        self.logging_service.log_error(ApplicationMessages.METHOD_FAILED.format(error=str(error)), error)
        
        # Dispatch error event
        self.event_dispatcher.dispatch_event("method_execution_failed", {
            "error": error
        })
    
    def cancel_current_execution(self) -> bool:
        """Cancel the currently running method."""
        if self.method_runner.cancel_current_run():
            self.logging_service.log_info("Method execution cancelled")
            self.event_dispatcher.dispatch_event("method_execution_cancelled")
            return True
        return False
    
    def is_method_running(self) -> bool:
        """Check if a method is currently running."""
        return self.method_runner.is_running()
    
    def _setup_event_handlers(self):
        """Setup internal event handlers."""
        pass  # Can be extended for internal event handling

    def _on_method_completed(self, results: Dict[str, Any]) -> None:
        """Internal callback for method completion."""
        try:
            self.handle_method_completed(results)
        except Exception as e:
            self.logger.error(f"Error handling method completion: {e}")
            self.handle_method_error(e)
