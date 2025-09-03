"""
Professional figure renderers with proper separation of concerns.
"""
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Tuple
import numpy as np

try:
    from matplotlib.figure import Figure
    from matplotlib.ticker import StrMethodFormatter
    import matplotlib.cm as cm
    MATPLOTLIB_AVAILABLE = True
    FigureType = Figure
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    Figure = None
    FigureType = Any

from ..config import PlotConfig, ContentMessages


logger = logging.getLogger(__name__)


class BaseFigureRenderer:
    """Base implementation of figure renderer with common functionality."""
    
    def __init__(self, config: PlotConfig):
        self.config = config
        
        if not MATPLOTLIB_AVAILABLE:
            logger.warning("Matplotlib not available - plots will be disabled")
    
    def _is_available(self) -> bool:
        """Check if matplotlib is available."""
        return MATPLOTLIB_AVAILABLE
    
    def _create_figure(self, size: Tuple[int, int]) -> Optional[Any]:
        """Create a new matplotlib figure."""
        if not self._is_available():
            return None
        
        return Figure(figsize=size, dpi=self.config.FIGURE_DPI)
    
    def _get_task_colors(self, task_ids: List[int]) -> Dict[int, Any]:
        """Generate consistent colors for task IDs."""
        if not task_ids or not self._is_available():
            return {}
        
        colors = cm.get_cmap(self.config.GANTT_COLORMAP, len(task_ids))
        return {task_id: colors(i) for i, task_id in enumerate(task_ids)}
    
    def _add_grid_and_formatting(self, ax, title: str, xlabel: str, ylabel: str):
        """Add common formatting to axes."""
        if not ax:
            return
        
        ax.set_title(title)
        ax.set_xlabel(xlabel)
        ax.set_ylabel(ylabel)
        
        # Always show grid for now - can be made configurable later
        ax.grid(True, linestyle='--', linewidth=0.5, alpha=self.config.GRID_ALPHA)


