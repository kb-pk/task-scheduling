"""
Configuration constants and settings for the GUI module.
"""
from dataclasses import dataclass
from typing import Dict, Any


@dataclass(frozen=True)
class UIConstants:
    """UI constants and styling."""
    
    # Layout constants
    DEFAULT_SIDEBAR_WIDTH: int = 360
    DEFAULT_WINDOW_WIDTH: int = 960
    DEFAULT_WINDOW_HEIGHT: int = 720
    WINDOW_SIZE_FACTOR: float = 0.6
    
    # Padding and spacing
    STANDARD_PADDING: int = 10
    WIDGET_SPACING: int = 6
    SMALL_SPACING: int = 3
    LARGE_SPACING: int = 8
    
    # Widget dimensions
    ENTRY_WIDTH: int = 14
    TOOLTIP_WRAP_LENGTH: int = 280
    DESCRIPTION_MIN_WIDTH: int = 100
    DESCRIPTION_PADDING: int = 20
    
    # Timing
    WIDGET_READY_DELAY_MS: int = 1
    TOOLTIP_DELAY_MS: int = 400
    UI_UPDATE_INTERVAL_MS: int = 100
    
    # Colors
    TOOLTIP_BACKGROUND: str = "#ffffe0"
    ERROR_COLOR: str = "#d62728"
    SUCCESS_COLOR: str = "#2ca02c"
    
    # Fonts
    DEFAULT_FONT: str = "TkDefaultFont"
    MONOSPACE_FONT: str = "Consolas"
    MONOSPACE_SIZE: int = 9


@dataclass(frozen=True)
class ValidationMessages:
    """Validation and error messages."""
    
    INVALID_VALUE: str = "Invalid value for '{param}': {error}"
    STOP_CRITERION_ERROR: str = "Could not set stop criterion: {error}"
    NO_METHOD_SELECTED: str = "No method selected"
    NO_METHODS_FOUND: str = "<no methods found>"
    NO_DESCRIPTION: str = "(no description)"
    ALGORITHM_RUNNING: str = "An algorithm is already running"
    
    @staticmethod
    def format_bounds(min_val: Any = None, max_val: Any = None) -> str:
        """Format parameter bounds for display."""
        bounds = []
        if min_val is not None:
            bounds.append(f"min={min_val}")
        if max_val is not None:
            bounds.append(f"max={max_val}")
        return f" ({', '.join(bounds)})" if bounds else ""


@dataclass
class SidebarConfig:
    """Configuration for sidebar behavior."""
    
    width: int = UIConstants.DEFAULT_SIDEBAR_WIDTH
    enable_tooltips: bool = True
    auto_validate_parameters: bool = True
    show_parameter_bounds: bool = True
    wrap_descriptions: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'width': self.width,
            'enable_tooltips': self.enable_tooltips,
            'auto_validate_parameters': self.auto_validate_parameters,
            'show_parameter_bounds': self.show_parameter_bounds,
            'wrap_descriptions': self.wrap_descriptions
        }
        
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SidebarConfig':
        """Create from dictionary."""
        return cls(**data)
