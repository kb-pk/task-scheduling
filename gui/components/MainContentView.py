"""
Professional main content view with proper separation of concerns.
"""
import tkinter as tk
from tkinter import ttk
from typing import Dict, Any, Optional
import logging

try:
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    FigureCanvasTkAgg = None

from ..utils import PlotManager, LogHandler
from ..config import ContentConfig, ContentMessages, PlotConfig
from ..rendering import GanttChartRenderer, HistoryChartRenderer, BaseFigureRenderer
from ..rendering.FigureRenderers import create_figure_renderers


logger = logging.getLogger(__name__)


class MainContentView(ttk.Frame, PlotManager, LogHandler):
    """
    Professional main content view with clean architecture.
    Handles visualization of optimization results and diagnostics.
    """
    
    def __init__(self, parent: tk.Widget, config: Optional[ContentConfig] = None):
        super().__init__(parent, padding=(10, 10))
        
        self.config = config or ContentConfig()
        self.plot_config = PlotConfig()
        
        # Create renderers
        self.gantt_renderer, self.history_renderer = create_figure_renderers(self.plot_config)
        
        # UI components
        self._main_notebook: Optional[ttk.Notebook] = None
        self._gantt_notebook: Optional[ttk.Notebook] = None
        self._linear_notebook: Optional[ttk.Notebook] = None
        self._diagnostics_text: Optional[tk.Text] = None
        
        # Tab references
        self._tabs: Dict[str, ttk.Frame] = {}
        
        self._setup_layout()
        self._configure_grid()
    
    def _setup_layout(self):
        """Setup the main layout structure."""
        self._create_main_notebook()
        self._create_gantt_section()
        self._create_linear_section()
        self._create_diagnostics_section()
    
    def _configure_grid(self):
        """Configure grid layout."""
        self.grid(row=0, column=1, sticky="nsew")
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
    
    def _create_main_notebook(self):
        """Create the main notebook widget."""
        self._main_notebook = ttk.Notebook(self)
        self._main_notebook.grid(row=0, column=0, sticky="nsew")
    
    def _create_gantt_section(self):
        """Create Gantt chart section with sub-tabs."""
        gantt_frame = ttk.Frame(self._main_notebook)
        self._main_notebook.add(gantt_frame, text=ContentMessages.GANTT_TAB)
        
        self._gantt_notebook = ttk.Notebook(gantt_frame)
        self._gantt_notebook.pack(fill="both", expand=True)
        
        # Create Gantt sub-tabs
        makespan_frame = ttk.Frame(self._gantt_notebook)
        energy_frame = ttk.Frame(self._gantt_notebook)
        
        self._gantt_notebook.add(makespan_frame, text=ContentMessages.MAKESPAN_SUBTAB)
        self._gantt_notebook.add(energy_frame, text=ContentMessages.ENERGY_SUBTAB)
        
        self._tabs["gantt_makespan"] = makespan_frame
        self._tabs["gantt_energy"] = energy_frame
        
        # Add placeholder labels if matplotlib is not available
        if not MATPLOTLIB_AVAILABLE:
            self._add_placeholder_label(makespan_frame)
            self._add_placeholder_label(energy_frame)
    
    def _create_linear_section(self):
        """Create linear/history chart section with sub-tabs."""
        linear_frame = ttk.Frame(self._main_notebook)
        self._main_notebook.add(linear_frame, text=ContentMessages.LINEAR_TAB)
        
        self._linear_notebook = ttk.Notebook(linear_frame)
        self._linear_notebook.pack(fill="both", expand=True)
        
        # Create linear sub-tabs
        makespan_frame = ttk.Frame(self._linear_notebook)
        energy_frame = ttk.Frame(self._linear_notebook)
        
        self._linear_notebook.add(makespan_frame, text=ContentMessages.MAKESPAN_SUBTAB)
        self._linear_notebook.add(energy_frame, text=ContentMessages.ENERGY_SUBTAB)
        
        self._tabs["linear_makespan"] = makespan_frame
        self._tabs["linear_energy"] = energy_frame
        
        # Add placeholder labels if matplotlib is not available
        if not MATPLOTLIB_AVAILABLE:
            self._add_placeholder_label(makespan_frame)
            self._add_placeholder_label(energy_frame)
    
    def _create_diagnostics_section(self):
        """Create diagnostics/logging section."""
        diag_frame = ttk.Frame(self._main_notebook)
        self._main_notebook.add(diag_frame, text=ContentMessages.DIAGNOSTICS_TAB)
        
        # Create text widget with scrollbar
        self._diagnostics_text = tk.Text(
            diag_frame, 
            wrap="word", 
            state="disabled", 
            height=10,
            font=(self.config.default_font_family, 9)
        )
        
        scrollbar = ttk.Scrollbar(diag_frame, orient="vertical", 
                                command=self._diagnostics_text.yview)
        self._diagnostics_text.configure(yscrollcommand=scrollbar.set)
        
        # Grid the components
        scrollbar.pack(side="right", fill="y")
        self._diagnostics_text.pack(side="left", fill="both", expand=True)
        
        self._tabs["diagnostics"] = diag_frame
    
    def _add_placeholder_label(self, parent: ttk.Frame):
        """Add placeholder label when matplotlib is not available."""
        label = ttk.Label(parent, text=ContentMessages.MATPLOTLIB_NOT_FOUND)
        label.pack(pady=20)
    
    # PlotManager interface implementation
    def clear_all_plots(self) -> None:
        """Clear all existing plots."""
        plot_tabs = ["gantt_makespan", "gantt_energy", "linear_makespan", "linear_energy"]
        
        for tab_name in plot_tabs:
            tab_frame = self._tabs.get(tab_name)
            if tab_frame:
                self._clear_frame_widgets(tab_frame)
    
    def render_solution_plots(self, solution_data: Dict[str, Any]) -> None:
        """Render plots for solution data."""
        if self.config.auto_clear_on_new_data:
            self.clear_all_plots()
        
        try:
            # Render Gantt charts
            self._render_gantt_charts(solution_data)
            
            # Render history charts
            self._render_history_charts(solution_data)
            
            logger.info("Successfully rendered solution plots")
            
        except Exception as e:
            logger.error(f"Error rendering solution plots: {e}")
            self.log_message(f"Error rendering plots: {e}")
    
    # LogHandler interface implementation
    def log_message(self, message: str) -> None:
        """Log a message to the diagnostics area."""
        if not self._diagnostics_text:
            return
        
        try:
            self._diagnostics_text.configure(state="normal")
            self._diagnostics_text.insert("end", message)
            self._diagnostics_text.configure(state="disabled")
            self._diagnostics_text.see("end")
            
            # Limit the number of lines to prevent memory issues
            self._limit_diagnostics_lines()
            
        except tk.TclError as e:
            logger.warning(f"Could not log message to diagnostics: {e}")
    
    # Private methods
    def _clear_frame_widgets(self, frame: ttk.Frame):
        """Clear all widgets from a frame."""
        for widget in frame.winfo_children():
            widget.destroy()
    
    def _render_gantt_charts(self, solution_data: Dict[str, Any]):
        """Render Gantt charts for different views."""
        if not MATPLOTLIB_AVAILABLE or not self.gantt_renderer:
            return
        
        # Makespan Gantt
        makespan_fig = self.gantt_renderer.create_gantt_figure(solution_data, "makespan")
        self._display_figure(self._tabs["gantt_makespan"], makespan_fig)
        
        # Energy Gantt
        energy_fig = self.gantt_renderer.create_gantt_figure(solution_data, "energy")
        self._display_figure(self._tabs["gantt_energy"], energy_fig)
    
    def _render_history_charts(self, solution_data: Dict[str, Any]):
        """Render history/convergence charts."""
        if not MATPLOTLIB_AVAILABLE or not self.history_renderer:
            return
        
        # Makespan history
        makespan_history = solution_data.get("history_makespan", [])
        if makespan_history:
            makespan_fig = self.history_renderer.create_history_figure(
                makespan_history, "Makespan History", "Makespan"
            )
            self._display_figure(self._tabs["linear_makespan"], makespan_fig)
        
        # Energy history
        energy_history = solution_data.get("history_energy", [])
        if energy_history:
            energy_fig = self.history_renderer.create_history_figure(
                energy_history, "Energy History", "Energy"
            )
            self._display_figure(self._tabs["linear_energy"], energy_fig)
    
    def _display_figure(self, parent: ttk.Frame, figure: Any):
        """Display a matplotlib figure in the given frame."""
        if not figure or not MATPLOTLIB_AVAILABLE:
            no_data_label = ttk.Label(parent, text=ContentMessages.NO_DATA_MESSAGE)
            no_data_label.pack(pady=20)
            return
        
        try:
            canvas = FigureCanvasTkAgg(figure, master=parent)
            canvas.draw()
            canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        except Exception as e:
            logger.error(f"Error displaying figure: {e}")
            error_label = ttk.Label(parent, text=f"Error displaying plot: {e}")
            error_label.pack(pady=20)
    
    def _limit_diagnostics_lines(self):
        """Limit the number of lines in diagnostics to prevent memory issues."""
        if not self._diagnostics_text:
            return
        
        try:
            line_count = int(self._diagnostics_text.index('end-1c').split('.')[0])
            if line_count > self.config.diagnostics_max_lines:
                excess_lines = line_count - self.config.diagnostics_max_lines
                self._diagnostics_text.configure(state="normal")
                self._diagnostics_text.delete('1.0', f'{excess_lines}.0')
                self._diagnostics_text.configure(state="disabled")
        except Exception as e:
            logger.warning(f"Could not limit diagnostics lines: {e}")
    
    def cleanup(self):
        """Cleanup resources."""
        try:
            self.clear_all_plots()
        except Exception as e:
            logger.warning(f"Error during cleanup: {e}")


# Backward compatibility alias
class MainContent(MainContentView):
    """Backward compatibility alias."""
    
    def __init__(self, parent: tk.Widget, **kwargs):
        config = ContentConfig()
        super().__init__(parent, config)
    
    def log(self, message: str):
        """Backward compatibility method."""
        self.log_message(message)
    
    def clear_plots(self):
        """Backward compatibility method."""
        self.clear_all_plots()
    
    def render_plots(self, solution_data: Dict[str, Any]):
        """Backward compatibility method."""
        self.render_solution_plots(solution_data)