class GanttChartRenderer(BaseFigureRenderer):
    """Specialized renderer for Gantt charts."""
    
    def create_gantt_figure(self, data: Dict[str, Any], view_type: str) -> Optional[Any]:
        """Create Gantt chart figure based on view type."""
        if view_type.lower() == "makespan":
            return self._create_makespan_gantt(data)
        elif view_type.lower() == "energy":
            return self._create_energy_gantt(data)
        else:
            logger.error(f"Unknown Gantt view type: {view_type}")
            return None
    
    def _create_makespan_gantt(self, data: Dict[str, Any]) -> Optional[Any]:
        """Create Gantt chart with time on X-axis."""
        schedule_map = data.get("schedule_map", {})
        machine_names = data.get("machine_names", [])
        
        if not schedule_map:
            return None
        
        fig = self._create_figure(self.config.GANTT_FIGURE_SIZE)
        if not fig:
            return None
        
        ax = fig.add_subplot(111)
        
        # Get all unique task IDs for consistent coloring
        all_task_ids = self._extract_all_task_ids(schedule_map)
        task_colors = self._get_task_colors(sorted(all_task_ids))
        
        # Calculate makespan
        makespan = self._calculate_makespan(schedule_map)
        
        # Draw time-based bars
        self._draw_time_based_bars(ax, schedule_map, task_colors, makespan)
        
        # Add makespan line
        if makespan > 0:
            self._add_makespan_line(ax, makespan, len(machine_names))
        
        # Format axes
        if machine_names:
            ax.set_yticks(range(len(machine_names)))
            ax.set_yticklabels(machine_names)
        
        ax.invert_yaxis()
        self._add_grid_and_formatting(ax, "Gantt Chart - Makespan View", "Time", "Machine")
        fig.tight_layout()
        
        return fig
    
    def _create_energy_gantt(self, data: Dict[str, Any]) -> Optional[Any]:
        """Create Gantt chart with energy on X-axis."""
        schedule_map = data.get("schedule_map", {})
        machine_names = data.get("machine_names", [])
        
        if not schedule_map:
            return None
        
        fig = self._create_figure(self.config.GANTT_FIGURE_SIZE)
        if not fig:
            return None
        
        ax = fig.add_subplot(111)
        
        # Get all unique task IDs for consistent coloring
        all_task_ids = self._extract_all_task_ids(schedule_map)
        task_colors = self._get_task_colors(sorted(all_task_ids))
        
        # Calculate max energy (using mock power values for now)
        max_energy = self._calculate_max_energy(schedule_map)
        
        # Draw energy-based bars
        self._draw_energy_based_bars(ax, schedule_map, task_colors, max_energy)
        
        # Add max energy line
        if max_energy > 0:
            self._add_energy_line(ax, max_energy, len(machine_names))
        
        # Format axes
        if machine_names:
            ax.set_yticks(range(len(machine_names)))
            ax.set_yticklabels(machine_names)
        
        ax.invert_yaxis()
        self._add_grid_and_formatting(ax, "Gantt Chart - Energy View", "Energy", "Machine")
        fig.tight_layout()
        
        return fig
    
    def _extract_all_task_ids(self, schedule_map: Dict[str, Any]) -> List[int]:
        """Extract all unique task IDs from schedule map."""
        task_ids = set()
        for tasks in schedule_map.values():
            for task_id, _, _ in tasks:
                task_ids.add(task_id)
        return list(task_ids)
    
    def _calculate_makespan(self, schedule_map: Dict[str, Any]) -> float:
        """Calculate makespan from schedule map."""
        makespan = 0.0
        for tasks in schedule_map.values():
            machine_end_time = 0.0
            for task_id, start_time, duration in tasks:
                machine_end_time = max(machine_end_time, start_time + duration)
            makespan = max(makespan, machine_end_time)
        return makespan
    
    def _calculate_max_energy(self, schedule_map: Dict[str, Any]) -> float:
        """Calculate maximum energy consumption (mock implementation)."""
        max_energy = 0.0
        for machine_id, tasks in schedule_map.items():
            machine_energy = 0.0
            # Mock power calculation
            p_busy = self.config.MOCK_BASE_POWER + machine_id * self.config.MOCK_POWER_INCREMENT
            for task_id, start_time, duration in tasks:
                machine_energy += duration * p_busy
            max_energy = max(max_energy, machine_energy)
        return max_energy
    
    def _draw_time_based_bars(self, ax, schedule_map: Dict[str, Any], 
                             task_colors: Dict[int, Any], makespan: float):
        """Draw time-based Gantt bars."""
        for machine_id, tasks in schedule_map.items():
            for task_id, start_time, duration in tasks:
                color = task_colors.get(task_id, 'gray')
                ax.barh(machine_id, duration, left=start_time, 
                       height=self.config.BAR_HEIGHT, align='center', 
                       color=color, edgecolor='black')
                
                # Add task label if bar is wide enough
                if duration > makespan * self.config.MIN_LABEL_WIDTH_RATIO:
                    ax.text(start_time + duration/2, machine_id, f'T{task_id}',
                           ha='center', va='center', 
                           color=self.config.TASK_LABEL_COLOR,
                           fontsize=self.config.TASK_LABEL_FONT_SIZE,
                           weight=self.config.TASK_LABEL_WEIGHT)
    
    def _draw_energy_based_bars(self, ax, schedule_map: Dict[str, Any], 
                               task_colors: Dict[int, Any], max_energy: float):
        """Draw energy-based Gantt bars."""
        for machine_id, tasks in schedule_map.items():
            current_energy = 0.0
            # Mock power calculation
            p_busy = self.config.MOCK_BASE_POWER + machine_id * self.config.MOCK_POWER_INCREMENT
            
            for task_id, start_time, duration in tasks:
                task_energy = duration * p_busy
                color = task_colors.get(task_id, 'gray')
                ax.barh(machine_id, task_energy, left=current_energy,
                       height=self.config.BAR_HEIGHT, align='center',
                       color=color, edgecolor='black')
                
                # Add task label if bar is wide enough
                if task_energy > max_energy * self.config.MIN_LABEL_WIDTH_RATIO:
                    ax.text(current_energy + task_energy/2, machine_id, f'T{task_id}',
                           ha='center', va='center',
                           color=self.config.TASK_LABEL_COLOR,
                           fontsize=self.config.TASK_LABEL_FONT_SIZE,
                           weight=self.config.TASK_LABEL_WEIGHT)
                
                current_energy += task_energy
    
    def _add_makespan_line(self, ax, makespan: float, num_machines: int):
        """Add makespan indicator line."""
        ax.axvline(makespan, color=self.config.MAKESPAN_LINE_COLOR, 
                  linestyle='--', linewidth=1.2)
        ax.text(makespan, num_machines - 0.5, 
               ContentMessages.MAKESPAN_LABEL.format(value=makespan),
               rotation=90, va='bottom', ha='left', 
               color=self.config.MAKESPAN_LINE_COLOR,
               fontsize=self.config.AXIS_LABEL_FONT_SIZE,
               bbox=dict(boxstyle='round,pad=0.2', facecolor='white', 
                        alpha=self.config.LEGEND_ALPHA))
    
    def _add_energy_line(self, ax, max_energy: float, num_machines: int):
        """Add max energy indicator line."""
        ax.axvline(max_energy, color=self.config.ENERGY_LINE_COLOR, 
                  linestyle='--', linewidth=1.2)
        ax.text(max_energy, num_machines - 0.5,
               ContentMessages.MAX_ENERGY_LABEL.format(value=max_energy),
               rotation=90, va='bottom', ha='left',
               color=self.config.ENERGY_LINE_COLOR,
               fontsize=self.config.AXIS_LABEL_FONT_SIZE,
               bbox=dict(boxstyle='round,pad=0.2', facecolor='white',
                        alpha=self.config.LEGEND_ALPHA))


