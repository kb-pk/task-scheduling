"""
Interfaces and protocols for main content visualization components.
"""
from abc import ABC, abstractmethod
from typing import Protocol, Dict, Any, List, Optional

try:
    from matplotlib.figure import Figure
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    Figure = Any


class PlotDataProvider(Protocol):
    """Protocol for providing plot data."""
    
    def get_schedule_map(self) -> Dict[str, Any]:
        """Get schedule mapping data."""
        ...
    
    def get_machine_names(self) -> List[str]:
        """Get machine names for display."""
        ...
    
    def get_history_data(self, metric: str) -> List[float]:
        """Get historical metric data."""
        ...


class GanttRenderer(Protocol):
    """Protocol for Gantt chart rendering."""
    
    def create_gantt_figure(self, data: Dict[str, Any], view_type: str) -> Optional[Any]:
        """Create Gantt chart figure."""
        ...


class HistoryRenderer(Protocol):
    """Protocol for history/convergence chart rendering."""
    
    def create_history_figure(self, data: List[float], title: str, y_label: str) -> Optional[Any]:
        """Create history/convergence figure."""
        ...


class LogHandler(Protocol):
    """Protocol for handling log messages."""
    
    def log_message(self, message: str) -> None:
        """Log a message."""
        ...


class PlotManager(ABC):
    """Abstract manager for plot operations."""
    
    @abstractmethod
    def clear_all_plots(self) -> None:
        """Clear all existing plots."""
        pass
    
    @abstractmethod
    def render_solution_plots(self, solution_data: Dict[str, Any]) -> None:
        """Render plots for solution data."""
        pass


class TabManager(Protocol):
    """Protocol for managing notebook tabs."""
    
    def create_tab(self, name: str) -> Any:
        """Create a new tab."""
        ...
    
    def add_tab(self, tab: Any, title: str) -> None:
        """Add tab to notebook."""
        ...
    
    def get_tab(self, name: str) -> Optional[Any]:
        """Get existing tab by name."""
        ...
