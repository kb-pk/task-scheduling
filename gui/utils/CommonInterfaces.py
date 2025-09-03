"""
GUI interfaces and protocols for proper dependency injection and testability.
"""
from abc import ABC, abstractmethod
from typing import Protocol, Dict, List, Any, Optional
from scheduler.methods.BaseMethod import BaseMethod
from scheduler.Parameters import ParamDef


class ParameterValidator(Protocol):
    """Protocol for parameter validation."""
    
    def validate_parameter(self, param_def: ParamDef, value: str) -> tuple[bool, Optional[str]]:
        """
        Validate a parameter value.
        
        Args:
            param_def: Parameter definition to validate against
            value: String value to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        ...


class UIEventHandler(Protocol):
    """Protocol for handling UI events."""
    
    def on_algorithm_changed(self, method: Optional[BaseMethod]) -> None:
        """Handle algorithm selection change."""
        ...
        
    def on_objective_changed(self, objective: str) -> None:
        """Handle optimization objective change."""
        ...
        
    def on_start_clicked(self) -> None:
        """Handle start button click."""
        ...


class WidgetFactory(ABC):
    """Abstract factory for creating parameter widgets."""
    
    @abstractmethod
    def create_boolean_widget(self, parent, param_def: ParamDef) -> Dict[str, Any]:
        """Create widget for boolean parameter."""
        pass
        
    @abstractmethod
    def create_numeric_widget(self, parent, param_def: ParamDef) -> Dict[str, Any]:
        """Create widget for numeric parameter."""
        pass
        
    @abstractmethod
    def create_list_single_widget(self, parent, param_def: ParamDef) -> Dict[str, Any]:
        """Create widget for single-select list parameter."""
        pass


class TooltipProvider(Protocol):
    """Protocol for providing tooltips."""
    
    def attach_tooltip(self, widget, text: str) -> None:
        """Attach tooltip to widget."""
        ...


class SidebarController(ABC):
    """Abstract controller for sidebar operations."""
    
    @abstractmethod
    def get_selected_method(self) -> Optional[BaseMethod]:
        """Get currently selected method."""
        pass
        
    @abstractmethod
    def get_objective(self) -> str:
        """Get selected optimization objective."""
        pass
        
    @abstractmethod
    def apply_parameters(self, method: BaseMethod) -> List[str]:
        """Apply UI parameters to method. Returns warnings."""
        pass
        
    @abstractmethod
    def set_start_button_enabled(self, enabled: bool) -> None:
        """Enable or disable start button."""
        pass
