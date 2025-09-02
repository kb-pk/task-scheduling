import tkinter as tk
from tkinter import ttk
import tkinter.font as tkfont
from typing import Dict, Tuple
import textwrap

from scheduler.Registry import UIRegistrator
from scheduler.UI import UI

from . import tooltip
# Descriptions now come from each method instance directly
import scheduler.Common as Common
from scheduler.ProgramState import ProgramState
from scheduler.methods.BaseMethod import BaseMethod
from scheduler.Parameters import ParamDef, ParamValueTypes

# Optional matplotlib embedding for higher-quality plots
try:
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    from matplotlib.figure import Figure
    _HAS_MPL = True
except Exception:
    _HAS_MPL = False

# Helper at module scope to update description text safely from method.get_description()
def _refresh_description_for(app) -> None:
    try:
        display = app._algo_var.get()
        entry = app._algo_map.get(display)
        text = ""
        if entry:
            _, method = entry
            try:
                text = method.get_description() or ""
            except Exception:
                text = ""
        # Normalize whitespace from triple-quoted strings and tabs for clean rendering
        text = textwrap.dedent((text or "").replace("\t", "    ")).strip() or "(no description)"
        try:
            app._desc_label.configure(text=text)
        except Exception:
            pass
    except Exception:
        # Silently ignore if being called during teardown/init
        pass
