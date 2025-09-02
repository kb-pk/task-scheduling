import tkinter as tk
from tkinter import ttk
from typing import Optional
import sys
import io

from .method_loader import method_name_map
from . import tooltip
from .description_loader import get_description
from scheduler.Parametrs import get_method_param_defs, get_or_set_method
from scheduler.methods.BaseMethod import Mode
import scheduler.Common as Common


# Helper at module scope to update description text safely
def _refresh_description_for(app) -> None:
    try:
        name = app._algo_var.get()
        lang = app._desc_lang.get()
        text = get_description(name, lang) or "(no description)"
        app._desc_text.configure(state="normal")
        app._desc_text.delete("1.0", "end")
        app._desc_text.insert("1.0", text)
        app._desc_text.configure(state="disabled")
    except Exception:
        # Silently ignore if being called during teardown/init
        pass


class SchedulerApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Task Scheduling")
        try:
            self.state("zoomed")
        except Exception:
            sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
            self.geometry(f"{sw}x{sh}+0+0")

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

    def _build_sidebar(self) -> None:
        # Section: Algorithm selection
        section = ttk.LabelFrame(self.sidebar, text="Parameters")
        section.grid(row=0, column=0, sticky="nsew")

        # Algorithm dropdown
        ttk.Label(section, text="Algorithm:").grid(row=0, column=0, sticky="w", padx=(10, 6), pady=(10, 6))

        self._algo_var = tk.StringVar()
        self._algo_map = method_name_map()  # {display: module_qualname}

        values = list(self._algo_map.keys()) if self._algo_map else ["<no methods found>"]
        self._algo_combo = ttk.Combobox(section, textvariable=self._algo_var, state="readonly", values=values)
        if values:
            self._algo_combo.current(0)
        self._algo_combo.grid(row=0, column=1, sticky="ew", padx=(0, 10), pady=(10, 6))
        self._algo_combo.bind("<<ComboboxSelected>>", self._on_algo_changed)
        section.columnconfigure(1, weight=1)

        # Optimization objective
        ttk.Label(section, text="Objective:").grid(row=1, column=0, sticky="w", padx=(10, 6))
        self._objective_var = tk.StringVar(value="MAKESPAN")
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

        # Description header with language toggle
        hdr = ttk.Frame(section)
        hdr.grid(row=3, column=0, columnspan=2, sticky="ew", padx=(10, 10))
        ttk.Label(hdr, text="Description:").grid(row=0, column=0, sticky="w")
        self._desc_lang = tk.StringVar(value="en")
        # Use a lambda to defer attribute lookup until click-time
        self._desc_toggle = ttk.Button(hdr, text="EN", width=6, command=lambda: self._toggle_desc_lang())
        self._desc_toggle.grid(row=0, column=1, sticky="e")
        hdr.columnconfigure(0, weight=1)

        # Description text area with scrollbar
        self._desc_text = tk.Text(section, wrap="word", height=10, state="disabled")
        self._desc_text.grid(row=4, column=0, columnspan=2, sticky="nsew", padx=(10, 10), pady=(4, 10))

        # Allow the description area to grow within the section
        section.rowconfigure(4, weight=1)

        # Bottom action bar with Start button (fixed row at bottom)
        actions = ttk.Frame(section)
        actions.grid(row=5, column=0, columnspan=2, sticky="ew", padx=(10, 10), pady=(0, 6))
        self._start_btn = ttk.Button(actions, text="Start", command=self._on_start_clicked)
        self._start_btn.pack(side="left")
        section.rowconfigure(5, weight=0)

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
        ttk.Label(self._gantt_energy, text="Energy Gantt plot area").pack(padx=10, pady=10)
        ttk.Label(self._gantt_makespan, text="Makespan Gantt plot area").pack(padx=10, pady=10)

        # Linear tab with nested Energy/Makespan tabs
        self._tab_linear = ttk.Frame(self._main_nb)
        self._main_nb.add(self._tab_linear, text="Linear")
        self._nb_linear = ttk.Notebook(self._tab_linear)
        self._nb_linear.pack(fill="both", expand=True)
        self._linear_energy = ttk.Frame(self._nb_linear)
        self._linear_makespan = ttk.Frame(self._nb_linear)
        self._nb_linear.add(self._linear_energy, text="Energy")
        self._nb_linear.add(self._linear_makespan, text="Makespan")
        ttk.Label(self._linear_energy, text="Energy linear plot area").pack(padx=10, pady=10)
        ttk.Label(self._linear_makespan, text="Makespan linear plot area").pack(padx=10, pady=10)

        # Diagnostics tab - will capture stdout/stderr (redirect enabled after init)
        self._tab_diag = ttk.Frame(self._main_nb)
        self._main_nb.add(self._tab_diag, text="Diagnostics")
        self._diag_text = tk.Text(self._tab_diag, wrap="word", state="disabled")
        _scroll = ttk.Scrollbar(self._tab_diag, orient="vertical", command=self._diag_text.yview)
        self._diag_text.configure(yscrollcommand=_scroll.set)
        self._diag_text.pack(side="left", fill="both", expand=True)
        _scroll.pack(side="right", fill="y")

        # Prepare diagnostics redirection but enable it after UI is ready
        self._orig_stdout = sys.stdout
        self._orig_stderr = sys.stderr
        self._diag_text.tag_configure("err", foreground="#aa0000")
        # Restore streams on close
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        # Initialize defaults
        try:
            self._on_objective_changed()
            self._on_algo_changed()
        except Exception:
            import traceback
            traceback.print_exc(file=self._orig_stderr)
            raise
        # Enable console redirection once UI and mainloop are ready
        self.after(0, self._enable_diagnostics_redirect)

    def _on_objective_changed(self) -> None:
        # Save both string selection and update Common.scheduling_mode (0/1)
        val = self._objective_var.get()
        if val == "ENERGY":
            Common.scheduling_mode = Common.ENERGY_MODE
        else:
            Common.scheduling_mode = Common.MAKESPAN_MODE

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
        method_cls = self._algo_map.get(display)
        if not method_cls:
            return

        param_defs = get_method_param_defs(method_cls)  # list[ParamDef]
        # Build rows: label + input per param
        for r, spec in enumerate(param_defs):
            ttk.Label(self._params_area, text=f"{spec.name}:").grid(row=r, column=0, sticky="w", padx=(0, 6), pady=3)

            # Choose widget based on type
            if spec.ptype == "bool":
                var = tk.BooleanVar(value=bool(spec.default))
                widget = ttk.Checkbutton(self._params_area, variable=var)
            else:
                # int/float as Entry; value kept as string
                var = tk.StringVar(value=str(spec.default))
                widget = ttk.Entry(self._params_area, textvariable=var, width=14)
            widget.grid(row=r, column=1, sticky="ew", pady=3)

            # Tooltip with description and bounds
            desc = spec.description or ""
            bounds = []
            if spec.min_value is not None:
                bounds.append(f"min={spec.min_value}")
            if spec.max_value is not None:
                bounds.append(f"max={spec.max_value}")
            tip_text = desc
            if bounds:
                tip_text = f"{desc} (" + ", ".join(bounds) + ")"
            tooltip.attach(widget, tip_text)

            self._param_controls[spec.name] = {"var": var, "widget": widget, "spec": spec}

        self._params_area.columnconfigure(1, weight=1)
        # Refresh description when algorithm changes
        _refresh_description_for(self)

    def get_parameters(self) -> list:
        """Return current parameter values in the order defined by PARAM_DEFS."""
        display = self._algo_var.get()
        method_cls = self._algo_map.get(display)
        if not method_cls:
            return []
        order = get_method_param_defs(method_cls)
        values = []
        for spec in order:
            ctrl = self._param_controls.get(spec.name)
            if not ctrl:
                values.append(spec.default)
                continue
            var = ctrl["var"]
            v = var.get()
            values.append(v)
        return values

    

    def _on_close(self) -> None:
        # Restore std streams then destroy window
        try:
            sys.stdout = self._orig_stdout
            sys.stderr = self._orig_stderr
        except Exception:
            pass
        self.destroy()

    def _enable_diagnostics_redirect(self) -> None:
        try:
            sys.stdout = _TextRedirect(self._diag_text)
            sys.stderr = _TextRedirect(self._diag_text, tag="err")
        except Exception:
            # If widget is gone, keep originals
            pass

    # --- Description language toggle ---
    def _toggle_desc_lang(self) -> None:
        cur = self._desc_lang.get().lower()
        nxt = "pl" if cur == "en" else "en"
        self._desc_lang.set(nxt)
        self._desc_toggle.configure(text=nxt.upper())
        _refresh_description_for(self)

    # --- Actions ---
    def _on_start_clicked(self) -> None:
        # Switch to Diagnostics tab so user sees output
        try:
            self._main_nb.select(self._tab_diag)
        except Exception:
            pass

        display = self._algo_var.get()
        method_cls = self._algo_map.get(display)
        if not method_cls:
            print("[ERROR] No algorithm selected.")
            return

        # Gather parameter values and run
        values = self.get_parameters()
        obj = self.get_objective()
        print(f"\n>>> Starting '{display}' with objective={obj} and params={values}")
        try:
            Common.prepare_results_directory()
        except Exception as e:
            print(f"[WARN] Could not prepare results directory: {e}")

        try:
            method = get_or_set_method(method_cls, values)
            method.run()
            method.print_schedule()
        except Exception as e:
            import traceback
            print("[ERROR] Run failed:")
            traceback.print_exc()


class _TextRedirect(io.TextIOBase):
    def __init__(self, text: tk.Text, tag: str | None = None):
        super().__init__()
        self.text = text
        self.tag = tag

    def writable(self) -> bool:
        return True

    def write(self, s: str) -> int:
        if not s:
            return 0
        # Ensure UI update happens on main thread
        def append():
            try:
                self.text.configure(state="normal")
                if self.tag:
                    self.text.insert("end", s, (self.tag,))
                else:
                    self.text.insert("end", s)
                self.text.see("end")
            finally:
                self.text.configure(state="disabled")

        try:
            self.text.after(0, append)
        except Exception:
            # Fallback if widget destroyed
            pass
        return len(s)


def run() -> None:
    app = SchedulerApp()
    app.mainloop()


if __name__ == "__main__":
    run()
