import tkinter as tk
from tkinter import ttk
import tkinter.font as tkfont
import textwrap
from typing import Dict, Tuple, Callable, Any

from scheduler.ProgramState import ProgramState
from scheduler.methods.BaseMethod import BaseMethod
from scheduler.Parameters import ParamDef, ParamValueTypes
from . import ParamHint

class Sidebar(ttk.Frame):
    def __init__(self, parent, state: ProgramState, method_instances: Dict[str, BaseMethod], on_start_clicked: Callable, on_objective_changed: Callable, **kwargs):
        super().__init__(parent, **kwargs)
        self.state = state
        self.method_instances = method_instances
        self._on_start_clicked_callback = on_start_clicked
        self._on_objective_changed_callback = on_objective_changed

        self.grid(row=0, column=0, sticky="nsw")
        self.columnconfigure(0, weight=1)
        
        self.grid_propagate(False)

        self._param_controls: Dict[str, Dict[str, Any]] = {}
        self._list_single_groups: list[Dict[str, Any]] = []
        self._algo_map: Dict[str, Tuple[str, BaseMethod]] = {}

        self._build_controls()
        self.after(1, self._on_algo_changed) # Use `after` to ensure widgets are ready

    def get_selected_method(self) -> BaseMethod | None:
        display = self._algo_var.get()
        entry = self._algo_map.get(display)
        return entry[1] if entry else None

    def get_objective(self) -> str:
        return self._objective_var.get()

    def apply_parameters_to_method(self, method: BaseMethod) -> list[str]:
        """Read widgets and set values on the method's ParamDef instances. Returns a list of warnings."""
        warnings = []
        for key, ctrl in self._param_controls.items():
            spec: ParamDef = ctrl["spec"]
            var = ctrl["var"]
            val = var.get()
            try:
                spec.set_value(val)
            except Exception as e:
                warnings.append(f"Invalid value for '{key}': {e}")

        try:
            if self._list_single_groups:
                sel = self._list_single_groups[0]["var"].get()
                self.state.stop_criterion.set(self.state.stop_criterion.State(sel))
        except Exception as e:
            warnings.append(f"Could not set stop criterion: {e}")
        
        return warnings
    
    def enable_start_button(self):
        """Enables the start button."""
        if hasattr(self, '_start_btn'):
            self._start_btn.config(state="normal")

    def disable_start_button(self):
        """Disables the start button."""
        if hasattr(self, '_start_btn'):
            self._start_btn.config(state="disabled")

    def _build_controls(self):
        # Section: Parameters
        section = ttk.LabelFrame(self, text="Parameters")
        section.grid(row=0, column=0, sticky="nsew")
        section.columnconfigure(1, weight=1)

        # Algorithm dropdown
        ttk.Label(section, text="Algorithm:").grid(row=0, column=0, sticky="w", padx=(10, 6), pady=(10, 6))
        self._algo_var = tk.StringVar()
        for key, inst in (self.method_instances or {}).items():
            display = inst.get_name() or key
            if display in self._algo_map:
                display = f"{display} ({key})"
            self._algo_map[display] = (key, inst)
        
        values = list(self._algo_map.keys()) if self._algo_map else ["<no methods found>"]
        self._algo_combo = ttk.Combobox(section, textvariable=self._algo_var, state="readonly", values=values)
        if values:
            self._algo_combo.current(0)
        self._algo_combo.grid(row=0, column=1, sticky="ew", padx=(0, 10), pady=(10, 6))
        self._algo_combo.bind("<<ComboboxSelected>>", self._on_algo_changed)

        # Optimization objective
        ttk.Label(section, text="Objective:").grid(row=1, column=0, sticky="w", padx=(10, 6))
        current_obj = self.state.scheduling.get().name.upper() if self.state else "MAKESPAN"
        self._objective_var = tk.StringVar(value=current_obj)
        rb_ms = ttk.Radiobutton(section, text="Makespan", value="MAKESPAN", variable=self._objective_var, command=self._on_objective_changed)
        rb_en = ttk.Radiobutton(section, text="Energy", value="ENERGY", variable=self._objective_var, command=self._on_objective_changed)
        rb_ms.grid(row=1, column=1, sticky="w", padx=(0, 6))
        rb_en.grid(row=1, column=1, sticky="e", padx=(0, 10))

        # Dynamic parameters area
        self._params_area = ttk.Frame(section)
        self._params_area.grid(row=2, column=0, columnspan=2, sticky="new", padx=(10, 10), pady=(6, 10))
        self._params_area.columnconfigure(1, weight=1)

        # Description block
        self._desc_section = ttk.LabelFrame(self, text="Description")
        self._desc_section.grid(row=1, column=0, sticky="ew", pady=(8, 0))
        self._desc_label = ttk.Label(self._desc_section, text="", justify="left", anchor="nw", font=tkfont.nametofont("TkDefaultFont"))
        self._desc_label.grid(row=0, column=0, sticky="ew", padx=(10, 10), pady=(6, 10))
        self._desc_section.columnconfigure(0, weight=1)
        self._desc_section.bind("<Configure>", self._resize_description_wrap)

        # Action bar
        actions = ttk.Frame(self)
        actions.grid(row=2, column=0, sticky="ew", padx=(10, 10), pady=(8, 6))
        self._start_btn = ttk.Button(actions, text="Start", command=self._on_start_clicked_callback)
        self._start_btn.pack(side="left")

        self.rowconfigure(1, weight=0)

    def _on_objective_changed(self):
        self._on_objective_changed_callback(self.get_objective())

    def _on_algo_changed(self, _event=None):
        for child in self._params_area.winfo_children():
            child.destroy()
        self._param_controls.clear()
        self._list_single_groups = []

        method = self.get_selected_method()
        if not method:
            self._update_description(None)
            return

        self._update_description(method)

        param_defs = method.get_parameters()
        row = 0
        for spec in param_defs:
            ptype = spec.get_ptype()
            if ptype in (ParamValueTypes.INT, ParamValueTypes.FLOAT, ParamValueTypes.BOOLEAN):
                self._create_simple_param_widget(spec, row)
                row += 1
            elif ptype == ParamValueTypes.LIST_SINGLE:
                row = self._create_list_single_param_widget(spec, row)

    def _update_description(self, method: BaseMethod | None):
        text = ""
        if method:
            try:
                text = method.get_description() or ""
            except Exception:
                pass
        
        text = textwrap.dedent(text.replace("\t", "    ")).strip() or "(no description)"
        self._desc_label.configure(text=text)
        self._resize_description_wrap()

    def _resize_description_wrap(self, _event=None):
        try:
            w = max(100, self._desc_section.winfo_width() - 20)
            self._desc_label.configure(wraplength=w)
        except Exception:
            pass
    
    def _create_simple_param_widget(self, spec: ParamDef, row: int):
        ttk.Label(self._params_area, text=f"{spec.get_name()}:").grid(row=row, column=0, sticky="w", padx=(0, 6), pady=3)
        
        ptype = spec.get_ptype()
        if ptype == ParamValueTypes.BOOLEAN:
            var = tk.StringVar(value="true" if bool(spec.get_value()) else "false")
            frame = ttk.Frame(self._params_area)
            rb_true = ttk.Radiobutton(frame, text="True", value="true", variable=var)
            rb_false = ttk.Radiobutton(frame, text="False", value="false", variable=var)
            rb_true.pack(side="left", padx=(0, 6))
            rb_false.pack(side="left")
            widget = frame
        else: # INT, FLOAT
            var = tk.StringVar(value=str(spec.get_value()))
            widget = ttk.Entry(self._params_area, textvariable=var, width=14)
        
        widget.grid(row=row, column=1, sticky="ew", pady=3)

        bounds = []
        if spec.get_min_value() is not None: bounds.append(f"min={spec.get_min_value()}")
        if spec.get_max_value() is not None: bounds.append(f"max={spec.get_max_value()}")
        tip_text = spec.get_description() or ""
        if bounds: tip_text = f"{tip_text} ({', '.join(bounds)})"
        ParamHint.attach(widget, tip_text)

        self._param_controls[spec.get_name()] = {"var": var, "widget": widget, "spec": spec}

    def _create_list_single_param_widget(self, spec: ParamDef, row: int) -> int:
        ttk.Label(self._params_area, text=f"{spec.get_name()}:").grid(row=row, column=0, sticky="w", padx=(0, 6), pady=3)
        row += 1
        
        sub_params: list[ParamDef] = spec.get_value()
        group_var = tk.IntVar()
        try:
            group_var.set(self.state.stop_criterion.get().value)
        except Exception:
            group_var.set(0)

        sub_widgets = []
        for idx, sub in enumerate(sub_params):
            rb = ttk.Radiobutton(self._params_area, value=idx, variable=group_var, text=sub.get_name())
            rb.grid(row=row, column=0, sticky="w", padx=(20, 6))

            if sub.get_ptype() == ParamValueTypes.BOOLEAN:
                svar = tk.StringVar(value="true" if bool(sub.get_value()) else "false")
                frame = ttk.Frame(self._params_area)
                sw_true = ttk.Radiobutton(frame, text="True", value="true", variable=svar)
                sw_false = ttk.Radiobutton(frame, text="False", value="false", variable=svar)
                sw_true.pack(side="left", padx=(0, 6))
                sw_false.pack(side="left")
                sw = frame
            else:
                svar = tk.StringVar(value=str(sub.get_value()))
                sw = ttk.Entry(self._params_area, textvariable=svar, width=14)
            
            sw.grid(row=row, column=1, sticky="ew", pady=3)

            bounds = []
            if sub.get_min_value() is not None: bounds.append(f"min={sub.get_min_value()}")
            if sub.get_max_value() is not None: bounds.append(f"max={sub.get_max_value()}")
            tip_text = sub.get_description() or ""
            if bounds: tip_text = f"{tip_text} ({', '.join(bounds)})"
            ParamHint.attach(sw, tip_text)

            self._param_controls[f"{spec.get_name()}::{sub.get_name()}"] = {"var": svar, "widget": sw, "spec": sub}
            sub_widgets.append(sw)
            row += 1

        def _apply_group_state(*_args):
            sel = group_var.get()
            for i, w in enumerate(sub_widgets):
                state = "normal" if i == sel else "disabled"
                if isinstance(w, ttk.Frame):
                    for child in w.winfo_children():
                        child.configure(state=state)
                else:
                    w.configure(state=state)
        
        group_var.trace_add("write", _apply_group_state)
        self.after(1, _apply_group_state)

        self._list_single_groups.append({"spec": spec, "var": group_var, "widgets": sub_widgets})
        return row