@UIRegistrator.register_class
class GUI(tk.Tk, UI):
    def __init__(self, state: ProgramState, t, method_instances: Dict[str, BaseMethod]) -> None:
        # Initialize UI base fields expected by scheduler.UI.UI
        self.state = state
        self.T = t
        self.method_instances = method_instances

        super().__init__()
        self.title("Task Scheduling")
        # Center the window at half of the screen size
        self.after(0, self._center_initial_window)

        # Root layout: left sidebar for parameters, right area for content/plots
        self.columnconfigure(0, weight=0)  # sidebar
        self.columnconfigure(1, weight=1)  # main
        self.rowconfigure(0, weight=1)

        SIDEBAR_WIDTH = 360
        self.sidebar = ttk.Frame(self, padding=(10, 10), width=SIDEBAR_WIDTH)
        self.sidebar.grid(row=0, column=0, sticky="nsw")
        # allow dynamic height
        try:
            self.sidebar.grid_propagate(False)
        except Exception:
            pass
        try:
            self.columnconfigure(0, minsize=SIDEBAR_WIDTH)
        except Exception:
            pass
        try:
            self.sidebar.columnconfigure(0, weight=1)
        except Exception:
            pass

        self.main_area = ttk.Frame(self, padding=(10, 10))
        self.main_area.grid(row=0, column=1, sticky="nsew")
        self.main_area.columnconfigure(0, weight=1)
        self.main_area.rowconfigure(0, weight=1)

        # Build the parameter controls
        self._build_sidebar()

    def _center_initial_window(self) -> None:
        try:
            sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
            w = max(800, int(sw * 0.5))
            h = max(600, int(sh * 0.5))
            x = max(0, (sw - w) // 2)
            y = max(0, (sh - h) // 2)
            self.geometry(f"{w}x{h}+{x}+{y}")
        except Exception:
            pass

    # UI interface hooks
    def log(self, message):
        self._append_diag(f"{message}\n")

    def start(self):
        # Start the app
        self.mainloop()

    def _build_sidebar(self) -> None:
        # Section: Algorithm selection
        section = ttk.LabelFrame(self.sidebar, text="Parameters")
        section.grid(row=0, column=0, sticky="nsew")

        # Algorithm dropdown
        ttk.Label(section, text="Algorithm:").grid(row=0, column=0, sticky="w", padx=(10, 6), pady=(10, 6))

        self._algo_var = tk.StringVar()
        # Build display map from provided method instances
        # Map display name -> (registry_key, method_instance)
        self._algo_map: Dict[str, Tuple[str, BaseMethod]] = {}
        for key, inst in (self.method_instances or {}).items():
            display = inst.get_name() or key
            # Ensure unique display names by appending key if duplicated
            if display in self._algo_map:
                display = f"{display} ({key})"
            self._algo_map[display] = (key, inst)

        values = list(self._algo_map.keys()) if self._algo_map else ["<no methods found>"]
        self._algo_combo = ttk.Combobox(section, textvariable=self._algo_var, state="readonly", values=values)
        if values:
            self._algo_combo.current(0)
        self._algo_combo.grid(row=0, column=1, sticky="ew", padx=(0, 10), pady=(10, 6))
        self._algo_combo.bind("<<ComboboxSelected>>", self._on_algo_changed)
        section.columnconfigure(1, weight=1)

        # Optimization objective
        ttk.Label(section, text="Objective:").grid(row=1, column=0, sticky="w", padx=(10, 6))
        # Initialize from ProgramState
        current_obj = self.state.scheduling.get().name.upper() if self.state else "MAKESPAN"
        self._objective_var = tk.StringVar(value=current_obj)
        self._rb_ms = ttk.Radiobutton(
            section,
            text="Makespan",
            value="MAKESPAN",
            variable=self._objective_var,
            command=self._on_objective_changed,
        )
        self._rb_en = ttk.Radiobutton(
            section,
            text="Energy",
            value="ENERGY",
            variable=self._objective_var,
            command=self._on_objective_changed,
        )
        # radios in the same row, right of label
        self._rb_ms.grid(row=1, column=1, sticky="w", padx=(0, 6))
        self._rb_en.grid(row=1, column=1, sticky="e", padx=(0, 10))

        # Dynamic parameters area
        self._params_area = ttk.Frame(section)
        self._params_area.grid(row=2, column=0, columnspan=2, sticky="new", padx=(10, 10), pady=(6, 10))
        self._param_controls = {}

        # Description block as its own section under Parameters
        self._desc_section = ttk.LabelFrame(self.sidebar, text="Description")
        self._desc_section.grid(row=1, column=0, sticky="ew", pady=(8, 0))
        # Plain text label with word wrap; wraplength bound to section width
        self._desc_label = ttk.Label(self._desc_section, text="", justify="left", anchor="nw")
        # Set a readable default font (TkDefaultFont)
        try:
            self._desc_label.configure(font=tkfont.nametofont("TkDefaultFont"))
        except Exception:
            pass
        self._desc_label.grid(row=0, column=0, sticky="ew", padx=(10, 10), pady=(6, 10))
        self._desc_section.columnconfigure(0, weight=1)
        try:
            self._desc_section.grid_propagate(True)
        except Exception:
            pass
        # Keep label wraplength in sync with available width
        def _resize_wrap(_event=None):
            try:
                w = max(100, self._desc_section.winfo_width() - 20)
                self._desc_label.configure(wraplength=w)
            except Exception:
                pass
        self._desc_section.bind("<Configure>", _resize_wrap)
        self.after(0, _resize_wrap)

        # Bottom action bar with Start button placed below description
        actions = ttk.Frame(self.sidebar)
        actions.grid(row=2, column=0, sticky="ew", padx=(10, 10), pady=(8, 6))
        self._start_btn = ttk.Button(actions, text="Start", command=self._on_start_clicked)
        self._start_btn.pack(side="left")
        # Sidebar growth rules
        # Do not expand description vertically; keep natural height
        try:
            self.sidebar.rowconfigure(1, weight=0)
        except Exception:
            pass

        # Main notebook with tabs: Gantt, Linear, Diagnostics
        self._main_nb = ttk.Notebook(self.main_area)
        self._main_nb.grid(row=0, column=0, sticky="nsew")

        # Gantt tab with nested Energy/Makespan tabs
        self._tab_gantt = ttk.Frame(self._main_nb)
        self._main_nb.add(self._tab_gantt, text="Gantt")
        self._nb_gantt = ttk.Notebook(self._tab_gantt)
        self._nb_gantt.pack(fill="both", expand=True)
        self._gantt_energy = ttk.Frame(self._nb_gantt)
        self._gantt_makespan = ttk.Frame(self._nb_gantt)
        self._nb_gantt.add(self._gantt_energy, text="Energy")
        self._nb_gantt.add(self._gantt_makespan, text="Makespan")
        if not _HAS_MPL:
            ttk.Label(self._gantt_energy, text="Matplotlib not installed").pack(padx=10, pady=10)
            ttk.Label(self._gantt_makespan, text="Matplotlib not installed").pack(padx=10, pady=10)

        # Linear tab with nested Energy/Makespan tabs
        self._tab_linear = ttk.Frame(self._main_nb)
        self._main_nb.add(self._tab_linear, text="Linear")
        self._nb_linear = ttk.Notebook(self._tab_linear)
        self._nb_linear.pack(fill="both", expand=True)
        self._linear_energy = ttk.Frame(self._nb_linear)
        self._linear_makespan = ttk.Frame(self._nb_linear)
        self._nb_linear.add(self._linear_energy, text="Energy")
        self._nb_linear.add(self._linear_makespan, text="Makespan")
        # Linear plots rendered after run

        # Diagnostics tab
        self._tab_diag = ttk.Frame(self._main_nb)
        self._main_nb.add(self._tab_diag, text="Diagnostics")
        self._diag_text = tk.Text(self._tab_diag, wrap="word", state="disabled")
        _scroll = ttk.Scrollbar(self._tab_diag, orient="vertical", command=self._diag_text.yview)
        self._diag_text.configure(yscrollcommand=_scroll.set)
        self._diag_text.pack(side="left", fill="both", expand=True)
        _scroll.pack(side="right", fill="y")

        # Configure tags and close handler
        self._diag_text.tag_configure("err", foreground="#aa0000")
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        # Initialize defaults
        try:
            self._on_objective_changed()
            self._on_algo_changed()
        except Exception:
            import traceback
            self._append_diag(traceback.format_exc(), tag="err")
            raise

    def _on_objective_changed(self) -> None:
        # Update ProgramState and keep Common in sync for legacy helpers
        val = self._objective_var.get().upper()
        try:
            if val == "ENERGY":
                # Only change optimization objective; leave output as configured by user/system
                self.state.scheduling.set(self.state.scheduling.State.energy)
                Common.scheduling_mode = Common.ENERGY_MODE
            else:
                self.state.scheduling.set(self.state.scheduling.State.makespan)
                Common.scheduling_mode = Common.MAKESPAN_MODE
        except Exception:
            # If state not available, best-effort Common fallback
            Common.scheduling_mode = Common.ENERGY_MODE if val == "ENERGY" else Common.MAKESPAN_MODE

    def get_objective(self) -> str:
        """Return selected objective as 'ENERGY' or 'MAKESPAN'."""
        return self._objective_var.get()

    # --- Algorithm params dynamic form ---
    def _on_algo_changed(self, _event=None) -> None:
        # Clear previous controls
        for child in self._params_area.winfo_children():
            child.destroy()
        self._param_controls.clear()

        display = self._algo_var.get()
        entry = self._algo_map.get(display)
        if not entry:
            return
        _, method = entry

        # Retrieve live ParamDef list from the instance
        param_defs = method.get_parameters()
        row = 0
        # Track LIST_SINGLE groups for selection handling
        self._list_single_groups = []
        for spec in param_defs:
            ptype = spec.get_ptype()
            # Simple types
            if ptype in (ParamValueTypes.INT, ParamValueTypes.FLOAT, ParamValueTypes.BOOLEAN):
                ttk.Label(self._params_area, text=f"{spec.get_name()}:").grid(row=row, column=0, sticky="w", padx=(0, 6), pady=3)
                if ptype == ParamValueTypes.BOOLEAN:
                    var = tk.StringVar(value="true" if bool(spec.get_value()) else "false")
                    frame = ttk.Frame(self._params_area)
                    rb_true = ttk.Radiobutton(frame, text="True", value="true", variable=var)
                    rb_false = ttk.Radiobutton(frame, text="False", value="false", variable=var)
                    rb_true.pack(side="left", padx=(0, 6))
                    rb_false.pack(side="left")
                    widget = frame
                else:
                    var = tk.StringVar(value=str(spec.get_value()))
                    widget = ttk.Entry(self._params_area, textvariable=var, width=14)
                widget.grid(row=row, column=1, sticky="ew", pady=3)

                desc = spec.get_description() or ""
                bounds = []
                if spec.get_min_value() is not None:
                    bounds.append(f"min={spec.get_min_value()}")
                if spec.get_max_value() is not None:
                    bounds.append(f"max={spec.get_max_value()}")
                tip_text = desc
                if bounds:
                    tip_text = f"{desc} (" + ", ".join(bounds) + ")"
                tooltip.attach(widget, tip_text)

                self._param_controls[spec.get_name()] = {"var": var, "widget": widget, "spec": spec}
                row += 1
            elif ptype == ParamValueTypes.LIST_SINGLE:
                # Group label
                ttk.Label(self._params_area, text=f"{spec.get_name()}:").grid(row=row, column=0, sticky="w", padx=(0, 6), pady=3)
                row += 1
                sub_params = spec.get_value()  # list[ParamDef]
                group_var = tk.IntVar()
                # Initialize selection: if this is the only LIST_SINGLE, align with ProgramState stop_criterion
                try:
                    # crude default to current state index
                    group_var.set(self.state.stop_criterion.get().value)
                except Exception:
                    group_var.set(0)

                # Render each sub-parameter with a radio to select it
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

                    # Tooltip
                    desc = sub.get_description() or ""
                    bounds = []
                    if sub.get_min_value() is not None:
                        bounds.append(f"min={sub.get_min_value()}")
                    if sub.get_max_value() is not None:
                        bounds.append(f"max={sub.get_max_value()}")
                    tip_text = desc
                    if bounds:
                        tip_text = f"{desc} (" + ", ".join(bounds) + ")"
                    tooltip.attach(sw, tip_text)

                    self._param_controls[f"{spec.get_name()}::{sub.get_name()}"] = {"var": svar, "widget": sw, "spec": sub}
                    sub_widgets.append(sw)
                    row += 1

                # Enable only selected sub-widget
                def _apply_group_state(*_args):
                    sel = group_var.get()
                    for idx, w in enumerate(sub_widgets):
                        try:
                            state = "normal" if idx == sel else "disabled"
                            # Frame containing radios vs Entry
                            if isinstance(w, ttk.Frame):
                                for child in w.winfo_children():
                                    child.configure(state=state)
                            else:
                                w.configure(state=state)
                        except Exception:
                            pass
                group_var.trace_add("write", lambda *_: _apply_group_state())
                _apply_group_state()

                # Keep for later to update ProgramState on Start
                self._list_single_groups.append({"spec": spec, "var": group_var, "widgets": sub_widgets})

        self._params_area.columnconfigure(1, weight=1)
        # Refresh description when algorithm changes
        _refresh_description_for(self)

    def _apply_parameters_to_method(self, method: BaseMethod) -> None:
        """Read widgets and set values on the method's ParamDef instances."""
        for key, ctrl in self._param_controls.items():
            spec: ParamDef = ctrl["spec"]
            var = ctrl["var"]
            val = var.get()
            try:
                spec.set_value(val)
            except Exception as e:
                self._append_diag(f"[WARN] Invalid value for '{key}': {e}\n", tag="err")

        # If method uses a LIST_SINGLE group (e.g., stop criterion), update state to chosen index
        try:
            if hasattr(self, "_list_single_groups") and self._list_single_groups:
                # For now assume single relevant group controls global stop_criterion
                sel = self._list_single_groups[0]["var"].get()
                self.state.stop_criterion.set(sel)
        except Exception:
            pass

        # Sync commonly cached fields used by evolutionary methods
        try:
            # Many methods cache values derived from PARAM_DEFS during __init__
            # Refresh them here after we've set new values from the UI.
            params = getattr(method, 'PARAM_DEFS', None)
            if isinstance(params, list) and len(params) >= 2:
                # Population size
                if hasattr(method, '_pop_size'):
                    try:
                        method._pop_size = params[0].get_value()
                    except Exception:
                        pass
                # Stop criteria-related cached fields
                if hasattr(method, '_stop_criteria') or hasattr(method, '_iterations') or hasattr(method, '_sched_value'):
                    try:
                        stop_criteria = params[1].get_value()  # list of ParamDef
                        if hasattr(method, '_stop_criteria'):
                            method._stop_criteria = stop_criteria
                        # Index 0: iterations, Index 1: target sched value
                        if hasattr(method, '_iterations') and len(stop_criteria) > 0:
                            method._iterations = stop_criteria[0].get_value()
                        if hasattr(method, '_sched_value') and len(stop_criteria) > 1:
                            method._sched_value = stop_criteria[1].get_value()
                    except Exception:
                        pass
        except Exception:
            pass
    

    def _on_close(self) -> None:
        self.destroy()

    # --- Actions ---
    def _on_start_clicked(self) -> None:
        # Switch to Diagnostics tab so user sees output
        try:
            self._main_nb.select(self._tab_diag)
        except Exception:
            pass

        display = self._algo_var.get()
        entry = self._algo_map.get(display)
        if not entry:
            self.log("[ERROR] No algorithm selected.")
            return

        # Gather parameter values and run
        obj = self.get_objective()
        self.log(f"\n>>> Starting '{display}' with objective={obj}")
        try:
            Common.prepare_results_directory()
        except Exception as e:
            self.log(f"[WARN] Could not prepare results directory: {e}")

        try:
            _, method = entry
            self._apply_parameters_to_method(method)
            method.run()
            # Render linear plots in tabs
            self._render_plots(method)
        except Exception:
            import traceback
            self.log("[ERROR] Run failed:")
            self._append_diag(trackbar_format := traceback.format_exc(), tag="err")


    # --- Diagnostics logging ---
    def _append_diag(self, s: str, tag: str | None = None) -> None:
        if not s:
            return
        def append():
            try:
                self._diag_text.configure(state="normal")
                if tag:
                    self._diag_text.insert("end", s, (tag,))
                else:
                    self._diag_text.insert("end", s)
                self._diag_text.see("end")
            finally:
                self._diag_text.configure(state="disabled")
        try:
            self._diag_text.after(0, append)
        except Exception:
            pass

    # --- Plot rendering ---
    def _render_plots(self, method: BaseMethod) -> None:
        try:
            history_fn = getattr(method, 'get_history', None)
            ys_mk, ys_en = [], []
            if callable(history_fn):
                hist = history_fn()
                # Handle both legacy dict and new list[IndividualFitness]
                if isinstance(hist, dict):
                    ys_mk = list(hist.get('makespan', []))
                    ys_en = list(hist.get('energy', []))
                elif isinstance(hist, list):
                    try:
                        mk_key = self.state.scheduling.State.makespan
                        en_key = self.state.scheduling.State.energy
                        ys_mk = [float(h.get_all()[mk_key]) for h in hist if h is not None]
                        ys_en = [float(h.get_all()[en_key]) for h in hist if h is not None]
                    except Exception:
                        ys_mk, ys_en = [], []

            # Clear containers
            self._clear_children(self._linear_energy)
            self._clear_children(self._linear_makespan)
            self._clear_children(self._gantt_energy)
            self._clear_children(self._gantt_makespan)

            self._draw_mpl_line_makespan(self._linear_makespan, ys_mk)
            self._draw_mpl_line_energy(self._linear_energy, ys_en)
            self._draw_mpl_gantt_makespan(self._gantt_makespan, method)
            self._draw_mpl_gantt_energy(self._gantt_energy, method)
        except Exception:
            import traceback
            self._append_diag(traceback.format_exc(), tag="err")

    def _clear_children(self, container) -> None:
        try:
            for child in container.winfo_children():
                child.destroy()
        except Exception:
            pass

    

    # --- Matplotlib-backed line charts
    def _draw_mpl_line_metric(self, frame, ys, title: str, y_label: str) -> None:
        if not ys:
            lbl = ttk.Label(frame, text="No data", foreground="#666")
            lbl.pack()
            return
        fig = Figure(figsize=(6, 3), dpi=100)
        ax = fig.add_subplot(111)
        xs = list(range(len(ys)))
        # Plot best-so-far as a step function to highlight changes
        ax.step(xs, ys, where='post', linewidth=1.5, color="#1f77b4", label="Best so far")
        # Highlight epochs where the best value improved
        change_x = []
        change_y = []
        prev = ys[0]
        for i in range(1, len(ys)):
            if ys[i] < prev:
                change_x.append(i)
                change_y.append(ys[i])
                prev = ys[i]
        if change_x:
            ax.scatter(change_x, change_y, s=18, color="#d62728", zorder=3, label="Improvement")
        ax.set_title(title)
        ax.set_xlabel("Epoch")
        ax.set_ylabel(y_label)
        # Format Y axis to plain numbers (no scientific notation)
        try:
            from matplotlib.ticker import StrMethodFormatter
            ax.ticklabel_format(style='plain', axis='y', useOffset=False)
            ax.yaxis.set_major_formatter(StrMethodFormatter('{x:,.0f}'))
        except Exception:
            pass
        ax.grid(True, alpha=0.3)
        ax.legend(loc="best")
        fig.tight_layout()
        canvas = FigureCanvasTkAgg(fig, master=frame)
        widget = canvas.get_tk_widget()
        widget.pack(fill="both", expand=True)

        def _on_resize(event=None):
            try:
                w = max(200, frame.winfo_width())
                h = max(150, frame.winfo_height())
                dpi = fig.get_dpi()
                fig.set_size_inches(w / dpi, h / dpi)
                canvas.draw_idle()
            except Exception:
                pass
        # Bind after packing so sizes are available
        frame.bind("<Configure>", lambda e: _on_resize(e))
        _on_resize()

    def _draw_mpl_line_makespan(self, frame, ys) -> None:
        self._draw_mpl_line_metric(frame, ys, title="Makespan over Epochs", y_label="Makespan")

    def _draw_mpl_line_energy(self, frame, ys) -> None:
        self._draw_mpl_line_metric(frame, ys, title="Energy over Epochs", y_label="Energy")

    def _draw_mpl_gantt_makespan(self, frame, method: BaseMethod) -> None:
        try:
            schedule = method.get_best_solution()
            if not schedule:
                ttk.Label(frame, text="No schedule to plot").pack()
                return
            etc = getattr(method, 'etc', None)
            if etc is None:
                ttk.Label(frame, text="Missing ETC data").pack()
                return
            # Compute per-machine cumulative durations for makespan
            loads = []
            for m_id, tasks in sorted(schedule.items()):
                total = 0.0
                for t in tasks:
                    total += float(etc[t][m_id])
                loads.append(total)
            makespan = max(loads) if loads else 0.0
            # Create figure
            fig = Figure(figsize=(6, 3), dpi=100)
            ax = fig.add_subplot(111)
            # Colors based on number of tasks
            try:
                import numpy as np
                from matplotlib import cm
                num_tasks = len(etc)
                colors = cm.viridis(np.linspace(0, 1, num_tasks))
            except Exception:
                colors = None

            for machine_id in sorted(schedule.keys()):
                current_time = 0.0
                for task_id in schedule[machine_id]:
                    duration = float(etc[task_id][machine_id])
                    color = None
                    if colors is not None:
                        color = colors[int(task_id) % len(colors)]
                    ax.barh(machine_id, duration, left=current_time, height=0.6, align='center',
                            color=color, edgecolor='black')
                    current_time += duration

            ax.set_yticks(sorted(schedule.keys()))
            ax.set_yticklabels([f"Machine {m}" for m in sorted(schedule.keys())])
            ax.invert_yaxis()
            ax.set_xlabel('Time')
            name = getattr(method, 'get_name', lambda: 'Method')()
            ax.set_title(f'Schedule (Gantt) - {name}')
            ax.grid(True, linestyle='--', linewidth=0.5, alpha=0.6)
            if makespan:
                ax.axvline(makespan, color='red', linestyle='--', linewidth=1.2)
                ax.text(makespan, 0.5, f'Makespan: {makespan:.2f}', rotation=90, va='bottom', ha='left',
                        color='red', fontsize=9, backgroundcolor='white')

            canvas = FigureCanvasTkAgg(fig, master=frame)
            widget = canvas.get_tk_widget()
            widget.pack(fill="both", expand=True)
            def _on_resize(event=None):
                try:
                    w = max(200, frame.winfo_width())
                    h = max(150, frame.winfo_height())
                    dpi = fig.get_dpi()
                    fig.set_size_inches(w / dpi, h / dpi)
                    canvas.draw_idle()
                except Exception:
                    pass
            frame.bind("<Configure>", lambda e: _on_resize(e))
            _on_resize()
        except Exception:
            import traceback
            self._append_diag(traceback.format_exc(), tag="err")

    def _draw_mpl_gantt_energy(self, frame, method: BaseMethod) -> None:
        try:
            schedule = method.get_best_solution()
            if not schedule:
                ttk.Label(frame, text="No schedule to plot").pack()
                return
            etc = getattr(method, 'etc', None)
            machines = getattr(method, 'machines', None)
            if etc is None or machines is None:
                ttk.Label(frame, text="Missing data for energy plot").pack()
                return
            # Compute per-machine busy energy
            busy_energies = []
            for m_id, tasks in sorted(schedule.items()):
                busy_e = 0.0
                for task_id in tasks:
                    duration = float(etc[task_id][m_id])
                    busy_e += duration * float(machines.loc[m_id, 'P_busy'])
                busy_energies.append(busy_e)
            max_busy_energy = max(busy_energies) if busy_energies else 0.0

            fig = Figure(figsize=(6, 3), dpi=100)
            ax = fig.add_subplot(111)
            try:
                import numpy as np
                from matplotlib import cm
                num_tasks = len(etc)
                colors = cm.viridis(np.linspace(0, 1, num_tasks))
            except Exception:
                colors = None

            for machine_id in sorted(schedule.keys()):
                current_energy = 0.0
                for task_id in schedule[machine_id]:
                    duration = float(etc[task_id][machine_id])
                    energy = duration * float(machines.loc[machine_id, 'P_busy'])
                    color = None
                    if colors is not None:
                        color = colors[int(task_id) % len(colors)]
                    ax.barh(machine_id, energy, left=current_energy, height=0.6, align='center',
                            color=color, edgecolor='black')
                    current_energy += energy

            ax.set_yticks(sorted(schedule.keys()))
            ax.set_yticklabels([f"Machine {m}" for m in sorted(schedule.keys())])
            ax.invert_yaxis()
            ax.set_xlabel('Energy')
            name = getattr(method, 'get_name', lambda: 'Method')()
            ax.set_title(f'Schedule (Energy Gantt) - {name}')
            ax.grid(True, linestyle='--', linewidth=0.5, alpha=0.6)
            if max_busy_energy:
                ax.axvline(max_busy_energy, color='red', linestyle='--', linewidth=1.2)
                ax.text(max_busy_energy, 0.5, f'Max busy energy: {max_busy_energy:.2f}', rotation=90, va='bottom', ha='left',
                        color='red', fontsize=9, backgroundcolor='white')

            canvas = FigureCanvasTkAgg(fig, master=frame)
            widget = canvas.get_tk_widget()
            widget.pack(fill="both", expand=True)
            def _on_resize(event=None):
                try:
                    w = max(200, frame.winfo_width())
                    h = max(150, frame.winfo_height())
                    dpi = fig.get_dpi()
                    fig.set_size_inches(w / dpi, h / dpi)
                    canvas.draw_idle()
                except Exception:
                    pass
            frame.bind("<Configure>", lambda e: _on_resize(e))
            _on_resize()
        except Exception:
            import traceback
            self._append_diag(traceback.format_exc(), tag="err")


def run() -> None:
    # Development convenience: basic self-host without Main
    from scheduler.MethodCache import MethodCache
    from scheduler.Logger import Logger
    from scheduler.Registry import MethodRegistry
    from lang.Lang import T
    from scheduler.ProgramState import ProgramState

    state = ProgramState()
    t = T(state)
    logger = Logger(state, print)
    cache = MethodCache()
    methods: Dict[str, BaseMethod] = {}
    for name, cls in MethodRegistry.get_registry().items():
        try:
            methods[name] = cls(state, logger, t, cache)
        except Exception:
            continue
    app = GUI(state, t, methods)
    app.mainloop()


if __name__ == "__main__":
    run()
