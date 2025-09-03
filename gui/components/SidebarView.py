"""
Professional sidebar implementation with proper architecture and separation of concerns.
"""
import tkinter as tk
from tkinter import ttk
import tkinter.font as tkfont
import textwrap
from typing import Dict, Tuple, Callable, Any, Optional, List

from scheduler.ProgramState import ProgramState
from scheduler.methods.BaseMethod import BaseMethod
from scheduler.Parameters import ParamDef

from ..utils import UIEventHandler, SidebarController
from ..config import UIConstants, ValidationMessages, SidebarConfig
from ..utils import ParameterValidator
from ..utils import WidgetFactory
from ..ParamHint import TkinterTooltipProvider


class SidebarView(ttk.Frame):
    """View component of the sidebar - handles UI layout and events."""
    
    def __init__(self, parent: tk.Widget, config: SidebarConfig, **kwargs):
        super().__init__(parent, **kwargs)
        self.config = config
        self._controller: Optional[SidebarController] = None
        self._event_handler: Optional[UIEventHandler] = None
        
        # UI State
        self._algo_var = tk.StringVar()
        self._objective_var = tk.StringVar()
        
        # UI Components
        self._algo_combo: Optional[ttk.Combobox] = None
        self._start_btn: Optional[ttk.Button] = None
        self._desc_label: Optional[ttk.Label] = None
        self._desc_section: Optional[ttk.LabelFrame] = None
        self._params_area: Optional[ttk.Frame] = None
        
        self._setup_layout()
    
    def set_controller(self, controller: SidebarController):
        """Set the controller for this view."""
        self._controller = controller
    
    def set_event_handler(self, handler: UIEventHandler):
        """Set the event handler for this view."""
        self._event_handler = handler
    
    def _setup_layout(self):
        """Setup the main layout structure."""
        self.grid(row=0, column=0, sticky="nsw")
        self.columnconfigure(0, weight=1)
        self.grid_propagate(False)
        
        # Create main sections
        self._create_parameters_section()
        self._create_description_section()
        self._create_action_section()
        
        # Configure row weights
        self.rowconfigure(1, weight=0)  # Description section doesn't expand
    
    def _create_parameters_section(self):
        """Create the parameters configuration section."""
        section = ttk.LabelFrame(self, text="Parameters")
        section.grid(row=0, column=0, sticky="nsew")
        section.columnconfigure(1, weight=1)
        
        self._create_algorithm_selector(section)
        self._create_objective_selector(section)
        self._create_dynamic_parameters_area(section)
    
    def _create_algorithm_selector(self, parent: ttk.Widget):
        """Create algorithm selection dropdown."""
        ttk.Label(parent, text="Algorithm:").grid(
            row=0, column=0, sticky="w",
            padx=(UIConstants.STANDARD_PADDING, UIConstants.WIDGET_SPACING),
            pady=(UIConstants.STANDARD_PADDING, UIConstants.WIDGET_SPACING)
        )
        
        self._algo_combo = ttk.Combobox(
            parent, textvariable=self._algo_var, 
            state="readonly", values=[ValidationMessages.NO_METHODS_FOUND]
        )
        self._algo_combo.grid(
            row=0, column=1, sticky="ew",
            padx=(0, UIConstants.STANDARD_PADDING),
            pady=(UIConstants.STANDARD_PADDING, UIConstants.WIDGET_SPACING)
        )
        self._algo_combo.bind("<<ComboboxSelected>>", self._on_algorithm_changed)
    
    def _create_objective_selector(self, parent: ttk.Widget):
        """Create optimization objective selector."""
        ttk.Label(parent, text="Objective:").grid(
            row=1, column=0, sticky="w",
            padx=(UIConstants.STANDARD_PADDING, UIConstants.WIDGET_SPACING)
        )
        
        # Create frame for radio buttons
        obj_frame = ttk.Frame(parent)
        obj_frame.grid(row=1, column=1, sticky="ew", padx=(0, UIConstants.STANDARD_PADDING))
        
        rb_makespan = ttk.Radiobutton(
            obj_frame, text="Makespan", value="MAKESPAN",
            variable=self._objective_var, command=self._on_objective_changed
        )
        rb_energy = ttk.Radiobutton(
            obj_frame, text="Energy", value="ENERGY",
            variable=self._objective_var, command=self._on_objective_changed
        )
        
        rb_makespan.pack(side="left", padx=(0, UIConstants.WIDGET_SPACING))
        rb_energy.pack(side="left")
    
    def _create_dynamic_parameters_area(self, parent: ttk.Widget):
        """Create area for dynamic parameter widgets."""
        self._params_area = ttk.Frame(parent)
        self._params_area.grid(
            row=2, column=0, columnspan=2, sticky="new",
            padx=(UIConstants.STANDARD_PADDING, UIConstants.STANDARD_PADDING),
            pady=(UIConstants.WIDGET_SPACING, UIConstants.STANDARD_PADDING)
        )
        self._params_area.columnconfigure(1, weight=1)
    
    def _create_description_section(self):
        """Create the algorithm description section."""
        self._desc_section = ttk.LabelFrame(self, text="Description")
        self._desc_section.grid(
            row=1, column=0, sticky="ew",
            pady=(UIConstants.LARGE_SPACING, 0)
        )
        
        self._desc_label = ttk.Label(
            self._desc_section, text=ValidationMessages.NO_DESCRIPTION,
            justify="left", anchor="nw",
            font=tkfont.nametofont(UIConstants.DEFAULT_FONT)
        )
        self._desc_label.grid(
            row=0, column=0, sticky="ew",
            padx=(UIConstants.STANDARD_PADDING, UIConstants.STANDARD_PADDING),
            pady=(UIConstants.WIDGET_SPACING, UIConstants.STANDARD_PADDING)
        )
        
        self._desc_section.columnconfigure(0, weight=1)
        if self.config.wrap_descriptions:
            self._desc_section.bind("<Configure>", self._on_description_resize)
    
    def _create_action_section(self):
        """Create the action buttons section."""
        actions = ttk.Frame(self)
        actions.grid(
            row=2, column=0, sticky="ew",
            padx=(UIConstants.STANDARD_PADDING, UIConstants.STANDARD_PADDING),
            pady=(UIConstants.LARGE_SPACING, UIConstants.WIDGET_SPACING)
        )
        
        self._start_btn = ttk.Button(
            actions, text="Start", command=self._on_start_clicked
        )
        self._start_btn.pack(side="left")
    
    def _on_algorithm_changed(self, _event=None):
        """Handle algorithm selection change."""
        if self._event_handler:
            method = self._get_selected_method_from_ui()
            self._event_handler.on_algorithm_changed(method)
    
    def _on_objective_changed(self):
        """Handle objective selection change."""
        if self._event_handler:
            self._event_handler.on_objective_changed(self._objective_var.get())
    
    def _on_start_clicked(self):
        """Handle start button click."""
        if self._event_handler:
            self._event_handler.on_start_clicked()
    
    def _on_description_resize(self, _event=None):
        """Handle description section resize for text wrapping."""
        if not self._desc_section or not self._desc_label:
            return
        
        try:
            width = max(
                UIConstants.DESCRIPTION_MIN_WIDTH,
                self._desc_section.winfo_width() - UIConstants.DESCRIPTION_PADDING
            )
            self._desc_label.configure(wraplength=width)
        except tk.TclError:
            pass  # Widget might be destroyed
    
    def _get_selected_method_from_ui(self) -> Optional[BaseMethod]:
        """Get the currently selected method from UI state."""
        if self._controller:
            return self._controller.get_selected_method()
        return None
    
    # Public interface for controller
    def update_algorithm_list(self, algorithms: Dict[str, Tuple[str, BaseMethod]]):
        """Update the algorithm dropdown list."""
        if not self._algo_combo:
            print("DEBUG: No algorithm combo box available")
            return
        
        print(f"DEBUG: Updating algorithm list with {len(algorithms)} algorithms")
        values = list(algorithms.keys()) if algorithms else [ValidationMessages.NO_METHODS_FOUND]
        print(f"DEBUG: Setting combobox values to: {values}")
        self._algo_combo.configure(values=values)
        
        if values and values[0] != ValidationMessages.NO_METHODS_FOUND:
            self._algo_combo.current(0)
            print(f"DEBUG: Set current selection to: {values[0]}")
        else:
            print("DEBUG: No valid methods found, showing 'no methods found'")
    
    def update_objective(self, objective: str):
        """Update the selected objective."""
        self._objective_var.set(objective)
    
    def update_description(self, description: str):
        """Update the algorithm description."""
        if not self._desc_label:
            return
        
        text = textwrap.dedent(description.replace("\t", "    ")).strip()
        if not text:
            text = ValidationMessages.NO_DESCRIPTION
        
        self._desc_label.configure(text=text)
        self._on_description_resize()
    
    def clear_parameters_area(self):
        """Clear all parameter widgets."""
        if self._params_area:
            for child in self._params_area.winfo_children():
                child.destroy()
    
    def get_parameters_area(self) -> Optional[ttk.Frame]:
        """Get the parameters area for widget creation."""
        return self._params_area
    
    def set_start_button_enabled(self, enabled: bool):
        """Enable or disable the start button."""
        if self._start_btn:
            self._start_btn.configure(state="normal" if enabled else "disabled")
    
    def get_algorithm_var(self) -> tk.StringVar:
        """Get the algorithm selection variable."""
        return self._algo_var
    
    def get_objective_var(self) -> tk.StringVar:
        """Get the objective selection variable."""
        return self._objective_var
