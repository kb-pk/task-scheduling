"""
Sidebar controller - handles business logic and coordinates between view and model.
"""
from typing import Dict, Tuple, Optional, List, Callable
import logging

from scheduler.ProgramState import ProgramState
from scheduler.methods.BaseMethod import BaseMethod
from scheduler.Parameters import ParamDef

from ..utils import SidebarController, UIEventHandler
from ..config import SidebarConfig, ValidationMessages  
from ..utils.Validation import DefaultParameterValidator, ParameterApplier
from ..utils.WidgetFactory import TkinterWidgetFactory, ParameterWidgetManager
from .SidebarView import SidebarView
from ..ParamHint import TkinterTooltipProvider


logger = logging.getLogger(__name__)


class SidebarControllerImpl(SidebarController, UIEventHandler):
    """
    Controller implementation for sidebar component.
    Handles coordination between UI and business logic.
    """
    
    def __init__(
        self,
        parent,
        state: ProgramState,
        method_instances: Dict[str, BaseMethod],
        on_start_clicked: Callable,
        on_objective_changed: Callable,
        config: Optional[SidebarConfig] = None
    ):
        # Dependencies
        self.state = state
        self.method_instances = method_instances or {}
        self._on_start_clicked_callback = on_start_clicked
        self._on_objective_changed_callback = on_objective_changed
        self.config = config or SidebarConfig()
        
        # Algorithm mapping: display_name -> (key, method_instance)
        self._algo_map: Dict[str, Tuple[str, BaseMethod]] = {}
        
        # Components
        self.validator = DefaultParameterValidator()
        self.parameter_applier = ParameterApplier(self.validator)
        self.tooltip_provider = TkinterTooltipProvider()
        self.widget_factory = TkinterWidgetFactory(self.tooltip_provider)
        self.widget_manager = ParameterWidgetManager(self.widget_factory)
        
        # Create view
        self.view = SidebarView(parent, self.config, width=self.config.width)
        self.view.set_controller(self)
        self.view.set_event_handler(self)
        
        # Initialize
        self._initialize()
    
    def _initialize(self):
        """Initialize the sidebar with data."""
        self._build_algorithm_map()
        self._update_algorithm_list()
        self._set_initial_objective()
        
        # Trigger initial algorithm change after widgets are ready
        self.view.after(1, self._on_initial_algorithm_change)
    
    def _build_algorithm_map(self):
        """Build mapping of display names to method instances."""
        self._algo_map.clear()
        
        logger.debug(f"Building algorithm map with {len(self.method_instances)} methods")
        for key, instance in self.method_instances.items():
            logger.debug(f"Processing method {key}: {instance}")
            display_name = instance.get_name() or key
            
            # Handle duplicate display names
            if display_name in self._algo_map:
                display_name = f"{display_name} ({key})"
            
            self._algo_map[display_name] = (key, instance)
            logger.debug(f"Added to map: {display_name}")
        
        logger.debug(f"Final algorithm map: {list(self._algo_map.keys())}")
    
    def _update_algorithm_list(self):
        """Update the algorithm dropdown in the view."""
        self.view.update_algorithm_list(self._algo_map)
    
    def _set_initial_objective(self):
        """Set initial optimization objective from state."""
        try:
            if self.state and hasattr(self.state, 'scheduling'):
                current_obj = self.state.scheduling.get().name.upper()
                self.view.update_objective(current_obj)
            else:
                self.view.update_objective("MAKESPAN")
        except Exception as e:
            logger.warning(f"Could not set initial objective: {e}")
            self.view.update_objective("MAKESPAN")
    
    def _on_initial_algorithm_change(self):
        """Handle initial algorithm change after UI is ready."""
        try:
            # Ensure we have a default selection if nothing is selected
            if not self.view.get_algorithm_var().get() and self._algo_map:
                first_algo = next(iter(self._algo_map.keys()))
                logger.debug(f"Setting default algorithm to: {first_algo}")
                self.view.get_algorithm_var().set(first_algo)
            
            self.on_algorithm_changed(self.get_selected_method())
        except Exception as e:
            logger.error(f"Error in initial algorithm change: {e}")
    
    # SidebarController interface implementation
    def get_selected_method(self) -> Optional[BaseMethod]:
        """Get currently selected method instance."""
        display_name = self.view.get_algorithm_var().get()
        logger.debug(f"Getting selected method for display name: '{display_name}'")
        logger.debug(f"Available algorithms in map: {list(self._algo_map.keys())}")
        
        entry = self._algo_map.get(display_name)
        if entry:
            method = entry[1]
            logger.debug(f"Found method: {method.get_name() if method else 'None'}")
            return method
        else:
            logger.warning(f"No method found for display name: '{display_name}'")
            return None
    
    def get_objective(self) -> str:
        """Get selected optimization objective."""
        return self.view.get_objective_var().get()
    
    def apply_parameters(self, method: BaseMethod) -> List[str]:
        """Apply UI parameter values to method instance."""
        return self.parameter_applier.apply_parameters_to_method(
            method,
            self.widget_manager.param_controls,
            self.widget_manager.list_single_groups,
            self.state
        )
    
    def set_start_button_enabled(self, enabled: bool) -> None:
        """Enable or disable start button."""
        self.view.set_start_button_enabled(enabled)
    
    # UIEventHandler interface implementation
    def on_algorithm_changed(self, method: Optional[BaseMethod]) -> None:
        """Handle algorithm selection change."""
        try:
            self._clear_parameter_widgets()
            
            if not method:
                self.view.update_description("")
                return
            
            self._update_method_description(method)
            self._create_parameter_widgets(method)
            
            logger.debug(f"Algorithm changed to: {method.get_name()}")
            
        except Exception as e:
            logger.error(f"Error handling algorithm change: {e}")
    
    def on_objective_changed(self, objective: str) -> None:
        """Handle optimization objective change."""
        try:
            self._on_objective_changed_callback(objective)
            logger.debug(f"Objective changed to: {objective}")
        except Exception as e:
            logger.error(f"Error handling objective change: {e}")
    
    def on_start_clicked(self) -> None:
        """Handle start button click."""
        try:
            self._on_start_clicked_callback()
        except Exception as e:
            logger.error(f"Error handling start click: {e}")
    
    # Private methods
    def _clear_parameter_widgets(self):
        """Clear all parameter widgets from the UI."""
        self.view.clear_parameters_area()
        self.widget_manager.clear_all()
    
    def _update_method_description(self, method: BaseMethod):
        """Update the description display for the selected method."""
        try:
            description = method.get_description() or ""
            self.view.update_description(description)
        except Exception as e:
            logger.warning(f"Could not get method description: {e}")
            self.view.update_description("")
    
    def _create_parameter_widgets(self, method: BaseMethod):
        """Create parameter widgets for the selected method."""
        try:
            param_defs = method.get_parameters()
            if not param_defs:
                return
            
            params_area = self.view.get_parameters_area()
            if not params_area:
                logger.error("Parameters area not available")
                return
            
            self.widget_manager.create_parameter_widgets(params_area, param_defs)
            
        except Exception as e:
            logger.error(f"Error creating parameter widgets: {e}")
    
    def cleanup(self):
        """Cleanup resources."""
        try:
            self.tooltip_provider.cleanup()
        except Exception as e:
            logger.warning(f"Error during cleanup: {e}")


# Factory function for creating sidebar
def create_sidebar(
    parent,
    state: ProgramState,
    method_instances: Dict[str, BaseMethod],
    on_start_clicked: Callable,
    on_objective_changed: Callable,
    config: Optional[SidebarConfig] = None
) -> SidebarControllerImpl:
    """
    Factory function to create a fully configured sidebar.
    
    Args:
        parent: Parent widget
        state: Program state
        method_instances: Available optimization methods
        on_start_clicked: Callback for start button
        on_objective_changed: Callback for objective change
        config: Optional configuration
        
    Returns:
        Configured sidebar controller
    """
    return SidebarControllerImpl(
        parent, state, method_instances,
        on_start_clicked, on_objective_changed, config
    )
