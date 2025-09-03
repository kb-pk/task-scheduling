"""
Widget factory for creating parameter input controls.
"""
import tkinter as tk
from tkinter import ttk
from typing import Dict, Any, List
from scheduler.Parameters import ParamDef, ParamValueTypes
from .CommonInterfaces import WidgetFactory, TooltipProvider
from ..config import UIConstants, ValidationMessages


class TkinterWidgetFactory(WidgetFactory):
    """Tkinter implementation of widget factory."""
    
    def __init__(self, tooltip_provider: TooltipProvider):
        self.tooltip_provider = tooltip_provider
    
    def create_boolean_widget(self, parent, param_def: ParamDef) -> Dict[str, Any]:
        """Create radio button widget for boolean parameter."""
        current_value = bool(param_def.get_value())
        var = tk.StringVar(value="true" if current_value else "false")
        
        frame = ttk.Frame(parent)
        rb_true = ttk.Radiobutton(frame, text="True", value="true", variable=var)
        rb_false = ttk.Radiobutton(frame, text="False", value="false", variable=var)
        
        rb_true.pack(side="left", padx=(0, UIConstants.WIDGET_SPACING))
        rb_false.pack(side="left")
        
        tooltip_text = self._build_tooltip_text(param_def)
        if tooltip_text:
            self.tooltip_provider.attach_tooltip(frame, tooltip_text)
        
        return {
            "var": var,
            "widget": frame,
            "spec": param_def,
            "type": "boolean"
        }
    
    def create_numeric_widget(self, parent, param_def: ParamDef) -> Dict[str, Any]:
        """Create entry widget for numeric parameter."""
        var = tk.StringVar(value=str(param_def.get_value()))
        widget = ttk.Entry(parent, textvariable=var, width=UIConstants.ENTRY_WIDTH)
        
        tooltip_text = self._build_tooltip_text(param_def)
        if tooltip_text:
            self.tooltip_provider.attach_tooltip(widget, tooltip_text)
        
        return {
            "var": var,
            "widget": widget,
            "spec": param_def,
            "type": "numeric"
        }
    
    def create_list_single_widget(self, parent, param_def: ParamDef) -> Dict[str, Any]:
        """Create radio button group for single-select list parameter."""
        sub_params: List[ParamDef] = param_def.get_value()
        group_var = tk.IntVar(value=0)  # Default to first option
        
        widgets_info = []
        sub_widgets = []
        
        for idx, sub_param in enumerate(sub_params):
            # Create radio button for selection
            rb = ttk.Radiobutton(parent, value=idx, variable=group_var, 
                               text=sub_param.get_name())
            
            # Create parameter widget
            if sub_param.get_ptype() == ParamValueTypes.BOOLEAN:
                sub_widget_info = self.create_boolean_widget(parent, sub_param)
            else:
                sub_widget_info = self.create_numeric_widget(parent, sub_param)
            
            widgets_info.append({
                "radio_button": rb,
                "param_widget": sub_widget_info,
                "index": idx
            })
            sub_widgets.append(sub_widget_info["widget"])
        
        return {
            "var": group_var,
            "widgets_info": widgets_info,
            "sub_widgets": sub_widgets,
            "spec": param_def,
            "type": "list_single"
        }
    
    def _build_tooltip_text(self, param_def: ParamDef) -> str:
        """Build tooltip text with description and bounds."""
        description = param_def.get_description() or ""
        bounds = ValidationMessages.format_bounds(
            param_def.get_min_value(),
            param_def.get_max_value()
        )
        return f"{description}{bounds}".strip()


