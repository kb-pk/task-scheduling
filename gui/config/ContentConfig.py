"""
Configuration and constants specific to main content visualization.
"""
from dataclasses import dataclass
from typing import Dict, Any


@dataclass(frozen=True)
class PlotConfig:
    """Configuration for plot rendering."""
    
    # Figure dimensions
    GANTT_FIGURE_SIZE: tuple[int, int] = (10, 6)
    LINEAR_FIGURE_SIZE: tuple[int, int] = (8, 4)
    FIGURE_DPI: int = 100
    
    # Colors and styling
    GANTT_COLORMAP: str = 'viridis'
    MAKESPAN_LINE_COLOR: str = 'red'
    ENERGY_LINE_COLOR: str = 'red'
    HISTORY_LINE_COLOR: str = "#1f77b4"
    IMPROVEMENT_COLOR: str = "#d62728"
    
    # Layout constants
    BAR_HEIGHT: float = 0.6
    MIN_LABEL_WIDTH_RATIO: float = 0.02
    GRID_ALPHA: float = 0.7
    LEGEND_ALPHA: float = 0.8
    
    # Text and labels
    TASK_LABEL_COLOR: str = 'white'
    TASK_LABEL_FONT_SIZE: int = 8
    TASK_LABEL_WEIGHT: str = 'bold'
    AXIS_LABEL_FONT_SIZE: int = 9
    
    # Mock values (should be removed in production)
    MOCK_BASE_POWER: int = 100
    MOCK_POWER_INCREMENT: int = 10
    
    # Features
    show_improvement_markers: bool = True


@dataclass(frozen=True)
class ContentMessages:
    """Messages for main content component."""
    
    NO_DATA_MESSAGE: str = "No data to display."
    MATPLOTLIB_NOT_FOUND: str = "Matplotlib not found. Plots are disabled."
    MAKESPAN_LABEL: str = "Makespan: {value:.1f}"
    MAX_ENERGY_LABEL: str = "Max Energy: {value:.1f}"
    
    # Tab titles
    GANTT_TAB: str = "Gantt"
    LINEAR_TAB: str = "Linear"
    DIAGNOSTICS_TAB: str = "Diagnostics"
    
    MAKESPAN_SUBTAB: str = "Makespan"
    ENERGY_SUBTAB: str = "Energy"


@dataclass
class ContentConfig:
    """Configuration for main content behavior."""
    
    enable_matplotlib: bool = True
    auto_clear_on_new_data: bool = True
    show_improvement_markers: bool = True
    enable_grid: bool = True
    default_font_family: str = "Consolas"
    diagnostics_max_lines: int = 1000
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'enable_matplotlib': self.enable_matplotlib,
            'auto_clear_on_new_data': self.auto_clear_on_new_data,
            'show_improvement_markers': self.show_improvement_markers,
            'enable_grid': self.enable_grid,
            'default_font_family': self.default_font_family,
            'diagnostics_max_lines': self.diagnostics_max_lines
        }