class HistoryChartRenderer(BaseFigureRenderer):
    """Specialized renderer for history/convergence charts."""
    
    def create_history_figure(self, data: List[float], title: str, y_label: str) -> Optional[Any]:
        """Create history/convergence chart."""
        if not data:
            return None
        
        fig = self._create_figure(self.config.LINEAR_FIGURE_SIZE)
        if not fig:
            return None
        
        ax = fig.add_subplot(111)
        
        xs = list(range(len(data)))
        
        # Plot best-so-far as step function
        ax.step(xs, data, where='post', linewidth=1.5, 
               color=self.config.HISTORY_LINE_COLOR, label="Best so far")

        # Highlight improvement points
        if self.config.show_improvement_markers:
            self._add_improvement_markers(ax, data, xs)
        
        # Format axes
        self._format_history_axes(ax, title, y_label, data)
        
        fig.tight_layout()
        return fig
    
    def _add_improvement_markers(self, ax, data: List[float], xs: List[int]):
        """Add markers for improvement points."""
        change_x, change_y = [], []
        if data:
            prev_best = data[0]
            for i in range(1, len(data)):
                if data[i] < prev_best:
                    change_x.append(i)
                    change_y.append(data[i])
                    prev_best = data[i]
        
        if change_x:
            ax.scatter(change_x, change_y, s=25, 
                      color=self.config.IMPROVEMENT_COLOR, 
                      zorder=3, label="Improvement")
    
    def _format_history_axes(self, ax, title: str, y_label: str, data: List[float]):
        """Format axes for history chart."""
        ax.set_title(title)
        ax.set_xlabel("Epoch")
        ax.set_ylabel(y_label)
        
        # Format Y axis to avoid scientific notation
        try:
            ax.ticklabel_format(style='plain', axis='y', useOffset=False)
            ax.yaxis.set_major_formatter(StrMethodFormatter('{x:,.0f}'))
        except Exception as e:
            logger.warning(f"Could not format Y axis: {e}")
        
        # Always show grid for history charts
        ax.grid(True, alpha=0.3)
        
        if len(data) > 1:  # Only show legend if we have meaningful data
            ax.legend(loc="best")


# Factory function for creating renderers
def create_figure_renderers(config: PlotConfig) -> Tuple[GanttChartRenderer, HistoryChartRenderer]:
    """Create configured figure renderers."""
    gantt_renderer = GanttChartRenderer(config)
    history_renderer = HistoryChartRenderer(config)
    return gantt_renderer, history_renderer