class ParameterWidgetManager:
    """Manages parameter widgets and their state."""
    
    def __init__(self, widget_factory: WidgetFactory):
        self.widget_factory = widget_factory
        self.param_controls: Dict[str, Dict[str, Any]] = {}
        self.list_single_groups: List[Dict[str, Any]] = []
    
    def clear_all(self):
        """Clear all parameter controls."""
        self.param_controls.clear()
        self.list_single_groups.clear()
    
    def create_parameter_widgets(self, parent, param_defs: List[ParamDef]) -> int:
        """
        Create widgets for all parameter definitions.
        
        Args:
            parent: Parent widget
            param_defs: List of parameter definitions
            
        Returns:
            Next available row number
        """
        row = 0
        
        for spec in param_defs:
            ptype = spec.get_ptype()
            
            if ptype in (ParamValueTypes.INT, ParamValueTypes.FLOAT, ParamValueTypes.BOOLEAN):
                row = self._create_simple_parameter(parent, spec, row)
            elif ptype == ParamValueTypes.LIST_SINGLE:
                row = self._create_list_single_parameter(parent, spec, row)
        
        return row
    
    def _create_simple_parameter(self, parent, spec: ParamDef, row: int) -> int:
        """Create widget for simple parameter type."""
        # Create label
        ttk.Label(parent, text=f"{spec.get_name()}:").grid(
            row=row, column=0, sticky="w", 
            padx=(0, UIConstants.WIDGET_SPACING), 
            pady=UIConstants.SMALL_SPACING
        )
        
        # Create widget based on type
        if spec.get_ptype() == ParamValueTypes.BOOLEAN:
            widget_info = self.widget_factory.create_boolean_widget(parent, spec)
        else:
            widget_info = self.widget_factory.create_numeric_widget(parent, spec)
        
        # Grid the widget
        widget_info["widget"].grid(
            row=row, column=1, sticky="ew", 
            pady=UIConstants.SMALL_SPACING
        )
        
        # Store widget info
        self.param_controls[spec.get_name()] = widget_info
        
        return row + 1
    
    def _create_list_single_parameter(self, parent, spec: ParamDef, row: int) -> int:
        """Create widget for list single parameter type."""
        # Create label
        ttk.Label(parent, text=f"{spec.get_name()}:").grid(
            row=row, column=0, sticky="w",
            padx=(0, UIConstants.WIDGET_SPACING),
            pady=UIConstants.SMALL_SPACING
        )
        row += 1
        
        # Create list single widget
        widget_info = self.widget_factory.create_list_single_widget(parent, spec)
        
        # Grid all sub-widgets
        for sub_info in widget_info["widgets_info"]:
            # Grid radio button
            sub_info["radio_button"].grid(
                row=row, column=0, sticky="w",
                padx=(20, UIConstants.WIDGET_SPACING)
            )
            
            # Grid parameter widget
            sub_info["param_widget"]["widget"].grid(
                row=row, column=1, sticky="ew",
                pady=UIConstants.SMALL_SPACING
            )
            
            # Store in param controls with composite key
            param_name = f"{spec.get_name()}::{sub_info['param_widget']['spec'].get_name()}"
            self.param_controls[param_name] = sub_info["param_widget"]
            
            row += 1
        
        # Store group info
        self.list_single_groups.append(widget_info)
        
        # Setup state management
        self._setup_list_single_state_management(widget_info)
        
        return row
    
    def _setup_list_single_state_management(self, widget_info: Dict[str, Any]):
        """Setup state management for list single parameter group."""
        def apply_group_state(*_args):
            selected_index = widget_info["var"].get()
            
            for sub_info in widget_info["widgets_info"]:
                widget = sub_info["param_widget"]["widget"]
                is_selected = sub_info["index"] == selected_index
                state = "normal" if is_selected else "disabled"
                
                if isinstance(widget, ttk.Frame):
                    # Boolean widget - update all children
                    for child in widget.winfo_children():
                        child.configure(state=state)
                else:
                    # Entry widget
                    widget.configure(state=state)
        
        # Trace variable changes
        widget_info["var"].trace_add("write", apply_group_state)
        
        # Apply initial state after widget creation
        widget_info["widget"] = widget_info["widgets_info"][0]["radio_button"]  # For after() reference
        widget_info["widget"].after(UIConstants.WIDGET_READY_DELAY_MS, apply_group_state)
